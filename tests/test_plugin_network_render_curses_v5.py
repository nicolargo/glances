"""Glances v5 — tests for the network plugin's curses renderer."""

from __future__ import annotations

import pytest

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.network.render_curses_v5 import render


@pytest.fixture
def network_fields():
    """Minimal subset of the network fields_description schema."""
    return {
        "interface_name": {"unit": "string", "primary_key": True},
        "bytes_recv": {"unit": "bytespers", "rate": True, "watched": True, "prominent": True},
        "bytes_sent": {"unit": "bytespers", "rate": True, "watched": True, "prominent": True},
        "errors_in": {"unit": "number", "rate": True},
        "errors_out": {"unit": "number", "rate": True},
        "is_up": {"unit": "bool"},
        "bytes_speed_rate_per_sec": {"unit": "bytespers"},
    }


@pytest.fixture
def network_payload():
    """Realistic network payload — three interfaces, post-_transform_gauge."""
    return {
        "data": [
            {
                "interface_name": "eth0",
                "bytes_recv": 150_000.0,  # 150 KB/s → 1.2 Mb/s
                "bytes_sent": 32_000.0,  # 32 KB/s   → 256 Kb/s
                "errors_in": 0.0,
                "errors_out": 0.0,
                "is_up": True,
                "bytes_speed_rate_per_sec": 62_500_000.0,
            },
            {
                "interface_name": "wlp0s20f3",
                "bytes_recv": 5_625.0,  # 5.5 KB/s → 45 Kb/s
                "bytes_sent": 1_500.0,  # 1.5 KB/s → 12 Kb/s
                "errors_in": 0.0,
                "errors_out": 0.0,
                "is_up": True,
                "bytes_speed_rate_per_sec": 0.0,
            },
            {
                "interface_name": "lo",
                "bytes_recv": 0.0,
                "bytes_sent": 0.0,
                "errors_in": 0.0,
                "errors_out": 0.0,
                "is_up": True,
                "bytes_speed_rate_per_sec": 0.0,
            },
        ],
        "_levels": {
            "eth0": {
                "bytes_recv": {"level": "ok", "prominent": True},
                "bytes_sent": {"level": "ok", "prominent": True},
            },
            "wlp0s20f3": {
                "bytes_recv": {"level": "ok", "prominent": True},
                "bytes_sent": {"level": "ok", "prominent": True},
            },
            "lo": {},
        },
    }


# ---------------------------------------------------------------- structure


def test_render_first_row_is_network_header(network_payload, network_fields):
    rows = render(network_payload, network_fields)
    first = " ".join(c.text for c in rows[0].cells)
    assert "NETWORK" in first
    assert "Rx/s" in first
    assert "Tx/s" in first


def test_render_one_row_per_interface_plus_header(network_payload, network_fields):
    rows = render(network_payload, network_fields)
    # 1 header + 3 interfaces = 4 rows.
    assert len(rows) == 4


def test_render_each_data_row_has_three_cells(network_payload, network_fields):
    rows = render(network_payload, network_fields)
    for r in rows[1:]:
        assert len(r.cells) == 3


def test_render_interface_name_left_aligned(network_payload, network_fields):
    rows = render(network_payload, network_fields)
    # row 1: eth0 — left-padded to name_max_width.
    name_cell = rows[1].cells[0]
    assert name_cell.text.startswith("eth0")
    assert name_cell.text == name_cell.text.rstrip() + " " * (len(name_cell.text) - len(name_cell.text.rstrip()))


def test_render_rate_columns_right_aligned(network_payload, network_fields):
    rows = render(network_payload, network_fields)
    # row 1, cells 1 and 2: rates, right-aligned (no trailing spaces).
    assert rows[1].cells[1].text.endswith(rows[1].cells[1].text.lstrip())
    assert rows[1].cells[2].text.endswith(rows[1].cells[2].text.lstrip())


def test_render_rates_use_bit_unit_suffix(network_payload, network_fields):
    rows = render(network_payload, network_fields)
    flat = " ".join(c.text for row in rows for c in row.cells)
    # eth0: 150_000 B/s × 8 = 1_200_000 b/s → "1.1Mb"
    assert "Mb" in flat
    # wlp0s20f3: 5625 B/s × 8 = 45000 b/s → "43.9Kb"
    assert "Kb" in flat


def test_render_zero_rate_keeps_b_suffix(network_payload, network_fields):
    """Sub-K bits — display raw bits with no scale suffix (v4 parity)."""
    rows = render(network_payload, network_fields)
    flat = " ".join(c.text for row in rows for c in row.cells)
    # lo: 0 B/s × 8 = 0 b/s → "0b"
    assert "0b" in flat


# ---------------------------------------------------------------- filtering


