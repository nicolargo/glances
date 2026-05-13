"""Glances v5 — tests for the pure curses renderer."""

from __future__ import annotations

from glances.outputs.curses_renderer_v5 import (
    Cell,
    ColorRole,
    Frame,
    PluginBlock,
    Row,
    _reset_plugin_renderer_cache,
    build_frame,
    render_alert_block,
    render_collection_plugin,
    render_scalar_plugin,
    slot_for,
)

# --------------------------------------------------------------- dataclasses


def test_cell_defaults_to_default_color():
    cell = Cell(text="42")
    assert cell.color == ColorRole.DEFAULT


def test_row_holds_cells():
    row = Row(cells=[Cell("A"), Cell("B")])
    assert [c.text for c in row.cells] == ["A", "B"]


def test_pluginblock_height_and_width():
    block = PluginBlock(
        name="cpu",
        rows=[
            Row(cells=[Cell("CPU"), Cell("12.3%")]),
            Row(cells=[Cell("user:"), Cell("8.1%")]),
        ],
    )
    assert block.height == 2
    # "CPU" + " " + "12.3%" = 9; "user:" + " " + "8.1%" = 10
    assert block.width == 10


# --------------------------------------------------------------- slot routing


def test_slot_for_cpu_is_top():
    assert slot_for("cpu") == "top"


def test_slot_for_mem_is_top():
    assert slot_for("mem") == "top"


def test_slot_for_load_is_top():
    assert slot_for("load") == "top"


def test_slot_for_percpu_is_top():
    assert slot_for("percpu") == "top"


def test_slot_for_network_is_left():
    assert slot_for("network") == "left"


def test_slot_for_alert_is_right():
    assert slot_for("alert") == "right"


def test_slot_for_processlist_is_right():
    assert slot_for("processlist") == "right"


def test_slot_for_unknown_plugin_defaults_to_left():
    assert slot_for("unknownplugin") == "left"


# --------------------------------------------------------------- scalar plugin


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
    assert percent_cells[0].prominent is True


def test_render_scalar_handles_empty_payload():
    """Cycle-0: plugin registered but no data yet."""
    rows = render_scalar_plugin("mem", {}, MEM_FIELDS)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "MEM" in flat  # header still rendered


def test_render_scalar_honours_explicit_format_hint():
    fields = {
        "percent": {"unit": "percent", "label": "CPU", "format": "%.3f%%"},
    }
    rows = render_scalar_plugin("cpu", {"percent": 12.345}, fields)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "12.345%" in flat


def test_render_scalar_skips_internal_fields():
    """`internal: True` fields (e.g. time_since_update, cpucore) are
    never displayed — they support computation only."""
    fields = {
        "percent": {"unit": "percent", "label": "CPU", "watched": True},
        "time_since_update": {"unit": "seconds", "internal": True},
        "cpucore": {"unit": "number", "label": "cores", "internal": True},
        "user": {"unit": "percent", "label": "user"},
    }
    payload = {"percent": 12.0, "time_since_update": 1.5, "cpucore": 8, "user": 5.0}
    rows = render_scalar_plugin("cpu", payload, fields)

    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "time_since_update" not in flat
    assert "cpucore" not in flat
    assert "cores" not in flat
    # But declared visible fields are still rendered.
    assert "user" in flat
    assert "CPU" in flat


def test_render_scalar_aligns_columns_as_two_column_table():
    """Labels are left-padded, values right-padded; widths fit the widest."""
    fields = {
        "percent": {"unit": "percent", "label": "CPU", "watched": True},
        "user": {"unit": "percent", "label": "user"},
        "system": {"unit": "percent", "label": "system"},
    }
    payload = {"percent": 12.0, "user": 5.0, "system": 100.0}
    rows = render_scalar_plugin("cpu", payload, fields)

    # All label cells should be padded to the same width.
    label_widths = {len(r.cells[0].text) for r in rows if r.cells}
    assert len(label_widths) == 1, f"label cells not aligned: {label_widths}"
    # Same for value cells.
    value_widths = {len(r.cells[1].text) for r in rows if len(r.cells) >= 2}
    assert len(value_widths) == 1, f"value cells not aligned: {value_widths}"

    # Label cell text must end with spaces (left-aligned within its column).
    assert rows[1].cells[0].text == "user  "  # "user" padded to 6 ("system" is widest)
    # Value cell must start with spaces (right-aligned within its column).
    assert rows[1].cells[1].text == "  5.0%"  # "5.0%" right-padded to 6 ("100.0%" is widest)


