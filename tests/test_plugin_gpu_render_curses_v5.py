#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — tests for the gpu curses renderer."""

from __future__ import annotations

from glances.plugins.gpu.model_v5 import PluginModel
from glances.plugins.gpu.render_curses_v5 import render

# The REAL schema. `render()` takes `fields_desc` as an optional argument, but
# production ALWAYS passes it (`glances/outputs/curses_renderer_v5.py`), and
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
    assert "proc:" in flat
    assert "mem:" in flat
    assert "temperature:" in flat
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
    assert "proc mean:" in flat
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
    cards = [_card("nvidia0", "Tesla", proc=30, mem=40), _card("intel0", "Intel", proc=None, mem=None)]
    rows = render(_payload(cards), FIELDS)
    assert "N/A" in _flat(rows)
    # Every card row carries the same cell count: name + proc + mem.
    assert [len(r.cells) for r in rows[1:]] == [3, 3]


def test_multi_mode_mem_column_hidden_when_no_card_reports_it():
    # #3631 keeps a per-card N/A, but when *no* card reports memory the whole
    # column is dropped to narrow the plugin.
    cards = [_card("arm0", "Mali", proc=30, mem=None), _card("arm1", "Mali", proc=10, mem=None)]
    rows = render(_payload(cards), FIELDS)
    flat = _flat(rows)
    assert "mem" not in flat
    assert [len(r.cells) for r in rows[1:]] == [2, 2]


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
