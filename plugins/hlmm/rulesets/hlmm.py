#!/usr/bin/env python3

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Float,
    LevelDirection,
    List,
    Password,
    SimpleLevels,
    SingleChoice,
    SingleChoiceElement,
    String,
    migrate_to_password,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _special_agent_formspec():
    return Dictionary(
        title=Title("HLMM (HL Monitoring Module)"),
        help_text=Help(
            "Connects to the HLMON REST API, resolves hosts matching the configured "
            "name patterns, and imports their services as Checkmk services on the "
            "same-named hosts (via piggyback). This rule is assigned to a single "
            "'collector' host that runs the special agent -- see "
            "plans/2026-09-16-hlmm-plugin-konzept.md for the full design.\n\n"
            "Multiple host/service pattern combinations for the SAME collector host "
            "belong in ONE rule (add several entries to 'Host name patterns' / "
            "'Service name patterns' -- matching is OR across all of them), not in "
            "several separate rules: Checkmk special agent rules use first-match-wins "
            "per host, so only one rule's parameters take effect per collector host. "
            "Use a different collector host (and its own rule) for a genuinely "
            "independent host/pattern combination; 'Service name prefix' below can then "
            "distinguish which rule a given imported service came from."
        ),
        elements={
            "server_url": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("HLMON server URL"),
                    help_text=Help("e.g. https://hlmon.example.local"),
                    custom_validate=(
                        validators.Url(
                            protocols=[validators.UrlProtocol.HTTP, validators.UrlProtocol.HTTPS]
                        ),
                    ),
                ),
            ),
            "username": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Username"),
                    help_text=Help("HLMON API username for authentication."),
                ),
            ),
            "password": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Password / API token"),
                    help_text=Help(
                        "HLMON API password or token, used as the HTTP Basic Auth password."
                    ),
                    migrate=migrate_to_password,
                ),
            ),
            "verify_ssl": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Verify SSL certificate"),
                    help_text=Help(
                        "Disable SSL verification only if the server uses a "
                        "self-signed certificate."
                    ),
                    prefill=DefaultValue(True),
                    label=Label("Verify SSL certificate"),
                ),
            ),
            "host_patterns": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Hosts to import"),
                    help_text=Help(
                        "Which HLMON hosts to resolve (matching is always against "
                        "displayName, the human-readable name expected to match the "
                        "Checkmk hostname -- not HLMON's internal name field)."
                    ),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="patterns",
                            title=Title("Match by name pattern"),
                            parameter_form=List(
                                title=Title("Host name patterns"),
                                help_text=Help(
                                    "Regular expressions matched against each HLMON "
                                    "host's displayName. A host is resolved if it "
                                    "matches any of the patterns. Example: "
                                    "server-oracle, server-windows"
                                ),
                                element_template=String(title=Title("Pattern (Python regex)")),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                                add_element_label=Label("Add pattern"),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="all",
                            title=Title("All hosts (no filtering)"),
                            parameter_form=FixedValue(
                                value=None,
                                label=Label("Every host HLMON reports is resolved"),
                            ),
                        ),
                    ],
                    prefill=DefaultValue("patterns"),
                ),
            ),
            "service_patterns": DictElement(
                required=True,
                parameter_form=List(
                    title=Title("Service name patterns"),
                    help_text=Help(
                        "Regular expressions matched against each HLMON service's "
                        "displayName. A service is imported if it matches any of the "
                        "patterns. Example: orcl"
                    ),
                    element_template=String(title=Title("Pattern (Python regex)")),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    add_element_label=Label("Add pattern"),
                ),
            ),
            "service_prefix": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Service name prefix"),
                    help_text=Help(
                        "Prepended to each imported service's displayName to form the "
                        "Checkmk service name, e.g. 'HLMM' -> 'HLMM myservice'. A single "
                        "space is added automatically between the prefix and the service "
                        "name -- do not type a trailing space yourself, it's stripped. "
                        "Leave empty for no prefix at all. Useful to tell services "
                        "imported by different special agent rules (e.g. different "
                        "host/service pattern combinations) apart."
                    ),
                    prefill=DefaultValue("HLMM"),
                ),
            ),
            "downtime_handling": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Effect of HLMON downtime on the Checkmk service state"),
                    help_text=Help(
                        "A service reported as in downtime by HLMON is always marked "
                        "as such in the check output; this only controls whether that "
                        "also forces the Checkmk state to OK."
                    ),
                    elements=[
                        SingleChoiceElement(name="ok", title=Title("Force state to OK")),
                        SingleChoiceElement(
                            name="original", title=Title("Keep HLMON's reported state")
                        ),
                    ],
                    prefill=DefaultValue("ok"),
                ),
            ),
            "ack_handling": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Effect of HLMON acknowledgement on the Checkmk service state"),
                    help_text=Help(
                        "A service acknowledged in HLMON is always marked as such in "
                        "the check output; this only controls whether that also "
                        "forces the Checkmk state to OK."
                    ),
                    elements=[
                        SingleChoiceElement(name="ok", title=Title("Force state to OK")),
                        SingleChoiceElement(
                            name="original", title=Title("Keep HLMON's reported state")
                        ),
                    ],
                    prefill=DefaultValue("ok"),
                ),
            ),
            "staleness_levels": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Age of last HLMON check"),
                    help_text=Help(
                        "Warn/critical when a service's last HLMON check is older than "
                        "this. Leave unset to only show the age without affecting the "
                        "service state."
                    ),
                    form_spec_template=Float(unit_symbol="s"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(3600.0, 7200.0)),
                ),
            ),
            "include_host_status": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Import HLMON host status"),
                    help_text=Help(
                        "Also import each matched HLMON host's own status (separate "
                        "from its services, e.g. reachability) as a 'HLMM Host Status' "
                        "check on the piggybacked target host. Off by default so "
                        "upgrading doesn't silently add a new service to every host "
                        "after the next discovery."
                    ),
                    prefill=DefaultValue(False),
                    label=Label("Import host status as its own check"),
                ),
            ),
            "debug": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Debug mode"),
                    help_text=Help(
                        "Log detailed request/matching diagnostics to stderr. Intended "
                        "for troubleshooting via 'cmk -d' or a manual agent run, not "
                        "for permanent use."
                    ),
                    prefill=DefaultValue(False),
                    label=Label("Enable debug logging"),
                ),
            ),
        },
    )


rule_spec_hlmm = SpecialAgent(
    name="hlmm",
    title=Title("HLMM (HL Monitoring Module)"),
    topic=Topic.GENERAL,
    parameter_form=_special_agent_formspec,
)
