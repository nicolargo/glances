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

import csv as csv_module
import io
import json

from glances.outputs.stdout import CsvRenderer, Stdout, parse_selection, render_json, render_plain

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
    assert render_json([], {}) == "{}"


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


def test_csv_keeps_each_item_own_fields():
    """Port of v4 #3747 -- items of one collection may carry different field
    sets (a rate absent on the first sample): each keeps its own columns."""
    csv = CsvRenderer([("network", None)])
    first = {
        "network": [
            {"interface_name": "eth0", "bytes_sent": 1},
            {"interface_name": "wlan0", "bytes_sent": 2, "bytes_recv_rate_per_sec": 3.0},
        ]
    }
    header = csv.render(first, PKS).split(",")
    later = {
        "network": [
            {"interface_name": "eth0", "bytes_sent": 7},
            {"interface_name": "wlan0", "bytes_sent": 5, "bytes_recv_rate_per_sec": 6.0},
        ]
    }
    row = dict(zip(header, csv.render(later, PKS).split(",")))
    assert len(header) == 5
    assert row["network.eth0.bytes_sent"] == "7"
    assert row["network.wlan0.bytes_recv_rate_per_sec"] == "6.0"


def test_csv_pads_a_partial_item_and_keeps_existing_columns_in_place():
    """v4 `test_stdout_csv`: an item back with fewer fields gets one N/A per
    missing field, and an item inserted between two others moves no column."""
    csv = CsvRenderer([("network", None)])
    header = csv.render(EXPORTS, PKS).split(",")
    later = {
        "network": [
            {"interface_name": "eth0", "bytes_recv": 7, "bytes_sent": 8},
            {"interface_name": "ppp0", "bytes_recv": 9, "bytes_sent": 9},
            {"interface_name": "lo", "bytes_recv": 3},
        ]
    }
    row = csv.render(later, PKS).split(",")
    assert len(row) == len(header)
    assert row == ["eth0", "7", "8", "lo", "3", "N/A"]


def test_csv_whole_dict_plugin_gives_one_column_per_field():
    csv = CsvRenderer([("cpu", None)])
    cpu = {"cpu": {"user": 1.2, "system": 0.8, "idle": 98.0}}
    assert csv.render(cpu, PKS) == "cpu.user,cpu.system,cpu.idle"
    assert csv.render(cpu, PKS) == "1.2,0.8,98.0"


def test_csv_dict_plugin_locks_columns_when_keys_change():
    """A scalar/dict plugin whose exported keys change after the header line
    (e.g. `ip` once its public address resolves) must stay aligned to the
    header, like the list path: a key that appears later is dropped and a key
    that vanishes prints N/A, instead of the data row growing past the header."""
    csv = CsvRenderer([("ip", None)])
    first = {"ip": {"address": "192.168.1.5", "mask": "255.255.255.0"}}
    assert csv.render(first, {"ip": None}) == "ip.address,ip.mask"
    grown = {
        "ip": {"address": "192.168.1.5", "mask": "255.255.255.0", "public_address": "8.8.8.8"}
    }
    assert csv.render(grown, {"ip": None}) == "192.168.1.5,255.255.255.0"
    shrunk = {"ip": {"address": "192.168.1.5"}}
    assert csv.render(shrunk, {"ip": None}) == "192.168.1.5,N/A"


def test_csv_quotes_a_cell_holding_a_comma():
    """Mount options (`rw,relatime`) or a `strftime_format` with a comma used
    to shift every later cell by one column: such a cell is quoted, like the
    CSV export does, and the other cells are printed as before."""
    renderer = CsvRenderer([("now", "custom"), ("fs", None)])
    stats = {
        "now": {"iso": "2026-10-20T13:10:12-03:00", "custom": "Tue, 20 Oct 2026 13:10:12"},
        "fs": [{"mnt_point": "/", "options": "rw,relatime", "percent": 48.8}],
    }
    pks = {"now": None, "fs": "mnt_point"}
    header = renderer.render(stats, pks)
    line = renderer.render(stats, pks)
    assert header == "now.custom,fs./.mnt_point,fs./.options,fs./.percent"
    assert line == '"Tue, 20 Oct 2026 13:10:12",/,"rw,relatime",48.8'
    assert next(csv_module.reader([line])) == ["Tue, 20 Oct 2026 13:10:12", "/", "rw,relatime", "48.8"]


