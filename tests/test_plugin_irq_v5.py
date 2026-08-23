#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Unit tests for the v5 ``irq`` plugin model.

See docs/superpowers/specs/2026-08-04-glances-v5-g6c-design.md §3
"""

from __future__ import annotations

import asyncio

import pytest

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.irq.model_v5 import PluginModel, parse_interrupts
from glances.plugins.irq.render_curses_v5 import render

# Two CPUs. `1:` is numeric so v4 appends the alias (`1_i8042`);
# `LOC:` is not numeric so it stays as-is.
PROC_INTERRUPTS = """\
           CPU0       CPU1
  1:      44487        341   IO-APIC   1-edge      i8042
  8:         10          0   IO-APIC   8-edge      rtc0
LOC:   33549868   22394684   Local timer interrupts
FIQ:                          usb_fiq
"""


def test_parse_builds_human_names_and_sums_cpu_columns():
    rows = parse_interrupts(PROC_INTERRUPTS)
    by_line = {r["irq_line"]: r["irq_rate"] for r in rows}
    assert by_line["1_i8042"] == 44487 + 341
    assert by_line["8_rtc0"] == 10
    assert by_line["LOC"] == 33549868 + 22394684


def test_parse_tolerates_non_numeric_columns():
    """Raspberry Pi / Raspbian emit lines with no counter columns (v4 #1007)."""
    rows = parse_interrupts(PROC_INTERRUPTS)
    assert {"irq_line": "FIQ", "irq_rate": 0} in rows


def test_parse_empty_input_returns_empty_list():
    assert parse_interrupts("") == []


def test_grab_stats_returns_cumulative_counters(store_with, config_with):
    plugin = PluginModel(store_with(), config_with({}))
    plugin._read_proc = lambda: PROC_INTERRUPTS
    stats = asyncio.run(plugin._grab_stats())
    assert {r["irq_line"] for r in stats} == {"1_i8042", "8_rtc0", "LOC", "FIQ"}
    # Raw cumulative values — the base class turns them into rates.
    assert next(r for r in stats if r["irq_line"] == "8_rtc0")["irq_rate"] == 10


def test_first_cycle_publishes_items_with_rate_field_none(store_with, config_with):
    store = store_with()
    plugin = PluginModel(store, config_with({}))
    plugin._read_proc = lambda: PROC_INTERRUPTS
    asyncio.run(plugin.update())
    items = store.get("irq")["data"]
    assert items, "items must be published on cycle 1"
    assert all("irq_rate" in i and i["irq_rate"] is None for i in items), "no previous sample yet"


def test_second_cycle_computes_a_per_second_rate(store_with, config_with):
    store = store_with()
    plugin = PluginModel(store, config_with({}))
    plugin._read_proc = lambda: PROC_INTERRUPTS
    asyncio.run(plugin.update())
    # +2000 interrupts on rtc0 for the second sample.
    bumped = PROC_INTERRUPTS.replace("  8:         10          0", "  8:       2010          0")
    plugin._read_proc = lambda: bumped
    asyncio.run(plugin.update())
    rtc0 = next(i for i in store.get("irq")["data"] if i["irq_line"] == "8_rtc0")
    # Rate is delta / elapsed; elapsed is tiny in a test, so just assert the
    # delta was divided by something positive rather than published raw.
    assert rtc0["irq_rate"] > 0
    assert rtc0["irq_rate"] != 2000, "a raw delta means the rate machinery was bypassed"


def test_all_lines_published_not_just_top_five(store_with, config_with):
    """Divergence from v4: the model publishes every line (ranking moved to the
    TUI renderer) so exporters get the complete series."""
    store = store_with()
    plugin = PluginModel(store, config_with({}))
    content = "           CPU0\n" + "".join(f"{i}:  {i * 100}  IO-APIC {i}-edge dev{i}\n" for i in range(1, 9))
    plugin._read_proc = lambda: content
    asyncio.run(plugin.update())
    items = store.get("irq")["data"]
    assert len(items) == 8, "all 8 lines must be published, not just the busiest 5"
    assert {i["irq_line"] for i in items} == {f"{n}_dev{n}" for n in range(1, 9)}


def test_item_order_is_stable_across_cycles_even_as_rates_change(store_with, config_with):
    """Protects the CSV export: `build_export()` walks the list in order to emit
    columns, so the item ORDER — not just the item set — must not depend on the
    (constantly changing) rate, or the exported header churns every cycle."""
    store = store_with()
    plugin = PluginModel(store, config_with({}))
    first = "           CPU0\n" + "".join(f"{i}:  0  IO-APIC {i}-edge dev{i}\n" for i in range(1, 9))
    plugin._read_proc = lambda: first
    asyncio.run(plugin.update())
    order_cycle_1 = [i["irq_line"] for i in store.get("irq")["data"]]

    # Reverse the rate ranking entirely: if ordering still depended on rate,
    # the item order below would be the exact reverse of cycle 1's.
    second = "           CPU0\n" + "".join(f"{i}:  {(9 - i) * 100}  IO-APIC {i}-edge dev{i}\n" for i in range(1, 9))
    plugin._read_proc = lambda: second
    asyncio.run(plugin.update())
    order_cycle_2 = [i["irq_line"] for i in store.get("irq")["data"]]

    assert order_cycle_1 == order_cycle_2, "column order must be stable across cycles"
    assert order_cycle_1 == sorted(order_cycle_1), "order follows the primary key (irq_line)"


def test_get_export_returns_every_line(store_with, config_with):
    store = store_with()
    plugin = PluginModel(store, config_with({}))
    content = "           CPU0\n" + "".join(f"{i}:  {i * 100}  IO-APIC {i}-edge dev{i}\n" for i in range(1, 9))
    plugin._read_proc = lambda: content
    asyncio.run(plugin.update())
    exported = plugin.get_export()
    assert len(exported) == 8, "get_export() must not be capped at 5 either"
    assert {e["irq_line"] for e in exported} == {f"{n}_dev{n}" for n in range(1, 9)}


def test_missing_proc_file_yields_empty_collection(store_with, config_with):
    store = store_with()
    plugin = PluginModel(store, config_with({}))

    def _boom():
        raise FileNotFoundError("/proc/interrupts")

    plugin._read_proc = _boom
    asyncio.run(plugin.update())
    assert store.get("irq")["data"] == []


def test_non_linux_yields_empty_collection(store_with, config_with, monkeypatch):
    monkeypatch.setattr("glances.plugins.irq.model_v5.LINUX", False)
    store = store_with()
    plugin = PluginModel(store, config_with({}))
    asyncio.run(plugin.update())
    assert store.get("irq")["data"] == []


@pytest.mark.parametrize("attr,expected", [("plugin_name", "irq"), ("IS_COLLECTION", True), ("EMITS_ALERTS", False)])
def test_class_flags(attr, expected):
    assert getattr(PluginModel, attr) == expected


def test_disabled_by_default():
    assert PluginModel.DISABLED_BY_DEFAULT is True


_FIELDS = PluginModel.fields_description


def test_render_empty_payload_returns_no_rows():
    assert render({}, _FIELDS) == []
    assert render({"data": []}, _FIELDS) == []


def test_render_emits_a_header_then_one_row_per_irq():
    payload = {"data": [{"irq_line": "1_i8042", "irq_rate": 12.0}, {"irq_line": "LOC", "irq_rate": 3.0}]}
    rows = render(payload, _FIELDS)
    assert len(rows) == 3  # header + 2
    header = "".join(c.text for c in rows[0].cells)
    assert "IRQ" in header and "Rate/s" in header
    assert "1_i8042" in "".join(c.text for c in rows[1].cells)
    assert "LOC" in "".join(c.text for c in rows[2].cells)


def test_render_columns_align_across_all_rows():
    """Rate column must align: header, data rows, and over-long names all at the same x-offset."""
    payload = {"data": [{"irq_line": "1_i8042", "irq_rate": 12.0}, {"irq_line": "LOC", "irq_rate": 3.0}]}
    rows = render(payload, _FIELDS)
    # Name cell in header and each data row must have the same fixed width
    header_name_width = len(rows[0].cells[0].text)
    for row in rows[1:]:
        assert len(row.cells[0].text) == header_name_width, "Name column width must be consistent"


def test_render_truncates_over_long_irq_line():
    """IRQ lines longer than _NAME_MAX_WIDTH (24) are truncated, not causing misalignment."""
    long_irq_line = "this_is_a_very_long_irq_line_name_that_exceeds_max_width"
    payload = {"data": [{"irq_line": long_irq_line, "irq_rate": 10.0}]}
    rows = render(payload, _FIELDS)
    irq_text = rows[1].cells[0].text
    # Must be truncated to at most 24 chars
    assert len(irq_text) == 24, f"Expected 24 chars, got {len(irq_text)}"
    assert irq_text[: len(long_irq_line[:24])] == long_irq_line[:24]


def test_render_header_cells_have_header_color_role():
    """Both IRQ and Rate/s header cells must be styled as headers."""
    payload = {"data": [{"irq_line": "test", "irq_rate": 1.0}]}
    rows = render(payload, _FIELDS)
    header_row = rows[0]
    assert len(header_row.cells) == 2
    assert header_row.cells[0].color == ColorRole.HEADER, "IRQ header cell must have HEADER color role"
    assert header_row.cells[0].bold is True
    assert header_row.cells[1].color == ColorRole.HEADER, "Rate/s header cell must have HEADER color role"
    assert header_row.cells[1].bold is True


def test_render_tolerates_an_item_without_a_rate():
    """Cycle-1 items carry no `irq_rate`; the renderer must not raise and must show '-'."""
    rows = render({"data": [{"irq_line": "1_i8042"}]}, _FIELDS)
    assert len(rows) == 2
    rate_text = rows[1].cells[1].text
    # The rate cell must contain the placeholder "-"
    assert "-" in rate_text, f"Expected '-' in rate text, got: {rate_text}"


def test_render_skips_non_dict_items_in_data():
    """The renderer must gracefully skip non-dict items in the data list."""
    payload = {
        "data": [
            {"irq_line": "1_i8042", "irq_rate": 12.0},
            "invalid_string",
            None,
            {"irq_line": "LOC", "irq_rate": 3.0},
        ]
    }
    rows = render(payload, _FIELDS)
    # Header + 2 valid items, skipping the two non-dict entries
    assert len(rows) == 3, f"Expected 3 rows (header + 2 valid items), got {len(rows)}"
    irq_lines = ["".join(c.text for c in rows[i].cells) for i in range(1, len(rows))]
    assert "1_i8042" in irq_lines[0]
    assert "LOC" in irq_lines[1]


def test_render_ranks_and_caps_at_top_five():
    """The model now publishes every line; the renderer must do the top-5
    ranking that v4/the old model used to do, and a `None` rate (an item's
    first cycle) must sort last rather than raising."""
    payload = {
        "data": [
            {"irq_line": "a", "irq_rate": 10.0},
            {"irq_line": "b", "irq_rate": 50.0},
            {"irq_line": "c", "irq_rate": None},
            {"irq_line": "d", "irq_rate": 30.0},
            {"irq_line": "e", "irq_rate": 20.0},
            {"irq_line": "f", "irq_rate": 40.0},
            {"irq_line": "g", "irq_rate": 5.0},
        ]
    }
    rows = render(payload, _FIELDS)
    assert len(rows) == 6, "header + exactly 5 rows, even though 7 lines were published"
    rendered_lines = [row.cells[0].text.strip() for row in rows[1:]]
    # Highest 5 rates: b(50), f(40), d(30), e(20), a(10). c(None) and g(5) excluded.
    assert rendered_lines == ["b", "f", "d", "e", "a"]
