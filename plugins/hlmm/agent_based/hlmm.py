#!/usr/bin/env python3
"""Check plugins for HLMON service status imported via agent_hlmm.

See plans/2026-09-16-hlmm-plugin-konzept.md and
plans/2026-09-16-hlmm-plugin-plan.md (Tasks 5-6) for the design this
implements. The hlmm_services section is piggybacked onto the CheckMK host
that shares its name with the matched HLMON host's displayName; hlmm_status
lives on the collector host that runs the special agent.
"""

import json
from datetime import datetime

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Result,
    Service,
    State,
    check_levels,
    render,
)

_STATE_MAP = {
    "OK": State.OK,
    "WARNING": State.WARN,
    "CRITICAL": State.CRIT,
    "UNKNOWN": State.UNKNOWN,
}

_DEFAULT_CONFIG = {
    "downtime_handling": "ok",
    "ack_handling": "ok",
    "staleness_warn": None,
    "staleness_crit": None,
}


def _parse_json_section(string_table):
    if not string_table or not string_table[0]:
        return None
    try:
        return json.loads(string_table[0][0])
    except (json.JSONDecodeError, IndexError):
        return None


def _assign_items(services):
    """Assign a unique CheckMK item name to every service.

    Two services on the same host can share a displayName; the second (and
    further) occurrence gets its HLMON service id appended so discovery
    doesn't silently drop or merge them (see the concept doc's "open
    questions" section).
    """
    seen = {}
    for svc in services:
        base = svc.get("displayName") or f"service-{svc.get('id')}"
        seen[base] = seen.get(base, 0) + 1
        svc["_item"] = base if seen[base] == 1 else f"{base} ({svc['id']})"
    return services


def parse_hlmm_services(string_table):
    """Parse the {"config": {...}, "services": [...]} payload from agent_hlmm.

    The config is embedded in the section itself (not a separate CheckMK
    check-parameter ruleset) because downtime/ack handling and staleness
    thresholds are special-agent settings, not per-service check parameters
    -- see build_check_config() in agent_hlmm.
    """
    raw = _parse_json_section(string_table)
    if raw is None:
        return None
    config = {**_DEFAULT_CONFIG, **(raw.get("config") or {})}
    services = _assign_items(list(raw.get("services") or []))
    return {"config": config, "services": services}


def discover_hlmm_services(section):
    if not section:
        return
    for svc in section["services"]:
        yield Service(item=svc["_item"])


def _find_service(section, item):
    return next((s for s in section["services"] if s["_item"] == item), None)


def _check_staleness(timestamp, config):
    """Report the age of the last HLMON check for this service.

    Always shown (even when fresh/OK) so a stopped HLMON feed is visible
    per-service, not just via the collector-wide hlmm_status check. Levels
    are only applied when both staleness_warn and staleness_crit are set;
    otherwise the age is shown without escalating the state.
    """
    if not timestamp:
        yield Result(state=State.OK, summary="Letzter Check: unbekannt")
        return

    try:
        checked_at = datetime.fromisoformat(timestamp)
    except ValueError:
        yield Result(state=State.OK, summary=f"Letzter Check: {timestamp} (Format unbekannt)")
        return

    now = datetime.now(checked_at.tzinfo) if checked_at.tzinfo else datetime.now()
    delta = max((now - checked_at).total_seconds(), 0.0)

    warn = config.get("staleness_warn")
    crit = config.get("staleness_crit")
    if warn is None or crit is None:
        yield Result(state=State.OK, summary=f"Letzter Check vor {render.timespan(delta)}")
        return

    yield from check_levels(
        delta,
        levels_upper=("fixed", (warn, crit)),
        render_func=render.timespan,
        label="Letzter Check vor",
    )


def check_hlmm_services(item, section):
    if not section:
        yield Result(state=State.UNKNOWN, summary="Keine Daten vom Special Agent erhalten")
        return

    entry = _find_service(section, item)
    if entry is None:
        yield Result(state=State.UNKNOWN, summary="Von HLMON nicht mehr gemeldet")
        return

    config = section["config"]
    state = _STATE_MAP.get(entry.get("lastState"), State.UNKNOWN)
    notes = []

    if entry.get("inDowntime"):
        notes.append("HLMON: In Downtime")
        if config.get("downtime_handling", "ok") == "ok":
            state = State.OK
    if entry.get("lastProblemAcknowledged"):
        notes.append("HLMON: Acknowledged")
        if config.get("ack_handling", "ok") == "ok":
            state = State.OK

    summary = entry.get("lastOutput") or "(keine Ausgabe)"
    if notes:
        summary += " [" + ", ".join(notes) + "]"

    yield Result(state=state, summary=summary, details=entry.get("lastLongOutput") or None)
    yield from _check_staleness(entry.get("lastEventTimestamp"), config)


agent_section_hlmm_services = AgentSection(
    name="hlmm_services",
    parse_function=parse_hlmm_services,
)

check_plugin_hlmm_services = CheckPlugin(
    name="hlmm_services",
    service_name="HLMM %s",
    discovery_function=discover_hlmm_services,
    check_function=check_hlmm_services,
)


def parse_hlmm_status(string_table):
    return _parse_json_section(string_table) or {}


def discover_hlmm_status(section):
    if section:
        yield Service()


def check_hlmm_status(section):
    """Surface whether the special agent's HLMON query itself succeeded.

    Lives on the collector host (not piggybacked) -- see the concept doc,
    section 7.2: a broken/partial HLMON query needs to be visible somewhere
    even if it doesn't affect any single hlmm_services check directly.
    """
    if not section:
        yield Result(state=State.UNKNOWN, summary="Keine Statusdaten vom Special Agent erhalten")
        return

    errors = section.get("errors", [])
    hosts_matched = section.get("hosts_matched", 0)
    services_matched = section.get("services_matched", 0)
    duration = section.get("duration_seconds")

    if errors and hosts_matched == 0 and services_matched == 0:
        state = State.CRIT
        summary = f"HLMON-Abfrage fehlgeschlagen ({len(errors)} Fehler)"
    elif errors:
        state = State.WARN
        summary = f"HLMON-Abfrage teilweise fehlgeschlagen ({len(errors)} Fehler)"
    else:
        state = State.OK
        summary = f"{hosts_matched} Hosts, {services_matched} Services abgeglichen"

    if duration is not None:
        summary += f", Laufzeit {duration:.1f}s"

    details = "\n".join(f"{e.get('stage')}: {e.get('detail')}" for e in errors) or None
    yield Result(state=state, summary=summary, details=details)


agent_section_hlmm_status = AgentSection(
    name="hlmm_status",
    parse_function=parse_hlmm_status,
)

check_plugin_hlmm_status = CheckPlugin(
    name="hlmm_status",
    service_name="HLMM Query Status",
    discovery_function=discover_hlmm_status,
    check_function=check_hlmm_status,
)