def test_render_collection_skips_internal_fields():
    fields = {
        "interface_name": {"unit": "string", "label": "iface", "primary_key": True},
        "bytes_recv": {"unit": "bytespers", "label": "Rx"},
        "time_since_update": {"unit": "seconds", "internal": True},
    }
    payload = {
        "data": [{"interface_name": "eth0", "bytes_recv": 1024.0, "time_since_update": 1.5}],
        "_levels": {},
    }
    rows = render_collection_plugin("network", payload, fields)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "time_since_update" not in flat
    # Header should NOT include a time_since_update column.
    header_text = " ".join(c.text for c in rows[0].cells)
    assert "time_since_update" not in header_text


def test_render_scalar_value_width_floored_per_unit():
    """Value cells are padded to a minimum width derived from `unit`, so
    column widths don't jiggle cycle-to-cycle (percent → 6 chars min)."""
    fields = {
        "percent": {"unit": "percent", "label": "CPU", "watched": True},
        "user": {"unit": "percent", "label": "user"},
    }
    # Cycle A: small value (4 chars formatted).
    rows_a = render_scalar_plugin("cpu", {"percent": 5.0, "user": 1.0}, fields)
    # Cycle B: large value (6 chars formatted).
    rows_b = render_scalar_plugin("cpu", {"percent": 100.0, "user": 99.9}, fields)

    # In both cycles every value cell must be at least 6 chars wide.
    for rows in (rows_a, rows_b):
        for row in rows:
            if len(row.cells) >= 2:
                assert len(row.cells[1].text) >= 6, f"value cell too narrow: {row.cells[1].text!r}"

    # Same alignment width in both cycles.
    value_widths_a = {len(r.cells[1].text) for r in rows_a if len(r.cells) >= 2}
    value_widths_b = {len(r.cells[1].text) for r in rows_b if len(r.cells) >= 2}
    assert value_widths_a == value_widths_b


def test_render_collection_aligns_columns():
    """All cells in the same column share the same padded width."""
    fields = {
        "interface_name": {"unit": "string", "label": "iface", "primary_key": True},
        "bytes_recv": {"unit": "bytespers", "label": "Rx"},
        "bytes_sent": {"unit": "bytespers", "label": "Tx"},
    }
    payload = {
        "data": [
            {"interface_name": "eth0", "bytes_recv": 1024.0, "bytes_sent": 256.0},
            {"interface_name": "wlp0s20f3", "bytes_recv": 12345.0, "bytes_sent": 9876.0},
        ],
        "_levels": {},
    }
    rows = render_collection_plugin("network", payload, fields)

    # Each column has uniform width across rows.
    for col_idx in range(len(rows[0].cells)):
        widths = {len(r.cells[col_idx].text) for r in rows if col_idx < len(r.cells)}
        assert len(widths) == 1, f"col {col_idx} widths differ: {widths}"


# --------------------------------------------------------------- collection plugin


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
    rows = render_collection_plugin("network", _network_payload(), NETWORK_FIELDS)
    # 1 header + 2 interfaces
    assert len(rows) == 3


def test_render_collection_header_uses_plugin_name_uppercase():
    rows = render_collection_plugin("network", _network_payload(), NETWORK_FIELDS)
    header_text = " ".join(c.text for c in rows[0].cells)
    assert "NETWORK" in header_text


def test_render_collection_emits_per_item_level_colors():
    rows = render_collection_plugin("network", _network_payload(), NETWORK_FIELDS)
    eth_row = next(r for r in rows if any("eth0" in c.text for c in r.cells))
    rx_cells = [c for c in eth_row.cells if c.text.endswith("/s") and c.color != ColorRole.DEFAULT]
    assert any(c.color == ColorRole.WARNING for c in rx_cells)


