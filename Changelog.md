# CHANGELOG

## 0.0.3 (2026-09-16)

- Fixed: `verify_ssl=False` was silently ignored on real Checkmk sites even
  with a correct ruleset (0.0.2's fix), because `HlmmClient` set
  `session.verify = False` but never passed `verify=` on the actual request
  call. `requests` only falls back to `session.verify` when the per-call
  value is `None`; since it wasn't set, `requests` substituted
  `REQUESTS_CA_BUNDLE`/`CURL_CA_BUNDLE` from the environment (every OMD site
  sets `REQUESTS_CA_BUNDLE`), and that non-`None` value then won over
  `session.verify=False` in `requests`' own merge logic — re-enabling
  certificate verification against a CA bundle that doesn't know the HLMON
  server's certificate. `verify=` is now passed explicitly on every request.
  Confirmed via a regression test that exercises real `requests` merge logic
  (not a mocked session) with `REQUESTS_CA_BUNDLE` set.

## 0.0.2 (2026-09-16)

- Fixed: unchecking "Verify SSL certificate" in the special agent rule
  (and, for the same reason, non-default choices for downtime/ack handling,
  staleness levels, or debug mode) could silently have no effect. Cause: all
  five fields were declared `required=False` on their `DictElement`, which
  in Checkmk's ruleset API is meant for optional check-parameter inheritance
  and renders an extra "enable this field" toggle in Setup separate from the
  field's own widget — easy to miss, leaving the field at its prefill
  default even after "unchecking" it. All five are now `required=True`, so
  the widget's value is always what gets saved, with no separate toggle.
  **Existing saved rules must be re-opened and re-saved in Setup** for this
  fix to take effect, since the old stored value may be missing these keys
  entirely.

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
