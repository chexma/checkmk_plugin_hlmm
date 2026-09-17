#!/usr/bin/env python3

import json

from cmk.server_side_calls.v1 import SpecialAgentCommand, SpecialAgentConfig, noop_parser


def _agent_arguments(params, host_config):
    args = [
        "--url",
        params["server_url"],
        "--username",
        params["username"],
    ]

    if not params.get("verify_ssl", True):
        args.append("--no-verify-ssl")

    # Each host_service_mappings entry is {"hosts": ("patterns", [regex, ...])
    # or ("all", None), "service_patterns": [regex, ...]}. Serialized as one
    # JSON object per --mapping flag so agent_hlmm can scope each entry's
    # service patterns to only the hosts that entry's host patterns matched.
    for mapping in params.get("host_service_mappings", []):
        host_mode, host_value = mapping.get("hosts", ("patterns", []))
        payload = {"service_patterns": mapping.get("service_patterns", [])}
        if host_mode == "all":
            payload["all_hosts"] = True
        else:
            payload["all_hosts"] = False
            payload["host_patterns"] = host_value or []
        args.extend(["--mapping", json.dumps(payload, separators=(",", ":"))])

    # Note: "" (no prefix) is a valid, intentional value -- must not be
    # treated as falsy/absent here.
    if "service_prefix" in params:
        args.extend(["--service-prefix", params["service_prefix"]])

    if "downtime_handling" in params:
        args.extend(["--downtime-handling", params["downtime_handling"]])

    if "ack_handling" in params:
        args.extend(["--ack-handling", params["ack_handling"]])

    staleness_levels = params.get("staleness_levels")
    if staleness_levels and staleness_levels[0] == "fixed":
        warn, crit = staleness_levels[1]
        args.extend(["--staleness-warn", str(int(warn)), "--staleness-crit", str(int(crit))])

    if params.get("include_host_status"):
        args.append("--include-host-status")

    if params.get("debug"):
        args.append("--debug")

    args.extend(["--password-ref", params["password"]])

    yield SpecialAgentCommand(command_arguments=args)


special_agent_hlmm = SpecialAgentConfig(
    name="hlmm",
    parameter_parser=noop_parser,
    commands_function=_agent_arguments,
)
