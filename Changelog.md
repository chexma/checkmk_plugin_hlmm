# CHANGELOG

## 0.0.11 (2026-09-17)

- **Relicensed to GPLv3.** The `hlmm_services`/`hlmm_host_status`/
  `hlmm_status` checkman pages' `license:` header is updated from GPLv2 to
  GPLv3, matching the license stated in README.md.

## 0.0.10 (2026-09-17)

- **Translated all remaining German check output to English.** The
  `HLMM Service Status`/`HLMM Host Status`/`HLMM Query Status` checks
  previously mixed English and German in their summaries/notices (e.g.
  "Im aktuellen Status seit", "Letzter Check vor", "Quelle:"/"Kunde:",
  "HLMON-Abfrage fehlgeschlagen"); all of these are now English. The
  `hlmm_host_status`/`hlmm_services` checkman pages are updated to match
  the renamed "In current state since" notice.
- Removed a dangling reference to a local, unshipped design document
  (`plans/2026-09-16-hlmm-plugin-konzept.md`) from the special agent
  ruleset's help text in Checkmk's Setup GUI — that file isn't part of
  the MKP package, so the reference was dead for anyone who only
  installed the package.
- Author metadata updated to "Andre Eckstein (Andre.Eckstein@Bechtle.com)".

## 0.0.9 (2026-09-17)

- **"Import HLMON host status" now defaults to on** for new special agent
  rules, instead of being opt-in. Existing saved rules are unaffected (they
  keep whatever value they already have stored); only newly created rules
  get the check by default. Ruleset help text and the `hlmm_host_status`
  checkman page are updated to match.
- Added a top-level `README.md` for GitHub covering the plugin's purpose,
  piggyback architecture, checks provided, installation, and the full
  ruleset configuration including 0.0.8's host/service pattern mappings.

## 0.0.8 (2026-09-17)

- **Grouped host/service pattern mappings.** The special agent ruleset's
  "Host name patterns" and "Service name patterns" fields (each a single,
  global list combined as a cross-product) are replaced by a new "Host /
  service pattern mappings" list: each entry pairs its own "Hosts to
  import" (name patterns, or "All hosts") with the service-name patterns
  that apply only to hosts matched by that entry. A host matched by more
  than one entry gets the union of every matching entry's service
  patterns. This lets one collector host cleanly express independent
  host/service pattern groups (e.g. Oracle hosts -> `orcl` patterns,
  Windows hosts -> `disk`/`cpu` patterns) in a single rule, instead of the
  old global cross-product where every host pattern was checked against
  every service pattern.
- Agent-side: `resolve_hosts()`/`filter_services()` (global pattern list)
  are replaced by `resolve_mappings()`/`filter_services_by_host()`, which
  track the service patterns that apply per resolved host id. The special
  agent CLI accordingly replaces the old `--host-pattern`/`--all-hosts`/
  `--service-pattern` flags with a repeatable `--mapping` flag carrying one
  JSON object per mapping entry (see `agent_hlmm --help`).
- No parameter migration is provided for existing saved rules using the old
  `host_patterns`/`service_patterns` keys — re-save affected rules with the
  new "Host / service pattern mappings" list after upgrading.

## 0.0.7 (2026-09-16)

Extends the plugin using previously unused fields identified from a real
captured agent run (`temp/hlm-agent.txt`).

- **New `HLMM Host Status` check.** Imports each matched HLMON host's own
  status (e.g. reachability), separate from its services, as a check on the
  piggybacked target host. Opt-in via the new special agent setting "Import
  HLMON host status" (default off, so upgrading doesn't silently add a new
  service to every already-monitored host after the next discovery). HLMON
  hosts use a different `lastState` vocabulary than services
  (`UP`/`DOWN`/`UNREACHABLE`/`UNKNOWN` instead of
  `OK`/`WARNING`/`CRITICAL`/`UNKNOWN`); `UNREACHABLE` maps to `CRIT`.
- **"Im aktuellen Status seit" (state-duration) notice**, based on HLMON's
  `lastChangeTimestamp`, shown in addition to the existing "last check ago"
  age (`lastEventTimestamp`) — for both `HLMM Service Status` and the new
  `HLMM Host Status`. Never affects the Checkmk state.
- **Service labels** derived from HLMON's `eventSource`, `eventSourceType1`,
  and `templateIds` fields (`hlmm/event_source`, `hlmm/event_source_type`,
  `hlmm/template_ids`), so imported services can be filtered/grouped by
  their underlying HLMON check template. Only emitted when the source field
  is actually present.
- **Additional `HLMM Service Status` notices**: originating `source` and
  `customerName` (always, when present), and the number of linked tickets
  and comments in HLMON (`ticketCount`/`commentCount`, only shown when
  greater than 0). Details-only, never affects the Checkmk state.

## 0.0.6 (2026-09-16)

- **Fixed: "Service name prefix" glued directly onto the service name with
  no space** (e.g. "HLMM" + "myservice" -> "HLMMmyservice" instead of
  "HLMM myservice"). The separating space used to have to be typed into the
  prefix field itself (default `"HLMM "` with a trailing space) — easy to
  lose, since trailing whitespace in a text field is invisible and can be
  silently stripped on save. `_assign_items()` in `agent_based/hlmm.py` now
  always inserts exactly one space itself between a non-empty prefix and
  the service name (after `.strip()`-ping the prefix, so a trailing space
  the user *did* type doesn't produce a double space); the ruleset/agent
  default changed from `"HLMM "` to `"HLMM"` accordingly. Existing rules
  using the old `"HLMM "` default keep working unchanged (the trailing
  space is just stripped and re-added); rules that were saved with a bare
  `"HLMM"` (no trailing space) now get the space they were always meant to.

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
