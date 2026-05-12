"""Glances v5 — tests for the pure curses renderer."""

from __future__ import annotations

from glances.outputs.curses_renderer_v5 import (
    Cell,
    ColorRole,
    Row,
    render_scalar_plugin,
)

# ---------------------------------------------------------------- dataclasses


def test_cell_defaults_to_default_color():
    cell = Cell(text="42")
    assert cell.color == ColorRole.DEFAULT


def test_row_holds_cells():
    row = Row(cells=[Cell("A"), Cell("B")])
    assert [c.text for c in row.cells] == ["A", "B"]


# ---------------------------------------------------------------- scalar plugin


MEM_FIELDS = {
    "total": {"unit": "bytes", "label": "total"},
    "available": {"unit": "bytes", "label": "avail"},
    "percent": {
        "unit": "percent",
        "label": "MEM",
        "watched": True,
        "prominent": True,
    },
    "used": {"unit": "bytes", "label": "used"},
    "free": {"unit": "bytes", "label": "free"},
}


def _mem_payload(level: str = "ok") -> dict:
    return {
        "total": 16_000_000_000,
        "available": 8_000_000_000,
        "percent": 72.0,
        "used": 8_000_000_000,
        "free": 4_000_000_000,
        "_levels": {"percent": {"level": level, "prominent": True}},
    }


def test_render_scalar_returns_at_least_one_row():
    rows = render_scalar_plugin("mem", _mem_payload(), MEM_FIELDS)
    assert len(rows) >= 1


def test_render_scalar_header_includes_plugin_label():
    """The first row carries the plugin's prominent label ('MEM') in upper-case."""
    rows = render_scalar_plugin("mem", _mem_payload(), MEM_FIELDS)
    header = rows[0]
    joined = " ".join(c.text for c in header.cells)
    assert "MEM" in joined


def test_render_scalar_shows_percent_value():
    rows = render_scalar_plugin("mem", _mem_payload(), MEM_FIELDS)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "72.0%" in flat


def test_render_scalar_formats_bytes_fields():
    rows = render_scalar_plugin("mem", _mem_payload(), MEM_FIELDS)
    flat = " ".join(c.text for row in rows for c in row.cells)
    # 16 GB total
    assert "14.9G" in flat or "15.9G" in flat  # 16_000_000_000 / 1024^3 ≈ 14.9


def test_render_scalar_applies_warning_color_on_watched_field():
    rows = render_scalar_plugin("mem", _mem_payload(level="warning"), MEM_FIELDS)
    percent_cells = [c for row in rows for c in row.cells if "%" in c.text]
    assert percent_cells
    assert percent_cells[0].color == ColorRole.WARNING


def test_render_scalar_applies_critical_color_with_prominent():
    rows = render_scalar_plugin("mem", _mem_payload(level="critical"), MEM_FIELDS)
    percent_cells = [c for row in rows for c in row.cells if "%" in c.text]
    assert percent_cells[0].color == ColorRole.CRITICAL
    # prominent=True triggers background-highlight rendering — exposed as
    # the `prominent` flag on the cell so the curses layer can pick the
    # right attribute (A_REVERSE vs plain colour).
    assert percent_cells[0].prominent is True


def test_render_scalar_handles_empty_payload():
    """Cycle-0: plugin registered but no data yet."""
    rows = render_scalar_plugin("mem", {}, MEM_FIELDS)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "MEM" in flat  # header still rendered
    # No percent value — should not crash.


def test_render_scalar_honours_explicit_format_hint():
    fields = {
        "percent": {"unit": "percent", "label": "CPU", "format": "%.3f%%"},
    }
    rows = render_scalar_plugin("cpu", {"percent": 12.345}, fields)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "12.345%" in flat


# ---------------------------------------------------------------- collection plugin


NETWORK_FIELDS = {
    "interface_name": {"unit": "string", "label": "iface", "primary_key": True},
    "bytes_recv": {"unit": "bytespers", "label": "Rx", "rate": True, "watched": True, "prominent": True},
    "bytes_sent": {"unit": "bytespers", "label": "Tx", "rate": True, "watched": True, "prominent": True},
    "is_up": {"unit": "bool", "label": "up"},
}


def _network_payload() -> dict:
    return {
        "data": [
            {"interface_name": "eth0", "bytes_recv": 1200.0, "bytes_sent": 300.0, "is_up": True},
            {"interface_name": "lo", "bytes_recv": 0.0, "bytes_sent": 0.0, "is_up": True},
        ],
        "_levels": {
            "eth0": {
                "bytes_recv": {"level": "warning", "prominent": True},
                "bytes_sent": {"level": "ok", "prominent": True},
            },
            "lo": {
                "bytes_recv": {"level": "ok", "prominent": True},
                "bytes_sent": {"level": "ok", "prominent": True},
            },
        },
    }


