#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — tests for the gpu curses renderer."""

from __future__ import annotations

from glances.outputs.curses_renderer import ColorRole
from glances.plugins.gpu.model import PluginModel
from glances.plugins.gpu.render_curses import render

# The REAL schema. `render()` takes `fields_desc` as an optional argument, but
# production ALWAYS passes it (`glances/outputs/curses_renderer.py`), and
# these tests used to call `render()` with nothing -- so `field_label({}, ...)`
# returned the bare field name, which for gpu happens to equal the declared
# `short_name`. Every label assertion below therefore passed identically with
# and without the schema, i.e. it could not observe the schema at all.
# `test_schema_declares_the_tui_short_names` is what makes a deletion fail;
# passing the schema here is what makes these tests exercise production's path.
FIELDS = PluginModel.fields_description


def _payload(cards, levels=None):
    return {"data": cards, "_levels": levels or {}}


def _card(gpu_id="nvidia0", name="GeForce RTX", mem=40, proc=30, temp=55):
    return {"gpu_id": gpu_id, "name": name, "mem": mem, "proc": proc, "temperature": temp}


def _flat(rows):
    return "\n".join(" ".join(c.text for c in r.cells) for r in rows)


def test_empty_payload_returns_no_rows():
    assert render(_payload([]), FIELDS) == []


def test_single_gpu_summary_three_metric_rows():
    rows = render(_payload([_card()]), FIELDS)
    flat = _flat(rows)
    # Header (name) + proc/mem/temperature labels.
    assert "GeForce RTX" in flat
    assert "proc" in flat
    assert "mem" in flat
    assert "temperature" in flat
    # Labels carry no trailing colon, like every other plugin.
    assert ":" not in flat
    assert "30" in flat and "40" in flat and "55" in flat


def test_header_two_same_name():
    rows = render(_payload([_card("nvidia0", "Tesla"), _card("nvidia1", "Tesla")]), FIELDS)
    assert "2 Tesla" in _flat(rows)


def test_header_two_different_names():
    rows = render(_payload([_card("nvidia0", "Tesla"), _card("amd0", "Radeon")]), FIELDS)
    assert "2 GPUs" in _flat(rows)


def test_multi_mode_one_row_per_gpu():
    cards = [_card("nvidia0", "Tesla", proc=30, mem=40), _card("amd0", "Radeon", proc=10, mem=20)]
    rows = render(_payload(cards), FIELDS)
    flat = _flat(rows)
    # Multi rows use the name[:9] id and show proc + mem.
    assert "Tesla" in flat and "Radeon" in flat
    assert "mem" in flat


def test_meangpu_forces_summary_for_multi():
    cards = [_card("nvidia0", "Tesla", proc=20), _card("nvidia1", "Tesla", proc=40)]
    rows = render(_payload(cards), FIELDS, view={"meangpu": True})
    flat = _flat(rows)
    assert "proc mean" in flat
    assert "temp mean" in flat
    assert ":" not in flat
    assert "30" in flat  # mean of 20 and 40


def test_fahrenheit_temperature():
    rows = render(_payload([_card(temp=100)]), FIELDS, view={"fahrenheit": True})
    flat = _flat(rows)
    assert "212" in flat  # 100C -> 212F
    assert "F" in flat


def test_none_values_render_na():
    rows = render(_payload([_card(mem=None, proc=None, temp=None)]), FIELDS)
    assert "N/A" in _flat(rows)


def test_multi_mode_none_values_render_na():
    # #3631: an unavailable metric must be displayed as N/A, not hidden — hiding
    # it drops a cell and misaligns the rows of heterogeneous cards.
    cards = [_card("nvidia0", "Tesla", proc=30, mem=40), _card("intel0", "Intel", proc=None, mem=None, temp=None)]
    rows = render(_payload(cards), FIELDS)
    assert "N/A" in _flat(rows)
    # Every card row carries the same cell count: name + proc + mem + temperature.
    assert [len(r.cells) for r in rows[1:]] == [4, 4]


def test_multi_mode_mem_column_hidden_when_no_card_reports_it():
    # #3631 keeps a per-card N/A, but when *no* card reports memory the whole
    # column is dropped to narrow the plugin.
    cards = [_card("arm0", "Mali", proc=30, mem=None), _card("arm1", "Mali", proc=10, mem=None)]
    rows = render(_payload(cards), FIELDS)
    flat = _flat(rows)
    assert "mem" not in flat
    # name + proc + temperature.
    assert [len(r.cells) for r in rows[1:]] == [3, 3]


def test_multi_mode_shows_each_card_temperature():
    cards = [_card("nvidia0", "Tesla", temp=74), _card("nvidia1", "Tesla", temp=52)]
    rows = render(_payload(cards), FIELDS)
    assert rows[1].cells[-1].text.strip() == "74C"
    assert rows[2].cells[-1].text.strip() == "52C"


def test_multi_mode_temperature_takes_its_own_level_colour():
    cards = [_card("nvidia0", "Tesla", temp=74), _card("nvidia1", "Tesla", temp=52)]
    levels = {"nvidia0": {"temperature": {"level": "warning"}}}
    rows = render(_payload(cards, levels), FIELDS)
    assert rows[1].cells[-1].color == ColorRole.WARNING
    assert rows[2].cells[-1].color == ColorRole.DEFAULT


