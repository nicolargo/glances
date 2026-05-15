"""Glances v5 — tests for the fs plugin's curses renderer."""

from __future__ import annotations

import pytest

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.fs.render_curses_v5 import render


@pytest.fixture
def fs_fields():
    return {
        "mnt_point": {"unit": "string", "primary_key": True},
        "device_name": {"unit": "string"},
        "fs_type": {"unit": "string", "internal": True},
        "options": {"unit": "string", "internal": True},
        "size": {"unit": "bytes"},
        "used": {"unit": "bytes"},
        "free": {"unit": "bytes"},
        "percent": {"unit": "percent", "watched": True, "prominent": True},
    }


@pytest.fixture
def fs_payload():
    return {
        "data": [
            {
                "mnt_point": "/",
                "device_name": "/dev/sda1",
                "fs_type": "ext4",
                "options": "rw,relatime",
                "size": 500 * 1024**3,
                "used": 125 * 1024**3,
                "free": 375 * 1024**3,
                "percent": 25.0,
            },
            {
                "mnt_point": "/home",
                "device_name": "/dev/sda2",
                "fs_type": "ext4",
                "options": "rw,relatime",
                "size": 1024**4,
                "used": 512 * 1024**3,
                "free": 512 * 1024**3,
                "percent": 50.0,
            },
        ],
        "_levels": {
            "/": {"percent": {"level": "ok", "prominent": True}},
            "/home": {"percent": {"level": "careful", "prominent": True}},
        },
    }


# ---------------------------------------------------------------- structure


def test_render_first_row_is_filesys_header(fs_payload, fs_fields):
    rows = render(fs_payload, fs_fields)
    text = " ".join(c.text for c in rows[0].cells)
    assert "FILE SYS" in text
    assert "Used" in text
    assert "Total" in text


def test_render_one_row_per_filesystem(fs_payload, fs_fields):
    rows = render(fs_payload, fs_fields)
    # 1 header + 2 filesystems
    assert len(rows) == 3


def test_render_filesystems_sorted_by_mnt_point(fs_payload, fs_fields):
    rows = render(fs_payload, fs_fields)
    mnts = [r.cells[0].text.strip() for r in rows[1:]]
    assert mnts == sorted(mnts)


def test_render_each_data_row_has_three_cells(fs_payload, fs_fields):
    rows = render(fs_payload, fs_fields)
    for r in rows[1:]:
        assert len(r.cells) == 3


def test_render_used_and_total_in_bytes(fs_payload, fs_fields):
    rows = render(fs_payload, fs_fields)
    flat = " ".join(c.text for row in rows[1:] for c in row.cells)
    # 125 GiB → "125.0G", 500 GiB → "500.0G"
    assert "125.0G" in flat
    assert "500.0G" in flat


def test_render_columns_align_across_rows(fs_payload, fs_fields):
    rows = render(fs_payload, fs_fields)
    ncols = max(len(r.cells) for r in rows)
    for col in range(ncols):
        widths = {len(r.cells[col].text) for r in rows if col < len(r.cells)}
        assert len(widths) == 1, f"col {col} widths differ: {widths}"


def test_render_block_width_fits_sidebar_cap(fs_payload, fs_fields):
    """Row width (cells + 1-char gaps) must stay ≤ 34 (left sidebar cap)."""
    rows = render(fs_payload, fs_fields)
    for r in rows:
        natural_w = sum(len(c.text) for c in r.cells) + max(0, len(r.cells) - 1)
        assert natural_w <= 34, f"row width {natural_w} exceeds sidebar cap 34"


def test_render_handles_empty_data(fs_fields):
    rows = render({"data": [], "_levels": {}}, fs_fields)
    assert len(rows) == 1


def test_render_handles_empty_payload(fs_fields):
    rows = render({}, fs_fields)
    assert len(rows) == 1
    flat = " ".join(c.text for c in rows[0].cells)
    assert "FILE SYS" in flat


# ---------------------------------------------------------------- truncation


def test_render_long_mnt_point_truncated_with_underscore(fs_fields):
    """Long mountpoints are tail-truncated with a leading ``_`` (v4 parity)."""
    long_mnt = "/very/long/mountpoint/path/that/exceeds/limits"
    payload = {
        "data": [{"mnt_point": long_mnt, "size": 1024**3, "used": 0, "free": 1024**3, "percent": 0.0}],
        "_levels": {long_mnt: {}},
    }
    rows = render(payload, fs_fields)
    mnt_text = rows[1].cells[0].text
    assert mnt_text.startswith("_")
    # Width matches the value-row mnt column.
    assert len(mnt_text) == len(rows[0].cells[0].text)


# ---------------------------------------------------------------- color


def test_render_used_cell_inherits_percent_level(fs_fields):
    """Per-fs ``_levels.<mnt>.percent`` drives the Used cell color (v4 parity:
    v4 decorates the ``used`` cell with the percent threshold). The cell is
    coloured but NOT prominent — see fs.percent schema (``prominent: False``)."""
    payload = {
        "data": [{"mnt_point": "/", "size": 100, "used": 95, "free": 5, "percent": 95.0}],
        "_levels": {"/": {"percent": {"level": "critical", "prominent": False}}},
    }
    rows = render(payload, fs_fields)
    used_cell = rows[1].cells[1]
    assert used_cell.color == ColorRole.CRITICAL
    assert used_cell.prominent is False


def test_render_title_role_header_when_no_prominent_alert(fs_payload, fs_fields):
    rows = render(fs_payload, fs_fields)
    title = rows[0].cells[0]
    assert title.color == ColorRole.HEADER
    assert title.bold is True


def test_render_title_role_escalates_on_critical(fs_fields):
    payload = {
        "data": [{"mnt_point": "/", "size": 100, "used": 95, "free": 5, "percent": 95.0}],
        "_levels": {"/": {"percent": {"level": "critical", "prominent": True}}},
    }
    rows = render(payload, fs_fields)
    assert rows[0].cells[0].color == ColorRole.CRITICAL
    assert rows[0].cells[0].bold is True
