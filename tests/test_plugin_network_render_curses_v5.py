"""Glances v5 — tests for the network plugin's curses renderer."""

from __future__ import annotations

import pytest

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.network.model_v5 import PluginModel
from glances.plugins.network.render_curses_v5 import render


@pytest.fixture
def network_fields():
    """Minimal subset of the network fields_description schema."""
    return {
        "interface_name": {"unit": "string", "short_name": "interface", "primary_key": True},
        "bytes_recv": {
            "unit": "bytespers",
            "short_name": "Rx/s",
            "rate": True,
            "watched": True,
            "prominent": True,
        },
        "bytes_sent": {
            "unit": "bytespers",
            "short_name": "Tx/s",
            "rate": True,
            "watched": True,
            "prominent": True,
        },
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
                "bytes_speed_rate_per_sec": 125_000_000.0,
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


def test_header_short_names_match_the_shipped_schema(network_fields):
    """Pin the fixture's header labels to `model_v5.fields_description`.

    `render()` resolves its value-column headers through `field_label()`, so a
    fixture whose `short_name` drifted from the shipped schema would keep
    asserting `Rx/s` while the real TUI printed something else.
    """
    real = PluginModel.fields_description
    for key in ("bytes_recv", "bytes_sent"):
        assert network_fields[key]["short_name"] == real[key]["short_name"]


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


def test_render_defaults_to_bits_with_no_view(network_payload, network_fields):
    """No `view` argument — v4 default (bits/s, `b` suffix), unchanged behaviour."""
    rows = render(network_payload, network_fields)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "1.1Mb" in flat
    assert "43.9Kb" in flat


def test_render_view_byte_false_uses_bits(network_payload, network_fields):
    rows = render(network_payload, network_fields, view={"byte": False})
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "1.1Mb" in flat
    assert "43.9Kb" in flat


def test_render_view_byte_true_uses_bytes_per_second(network_payload, network_fields):
    """`--byte`: bytes/s, no `b` suffix (v4 `network/__init__.py:273`)."""
    rows = render(network_payload, network_fields, view={"byte": True})
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "146.5K" in flat
    assert "5.5K" in flat
    assert "1.1Mb" not in flat
    assert "43.9Kb" not in flat


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


def test_render_title_never_escalates_on_critical(network_fields):
    """v4 parity: the title is always TITLE/HEADER — only the VALUE carries the alert."""
    payload = {
        "data": [
            {"interface_name": "eth0", "bytes_recv": 9e6, "bytes_sent": 1e6, "is_up": True},
        ],
        "_levels": {
            "eth0": {"bytes_recv": {"level": "critical", "prominent": True}},
        },
    }
    rows = render(payload, network_fields)
    assert rows[0].cells[0].color == ColorRole.HEADER
    assert rows[0].cells[0].bold is True


def test_item_rows_are_marked_for_the_truncation_counter(network_payload, network_fields):
    rows = render(network_payload, network_fields)
    assert rows[0].item_start is False  # header
    assert sum(r.item_start for r in rows) == len(network_payload["data"])


# ---------------------------------------------------------------- hide_zero (design §5.1)


def test_render_skips_hidden_interfaces(network_fields):
    payload = {
        "data": [
            {"interface_name": "eth0", "bytes_recv": 100.0, "bytes_sent": 50.0, "is_up": True, "hidden": False},
            {"interface_name": "lo", "bytes_recv": 0.0, "bytes_sent": 0.0, "is_up": True, "hidden": True},
        ],
        "_levels": {},
    }
    rows = render(payload, network_fields)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "eth0" in flat
    assert "lo" not in flat


def test_render_keeps_row_when_hidden_key_absent(network_fields):
    """Payloads produced before this feature (or by plugins with no
    HIDE_ZERO_FIELDS) never carry `hidden` — must not be treated as hidden."""
    payload = {
        "data": [{"interface_name": "eth0", "bytes_recv": 100.0, "bytes_sent": 50.0, "is_up": True}],
        "_levels": {},
    }
    rows = render(payload, network_fields)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "eth0" in flat


# ---------------------------------------------------------------- alias (design §5.5)


def test_render_displays_alias_instead_of_interface_name(network_fields):
    """v4 parity (`network/__init__.py:262`): when an `alias` is published,
    it REPLACES the raw interface name in the rendered row."""
    payload = {
        "data": [
            {
                "interface_name": "eth0",
                "alias": "WAN",
                "bytes_recv": 0.0,
                "bytes_sent": 0.0,
                "is_up": True,
            },
        ],
        "_levels": {"eth0": {}},
    }
    rows = render(payload, network_fields)
    name_cell = rows[1].cells[0].text
    assert "WAN" in name_cell
    assert "eth0" not in name_cell


def test_render_falls_back_to_interface_name_when_no_alias(network_fields):
    payload = {
        "data": [{"interface_name": "eth0", "bytes_recv": 0.0, "bytes_sent": 0.0, "is_up": True}],
        "_levels": {"eth0": {}},
    }
    rows = render(payload, network_fields)
    assert "eth0" in rows[1].cells[0].text


@pytest.mark.parametrize("scaled", [999.96, 1000.0, 1023.9])
@pytest.mark.parametrize("symbol, factor", [("K", 1024), ("M", 1024**2), ("G", 1024**3)])
def test_rate_between_1000_and_1024_units_fits_the_column(scaled, symbol, factor):
    """`1000.0Kb` is 8 characters in a 7-wide column, shifting Tx/s. The decimal
    is dropped from 999.95 up (v4 auto_unit prints no decimal there)."""
    from glances.plugins.network.render_curses_v5 import _RATE_COL_WIDTH, _format_rate

    text = _format_rate(scaled * factor / 8)
    assert len(text) <= _RATE_COL_WIDTH, text
    assert text.endswith(f"{symbol}b"), text


def test_combined_mode_replaces_the_two_columns_with_their_sum():
    """`T` (v4 `network_sum`).

    v4 renders a dedicated `bytes_all` field its model computes; v5's schema
    has no such field, so the renderer sums the two rates. Same number, and
    the sum of two rates over one interval IS the combined rate.
    """
    from glances.plugins.network.render_curses_v5 import render

    payload = {
        "data": [{"interface_name": "eth0", "bytes_recv": 100.0, "bytes_sent": 25.0, "is_up": True}],
        "_levels": {},
    }
    fields = {"bytes_recv": {"short_name": "Rx/s"}, "bytes_sent": {"short_name": "Tx/s"}}

    apart = render(payload, fields)
    combined = render(payload, fields, view={"network_sum": True})

    assert [c.text.strip() for c in apart[0].cells][1:] == ["Rx/s", "Tx/s"]
    assert [c.text.strip() for c in combined[0].cells][1:] == ["Rx+Tx/s"]
    # 125 B/s x 8 = 1000 bits/s.
    assert [c.text.strip() for c in combined[1].cells][1:] == ["1000b"]


def test_combined_mode_drops_the_per_second_suffix_under_byte():
    """v4 labels it `Rx+Tx` under --byte (`network/__init__.py:246-254`)."""
    from glances.plugins.network.render_curses_v5 import render

    payload = {"data": [], "_levels": {}}
    header = render(payload, {}, view={"network_sum": True, "byte": True})[0]
    assert header.cells[1].text.strip() == "Rx+Tx"


def test_the_combined_cell_carries_no_threshold_colour():
    """The two fields have their own levels; a sum belongs to neither, and v4
    paints its combined cell plain for the same reason."""
    from glances.outputs.curses_renderer_v5 import ColorRole
    from glances.plugins.network.render_curses_v5 import render

    payload = {
        "data": [{"interface_name": "eth0", "bytes_recv": 100.0, "bytes_sent": 25.0, "is_up": True}],
        "_levels": {"eth0": {"bytes_recv": {"level": "critical", "prominent": True}}},
    }
    row = render(payload, {}, view={"network_sum": True})[1]
    assert row.cells[1].color == ColorRole.DEFAULT
    assert row.cells[1].prominent is False


# ---------------------------------------------------------------- `U` cumulative


def _cumul_payload(**overrides):
    item = {
        "interface_name": "eth0",
        "bytes_recv": 100.0,
        "bytes_sent": 25.0,
        "bytes_recv_cumul": 1024 * 1024,
        "bytes_sent_cumul": 1024,
        "is_up": True,
    }
    item.update(overrides)
    return {"data": [item], "_levels": {}}


def test_cumulative_mode_shows_the_counters_under_v4_headers():
    """`U` (v4 `network_cumul`): `Rx` / `Tx`, bits by default like the rates."""
    from glances.plugins.network.model_v5 import PluginModel
    from glances.plugins.network.render_curses_v5 import render

    rows = render(_cumul_payload(), PluginModel.fields_description, view={"network_cumul": True})
    assert [c.text.strip() for c in rows[0].cells][1:] == ["Rx", "Tx"]
    assert [c.text.strip() for c in rows[1].cells][1:] == ["8.0Mb", "8.0Kb"]


def test_cumulative_mode_shows_an_interface_with_no_rate_yet():
    """The counter exists from cycle 1 (v4 tests the raw `bytes_recv` there)."""
    from glances.plugins.network.render_curses_v5 import render

    payload = _cumul_payload(bytes_recv=None, bytes_sent=None)
    assert len(render(payload, {})) == 1, "rate mode: header only"
    assert len(render(payload, {}, view={"network_cumul": True})) == 2


def test_cumulative_cells_keep_the_rate_s_colour():
    """v4 reads the same `bytes_recv` decoration for its cumulative cells."""
    from glances.outputs.curses_renderer_v5 import ColorRole
    from glances.plugins.network.render_curses_v5 import render

    payload = _cumul_payload()
    payload["_levels"] = {"eth0": {"bytes_recv": {"level": "warning", "prominent": False}}}
    row = render(payload, {}, view={"network_cumul": True})[1]
    assert row.cells[1].color is ColorRole.WARNING


def test_cumulative_and_combined_compose_without_the_per_second_suffix():
    """v4: `Rx+Tx` in cumulative mode, even in bits (`network/__init__.py:246`)."""
    from glances.plugins.network.render_curses_v5 import render

    rows = render(_cumul_payload(), {}, view={"network_cumul": True, "network_sum": True})
    assert rows[0].cells[1].text.strip() == "Rx+Tx"
    # (1 MiB + 1 KiB) x 8 bits
    assert rows[1].cells[1].text.strip() == "8.0Mb"