def test_render_collection_skips_filtered_items_handled_upstream():
    """The base class filters items before the renderer sees them."""
    payload = {"data": [], "_levels": {}}
    rows = render_collection_plugin("network", payload, NETWORK_FIELDS)
    assert len(rows) == 1


# --------------------------------------------------------------- alert block


def test_render_alert_block_shows_recent_events():
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
    rows = render_alert_block(history, limit=10)
    assert len(rows) == 1 + 2
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "mem" in flat
    assert "eth0" in flat


def test_render_alert_block_truncates_to_limit():
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
    rows = render_alert_block(history, limit=3)
    assert len(rows) == 4


def test_render_alert_block_handles_empty_history():
    rows = render_alert_block([], limit=10)
    assert len(rows) >= 1


# --------------------------------------------------------------- frame builder


def test_build_frame_routes_cpu_mem_load_to_top_slot():
    """cpu, mem, load → top row (horizontal), matching v4's `_top` list."""
    store_snapshot = {
        "cpu": {"percent": 12.0, "_levels": {"percent": {"level": "ok"}}},
        "mem": _mem_payload(),
        "load": {"min1": 0.5, "_levels": {"min1": {"level": "ok"}}},
    }
    fields_by_plugin = {
        "cpu": {"percent": {"unit": "percent", "label": "CPU", "watched": True}},
        "mem": MEM_FIELDS,
        "load": {"min1": {"unit": "number", "label": "1 min", "watched": True}},
    }
    registry = [("cpu", False), ("mem", False), ("load", False)]

    frame = build_frame(store_snapshot, fields_by_plugin, registry, alerts_history=[])

    top_names = [b.name for b in frame.top]
    assert top_names == ["cpu", "mem", "load"]
    assert all(isinstance(b, PluginBlock) for b in frame.top)


def test_build_frame_routes_network_to_left_slot():
    """network → left sidebar, matching v4's `_left_sidebar`."""
    store_snapshot = {"network": _network_payload()}
    fields_by_plugin = {"network": NETWORK_FIELDS}
    registry = [("network", True)]

    frame = build_frame(store_snapshot, fields_by_plugin, registry, alerts_history=[])

    assert [b.name for b in frame.left] == ["network"]
    assert frame.top == []


def test_build_frame_synthesizes_alert_block_in_right_slot():
    """Alerts always appear in the right slot, even with no plugins."""
    frame = build_frame(
        store_snapshot={},
        fields_by_plugin={},
        registry=[],
        alerts_history=[],
    )
    assert [b.name for b in frame.right] == ["alert"]


def test_build_frame_alert_block_carries_history():
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
    ]
    frame = build_frame({}, {}, [], alerts_history=history)
    alert_block = frame.right[0]
    flat = " ".join(c.text for row in alert_block.rows for c in row.cells)
    assert "mem" in flat


def test_build_frame_orders_top_slot_per_v4_list():
    """Even if discovery yields plugins alphabetically (cpu, load, mem),
    the top slot must render them in the v4-declared order (cpu, mem, load)."""
    store_snapshot = {
        "cpu": {"percent": 12.0, "_levels": {"percent": {"level": "ok"}}},
        "load": {"min1": 0.5, "_levels": {"min1": {"level": "ok"}}},
        "mem": _mem_payload(),
    }
    fields_by_plugin = {
        "cpu": {"percent": {"unit": "percent", "label": "CPU", "watched": True}},
        "load": {"min1": {"unit": "number", "label": "1 min", "watched": True}},
        "mem": MEM_FIELDS,
    }
    # Discovery order is alphabetical → cpu, load, mem.
    registry = [("cpu", False), ("load", False), ("mem", False)]

    frame = build_frame(store_snapshot, fields_by_plugin, registry, alerts_history=[])

    top_names = [b.name for b in frame.top]
    assert top_names == ["cpu", "mem", "load"], f"top order wrong: {top_names}"


