#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — tests for the irq curses renderer."""

from __future__ import annotations

from glances.plugins.irq.render_curses_v5 import render


def _payload(items):
    return {"data": items}


def _irq(line, rate):
    return {"irq_line": line, "irq_rate": rate}


def test_item_rows_are_marked_for_the_truncation_counter():
    rows = render(_payload([_irq("0", 12.0), _irq("LOC", 340.0)]), {})
    assert rows[0].item_start is False  # header
    assert sum(r.item_start for r in rows) == 2
