#!/usr/bin/env python3

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

    # host_patterns is a CascadingSingleChoice: ("patterns", [regex, ...]) or
    # ("all", None) for no filtering at all.
    host_mode, host_value = params.get("host_patterns", ("patterns", []))
    if host_mode == "all":
        args.append("--all-hosts")
    else:
        for pattern in host_value or []:
            args.extend(["--host-pattern", pattern])

    for pattern in params.get("service_patterns", []):
        args.extend(["--service-pattern", pattern])

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

    if params.get("debug"):
        args.append("--debug")

    args.extend(["--password-ref", params["password"]])

    yield SpecialAgentCommand(command_arguments=args)


special_agent_hlmm = SpecialAgentConfig(
    name="hlmm",
    parameter_parser=noop_parser,
    commands_function=_agent_arguments,
)
