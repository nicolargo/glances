"""Glances v5 — tests for the processcount plugin's curses renderer."""

from __future__ import annotations

import pytest

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.processcount.render_curses_v5 import render


@pytest.fixture
def fields():
    return {
        "total": {"unit": "number"},
        "running": {"unit": "number"},
        "sleeping": {"unit": "number"},
        "thread": {"unit": "number"},
        "pid_max": {"unit": "number"},
    }


@pytest.fixture
def payload():
    return {
        "total": 215,
        "running": 3,
        "sleeping": 195,
        "thread": 1452,
        "pid_max": 32768,
    }


# ---------------------------------------------------------- structure


def test_render_produces_one_row(payload, fields):
    rows = render(payload, fields)
    assert len(rows) == 1


def test_render_title_is_tasks_header(payload, fields):
    rows = render(payload, fields)
    first = rows[0].cells[0]
    assert first.text == "TASKS"
    assert first.color == ColorRole.HEADER
    assert first.bold is True


def test_render_contains_aggregate_counts(payload, fields):
    rows = render(payload, fields)
    flat = "".join(c.text for c in rows[0].cells)
    assert "215" in flat
    assert "(1452 thr)" in flat
    assert "3 run" in flat
    assert "195 slp" in flat
    # Other = 215 - 3 - 195 = 17.
    assert "17 oth" in flat


def test_render_handles_missing_thread(fields):
    """psutil on macOS may not return ``thread`` — render skips the parenthesis."""
    payload = {"total": 10, "running": 1, "sleeping": 8, "thread": None, "pid_max": None}
    rows = render(payload, fields)
    flat = "".join(c.text for c in rows[0].cells)
    assert "thr" not in flat


def test_render_handles_missing_running_sleeping(fields):
    """If neither running nor sleeping is known, the renderer degrades but does not crash."""
    payload = {"total": 5, "running": None, "sleeping": None, "thread": 5, "pid_max": None}
    rows = render(payload, fields)
    flat = "".join(c.text for c in rows[0].cells)
    assert "TASKS" in flat
    assert "5 oth" in flat  # everything counts as "other" when run/slp are missing.


# ---------------------------------------------------------- edge cases


def test_render_empty_payload_shows_title_only(fields):
    rows = render({}, fields)
    assert len(rows) == 1
    assert rows[0].cells[0].text == "TASKS"
    # No counts surfaced.
    flat = "".join(c.text for c in rows[0].cells)
    assert "0 oth" not in flat


def test_render_none_payload_shows_title_only(fields):
    rows = render(None, fields)
    assert len(rows) == 1
    assert rows[0].cells[0].text == "TASKS"


def test_render_no_total_skips_aggregate(fields):
    """An engine that never ran (no `total`) → just the title."""
    payload = {"running": None, "sleeping": None, "thread": None, "pid_max": None}
    rows = render(payload, fields)
    flat = "".join(c.text for c in rows[0].cells)
    assert flat == "TASKS"
