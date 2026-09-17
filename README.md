# HLMM (HL Monitoring Module)

A [Checkmk](https://checkmk.com/) special agent plugin that pulls
service and host monitoring status from the external monitoring system
[HLMM](https://monitoring-module.com/de/produkte/monitoring-module/) via its REST API and attaches it as Checkmk services with the piggyback mechanism.

## How it works

Checkmk special agent rules run against a single host, but a HLMON query
can resolve many hosts at once. HLMM bridges that gap with Checkmk's
**piggyback** mechanism: it is configured once, on a single collector
host, queries HLMON, and emits one piggyback block per matched Checkmk
host.

```
Setup rule (Host / service pattern mappings, credentials, ...)
        │
        ▼
Special agent (runs on the "collector" host)
        │  queries the HLMON REST API
        ▼
   <<<hlmm_status>>>                       → on the collector host itself
   <<<<target-host>>>> ... <<<<>>>>        → piggybacked, one block per resolved host
       <<<hlmm_services:sep(0)>>>
       <<<hlmm_host_status:sep(0)>>>       → only if enabled
        │
        ▼
Checks run on each piggybacked Checkmk host
```

Hosts are matched by HLMON's `displayName` (the human-readable name that
lines up with Checkmk hostnames) — never HLMON's internal `name`/`hostName`
identifiers, which are opaque IDs like `hlmon_host_000153`.

## Checks provided

| Check | Runs on | Service name |
|---|---|---|
| `HLMM Service Status` | each piggybacked target host | `HLMM {displayName}` (configurable prefix) |
| `HLMM Host Status` *(optional, on by default)* | each piggybacked target host | `HLMM Host Status` |
| `HLMM Query Status` | the collector host | `HLMM Query Status` |

- **`HLMM Service Status`** — one service per matched HLMON service. Maps
  HLMON's `OK`/`WARNING`/`CRITICAL`/`UNKNOWN` to Checkmk states, and shows
  downtime/acknowledgement, check age, time in current state, and
  (when present) originating source, customer name, and linked
  ticket/comment counts. Services also carry Checkmk labels
  (`hlmm/event_source`, `hlmm/event_source_type`, `hlmm/template_ids`)
  derived from HLMON's event metadata.
- **`HLMM Host Status`** — a HLMON host's own status (e.g. reachability),
  separate from its services. HLMON hosts use a different state
  vocabulary (`UP`/`DOWN`/`UNREACHABLE`/`UNKNOWN`, with `UNREACHABLE`
  mapping to `CRIT`).
- **`HLMM Query Status`** — reports whether the special agent's own query
  against HLMON succeeded, so a broken or partial HLMON query is visible
  in one place instead of only showing up indirectly as stale checks.

See the built-in check manuals (`cmk -M hlmm_services` etc., or Checkmk's
"Manual of Checkmk" page) for the full details of each check.

## Requirements

- Checkmk **2.4.0p1** or newer.
- Network access from the collector host (where the special agent runs)
  to the HLMON REST API.
- A HLMON API user with read access to hosts and services.

## Installation

1. Download the latest `hlmm-X.Y.Z.mkp` file from this repository.
2. In Checkmk, go to **Setup > Maintenance > Extension packages** and
   upload it (or use `mkp install hlmm-X.Y.Z.mkp` on the server as the
   site user).
3. Create a rule under **Setup > Agents > Other integrations >
   HLMM (HL Monitoring Module)**, assigned to a single "collector" host.
4. Run service discovery on the collector host and on the Checkmk hosts
   you expect HLMON data to land on.

## Configuration

The special agent rule configures:

- **HLMON server URL, username, password/API token** (HTTP Basic Auth;
  the password is stored via Checkmk's password store).
- **Verify SSL certificate** — disable only for self-signed certificates.
- **Host / service pattern mappings** — a list of entries, each pairing:
  - **Hosts to import**: regular expressions matched against each HLMON
    host's `displayName`, or "All hosts" to skip host filtering entirely.
  - **Service name patterns**: regular expressions matched against each
    HLMON service's `displayName`, applied only to hosts matched by that
    same entry.

  A host matched by more than one entry gets the union of every matching
  entry's service patterns. This lets a single rule express independent
  host/service groupings, e.g.:

  | Entry | Hosts to import | Service name patterns |
  |---|---|---|
  | 1 | `server-oracle` | `orcl` |
  | 2 | `server-windows` | `disk`, `cpu` |

  Oracle hosts only ever get `orcl` services; Windows hosts only ever get
  `disk`/`cpu` services — instead of every host pattern being checked
  against every service pattern.

  > **Note:** HLMON's REST API has no server-side regex filtering (only an
  > exact-match `in` filter, used to batch-fetch services by host ID). The
  > special agent therefore always fetches the *entire* host list from
  > HLMON first (`GET /api/hosts`, unfiltered) and then applies the
  > configured regexes locally, in Python, against each host's
  > `displayName`. Narrower host patterns don't reduce the size of that
  > initial `/hosts` request — only how many of the returned hosts end up
  > matched.

- **Service name prefix** — prepended to each imported service's name
  (default `HLMM`), e.g. to tell services from different rules apart.
- **Effect of HLMON downtime / acknowledgement** on the Checkmk state —
  force to `OK`, or keep HLMON's reported state (downtime/acknowledgement
  is always shown in the check output either way).
- **Age of last HLMON check** — optional warn/critical thresholds on how
  stale a check may be.
- **Import HLMON host status** — on by default; adds the `HLMM Host
  Status` check per matched host. Uncheck if you only want the imported
  services.
- **Debug mode** — verbose request/matching diagnostics on stderr, for
  troubleshooting via `cmk -d` or a manual agent run.

Multiple host/service pattern combinations for the *same* collector host
belong in one rule (add more mapping entries), not several rules — Checkmk
special agent rules use first-match-wins per host, so only one rule's
parameters take effect per collector host. Use a different collector host
(and its own rule) for a genuinely independent set of patterns.

## License

GPLv3

## Author

Andre Eckstein (Andre.Eckstein@Bechtle.com)
