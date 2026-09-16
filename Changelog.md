# CHANGELOG

## 0.0.1 (2026-09-16)

Initial release, packaged as `hlmm`.

- Special agent (`agent_hlmm`) that queries the HLMON REST API, resolves
  hosts via configurable name-pattern regexes (matched against HLMON's
  `displayName`), and imports matching services via Checkmk piggyback onto
  the same-named hosts.
- `HLMM Service Status` check per imported service: state mapping,
  downtime/acknowledgement visibility with configurable OK-override, and an
  age check for the last HLMON update.
- `HLMM Query Status` check on the collector host, surfacing failed or
  partial HLMON queries.
- WATO ruleset for the special agent (server URL, credentials incl. password
  store, SSL verification, host/service patterns, downtime/ack handling,
  staleness thresholds, debug mode).
- `--debug` and `--replay-dir`/`--dump-dir` support in the agent for
  development and troubleshooting without live HLMON access.

Note: this plugin was briefly built once as `hlmon` before being renamed to
`hlmm` ("HL Monitoring Module") to distinguish our package identifier from
the external HLMON system it connects to — that `hlmon` 0.0.1 MKP was never
distributed and was removed from the site again; this `hlmm` 0.0.1 is the
first real release.
