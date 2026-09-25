#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the `--stdout`, `--stdout-json` and `--stdout-csv` outputs (v4 formats)."""

from __future__ import annotations

import json

from glances.outputs.stdout_v5 import CsvRenderer, StdoutV5, parse_selection, render_json, render_plain

EXPORTS = {
    "cpu": {"total": 12.5, "user": 8.0},
    "network": [
        {"interface_name": "eth0", "bytes_recv": 100, "bytes_sent": 50},
        {"interface_name": "lo", "bytes_recv": 1, "bytes_sent": 1},
    ],
}
PKS = {"cpu": None, "network": "interface_name"}


class _Plugin:
    def __init__(self, name, export, pk=None):
        self.plugin_name = name
        self._export = export
        self._primary_key = pk

    def get_export(self):
        return self._export


def _plugins():
    return [_Plugin("cpu", EXPORTS["cpu"]), _Plugin("network", EXPORTS["network"], "interface_name")]


def test_parse_selection_keeps_dotted_keys_whole():
    """The attribute is the last piece; a key may carry dots (`fs./mnt/a.b.percent`)."""
    assert parse_selection("cpu, mem.used,fs./mnt/a.b.percent") == [
        ("cpu", None, None),
        ("mem", None, "used"),
        ("fs", "/mnt/a.b", "percent"),
    ]


def test_plain_prints_v4_lines():
    lines = render_plain(parse_selection("cpu.total,network.bytes_recv,network.lo.bytes_sent"), EXPORTS, PKS)
    assert lines == [
        "cpu.total: 12.5",
        "network.eth0.bytes_recv: 100",
        "network.lo.bytes_recv: 1",
        "network.lo.bytes_sent: 1",
    ]


def test_plain_whole_plugin_and_all():
    assert render_plain(parse_selection("cpu"), EXPORTS, PKS) == [f"cpu: {EXPORTS['cpu']}"]
    assert render_plain(parse_selection("all"), EXPORTS, PKS) == [f"all: {EXPORTS}"]


def test_plain_skips_an_unknown_plugin_and_attribute():
    assert render_plain(parse_selection("nope,cpu.nope"), EXPORTS, PKS) == []


def test_json_is_one_object_keyed_by_plugin():
    assert json.loads(render_json(["cpu", "nope"], EXPORTS)) == {"cpu": EXPORTS["cpu"]}


def test_csv_prints_the_header_first_then_aligned_data():
    """v4 `GlancesStdoutCsv`: the first refresh prints the header only, and a
    collection's items are locked at header time -- a vanished item prints
    N/A, a new one has no column."""
    csv = CsvRenderer([("cpu", "total"), ("network", None)])
    assert csv.render(EXPORTS, PKS) == (
        "cpu.total,network.eth0.interface_name,network.eth0.bytes_recv,network.eth0.bytes_sent,"
        "network.lo.interface_name,network.lo.bytes_recv,network.lo.bytes_sent"
    )
    later = {
        "cpu": {"total": 20.0},
        "network": [{"interface_name": "eth0", "bytes_recv": 7, "bytes_sent": 8}, {"interface_name": "new0"}],
    }
    assert csv.render(later, PKS) == "20.0,eth0,7,8,N/A,N/A,N/A"


def test_output_once_writes_the_selected_format():
    written = []
    printer = StdoutV5(plugins=_plugins(), refresh_interval=1, stdout_json="cpu", write=written.append)
    printer.output_once()
    assert json.loads(written[0]) == {"cpu": EXPORTS["cpu"]}


def test_stop_after_counts_prints_then_quits():
    """`--stop-after 3` means three prints, then the process ends like `q`."""
    written, quits = [], []
    printer = StdoutV5(
        plugins=_plugins(),
        refresh_interval=0.1,
        stdout="cpu.total",
        stop_after=3,
        on_quit=lambda: quits.append(True),
        write=written.append,
    )
    printer.start()
    printer.join(5)
    assert written == ["cpu.total: 12.5"] * 3
    assert quits == [True]


def test_a_failing_plugin_does_not_end_the_stream():
    class _Broken(_Plugin):
        def get_export(self):
            raise RuntimeError("boom")

    written = []
    printer = StdoutV5(
        plugins=[_Broken("mem", None), *_plugins()], refresh_interval=1, stdout="mem,cpu.total", write=written.append
    )
    printer.output_once()
    assert written == ["cpu.total: 12.5"]
