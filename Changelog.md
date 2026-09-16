# CHANGELOG

## 0.0.5 (2026-09-16)

- **"All hosts" option for host selection.** "Hosts to import" in the
  special agent rule is now a choice between "Match by name pattern" (as
  before) and "All hosts (no filtering)". Implemented as an explicit mode
  (`resolve_hosts(..., match_all=True)`, agent CLI flag `--all-hosts`), not
  a documented `.*` regex trick — bypasses pattern compilation entirely, and
  any `--host-pattern` values are ignored when `--all-hosts` is set.

## 0.0.4 (2026-09-16)

Addresses the open items from `ToDO`:

- **Configurable service name prefix.** New special agent setting "Service
  name prefix" (default `"HLMM "`, can be empty for none). Since a
  `CheckPlugin`'s `service_name` is a fixed template and can't read per-rule
  configuration, the prefix now travels through the section's embedded
  `config` (like downtime/ack handling and staleness thresholds already did)
  and is baked into the item by the check plugin; `service_name` changed
  from `"HLMM %s"` to `"%s"` accordingly. Useful to tell services imported
  by different special agent rules (different host/service pattern
  combinations) apart.
- **Documented multiple-rules behavior.** Added ruleset help text explaining
  that multiple host/service pattern combinations for the *same* collector
  host belong in one rule (the pattern lists are OR-matched), not several
  separate rules — Checkmk special agent rules are first-match-wins per
  host, so only one rule's parameters would take effect. Use a separate
  collector host (with its own rule and, if useful, a distinct service
  prefix) for a genuinely independent combination.
- **"Last check ago" no longer clutters the summary when it's not a
  problem.** `HLMM Service Status`'s staleness line now uses `notice=`
  instead of `summary=` (and `check_levels(..., notice_only=True)` for the
  thresholded case), so it only appears in the summary when it's actually
  WARN/CRIT; otherwise it's still available in the details.
- **Performance data for `HLMM Query Status`.** New metrics
  `hlmm_status_hosts_matched`, `hlmm_status_services_matched`,
  `hlmm_status_duration`, plus a `graphing/hlmm.py` for readable titles and
  a combined graph — emitted whenever the special agent produced any status
  data, including the CRIT/WARN cases, so a gradually failing HLMON query
  becomes visible in a trend graph before it's a hard failure.

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
