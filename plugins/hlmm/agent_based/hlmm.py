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
    Metric,
    Result,
    Service,
    ServiceLabel,
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

# HLMON hosts use a *different* lastState vocabulary than services
# (up/down/unreachable/unknown, per the API reference's /hosts filter docs
# and the "UP" value in the real example host payload) -- do not reuse
# _STATE_MAP for hlmm_host_status, "UP" would map to UNKNOWN.
_HOST_STATE_MAP = {
    "UP": State.OK,
    "DOWN": State.CRIT,
    "UNREACHABLE": State.CRIT,
    "UNKNOWN": State.UNKNOWN,
}

_DEFAULT_CONFIG = {
    "service_prefix": "HLMM ",
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


def _assign_items(services, prefix):
    """Assign a unique CheckMK item name to every service.

    `prefix` (the special agent's "Service name prefix" setting, possibly
    empty) is prepended to every item, separated by exactly one space that
    this function adds itself -- the separator is never taken from `prefix`
    verbatim. That's deliberate: a user-typed or GUI-saved trailing space is
    easy to lose (invisible in a text field, and some form handling strips
    trailing whitespace on save), which previously caused prefixes like
    "HLMM" to glue directly onto the service name ("HLMMmyservice") instead
    of "HLMM myservice". `prefix` is `.strip()`-ped first so a trailing (or
    leading) space the user *did* type doesn't produce a double space.
    service_name itself is just "%s" (see check_plugin_hlmm_services) since
    a CheckPlugin's service_name is a fixed string and can't read per-rule
    configuration.

    Two services on the same host can share a displayName; the second (and
    further) occurrence gets its HLMON service id appended so discovery
    doesn't silently drop or merge them (see the concept doc's "open
    questions" section).
    """
    prefix = prefix.strip()
    item_prefix = f"{prefix} " if prefix else ""

    seen = {}
    for svc in services:
        name = svc.get("displayName") or f"service-{svc.get('id')}"
        base = f"{item_prefix}{name}"
        seen[base] = seen.get(base, 0) + 1
        svc["_item"] = base if seen[base] == 1 else f"{base} ({svc['id']})"
    return services


def parse_hlmm_services(string_table):
    """Parse the {"config": {...}, "services": [...]} payload from agent_hlmm.

    The config is embedded in the section itself (not a separate CheckMK
    check-parameter ruleset) because downtime/ack handling, the service name
    prefix, and staleness thresholds are special-agent settings, not
    per-service check parameters -- see build_check_config() in agent_hlmm.
    """
    raw = _parse_json_section(string_table)
    if raw is None:
        return None
    config = {**_DEFAULT_CONFIG, **(raw.get("config") or {})}
    services = _assign_items(list(raw.get("services") or []), config["service_prefix"])
    return {"config": config, "services": services}


def _build_service_labels(svc):
    """Service labels identifying the HLMON check template, for filtering/
    grouping imported services in Checkmk. Empty/missing values are skipped
    rather than emitted as an empty-value label."""
    if event_source := svc.get("eventSource"):
        yield ServiceLabel("hlmm/event_source", str(event_source))
    if event_source_type := svc.get("eventSourceType1"):
        yield ServiceLabel("hlmm/event_source_type", str(event_source_type))
    if template_ids := svc.get("templateIds"):
        # A Service can't carry several same-named labels, so a multi-value
        # field is joined into one label rather than repeated per ID.
        yield ServiceLabel("hlmm/template_ids", ",".join(str(t) for t in template_ids))


def discover_hlmm_services(section):
    if not section:
        return
    for svc in section["services"]:
        yield Service(item=svc["_item"], labels=list(_build_service_labels(svc)))


def _find_service(section, item):
    return next((s for s in section["services"] if s["_item"] == item), None)


def _check_staleness(timestamp, config):
    """Report the age of the last HLMON check for this service.

    Only shown in the summary when it's actually a problem (WARN/CRIT); a
    fresh/OK age is still available in the details, just not cluttering the
    summary line. Levels are only applied when both staleness_warn and
    staleness_crit are set; otherwise the age is shown (details-only) without
    escalating the state.
    """
    if not timestamp:
        yield Result(state=State.OK, notice="Last check: unknown")
        return

    try:
        checked_at = datetime.fromisoformat(timestamp)
    except ValueError:
        yield Result(state=State.OK, notice=f"Last check: {timestamp} (unknown format)")
        return

    now = datetime.now(checked_at.tzinfo) if checked_at.tzinfo else datetime.now()
    delta = max((now - checked_at).total_seconds(), 0.0)

    warn = config.get("staleness_warn")
    crit = config.get("staleness_crit")
    if warn is None or crit is None:
        yield Result(state=State.OK, notice=f"Last checked {render.timespan(delta)} ago")
        return

    yield from check_levels(
        delta,
        levels_upper=("fixed", (warn, crit)),
        render_func=render.timespan,
        label="Last checked",
        notice_only=True,
    )


def _check_state_since(timestamp):
    """Report how long the entry has been in its current state.

    Distinct from _check_staleness(): `timestamp` here is lastChangeTimestamp
    (when the state last changed), not lastEventTimestamp (when it was last
    checked). Purely informational -- always `notice=` (details-only unless
    combined with a non-OK Result from elsewhere in the same check), never
    escalates the state itself; there's no threshold concept for this.
    """
    if not timestamp:
        yield Result(state=State.OK, notice="In current state since: unknown")
        return

    try:
        changed_at = datetime.fromisoformat(timestamp)
    except ValueError:
        yield Result(state=State.OK, notice=f"In current state since: {timestamp} (unknown format)")
        return

    now = datetime.now(changed_at.tzinfo) if changed_at.tzinfo else datetime.now()
    delta = max((now - changed_at).total_seconds(), 0.0)
    yield Result(state=State.OK, notice=f"In current state since {render.timespan(delta)}")


def _check_status_entry(entry, config, state_map=_STATE_MAP):
    """Shared by check_hlmm_services and check_hlmm_host_status: state
    mapping, downtime/ack override + notes, staleness, and "in current
    state since". `state_map` differs because HLMON hosts and services use
    different lastState vocabularies -- see _HOST_STATE_MAP.
    """
    state = state_map.get(entry.get("lastState"), State.UNKNOWN)
    notes = []

    if entry.get("inDowntime"):
        notes.append("HLMON: In Downtime")
        if config.get("downtime_handling", "ok") == "ok":
            state = State.OK
    if entry.get("lastProblemAcknowledged"):
        notes.append("HLMON: Acknowledged")
        if config.get("ack_handling", "ok") == "ok":
            state = State.OK

    summary = entry.get("lastOutput") or "(no output)"
    if notes:
        summary += " [" + ", ".join(notes) + "]"

    yield Result(state=state, summary=summary, details=entry.get("lastLongOutput") or None)
    yield from _check_staleness(entry.get("lastEventTimestamp"), config)
    yield from _check_state_since(entry.get("lastChangeTimestamp"))


def _service_extra_notices(entry):
    """Extra, service-only informational notices (not applicable to the
    host-status check, which has no source/customer/ticket/comment fields).
    Always notice= (details-only unless something else in the same check
    already made the service non-OK) -- these never affect the state.
    """
    if source := entry.get("source"):
        yield Result(state=State.OK, notice=f"Source: {source}")
    if customer_name := entry.get("customerName"):
        yield Result(state=State.OK, notice=f"Customer: {customer_name}")
    if (ticket_count := entry.get("ticketCount") or 0) > 0:
        yield Result(state=State.OK, notice=f"{ticket_count} linked ticket(s) in HLMON")
    if (comment_count := entry.get("commentCount") or 0) > 0:
        yield Result(state=State.OK, notice=f"{comment_count} comment(s) in HLMON")


def check_hlmm_services(item, section):
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data received from the special agent")
        return

    entry = _find_service(section, item)
    if entry is None:
        yield Result(state=State.UNKNOWN, summary="No longer reported by HLMON")
        return

    yield from _check_status_entry(entry, section["config"])
    yield from _service_extra_notices(entry)


agent_section_hlmm_services = AgentSection(
    name="hlmm_services",
    parse_function=parse_hlmm_services,
)

check_plugin_hlmm_services = CheckPlugin(
    name="hlmm_services",
    # The prefix ("HLMM " by default, configurable, can be empty) is baked
    # into the item itself by _assign_items() -- service_name can't read
    # per-rule configuration, it's a fixed template.
    service_name="%s",
    discovery_function=discover_hlmm_services,
    check_function=check_hlmm_services,
)


def parse_hlmm_host_status(string_table):
    """Parse the {"config": {...}, "host": {...}} payload from agent_hlmm.

    Only emitted (and only ever piggybacked, like hlmm_services -- never on
    the collector host) when the special agent's "Import HLMON host status"
    setting is enabled; absent otherwise, so this check simply won't be
    discovered until that's turned on and rediscovered.
    """
    raw = _parse_json_section(string_table)
    if raw is None:
        return None
    config = {**_DEFAULT_CONFIG, **(raw.get("config") or {})}
    host = raw.get("host")
    if host is None:
        return None
    return {"config": config, "host": host}


def discover_hlmm_host_status(section):
    if section:
        yield Service()


def check_hlmm_host_status(section):
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data received from the special agent")
        return
    yield from _check_status_entry(section["host"], section["config"], state_map=_HOST_STATE_MAP)


agent_section_hlmm_host_status = AgentSection(
    name="hlmm_host_status",
    parse_function=parse_hlmm_host_status,
)

check_plugin_hlmm_host_status = CheckPlugin(
    name="hlmm_host_status",
    service_name="HLMM Host Status",
    discovery_function=discover_hlmm_host_status,
    check_function=check_hlmm_host_status,
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
        yield Result(state=State.UNKNOWN, summary="No status data received from the special agent")
        return

    errors = section.get("errors", [])
    hosts_matched = section.get("hosts_matched", 0)
    services_matched = section.get("services_matched", 0)
    duration = section.get("duration_seconds")

    if errors and hosts_matched == 0 and services_matched == 0:
        state = State.CRIT
        summary = f"HLMON query failed ({len(errors)} error(s))"
    elif errors:
        state = State.WARN
        summary = f"HLMON query partially failed ({len(errors)} error(s))"
    else:
        state = State.OK
        summary = f"{hosts_matched} hosts, {services_matched} services matched"

    if duration is not None:
        summary += f", runtime {duration:.1f}s"

    details = "\n".join(f"{e.get('stage')}: {e.get('detail')}" for e in errors) or None
    yield Result(state=state, summary=summary, details=details)

    yield Metric("hlmm_status_hosts_matched", hosts_matched)
    yield Metric("hlmm_status_services_matched", services_matched)
    if duration is not None:
        yield Metric("hlmm_status_duration", duration)


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
