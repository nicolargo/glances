"""Glances v5 — tests for the diskio plugin's curses renderer."""

from __future__ import annotations

import pytest

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.diskio.render_curses_v5 import render


@pytest.fixture
def diskio_fields():
    return {
        "disk_name": {"unit": "string", "primary_key": True},
        "read_count": {"unit": "number", "rate": True, "internal": True},
        "write_count": {"unit": "number", "rate": True, "internal": True},
        "read_bytes": {
            "unit": "bytespers",
            "rate": True,
            "watched": True,
            "prominent": False,
            "strict_thresholds": True,
        },
        "write_bytes": {
            "unit": "bytespers",
            "rate": True,
            "watched": True,
            "prominent": False,
            "strict_thresholds": True,
        },
    }


@pytest.fixture
def diskio_payload():
    return {
        "data": [
            {
                "disk_name": "sda",
                "read_count": 100.0,
                "write_count": 50.0,
                "read_bytes": 1_500_000.0,
                "write_bytes": 750_000.0,
            },
            {
                "disk_name": "nvme0n1",
                "read_count": 5.0,
                "write_count": 2.0,
                "read_bytes": 100.0,
                "write_bytes": 50.0,
            },
        ],
        "_levels": {},
    }


# ---------------------------------------------------------------- structure


def test_render_first_row_is_diskio_header(diskio_payload, diskio_fields):
    rows = render(diskio_payload, diskio_fields)
    text = " ".join(c.text for c in rows[0].cells)
    assert "DISK I/O" in text
    assert "R/s" in text
    assert "W/s" in text


def test_render_one_row_per_disk(diskio_payload, diskio_fields):
    rows = render(diskio_payload, diskio_fields)
    # 1 header + 2 disks
    assert len(rows) == 3


def test_render_disks_sorted_by_name(diskio_payload, diskio_fields):
    rows = render(diskio_payload, diskio_fields)
    names = [r.cells[0].text.strip() for r in rows[1:]]
    assert names == sorted(names)


def test_render_each_data_row_has_three_cells(diskio_payload, diskio_fields):
    rows = render(diskio_payload, diskio_fields)
    for r in rows[1:]:
        assert len(r.cells) == 3


def test_render_rate_cells_have_no_per_second_suffix(diskio_payload, diskio_fields):
    """The header carries the ``R/s`` / ``W/s`` labels so individual cells
    show the byte rate without ``/s`` (v4 parity — saves column width)."""
    rows = render(diskio_payload, diskio_fields)
    for r in rows[1:]:
        for c in r.cells[1:]:
            assert "/s" not in c.text


def test_render_rate_values_use_auto_unit(diskio_payload, diskio_fields):
    rows = render(diskio_payload, diskio_fields)
    flat = " ".join(c.text for row in rows[1:] for c in row.cells)
    # 1_500_000 B/s → "1.4M" ; 750_000 B/s → "732K" or "732.4K" depending
    # on the auto-unit decimal policy. We just check the suffix appears.
    assert "M" in flat or "K" in flat


def test_render_block_width_fits_sidebar_cap(diskio_payload, diskio_fields):
    """Row width ≤ 34 (left-sidebar cap)."""
    rows = render(diskio_payload, diskio_fields)
    for r in rows:
        natural_w = sum(len(c.text) for c in r.cells) + max(0, len(r.cells) - 1)
        assert natural_w <= 34, f"row width {natural_w} exceeds sidebar cap 34"


def test_render_columns_align_across_rows(diskio_payload, diskio_fields):
    rows = render(diskio_payload, diskio_fields)
    ncols = max(len(r.cells) for r in rows)
    for col in range(ncols):
        widths = {len(r.cells[col].text) for r in rows if col < len(r.cells)}
        assert len(widths) == 1, f"col {col} widths differ: {widths}"


def test_render_handles_empty_data(diskio_fields):
    rows = render({"data": [], "_levels": {}}, diskio_fields)
    assert len(rows) == 1


def test_render_handles_empty_payload(diskio_fields):
    rows = render({}, diskio_fields)
    assert len(rows) == 1
    flat = " ".join(c.text for c in rows[0].cells)
    assert "DISK I/O" in flat


def test_render_skips_disk_without_rate_yet(diskio_fields):
    """Cycle 1: read_bytes/write_bytes absent → skip the row entirely so
    the user does not see a "-" placeholder for every disk on startup."""
    payload = {
        "data": [
            {"disk_name": "sda", "read_count": 0.0, "write_count": 0.0},
            # No read_bytes/write_bytes keys (base class strips on cycle 1).
        ],
        "_levels": {},
    }
    rows = render(payload, diskio_fields)
    # Header only.
    assert len(rows) == 1


# ---------------------------------------------------------------- truncation


def test_render_long_disk_name_truncated_with_underscore(diskio_fields):
    long_name = "very_long_disk_identifier_that_overflows"
    payload = {
        "data": [{"disk_name": long_name, "read_bytes": 0.0, "write_bytes": 0.0}],
        "_levels": {long_name: {}},
    }
    rows = render(payload, diskio_fields)
    name_text = rows[1].cells[0].text
    assert name_text.startswith("_")
    assert len(name_text) == len(rows[0].cells[0].text)


# ---------------------------------------------------------------- color


def test_render_rate_cells_default_color_when_no_thresholds(diskio_payload, diskio_fields):
    """No ``_levels`` entry → cells render in DEFAULT (no green)."""
    rows = render(diskio_payload, diskio_fields)
    for r in rows[1:]:
        for c in r.cells[1:]:
            assert c.color == ColorRole.DEFAULT
            assert c.prominent is False


def test_render_rate_cell_inherits_level_when_threshold_fires(diskio_fields):
    """Per-disk ``_levels.<disk>.read_bytes`` drives the R/s cell color."""
    payload = {
        "data": [{"disk_name": "sda", "read_bytes": 15_000.0, "write_bytes": 100.0}],
        "_levels": {"sda": {"read_bytes": {"level": "warning", "prominent": False}}},
    }
    rows = render(payload, diskio_fields)
    rx_cell = rows[1].cells[1]
    assert rx_cell.color == ColorRole.WARNING
    assert rx_cell.prominent is False


def test_render_title_role_header_when_no_alert(diskio_payload, diskio_fields):
    rows = render(diskio_payload, diskio_fields)
    title = rows[0].cells[0]
    assert title.color == ColorRole.HEADER
    assert title.bold is True