def test_render_collection_returns_header_plus_one_row_per_item():
    from glances.outputs.curses_renderer_v5 import render_collection_plugin

    rows = render_collection_plugin("network", _network_payload(), NETWORK_FIELDS)
    # 1 header + 2 interfaces
    assert len(rows) == 3


def test_render_collection_header_uses_plugin_name_uppercase():
    from glances.outputs.curses_renderer_v5 import render_collection_plugin

    rows = render_collection_plugin("network", _network_payload(), NETWORK_FIELDS)
    header_text = " ".join(c.text for c in rows[0].cells)
    assert "NETWORK" in header_text


def test_render_collection_emits_per_item_level_colors():
    from glances.outputs.curses_renderer_v5 import render_collection_plugin

    rows = render_collection_plugin("network", _network_payload(), NETWORK_FIELDS)
    # Find the eth0 row and check Rx cell color.
    eth_row = next(r for r in rows if any("eth0" in c.text for c in r.cells))
    rx_cells = [c for c in eth_row.cells if c.text.endswith("/s") and c.color != ColorRole.DEFAULT]
    assert any(c.color == ColorRole.WARNING for c in rx_cells)


def test_render_collection_skips_filtered_items_handled_upstream():
    """The base class filters items before the renderer sees them."""
    from glances.outputs.curses_renderer_v5 import render_collection_plugin

    payload = {"data": [], "_levels": {}}
    rows = render_collection_plugin("network", payload, NETWORK_FIELDS)
    # Just the header, no item rows.
    assert len(rows) == 1


# ---------------------------------------------------------------- footer


def test_render_alert_footer_shows_recent_events():
    from glances.outputs.curses_renderer_v5 import render_alert_footer

    history = [
        {
            "ts": "2026-05-12T10:00:00+00:00",
            "plugin": "mem",
            "key": None,
            "field": "percent",
            "level": "warning",
            "previous_level": "ok",
            "value": 73.0,
            "prominent": True,
            "hostname": "h",
        },
        {
            "ts": "2026-05-12T10:01:00+00:00",
            "plugin": "network",
            "key": "eth0",
            "field": "bytes_recv",
            "level": "critical",
            "previous_level": "warning",
            "value": 9e7,
            "prominent": True,
            "hostname": "h",
        },
    ]
    rows = render_alert_footer(history, limit=10)
    assert len(rows) == 1 + 2  # header + 2 events
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "mem" in flat
    assert "eth0" in flat


def test_render_alert_footer_truncates_to_limit():
    from glances.outputs.curses_renderer_v5 import render_alert_footer

    history = [
        {
            "ts": f"2026-05-12T10:0{i}:00+00:00",
            "plugin": "mem",
            "key": None,
            "field": "percent",
            "level": "warning",
            "previous_level": "ok",
            "value": 73.0,
            "prominent": True,
            "hostname": "h",
        }
        for i in range(5)
    ]
    rows = render_alert_footer(history, limit=3)
    # 1 header + 3 events (the most recent 3).
    assert len(rows) == 4


def test_render_alert_footer_handles_empty_history():
    from glances.outputs.curses_renderer_v5 import render_alert_footer

    rows = render_alert_footer([], limit=10)
    # Just a header saying "no alerts" or similar — exact wording unspecified,
    # but it must produce at least one row and not crash.
    assert len(rows) >= 1


# ---------------------------------------------------------------- frame builder


def test_build_frame_arranges_scalars_left_collections_right():
    from glances.outputs.curses_renderer_v5 import build_frame

    store_snapshot = {
        "mem": _mem_payload(),
        "network": _network_payload(),
    }
    fields_by_plugin = {
        "mem": MEM_FIELDS,
        "network": NETWORK_FIELDS,
    }
    registry = [("mem", False), ("network", True)]  # (plugin_name, is_collection)

    frame = build_frame(store_snapshot, fields_by_plugin, registry, alerts_history=[])

    # mem is scalar → left column. network is collection → right column.
    assert frame.left
    assert frame.right
    assert any("MEM" in c.text for row in frame.left for c in row.cells)
    assert any("NETWORK" in c.text for row in frame.right for c in row.cells)


def test_build_frame_handles_missing_plugin_payload():
    """A plugin in the registry but absent from the store (cycle-0)."""
    from glances.outputs.curses_renderer_v5 import build_frame

    frame = build_frame(
        store_snapshot={},
        fields_by_plugin={"mem": MEM_FIELDS},
        registry=[("mem", False)],
        alerts_history=[],
    )
    # Header rendered, no value rows.
    flat = " ".join(c.text for row in frame.left for c in row.cells)
    assert "MEM" in flat
