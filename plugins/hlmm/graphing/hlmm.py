#!/usr/bin/env python3

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import Color, DecimalNotation, Metric, TimeNotation, Unit

metric_hlmm_status_hosts_matched = Metric(
    name="hlmm_status_hosts_matched",
    title=Title("HLMON hosts matched"),
    unit=Unit(DecimalNotation("")),
    color=Color.BLUE,
)

metric_hlmm_status_services_matched = Metric(
    name="hlmm_status_services_matched",
    title=Title("HLMON services matched"),
    unit=Unit(DecimalNotation("")),
    color=Color.GREEN,
)

metric_hlmm_status_duration = Metric(
    name="hlmm_status_duration",
    title=Title("HLMON query duration"),
    unit=Unit(TimeNotation()),
    color=Color.ORANGE,
)

graph_hlmm_status_matched = Graph(
    name="hlmm_status_matched",
    title=Title("HLMM Query Status: matched hosts/services"),
    simple_lines=["hlmm_status_hosts_matched", "hlmm_status_services_matched"],
)