def test_build_frame_full_layout():
    """Mixed registry: cpu/mem in top, network in left, alert in right."""
    store_snapshot = {
        "cpu": {"percent": 25.0, "_levels": {"percent": {"level": "ok"}}},
        "mem": _mem_payload(),
        "network": _network_payload(),
    }
    fields_by_plugin = {
        "cpu": {"percent": {"unit": "percent", "label": "CPU", "watched": True}},
        "mem": MEM_FIELDS,
        "network": NETWORK_FIELDS,
    }
    registry = [("cpu", False), ("mem", False), ("network", True)]

    frame = build_frame(store_snapshot, fields_by_plugin, registry, alerts_history=[])

    assert [b.name for b in frame.top] == ["cpu", "mem"]
    assert [b.name for b in frame.left] == ["network"]
    assert [b.name for b in frame.right] == ["alert"]


def test_build_frame_handles_missing_plugin_payload():
    """A plugin in the registry but absent from the store (cycle-0)."""
    frame = build_frame(
        store_snapshot={},
        fields_by_plugin={"mem": MEM_FIELDS},
        registry=[("mem", False)],
        alerts_history=[],
    )
    mem_block = next(b for b in frame.top if b.name == "mem")
    flat = " ".join(c.text for row in mem_block.rows for c in row.cells)
    assert "MEM" in flat


def test_build_frame_returns_a_frame_instance():
    frame = build_frame({}, {}, [], [])
    assert isinstance(frame, Frame)


# --------------------------------------------------------------- dynamic title role


def test_title_role_returns_header_when_no_prominent_escalation():
    from glances.outputs.curses_renderer_v5 import title_role

    payload = {
        "percent": 30.0,
        "_levels": {"percent": {"level": "ok", "prominent": True}},
    }
    assert title_role(payload) == ColorRole.HEADER


def test_title_role_stays_header_when_prominent_at_careful():
    """careful does NOT escalate the title — only warning/critical do."""
    from glances.outputs.curses_renderer_v5 import title_role

    payload = {"_levels": {"percent": {"level": "careful", "prominent": True}}}
    assert title_role(payload) == ColorRole.HEADER


def test_title_role_returns_warning_when_prominent_at_warning():
    from glances.outputs.curses_renderer_v5 import title_role

    payload = {"_levels": {"percent": {"level": "warning", "prominent": True}}}
    assert title_role(payload) == ColorRole.WARNING


def test_title_role_returns_critical_for_worst_level():
    """Multiple prominent fields — the worst level wins."""
    from glances.outputs.curses_renderer_v5 import title_role

    payload = {
        "_levels": {
            "percent": {"level": "warning", "prominent": True},
            "steal": {"level": "critical", "prominent": True},
            "iowait": {"level": "careful", "prominent": True},
        },
    }
    assert title_role(payload) == ColorRole.CRITICAL


def test_title_role_ignores_non_prominent_escalations():
    """A non-prominent field at critical doesn't promote the title color."""
    from glances.outputs.curses_renderer_v5 import title_role

    payload = {
        "_levels": {
            "irq": {"level": "critical", "prominent": False},
            "percent": {"level": "ok", "prominent": True},
        },
    }
    assert title_role(payload) == ColorRole.HEADER


def test_title_role_handles_collection_levels():
    """Collection plugins use a nested `_levels`: {pk: {field: {level, prominent}}}."""
    from glances.outputs.curses_renderer_v5 import title_role

    payload = {
        "_levels": {
            "eth0": {
                "bytes_recv": {"level": "warning", "prominent": True},
            },
            "lo": {"bytes_recv": {"level": "ok", "prominent": True}},
        },
    }
    assert title_role(payload) == ColorRole.WARNING


def test_title_role_handles_empty_payload():
    from glances.outputs.curses_renderer_v5 import title_role

    assert title_role({}) == ColorRole.HEADER


def test_cell_supports_bold_flag():
    """Cell carries an explicit `bold` field for non-HEADER colour cells
    that should still render bold (e.g. alert-coloured plugin titles)."""
    c = Cell(text="MEM", color=ColorRole.CRITICAL, bold=True)
    assert c.bold is True
    # default still False
    assert Cell(text="x").bold is False


# --------------------------------------------------------------- field_label


def test_field_label_returns_label_by_default():
    from glances.outputs.curses_renderer_v5 import field_label

    schema = {"label": "ctx switches", "short_name": "ctx_sw"}
    assert field_label(schema, "ctx_switches") == "ctx switches"