def test_multi_mode_fahrenheit_temperature():
    cards = [_card("nvidia0", "Tesla", temp=100), _card("nvidia1", "Tesla", temp=50)]
    rows = render(_payload(cards), FIELDS, view={"fahrenheit": True})
    assert rows[1].cells[-1].text.strip() == "212F"
    assert rows[2].cells[-1].text.strip() == "122F"


def test_multi_mode_temperature_column_hidden_when_no_card_reports_it():
    cards = [_card("arm0", "Mali", temp=None), _card("arm1", "Mali", temp=None)]
    rows = render(_payload(cards), FIELDS)
    assert "N/A" not in _flat(rows)
    # name + proc + mem.
    assert [len(r.cells) for r in rows[1:]] == [3, 3]


def test_schema_declares_the_tui_short_names():
    """Pin the schema the gpu labels resolve from -- TUI and WebUI alike.

    The renderer tests above cannot do this job: gpu's `short_name`s are
    spelled exactly like their field names, so `field_label()` returns the
    same string whether the schema declares them or falls back. Delete one
    from the model and both the TUI block and `PluginGpu.vue` (which resolves
    the same strings from `/api/5/gpu/info`) silently degrade to field names
    with every render assertion still green. This asserts the source instead,
    the way test_network_schema_declares_the_tui_short_names does.
    """
    fields = PluginModel.fields_description
    assert fields["proc"]["short_name"] == "proc"
    assert fields["mem"]["short_name"] == "mem"
    assert fields["temperature"]["short_name"] == "temperature"


def _painted(row):
    # The painter separates adjacent cells with exactly one space
    # (curses_renderer.row_width), so this is the on-screen line.
    return " ".join(c.text for c in row.cells)


def test_multi_mode_cells_carry_no_leading_space():
    # The painter already inserts one space between cells: a leading space in
    # the cell text doubled every gap and widened the top-row block.
    cards = [
        _card("intel0", "UHD Graphics", proc=11, mem=None, temp=None),
        _card("intel1", "Arc A370M", proc=0, mem=None, temp=52),
    ]
    rows = render(_payload(cards), FIELDS)
    assert _painted(rows[1]) == "UHD Graph  11%  N/A"
    assert _painted(rows[2]) == "Arc A370M   0%  52C"


def test_multi_mode_name_column_fits_the_longest_name():
    # Short names shrink the column; rows stay aligned whatever the lengths
    # (the old fixed `{:<7}` misaligned an 8- or 9-character name).
    cards = [_card("a", "Tesla", proc=5, temp=40), _card("b", "Radeon", proc=50, temp=60)]
    rows = render(_payload(cards), FIELDS)
    assert _painted(rows[1]) == "Tesla    5% mem  40%  40C"
    assert _painted(rows[2]) == "Radeon  50% mem  40%  60C"
    cards = [_card("a", "GT 1030X", proc=5), _card("b", "Arc A370M", proc=5)]
    lines = [_painted(r) for r in render(_payload(cards), FIELDS)[1:]]
    assert len({len(line) for line in lines}) == 1


def test_summary_label_column_fits_the_longest_label():
    rows = render(_payload([_card()]), FIELDS)
    assert [_painted(r) for r in rows[1:]] == ["proc         30%", "mem          40%", "temperature  55C"]
    cards = [_card("a", "Tesla", proc=20), _card("b", "Tesla", proc=40)]
    rows = render(_payload(cards), FIELDS, view={"meangpu": True})
    assert [_painted(r) for r in rows[1:]] == ["proc mean  30%", "mem mean   40%", "temp mean  55C"]


def test_summary_drops_temperature_row_when_card_hides_it():
    card = _card()
    card["hide_temperature"] = True
    rows = render(_payload([card]), FIELDS)
    assert [_painted(r) for r in rows[1:]] == ["proc  30%", "mem   40%"]


def test_summary_keeps_temperature_row_when_one_card_shows_it():
    hidden = _card("intel0", "Arc", temp=50)
    hidden["hide_temperature"] = True
    rows = render(_payload([hidden, _card("nvidia0", "RTX", temp=70)]), FIELDS, view={"meangpu": True})
    assert _painted(rows[-1]) == "temp mean  60C"


def test_multi_mode_drops_temperature_column_when_every_card_hides_it():
    cards = [
        _card("intel0", "UHD Graphics", proc=11, mem=None, temp=None),
        _card("intel1", "Arc A370M", proc=0, mem=None, temp=52),
    ]
    for card in cards:
        card["hide_temperature"] = True
    rows = render(_payload(cards), FIELDS)
    assert [_painted(r) for r in rows[1:]] == ["UHD Graph  11%", "Arc A370M   0%"]


def test_multi_mode_keeps_temperature_column_for_a_card_that_shows_it():
    hidden = _card("intel0", "Arc", mem=None, temp=50)
    hidden["hide_temperature"] = True
    rows = render(_payload([hidden, _card("nvidia0", "RTX", mem=None, temp=70)]), FIELDS)
    # Column kept for the NVIDIA card; the hidden card's cell keeps its value
    # so the rows stay aligned.
    assert [_painted(r) for r in rows[1:]] == ["Arc  30%  50C", "RTX  30%  70C"]
