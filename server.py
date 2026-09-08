#!/usr/bin/env python3
"""Zero-dependency server and live SSH collector for DTN Mission Control."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json, os, subprocess, time

ROOT = Path(__file__).resolve().parent
STATE_FILE = Path(os.environ.get("DTN_DASHBOARD_STATE", ROOT / "state.json"))
NODE_MAP_FILE = Path(os.environ.get("DTN_DASHBOARD_NODES", "/home/nick/ion-config/dtn-dashboard-nodes.json"))
PROCESS_NAMES = ("bpclock", "ipnfw", "udpclo", "cfdpclock", "bputa", "dtnex")

def process_counts():
    result = {}
    for name in PROCESS_NAMES:
        try:
            result[name] = int(subprocess.check_output(["pgrep", "-cx", name], text=True, stderr=subprocess.DEVNULL).strip() or 0)
        except (OSError, subprocess.SubprocessError, ValueError):
            result[name] = 0
    return result

def node_map():
    try:
        value = json.loads(NODE_MAP_FILE.read_text())
        return value if isinstance(value, list) else []
    except (OSError, json.JSONDecodeError):
        return []

def collect_counts(node):
    remote = "for p in bpclock ipnfw udpclo cfdpclock bputa dtnex; do printf '%s=' \"$p\"; pgrep -cx \"$p\" 2>/dev/null || printf '0'; done"
    if node.get("ssh") == "local":
        return process_counts(), True
    try:
        output = subprocess.check_output(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4", node["ssh"], remote], text=True, stderr=subprocess.STDOUT, timeout=8)
        counts = {}
        for item in output.split():
            name, _, value = item.partition("=")
            if name in PROCESS_NAMES:
                counts[name] = int(value or 0)
        return {name: counts.get(name, 0) for name in PROCESS_NAMES}, len(counts) == len(PROCESS_NAMES)
    except (OSError, subprocess.SubprocessError, ValueError, KeyError):
        return {name: 0 for name in PROCESS_NAMES}, False

def live_state():
    configured = node_map()
    if not configured:
        return None
    nodes = []
    for item in configured:
        counts, reachable = collect_counts(item)
        services = [["bpclock", 100 if counts["bpclock"] else 0], ["ipnfw", 100 if counts["ipnfw"] else 0], ["udpclo × 3", min(100, round(counts["udpclo"] / 3 * 100))], ["cfdpclock", 100 if counts["cfdpclock"] else 0], ["bputa", 100 if counts["bputa"] else 0], ["dtnex", 100 if counts["dtnex"] else 0]]
        active = sum(1 for _, health in services if health > 0)
        status = "online" if reachable and active == len(services) else "degraded" if reachable and active else "offline"
        nodes.append({"id": item["id"], "host": item.get("label", item["id"]), "ip": item.get("displayAddress", "configured node"), "sshTarget": item.get("ssh"), "eid": item.get("eid", "DTN node"), "role": item.get("role", "edge"), "status": status, "services": services})
    ids = [node["id"] for node in nodes]
    links = [[ids[index], ids[index + 1]] for index in range(len(ids) - 1)]
    return {"mode": "live", "observedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "nodes": nodes, "links": links, "events": [{"kind": "info", "title": "Live daemon poll completed", "meta": f"{len(nodes)} configured nodes · refreshed from SSH/local process probes", "time": "just now"}], "bundleGroups": []}

def read_state():
    collected = live_state()
    if collected is not None:
        return collected
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return {"mode": "no-data", "observedAt": None, "nodes": [], "links": [], "events": []}

def discover_neighbors():
    """Return non-invasive host observations from the local neighbor table.

    DTN node identity is never inferred from an IP alone. A host becomes a
    node only after its agent/gateway advertisement is authenticated.
    """
    neighbors = []
    try:
        output = subprocess.check_output(["ip", "neigh", "show"], text=True, timeout=2)
        for line in output.splitlines():
            fields = line.split()
            if fields and fields[0].count(".") == 3 and "FAILED" not in line:
                neighbors.append({"ip": fields[0], "source": "lan-neighbor", "reachable": "REACHABLE" in line})
    except (OSError, subprocess.SubprocessError):
        pass
    return neighbors

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/state":
            self.send_json(read_state())
        elif self.path == "/api/discovery":
            self.send_json({"observedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "neighbors": discover_neighbors()})
        else:
            path = ROOT / ("index.html" if self.path in ("/", "") else self.path.lstrip("/"))
            if path.is_file() and ROOT in path.parents:
                body = path.read_bytes(); self.send_response(200); self.send_header("Content-Type", self.content_type(path)); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            else: self.send_error(404)
    def do_POST(self):
        if self.path != "/api/action":
            self.send_error(404); return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length))
            node_id, action = request.get("nodeId"), request.get("action")
        except (ValueError, json.JSONDecodeError):
            self.send_error(400, "invalid JSON"); return
        if action not in {"ping", "status", "echo", "routes"}:
            self.send_error(400, "unsupported action"); return
        node = next((item for item in read_state().get("nodes", []) if item.get("id") == node_id), None)
        if node is None:
            # The static UI's fallback nodes are intentionally not action targets.
            self.send_json({"ok": False, "message": "Node is not present in the authenticated state snapshot."}); return
        if action == "ping":
            try:
                if node.get("sshTarget") == "local":
                    subprocess.check_output(["true"], timeout=1)
                else:
                    subprocess.check_output(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4", node["sshTarget"], "true"], stderr=subprocess.STDOUT, text=True, timeout=6)
                self.send_json({"ok": True, "message": f"{node['host']} responded to the host probe."})
            except (OSError, subprocess.SubprocessError):
                self.send_json({"ok": False, "message": f"{node['host']} did not respond to the host probe."})
            return
        self.send_json({"ok": False, "message": f"{action} requires an authenticated DTN agent on {node.get('host', node_id)}; no request was sent."})
    def send_json(self, value):
        body = json.dumps(value).encode(); self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    @staticmethod
    def content_type(path):
        return {".css":"text/css", ".js":"text/javascript", ".json":"application/json"}.get(path.suffix, "text/html")
    def log_message(self, *_): pass

if __name__ == "__main__":
    port = int(os.environ.get("DTN_DASHBOARD_PORT", "8088"))
    print(f"DTN Mission Control: http://127.0.0.1:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