def test_field_label_prefers_short_name_when_requested():
    from glances.outputs.curses_renderer_v5 import field_label

    schema = {"label": "ctx switches", "short_name": "ctx_sw"}
    assert field_label(schema, "ctx_switches", prefer_short=True) == "ctx_sw"


def test_field_label_falls_back_to_label_when_short_missing():
    from glances.outputs.curses_renderer_v5 import field_label

    schema = {"label": "ctx switches"}
    assert field_label(schema, "ctx_switches", prefer_short=True) == "ctx switches"


def test_field_label_falls_back_to_field_name_when_nothing_set():
    from glances.outputs.curses_renderer_v5 import field_label

    assert field_label({}, "ctx_switches") == "ctx_switches"
    assert field_label({}, "ctx_switches", prefer_short=True) == "ctx_switches"


# --------------------------------------------------------------- per-plugin renderer discovery


def test_build_frame_uses_custom_renderer_when_available(monkeypatch):
    """If `glances.plugins.<name>.render_curses_v5` exposes `render()`,
    it overrides the generic fallback."""
    import sys
    import types

    _reset_plugin_renderer_cache()

    sentinel_rows = [
        Row(cells=[Cell(text="MYCUSTOM"), Cell(text="42")]),
        Row(cells=[Cell(text="hello"), Cell(text="world")]),
    ]
    fake_module = types.ModuleType("glances.plugins.fakecpu.render_curses_v5")
    fake_module.render = lambda payload, fields_desc: sentinel_rows  # noqa: E731
    monkeypatch.setitem(sys.modules, "glances.plugins.fakecpu.render_curses_v5", fake_module)
    # Also mark fakecpu as a TOP-slot plugin via the constants — we monkeypatch by adding
    # to the TOP_SLOT tuple at module level.
    monkeypatch.setattr(
        "glances.outputs.curses_renderer_v5.TOP_SLOT",
        ("fakecpu",),
    )

    frame = build_frame(
        store_snapshot={"fakecpu": {"value": 42}},
        fields_by_plugin={"fakecpu": {"value": {"unit": "number"}}},
        registry=[("fakecpu", False)],
        alerts_history=[],
    )

    assert len(frame.top) == 1
    assert frame.top[0].rows == sentinel_rows
    _reset_plugin_renderer_cache()


def test_build_frame_falls_back_to_generic_when_no_custom_renderer():
    """A plugin without a `render_curses_v5` module gets the generic renderer."""
    _reset_plugin_renderer_cache()

    fields = {
        "percent": {"unit": "percent", "label": "MEM", "watched": True},
    }
    frame = build_frame(
        store_snapshot={"mem": {"percent": 50.0}},
        fields_by_plugin={"mem": fields},
        registry=[("mem", False)],
        alerts_history=[],
    )
    mem_block = next(b for b in frame.top if b.name == "mem")
    flat = " ".join(c.text for row in mem_block.rows for c in row.cells)
    assert "MEM" in flat
    assert "50.0%" in flat


def test_build_frame_custom_renderer_exception_falls_back_safely(monkeypatch):
    """If the custom renderer raises, we fall back to the generic one for this cycle."""
    import sys
    import types

    _reset_plugin_renderer_cache()

    def boom(payload, fields_desc):
        raise RuntimeError("custom renderer broke")

    fake_module = types.ModuleType("glances.plugins.brokenplug.render_curses_v5")
    fake_module.render = boom
    monkeypatch.setitem(sys.modules, "glances.plugins.brokenplug.render_curses_v5", fake_module)
    monkeypatch.setattr(
        "glances.outputs.curses_renderer_v5.TOP_SLOT",
        ("brokenplug",),
    )

    fields = {"value": {"unit": "number", "label": "VAL", "watched": True}}
    frame = build_frame(
        store_snapshot={"brokenplug": {"value": 1}},
        fields_by_plugin={"brokenplug": fields},
        registry=[("brokenplug", False)],
        alerts_history=[],
    )
    # Should not crash; block exists with generic-rendered content.
    assert len(frame.top) == 1
    flat = " ".join(c.text for row in frame.top[0].rows for c in row.cells)
    assert "VAL" in flat
    _reset_plugin_renderer_cache()
