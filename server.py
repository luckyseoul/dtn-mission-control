#!/usr/bin/env python3
"""Small zero-dependency server for the DTN Mission Control UI.

The UI works as a static prototype, while this server provides the seam for
real collectors. An agent or gateway can atomically replace state.json, or a
future collector can publish the same schema to /api/state.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json, os, subprocess, time

ROOT = Path(__file__).resolve().parent
STATE_FILE = Path(os.environ.get("DTN_DASHBOARD_STATE", ROOT / "state.json"))

def read_state():
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
                subprocess.check_output(["ping", "-c", "1", "-W", "1", node["ip"]], stderr=subprocess.STDOUT, text=True, timeout=3)
                self.send_json({"ok": True, "message": f"Host {node['ip']} responded to ICMP."})
            except (OSError, subprocess.SubprocessError):
                self.send_json({"ok": False, "message": f"Host {node['ip']} did not respond to ICMP."})
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