def test_csv_quotes_a_double_quote_and_a_line_break():
    """A double quote is doubled and a line break stays inside its quoted
    cell; a header cell built from such an item key is quoted too."""
    renderer = CsvRenderer([("fs", None)])
    stats = {"fs": [{"mnt_point": '/media/"usb"', "options": "ro\nnoexec"}]}
    pks = {"fs": "mnt_point"}
    header = renderer.render(stats, pks)
    line = renderer.render(stats, pks)
    assert header == '"fs./media/""usb"".mnt_point","fs./media/""usb"".options"'
    assert line == '"/media/""usb""","ro\nnoexec"'
    assert list(csv_module.reader(io.StringIO(f"{header}\n{line}\n"))) == [
        ['fs./media/"usb".mnt_point', 'fs./media/"usb".options'],
        ['/media/"usb"', "ro\nnoexec"],
    ]


def test_output_once_writes_the_selected_format():
    written = []
    printer = Stdout(plugins=_plugins(), refresh_interval=1, stdout_json="cpu", write=written.append)
    printer.output_once()
    assert json.loads(written[0]) == {"cpu": EXPORTS["cpu"]}


def test_stop_after_counts_prints_then_quits():
    """`--stop-after 3` means three prints, then the process ends like `q`."""
    written, quits = [], []
    printer = Stdout(
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
    printer = Stdout(
        plugins=[_Broken("mem", None), *_plugins()], refresh_interval=1, stdout="mem,cpu.total", write=written.append
    )
    printer.output_once()
    assert written == ["cpu.total: 12.5"]


def test_a_failing_plugin_is_reported_in_the_json_errors():
    """v4 `--stdout-json` (`GlancesJSONSerializer(include_errors=True)`): a
    failing plugin is left out of the stats and listed under `_errors`."""

    class _Broken(_Plugin):
        def get_export(self):
            raise RuntimeError("boom")

    written = []
    printer = Stdout(
        plugins=[_Broken("mem", None), *_plugins()], refresh_interval=1, stdout_json="mem,cpu", write=written.append
    )
    printer.output_once()
    assert json.loads(written[0]) == {
        "cpu": EXPORTS["cpu"],
        "_errors": [{"error": True, "plugin": "mem", "message": "boom"}],
    }
    # Every selected plugin failing still prints valid JSON.
    written.clear()
    Stdout(
        plugins=[_Broken("mem", None), _Broken("load", None)],
        refresh_interval=1,
        stdout_json="mem,load",
        write=written.append,
    ).output_once()
    assert json.loads(written[0]) == {
        "_errors": [
            {"error": True, "plugin": "mem", "message": "boom"},
            {"error": True, "plugin": "load", "message": "boom"},
        ]
    }


# ---------------------------------------------- security audit 2026-10-17, B-15

_INJECTED = "bash\x1b]0;PWNED\x07\x1b[2J\x7f\x9b"


def _processes():
    return [_Plugin("processlist", [{"pid": 1, "name": _INJECTED, "cpu_percent": 1.0}], "pid")]


def test_plain_neutralises_terminal_control_characters():
    """A process name wrote `\\x1b]0;PWNED\\x07\\x1b[2J` raw to the terminal."""
    written = []
    Stdout(plugins=_processes(), refresh_interval=1, stdout="processlist.name", write=written.append).output_once()
    assert written == ["processlist.1.name: bash?]0;PWNED??[2J??"]


def test_csv_neutralises_terminal_control_characters():
    written = []
    printer = Stdout(plugins=_processes(), refresh_interval=1, stdout_csv="processlist", write=written.append)
    printer.output_once()
    printer.output_once()
    assert written[1] == "1,bash?]0;PWNED??[2J??,1.0"