def test_render_skips_interfaces_marked_down(network_fields):
    payload = {
        "data": [
            {
                "interface_name": "eth0",
                "bytes_recv": 100.0,
                "bytes_sent": 50.0,
                "is_up": True,
            },
            {
                "interface_name": "docker0",
                "bytes_recv": 0.0,
                "bytes_sent": 0.0,
                "is_up": False,
            },
        ],
        "_levels": {},
    }
    rows = render(payload, network_fields)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "eth0" in flat
    assert "docker0" not in flat


def test_render_skips_interfaces_without_rate_yet(network_fields):
    """First cycle for a new interface: `bytes_recv` / `bytes_sent` absent."""
    payload = {
        "data": [
            {"interface_name": "eth0", "bytes_recv": 100.0, "bytes_sent": 50.0, "is_up": True},
            # `eth1` appeared on-the-fly — base class strips rate fields on cycle 1.
            {"interface_name": "eth1", "is_up": True},
        ],
        "_levels": {},
    }
    rows = render(payload, network_fields)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "eth0" in flat
    assert "eth1" not in flat


def test_render_handles_empty_data(network_fields):
    rows = render({"data": [], "_levels": {}}, network_fields)
    # Only the header row.
    assert len(rows) == 1
    flat = " ".join(c.text for c in rows[0].cells)
    assert "NETWORK" in flat


def test_render_handles_empty_payload(network_fields):
    rows = render({}, network_fields)
    assert len(rows) == 1
    flat = " ".join(c.text for c in rows[0].cells)
    assert "NETWORK" in flat


# ---------------------------------------------------------------- truncation


def test_render_long_interface_name_truncated_with_underscore(network_fields):
    """Long names tail-truncated with a leading underscore (v4 parity)."""
    long_name = "docker0123456789abcdefXYZ"  # 25 chars > _NAME_MAX_WIDTH
    payload = {
        "data": [
            {"interface_name": long_name, "bytes_recv": 100.0, "bytes_sent": 50.0, "is_up": True},
        ],
        "_levels": {long_name: {}},
    }
    rows = render(payload, network_fields)
    name_text = rows[1].cells[0].text
    # Truncated to _NAME_MAX_WIDTH (18 chars), prefixed with `_`, tail preserved.
    assert name_text.startswith("_")
    assert len(name_text) == 18
    assert name_text.endswith("XYZ")


def test_render_total_block_width_fits_sidebar_cap(network_payload, network_fields):
    """Each row's natural width (cells + 1-char gaps) must not exceed the
    v5 left sidebar cap (34) — otherwise the painter clips the right side
    of the Tx/s column. Regression guard for the 36→34 clipping bug."""
    rows = render(network_payload, network_fields)
    for r in rows:
        natural_w = sum(len(c.text) for c in r.cells) + max(0, len(r.cells) - 1)
        assert natural_w <= 34, f"row width {natural_w} exceeds sidebar cap 34"


def test_render_columns_align_across_rows(network_payload, network_fields):
    """All rows share the same per-column widths."""
    rows = render(network_payload, network_fields)
    ncols = max(len(r.cells) for r in rows)
    for col in range(ncols):
        widths = {len(r.cells[col].text) for r in rows if col < len(r.cells)}
        assert len(widths) == 1, f"col {col} widths differ: {widths}"


# ---------------------------------------------------------------- color


def test_render_rate_cell_color_reflects_per_interface_level(network_fields):
    """Per-interface `_levels` drive the rate cell color (v4 parity)."""
    payload = {
        "data": [
            {"interface_name": "eth0", "bytes_recv": 9e6, "bytes_sent": 1e6, "is_up": True},
        ],
        "_levels": {
            "eth0": {
                "bytes_recv": {"level": "critical", "prominent": True},
                "bytes_sent": {"level": "ok", "prominent": True},
            },
        },
    }
    rows = render(payload, network_fields)
    rx_cell = rows[1].cells[1]
    tx_cell = rows[1].cells[2]
    assert rx_cell.color == ColorRole.CRITICAL
    assert rx_cell.prominent is True
    assert tx_cell.color == ColorRole.OK


def test_render_title_role_header_when_no_prominent_alert(network_payload, network_fields):
    """All `_levels` at ok → title stays HEADER (white+bold)."""
    rows = render(network_payload, network_fields)
    title = rows[0].cells[0]
    assert title.color == ColorRole.HEADER
    assert title.bold is True


def test_render_title_role_escalates_on_critical(network_fields):
    """A critical+prominent rate anywhere bumps the title color."""
    payload = {
        "data": [
            {"interface_name": "eth0", "bytes_recv": 9e6, "bytes_sent": 1e6, "is_up": True},
        ],
        "_levels": {
            "eth0": {"bytes_recv": {"level": "critical", "prominent": True}},
        },
    }
    rows = render(payload, network_fields)
    assert rows[0].cells[0].color == ColorRole.CRITICAL
    assert rows[0].cells[0].bold is True
