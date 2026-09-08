# DTN Mission Control

This is a zero-dependency dashboard for the local ION/DTNEX testbed. Open `index.html` directly for the UI prototype, or run the small server so a collector can provide live state:

```bash
python3 dashboard/server.py
# http://127.0.0.1:8088
```

## Discovery and telemetry contract

The server deliberately separates host discovery from DTN identity. `/api/discovery` reports non-invasive LAN neighbor observations from `ip neigh`; an authenticated host agent or gateway must then publish the node identity and measurements to `state.json` (replace it atomically) or an equivalent `/api/state` provider.

Each `nodes[]` object supports `id`, `host`, `ip`, `eid`, `role` (`edge`, `gateway`, or `remote`), `status`, and `services: [[name, health_percent]]`. `links[]` contains `[source_id, target_id]`, so nodes advertised beyond the gateway appear in the same topology and route count as local nodes. `bundleGroups[]` drives the bundle-purpose panel and contains `{name, short, count, share, color}` entries; recommended names are `Administrative`, `Keepalive`, `Echo / probe`, `Retry / custody`, `CPB metadata`, and `Application payload`.

Recommended agent measurements are: ION process counts (`bpclock`, `ipnfw`, `udpclo`, `cfdpclock`, `bputa`), DTNEX heartbeat age, ingress/egress bundle counters, queue depth, last-seen peer, contact-plan freshness, CPB size/timestamp, and route advertisement age. Do not treat an IP or an open UDP/4556 port as proof of a DTN node; bind advertisements to an authenticated node ID/EID and include a `source` plus `observedAt` timestamp.

The repository includes a live SSH collector path. Keep its node map outside the repository with `DTN_DASHBOARD_NODES=/path/to/private-node-map.json`; each entry supplies a generic dashboard ID/label and an SSH alias. The collector polls the six critical daemon classes and emits fresh `mode: "live"` state. Bundle classification still requires a bundle-aware agent or gateway feed.
