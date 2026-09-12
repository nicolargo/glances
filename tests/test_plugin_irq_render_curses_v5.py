#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — tests for the irq curses renderer."""

from __future__ import annotations

from glances.plugins.irq.model_v5 import PluginModel
from glances.plugins.irq.render_curses_v5 import render

# The REAL schema, as production passes it (curses_renderer_v5.py:1459). The
# column labels come from it (field_label), so a hand-written subset without
# `short_name` would test a header no user ever sees.
_SCHEMA = PluginModel.fields_description


def _payload(items):
    return {"data": items}


def _irq(line, rate):
    return {"irq_line": line, "irq_rate": rate}


def test_item_rows_are_marked_for_the_truncation_counter():
    rows = render(_payload([_irq("0", 12.0), _irq("LOC", 340.0)]), _SCHEMA)
    assert rows[0].item_start is False  # header
    assert sum(r.item_start for r in rows) == 2


def test_the_rate_header_comes_from_the_schema():
    """G9-7 D5: the column label lives in the schema, so the TUI and the WebUI
    (labelFor -> /api/5/all/info) cannot drift. A hardcoded "Rate/s" in the
    renderer would pass the header assertions and still leave the WebUI
    labelling the column `irq_rate`.
    """
    assert PluginModel.fields_description["irq_rate"]["short_name"] == "Rate/s"
    rows = render(_payload([_irq("0", 12.0)]), _SCHEMA)
    assert "Rate/s" in " ".join(c.text for c in rows[0].cells)
