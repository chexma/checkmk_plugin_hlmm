#!/usr/bin/env python3

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
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
            "plans/2026-09-16-hlmm-plugin-konzept.md for the full design."
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
                required=False,
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
                parameter_form=List(
                    title=Title("Host name patterns"),
                    help_text=Help(
                        "Regular expressions matched against each HLMON host's "
                        "displayName (its human-readable name, which is expected to "
                        "match the Checkmk hostname -- not HLMON's internal name "
                        "field). A host is resolved if it matches any of the "
                        "patterns. Example: server-oracle, server-windows"
                    ),
                    element_template=String(title=Title("Pattern (Python regex)")),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    add_element_label=Label("Add pattern"),
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
            "downtime_handling": DictElement(
                required=False,
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
                required=False,
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
                required=False,
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
            "debug": DictElement(
                required=False,
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
