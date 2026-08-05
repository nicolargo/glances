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


def test_render_alert_block_empty_history_shows_no_alert_detected_when_settled():
    """Settled (initializing=False), empty history → a single header line
    ``ALERT (no alert detected)``. No separate placeholder row, no
    ``0 ongoing / 0 total`` count."""
    rows = render_alert_block([], limit=10, is_initializing=False)
    assert len(rows) == 1
    cell = rows[0].cells[0]
    assert cell.text == "ALERT (no alert detected)"
    assert cell.color == ColorRole.HEADER
    assert "initializing" not in cell.text
    assert "ongoing" not in cell.text


def test_render_alert_block_empty_history_shows_initializing_during_warmup():
    """is_initializing=True (warmup), empty history → a single header line
    ``ALERT (initializing)`` so the user knows alerts can't have fired yet."""
    rows = render_alert_block([], limit=10, is_initializing=True)
    assert len(rows) == 1
    cell = rows[0].cells[0]
    assert cell.text == "ALERT (initializing)"
    assert cell.color == ColorRole.HEADER
    assert "no alert detected" not in cell.text


def test_format_alert_time_same_day_returns_hms_local():
    """Same-day event → ``HH:MM:SS`` in local timezone."""
    from datetime import datetime, timezone

    from glances.outputs.curses_renderer_v5 import _format_alert_time

    # UTC noon → local time (whatever the test machine TZ is).
    ts = "2026-05-15T12:00:00+00:00"
    now_utc = datetime(2026, 5, 15, 14, 0, 0, tzinfo=timezone.utc)
    result = _format_alert_time(ts, now=now_utc)
    # Must be exactly 8 chars HH:MM:SS — no date, no TZ suffix.
    assert len(result) == 8
    assert result[2] == ":" and result[5] == ":"


def test_format_alert_time_other_day_includes_date():
    """Event from another day → date prefix included."""
    from datetime import datetime, timezone

    from glances.outputs.curses_renderer_v5 import _format_alert_time

    ts = "2026-05-13T12:00:00+00:00"  # 2 days ago
    now_utc = datetime(2026, 5, 15, 14, 0, 0, tzinfo=timezone.utc)
    result = _format_alert_time(ts, now=now_utc)
    # Must include date — at least "05-13" or "05/13" depending on style.
    assert "05" in result and "13" in result
    # And the time component is still present.
    assert ":" in result


def test_format_alert_time_naive_utc_is_handled():
    """If the timestamp lacks tzinfo, treat it as UTC (matches v5 emitter)."""
    from datetime import datetime, timezone

    from glances.outputs.curses_renderer_v5 import _format_alert_time

    ts = "2026-05-15T12:00:00"  # no tz suffix
    now_utc = datetime(2026, 5, 15, 14, 0, 0, tzinfo=timezone.utc)
    result = _format_alert_time(ts, now=now_utc)
    # Same-day → 8 chars HH:MM:SS.
    assert len(result) == 8


def test_format_alert_time_malformed_falls_back():
    """Unparseable input falls back to the raw HH:MM:SS slice — no crash."""
    from glances.outputs.curses_renderer_v5 import _format_alert_time

    result = _format_alert_time("not-a-timestamp")
    # Falls back to the original first 8 chars; the renderer just shows
    # whatever it has. The contract is "must not raise".
    assert isinstance(result, str)


def test_format_alert_duration_elapsed():
    """Elapsed time since the transition, formatted H:MM:SS, no microseconds."""
    from datetime import datetime, timezone

    from glances.outputs.curses_renderer_v5 import _format_alert_duration

    ts = "2026-05-15T08:00:00+00:00"
    now = datetime(2026, 5, 15, 8, 5, 30, 500000, tzinfo=timezone.utc)
    assert _format_alert_duration(ts, now=now) == "0:05:30"


def test_format_alert_duration_naive_ts_assumed_utc():
    """A naive ISO timestamp (as emitted by _build_event) is treated as UTC."""
    from datetime import datetime, timezone

    from glances.outputs.curses_renderer_v5 import _format_alert_duration

    now = datetime(2026, 5, 15, 8, 1, 0, tzinfo=timezone.utc)
    assert _format_alert_duration("2026-05-15T08:00:00", now=now) == "0:01:00"


def test_format_alert_duration_malformed_returns_none():
    """Unparseable timestamp → None so the caller drops the duration."""
    from glances.outputs.curses_renderer_v5 import _format_alert_duration

    assert _format_alert_duration("not-a-timestamp") is None


def test_format_alert_duration_future_returns_none():
    """Clock skew (ts in the future) → None rather than a negative duration."""
    from datetime import datetime, timezone

    from glances.outputs.curses_renderer_v5 import _format_alert_duration

    now = datetime(2026, 5, 15, 8, 0, 0, tzinfo=timezone.utc)
    assert _format_alert_duration("2026-05-15T08:05:00+00:00", now=now) is None


def test_render_alert_block_uses_local_time_for_events():
    """End-to-end: render_alert_block formats the ts via the local converter.
    We pick a UTC timestamp and assert it does NOT appear verbatim (a TZ
    conversion or local format must have happened)."""
    from datetime import datetime, timezone

    history = [
        {
            "ts": "2026-05-13T12:00:00+00:00",  # 2 days old in UTC
            "plugin": "mem",
            "key": None,
            "field": "percent",
            "level": "warning",
            "previous_level": "careful",
            "value": 75.0,
            "prominent": True,
            "is_initial": False,
            "hostname": "h",
        },
    ]
    # Pin "now" to keep the date-vs-hour decision deterministic.
    rows = render_alert_block(
        history,
        limit=10,
        is_initializing=False,
        now=datetime(2026, 5, 15, 14, 0, 0, tzinfo=timezone.utc),
    )
    flat = " ".join(c.text for row in rows for c in row.cells)
    # Date prefix expected (event is 2 days old).
    assert "05" in flat
    assert "13" in flat


def test_render_alert_block_nonempty_history_ignores_initializing_flag():
    """Once we have events the warmup flag is irrelevant — show the events."""
    history = [
        {
            "ts": "2026-05-15T14:00:00+00:00",
            "plugin": "mem",
            "key": None,
            "field": "percent",
            "level": "careful",
            "previous_level": "ok",
            "value": 60.0,
            "prominent": True,
            "is_initial": True,
            "hostname": "h",
        },
    ]
    rows = render_alert_block(history, limit=10, is_initializing=True)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "initializing" not in flat
    assert "careful" in flat


def test_render_alert_block_header_uses_new_ongoing_total_format():
    """Header is ``ALERT (<n> ongoing / <m> total)``."""
    history = [
        # Ongoing: warning, no resolution after.
        {
            "ts": "2026-05-15T08:00:00+00:00",
            "plugin": "mem",
            "key": None,
            "field": "percent",
            "level": "warning",
            "previous_level": "careful",
            "is_initial": False,
            "prominent": True,
            "value": 75.0,
            "hostname": "h",
        },
        # Resolved: warning → ok.
        {
            "ts": "2026-05-15T09:00:00+00:00",
            "plugin": "cpu",
            "key": None,
            "field": "total",
            "level": "ok",
            "previous_level": "warning",
            "is_initial": False,
            "prominent": True,
            "value": 30.0,
            "hostname": "h",
        },
    ]
    rows = render_alert_block(history, limit=10)
    header = rows[0].cells[0].text
    assert "ALERT" in header
    assert "1 ongoing" in header
    assert "2 total" in header


def test_render_alert_block_ongoing_event_carries_marker():
    """Latest event per (plugin, key, field) with non-ok level is marked
    ongoing, with the elapsed duration since its transition."""
    from datetime import datetime, timezone

    history = [
        {
            "ts": "2026-05-15T08:00:00+00:00",
            "plugin": "mem",
            "key": None,
            "field": "percent",
            "level": "careful",
            "previous_level": "ok",
            "is_initial": True,
            "prominent": True,
            "value": 60.0,
            "hostname": "h",
        },
    ]
    # Fixed "now" = 1h 23m 45s after the transition → deterministic duration.
    now = datetime(2026, 5, 15, 9, 23, 45, tzinfo=timezone.utc)
    rows = render_alert_block(history, limit=10, now=now)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "ongoing for 1:23:45" in flat


def test_render_alert_block_resolution_event_not_marked_ongoing():
    """``warning → ok`` is a resolution. Not ongoing."""
    history = [
        {
            "ts": "2026-05-15T08:00:00+00:00",
            "plugin": "mem",
            "key": None,
            "field": "percent",
            "level": "ok",
            "previous_level": "warning",
            "is_initial": False,
            "prominent": True,
            "value": 30.0,
            "hostname": "h",
        },
    ]
    rows = render_alert_block(history, limit=10)
    # Check only data rows (the header carries the ongoing/total counts and
    # would match the substring otherwise).
    data_flat = " ".join(c.text for row in rows[1:] for c in row.cells)
    assert "ongoing" not in data_flat
    # Header reflects "0 ongoing / 1 total".
    header = rows[0].cells[0].text
    assert "0 ongoing" in header
    assert "1 total" in header


def test_render_alert_block_only_latest_per_tuple_is_ongoing():
    """Two events for the same (plugin, key, field) — older non-ok is no
    longer ongoing once a newer event arrives."""
    history = [
        # Older non-ok.
        {
            "ts": "2026-05-15T08:00:00+00:00",
            "plugin": "mem",
            "key": None,
            "field": "percent",
            "level": "warning",
            "previous_level": "careful",
            "is_initial": False,
            "prominent": True,
            "value": 75.0,
            "hostname": "h",
        },
        # Newer resolution.
        {
            "ts": "2026-05-15T08:05:00+00:00",
            "plugin": "mem",
            "key": None,
            "field": "percent",
            "level": "ok",
            "previous_level": "warning",
            "is_initial": False,
            "prominent": True,
            "value": 30.0,
            "hostname": "h",
        },
    ]
    rows = render_alert_block(history, limit=10)
    data_flat = " ".join(c.text for row in rows[1:] for c in row.cells)
    # Neither data row is ongoing — resolved.
    assert "ongoing" not in data_flat
    header = rows[0].cells[0].text
    assert "0 ongoing" in header


def test_render_alert_block_initial_state_omits_arrow():
    """is_initial=True events render as the bare level (no `ok → ...` arrow)."""
    history = [
        {
            "ts": "2026-05-15T14:00:00+00:00",
            "plugin": "mem",
            "key": None,
            "field": "percent",
            "level": "careful",
            "previous_level": "ok",
            "value": 60.0,
            "prominent": True,
            "is_initial": True,
            "hostname": "h",
        },
    ]
    rows = render_alert_block(history, limit=10)
    flat = " ".join(c.text for row in rows for c in row.cells)
    # The arrow is for real transitions only.
    assert "→" not in flat
    # The level itself must still appear so operators see the steady state.
    assert "careful" in flat


def test_render_alert_block_transition_keeps_arrow():
    """is_initial=False (or absent) events render as `previous → new` (v5 default)."""
    history = [
        {
            "ts": "2026-05-15T14:01:00+00:00",
            "plugin": "mem",
            "key": None,
            "field": "percent",
            "level": "warning",
            "previous_level": "careful",
            "value": 75.0,
            "prominent": True,
            "is_initial": False,
            "hostname": "h",
        },
    ]
    rows = render_alert_block(history, limit=10)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "→" in flat
    assert "careful" in flat
    assert "warning" in flat


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


def test_build_frame_drops_empty_collection_plugin():
    """v4 parity: a collection (list) plugin with an empty list renders nothing
    at all — not even its header. It must contribute NO block to any slot."""
    store_snapshot = {"network": {"data": [], "_levels": {}}}
    fields_by_plugin = {"network": NETWORK_FIELDS}
    registry = [("network", True)]

    frame = build_frame(store_snapshot, fields_by_plugin, registry, alerts_history=[])

    assert frame.left == []
    assert frame.top == []
    assert [b.name for b in frame.header] == []


def test_build_frame_drops_absent_collection_plugin():
    """A collection plugin with no payload at all (disabled / not yet polled)
    is likewise dropped — no lonely header."""
    registry = [("network", True)]

    frame = build_frame({}, {"network": NETWORK_FIELDS}, registry, alerts_history=[])

    assert frame.left == []


def test_build_frame_keeps_non_empty_collection_plugin():
    """Control: the same plugin WITH list data still produces its block."""
    store_snapshot = {"network": _network_payload()}
    fields_by_plugin = {"network": NETWORK_FIELDS}
    registry = [("network", True)]

    frame = build_frame(store_snapshot, fields_by_plugin, registry, alerts_history=[])

    assert [b.name for b in frame.left] == ["network"]


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


def test_full_quicklook_hides_top_siblings():
    """In full-quicklook mode, TOP-slot siblings cpu/mem are hidden so
    quicklook spans the full width; quicklook itself and LEFT plugins stay.

    EXACT v4 parity (`enable_fullquicklook`, glances_curses.py:455): only
    cpu/npu/mpp/gpu/mem/memswap are disabled — `load` and `percpu` MUST
    stay visible. Hiding them would be a regression.
    """
    store_snapshot = {
        "quicklook": {"cpu": 12.0, "_levels": {"cpu": {"level": "ok"}}},
        "cpu": {"percent": 25.0, "_levels": {"percent": {"level": "ok"}}},
        "percpu": {"data": [{"cpu_number": 0, "total": 5.0}]},
        "mem": _mem_payload(),
        "load": {"min1": 0.5, "_levels": {}},
        "network": _network_payload(),
    }
    fields_by_plugin = {
        "quicklook": {"cpu": {"unit": "percent", "label": "CPU", "watched": True}},
        "cpu": {"percent": {"unit": "percent", "label": "CPU", "watched": True}},
        "percpu": {"cpu_number": {"unit": "number", "primary_key": True}},
        "mem": MEM_FIELDS,
        "load": {"min1": {"unit": "number", "label": "1 min", "watched": True}},
        "network": NETWORK_FIELDS,
    }
    registry = [
        ("quicklook", False),
        ("cpu", False),
        ("percpu", True),
        ("mem", False),
        ("load", False),
        ("network", True),
    ]

    frame = build_frame(
        store_snapshot,
        fields_by_plugin,
        registry,
        alerts_history=[],
        view={"full_quicklook": True},
    )

    top_names = [b.name for b in frame.top]
    # v4 parity: quicklook stays, and so do load + percpu.
    assert "quicklook" in top_names
    assert "load" in top_names
    assert "percpu" in top_names
    # cpu/mem are the hidden siblings.
    assert "cpu" not in top_names
    assert "mem" not in top_names
    assert [b.name for b in frame.left] == ["network"]


def test_no_full_quicklook_keeps_all_top():
    """Without full-quicklook, all TOP-slot plugins are rendered as usual."""
    store_snapshot = {
        "quicklook": {"cpu": 12.0, "_levels": {"cpu": {"level": "ok"}}},
        "cpu": {"percent": 25.0, "_levels": {"percent": {"level": "ok"}}},
        "mem": _mem_payload(),
        "network": _network_payload(),
    }
    fields_by_plugin = {
        "quicklook": {"cpu": {"unit": "percent", "label": "CPU", "watched": True}},
        "cpu": {"percent": {"unit": "percent", "label": "CPU", "watched": True}},
        "mem": MEM_FIELDS,
        "network": NETWORK_FIELDS,
    }
    registry = [
        ("quicklook", False),
        ("cpu", False),
        ("mem", False),
        ("network", True),
    ]

    frame = build_frame(
        store_snapshot,
        fields_by_plugin,
        registry,
        alerts_history=[],
        view={"full_quicklook": False},
    )

    top_names = [b.name for b in frame.top]
    assert top_names == ["quicklook", "cpu", "mem"]
    assert [b.name for b in frame.left] == ["network"]


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


# --------------------------------------------------------------- glue width


def test_pluginblock_width_counts_one_space_between_cells():
    block = PluginBlock(name="x", rows=[Row(cells=[Cell("ab"), Cell("cd")])])
    # "ab" + " " + "cd" = 5
    assert block.width == 5


def test_pluginblock_width_glue_cell_has_no_separator():
    block = PluginBlock(name="x", rows=[Row(cells=[Cell("ab"), Cell("cd", glue=True)])])
    # glued: "ab" + "cd" = 4 (no separator space)
    assert block.width == 4


# --------------------------------------------------------------- header slot


def test_slot_for_header_plugins():
    assert slot_for("system") == "header"
    assert slot_for("uptime") == "header"
    assert slot_for("cpu") == "top"
    assert slot_for("network") == "left"


def test_header_slot_orders_ip_between_system_and_uptime():
    from glances.outputs.curses_renderer_v5 import HEADER_SLOT

    assert HEADER_SLOT[:3] == ("system", "ip", "uptime")
    assert slot_for("ip") == "header"


def test_build_frame_routes_system_and_uptime_to_header():
    from glances.outputs.curses_renderer_v5 import build_frame

    snapshot = {
        "system": {"hostname": "h", "hr_name": "Ubuntu", "_levels": {}},
        "uptime": {"seconds": 3600, "_levels": {}},
        "cpu": {"total": 5.0, "_levels": {}},
    }
    fields = {
        "system": {"hostname": {"unit": "string"}, "hr_name": {"unit": "string"}},
        "uptime": {"seconds": {"unit": "seconds"}},
        "cpu": {"total": {"unit": "percent", "watched": True, "label": "CPU"}},
    }
    registry = [("system", False), ("uptime", False), ("cpu", False)]
    frame = build_frame(
        store_snapshot=snapshot,
        fields_by_plugin=fields,
        registry=registry,
        alerts_history=[],
    )
    header_names = [b.name for b in frame.header]
    # Ordered: system first, uptime last (HEADER_SLOT order).
    assert header_names == ["system", "uptime"]
    # They must NOT leak into the other slots.
    assert "system" not in [b.name for b in frame.top + frame.left + frame.right]
    assert "uptime" not in [b.name for b in frame.top + frame.left + frame.right]
    # cpu still lands in the top row.
    assert "cpu" in [b.name for b in frame.top]


def _header_snapshot_and_fields():
    snapshot = {
        "system": {"hostname": "h", "hr_name": "Ubuntu", "_levels": {}},
        "ip": {"address": "1.2.3.4", "mask_cidr": 24, "_levels": {}},
        "uptime": {"seconds": 3600, "_levels": {}},
    }
    fields = {
        "system": {"hostname": {"unit": "string"}, "hr_name": {"unit": "string"}},
        "ip": {"address": {"unit": "string"}, "mask_cidr": {"unit": "number"}},
        "uptime": {"seconds": {"unit": "seconds"}},
    }
    registry = [("system", False), ("ip", False), ("uptime", False)]
    return snapshot, fields, registry


def test_build_frame_header_all_three_when_no_flags():
    from glances.outputs.curses_renderer_v5 import build_frame

    snapshot, fields, registry = _header_snapshot_and_fields()
    frame = build_frame(snapshot, fields, registry, alerts_history=[], view={})
    assert [b.name for b in frame.header] == ["system", "ip", "uptime"]


def test_build_frame_hide_ip_flag_drops_ip_block():
    """Progressive header degradation level 2: `hide_ip` removes the ip block."""
    from glances.outputs.curses_renderer_v5 import build_frame

    snapshot, fields, registry = _header_snapshot_and_fields()
    frame = build_frame(snapshot, fields, registry, alerts_history=[], view={"hide_ip": True})
    assert [b.name for b in frame.header] == ["system", "uptime"]


def test_build_frame_hide_uptime_flag_drops_uptime_block():
    """Progressive header degradation level 3: `hide_uptime` removes uptime."""
    from glances.outputs.curses_renderer_v5 import build_frame

    snapshot, fields, registry = _header_snapshot_and_fields()
    frame = build_frame(snapshot, fields, registry, alerts_history=[], view={"hide_ip": True, "hide_uptime": True})
    assert [b.name for b in frame.header] == ["system"]


def test_build_frame_hide_os_info_shortens_system_block():
    """Level 1: `hide_os_info` drops the OS string from the system block but
    keeps the block (hostname stays)."""
    from glances.outputs.curses_renderer_v5 import build_frame

    snapshot, fields, registry = _header_snapshot_and_fields()
    full = build_frame(snapshot, fields, registry, alerts_history=[], view={})
    short = build_frame(snapshot, fields, registry, alerts_history=[], view={"hide_os_info": True})
    sys_full = next(b for b in full.header if b.name == "system")
    sys_short = next(b for b in short.header if b.name == "system")
    assert sys_short.width < sys_full.width  # OS-info dropped → narrower
    assert "system" in [b.name for b in short.header]  # block itself kept


def test_build_frame_header_order_system_ip_uptime():
    from glances.outputs.curses_renderer_v5 import build_frame

    snapshot = {
        "uptime": {"seconds": 3600, "_levels": {}},
        "ip": {"address": "192.168.1.10", "mask_cidr": 24, "_levels": {}},
        "system": {"hostname": "h", "hr_name": "Ubuntu", "_levels": {}},
    }
    fields = {
        "uptime": {"seconds": {"unit": "seconds"}},
        "ip": {"address": {"unit": "string"}},
        "system": {"hostname": {"unit": "string"}, "hr_name": {"unit": "string"}},
    }
    # Deliberately out of order — HEADER_SLOT.index must enforce the order.
    registry = [("uptime", False), ("ip", False), ("system", False)]
    frame = build_frame(
        store_snapshot=snapshot,
        fields_by_plugin=fields,
        registry=registry,
        alerts_history=[],
    )
    assert [b.name for b in frame.header] == ["system", "ip", "uptime"]


# ----------------------------------------------------- now = far-right header block


def _header_with_now_snapshot():
    snapshot = {
        "now": {"custom": "2026-07-25 11:30:00 CEST", "iso": "2026-07-25T11:30:00+02:00", "_levels": {}},
        "uptime": {"seconds": 3600, "_levels": {}},
        "ip": {"address": "192.168.1.10", "mask_cidr": 24, "_levels": {}},
        "system": {"hostname": "h", "hr_name": "Ubuntu", "_levels": {}},
    }
    fields = {
        "now": {"custom": {"unit": "string"}, "iso": {"unit": "string"}},
        "uptime": {"seconds": {"unit": "seconds"}},
        "ip": {"address": {"unit": "string"}, "mask_cidr": {"unit": "number"}},
        "system": {"hostname": {"unit": "string"}, "hr_name": {"unit": "string"}},
    }
    # Deliberately out of order — HEADER_SLOT.index must enforce the order.
    registry = [("now", False), ("uptime", False), ("ip", False), ("system", False)]
    return snapshot, fields, registry


def test_now_is_routed_to_the_header_slot():
    """`now` moved out of the left sidebar into the header (v4 divergence:
    v4 bottom-aligns it in the left column)."""
    from glances.outputs.curses_renderer_v5 import LEFT_SLOT, slot_for

    assert slot_for("now") == "header"
    assert "now" not in LEFT_SLOT


def test_header_slot_is_the_concatenation_of_both_alignment_groups():
    """Guards against the two group tuples drifting from the flat one."""
    from glances.outputs.curses_renderer_v5 import HEADER_SLOT, HEADER_SLOT_LEFT, HEADER_SLOT_RIGHT

    assert HEADER_SLOT == HEADER_SLOT_LEFT + HEADER_SLOT_RIGHT
    assert HEADER_SLOT_RIGHT[-1] == "now"  # far right of the banner


def test_build_frame_header_order_puts_now_last():
    from glances.outputs.curses_renderer_v5 import build_frame

    snapshot, fields, registry = _header_with_now_snapshot()
    frame = build_frame(snapshot, fields, registry, alerts_history=[], view={})
    assert [b.name for b in frame.header] == ["system", "ip", "uptime", "now"]
    # It must NOT leak back into the sidebar.
    assert "now" not in [b.name for b in frame.top + frame.left + frame.right]


def test_build_frame_hide_now_flag_drops_now_block():
    """Progressive header degradation level 1: `hide_now` removes the now block
    and brings the banner back to the v4 `system … ip … uptime` layout."""
    from glances.outputs.curses_renderer_v5 import build_frame

    snapshot, fields, registry = _header_with_now_snapshot()
    frame = build_frame(snapshot, fields, registry, alerts_history=[], view={"hide_now": True})
    assert [b.name for b in frame.header] == ["system", "ip", "uptime"]


def test_build_frame_skips_empty_scalar_blocks():
    """Regression: empty scalar blocks (e.g., cloud with no metadata) must not
    reach the painter. A block with zero rows reserves layout space (_HEADER_GAP)
    for a banner that never paints, creating visible double-spacing. `cloud` is
    registered in HEADER_SLOT_RIGHT but returns empty rows on non-cloud hosts.
    This test verifies such a block is skipped during frame construction, so the
    final header layout is identical to the baseline without cloud."""
    from glances.outputs.curses_renderer_v5 import build_frame

    # Baseline: system, ip, uptime, now (no cloud).
    snapshot_baseline = {
        "now": {"custom": "2026-07-25 11:30:00 CEST", "iso": "2026-07-25T11:30:00+02:00", "_levels": {}},
        "uptime": {"seconds": 3600, "_levels": {}},
        "ip": {"address": "192.168.1.10", "mask_cidr": 24, "_levels": {}},
        "system": {"hostname": "h", "hr_name": "Ubuntu", "_levels": {}},
    }
    fields_baseline = {
        "now": {"custom": {"unit": "string"}, "iso": {"unit": "string"}},
        "uptime": {"seconds": {"unit": "seconds"}},
        "ip": {"address": {"unit": "string"}, "mask_cidr": {"unit": "number"}},
        "system": {"hostname": {"unit": "string"}, "hr_name": {"unit": "string"}},
    }
    registry_baseline = [("now", False), ("uptime", False), ("ip", False), ("system", False)]
    frame_baseline = build_frame(snapshot_baseline, fields_baseline, registry_baseline, alerts_history=[], view={})

    # Same baseline, but add cloud with empty payload (off-cloud host).
    snapshot_with_cloud = {
        **snapshot_baseline,
        "cloud": {},  # Empty: no metadata (scalar plugin with no payload).
    }
    fields_with_cloud = {
        **fields_baseline,
        "cloud": {"platform": {"unit": "string"}},  # Minimal fields descriptor.
    }
    registry_with_cloud = [
        ("now", False),
        ("uptime", False),
        ("ip", False),
        ("system", False),
        ("cloud", False),  # Scalar, not collection.
    ]
    frame_with_cloud = build_frame(
        snapshot_with_cloud, fields_with_cloud, registry_with_cloud, alerts_history=[], view={}
    )

    # The header should be identical in both cases: cloud's empty rows mean it
    # is skipped, so frame.header should have the same blocks and order.
    assert [b.name for b in frame_baseline.header] == [b.name for b in frame_with_cloud.header]
    assert [b.name for b in frame_baseline.header] == ["system", "ip", "uptime", "now"]
    assert "cloud" not in [b.name for b in frame_with_cloud.header]


def test_build_frame_skips_zero_row_top_block():
    """The zero-row skip (`if not rows: continue`) is general, not
    header-only: a TOP-slot block that renders no rows (e.g. `npu` whose
    first item is malformed) must not reach `frame.top` either, so it
    never charges the top row an inter-block gap for nothing."""
    from glances.outputs.curses_renderer_v5 import build_frame

    # Baseline: cpu + mem only.
    snapshot_baseline = {"cpu": {"total": 4.5}, "mem": {"percent": 50.0}}
    registry_baseline = [("cpu", False), ("mem", False)]
    frame_baseline = build_frame(snapshot_baseline, {}, registry_baseline, alerts_history=[], view={})

    # Same baseline, but with an `npu` collection whose only item is not a
    # dict — the data list is non-empty (so the generic collection guard
    # does not skip it), yet the custom renderer returns zero rows.
    snapshot_with_npu = {**snapshot_baseline, "npu": {"data": ["not-a-dict"]}}
    registry_with_npu = [*registry_baseline, ("npu", True)]
    frame_with_npu = build_frame(snapshot_with_npu, {}, registry_with_npu, alerts_history=[], view={})

    assert [b.name for b in frame_baseline.top] == [b.name for b in frame_with_npu.top]
    assert [b.name for b in frame_baseline.top] == ["cpu", "mem"]
    assert "npu" not in [b.name for b in frame_with_npu.top]


# --------------------------------------------------------------- hide_* skip guards


def test_hide_quicklook_skips_block():
    from glances.outputs.curses_renderer_v5 import build_frame

    registry = [("quicklook", False), ("cpu", False), ("mem", False)]
    store = {n: {"_levels": {}} for n, _ in registry}
    fields = {n: {} for n, _ in registry}
    frame = build_frame(store, fields, registry, [], view={"hide_quicklook": True})
    names = [b.name for b in frame.top]
    assert "quicklook" not in names and "cpu" in names and "mem" in names


def test_hide_memswap_skips_block():
    from glances.outputs.curses_renderer_v5 import build_frame

    registry = [("quicklook", False), ("memswap", False), ("cpu", False)]
    store = {n: {"_levels": {}} for n, _ in registry}
    fields = {n: {} for n, _ in registry}
    frame = build_frame(store, fields, registry, [], view={"hide_memswap": True})
    names = [b.name for b in frame.top]
    assert "memswap" not in names and "quicklook" in names and "cpu" in names


def test_top_slot_has_npu_after_percpu_before_gpu():
    from glances.outputs.curses_renderer_v5 import TOP_SLOT

    assert "npu" in TOP_SLOT
    assert TOP_SLOT.index("percpu") < TOP_SLOT.index("npu") < TOP_SLOT.index("gpu")


def test_build_frame_hides_gpu_when_flagged():
    from glances.outputs.curses_renderer_v5 import build_frame

    # build_frame(store_snapshot, fields_by_plugin, registry, alerts_history, ..., view=None)
    registry = [("gpu", True)]
    snapshot = {
        "gpu": {
            "data": [{"gpu_id": "n0", "name": "X", "mem": 10, "proc": 5, "temperature": 40}],
            "_levels": {},
        }
    }
    fields = {"gpu": {}}
    shown = build_frame(snapshot, fields, registry, [], view={"hide_gpu": False})
    hidden = build_frame(snapshot, fields, registry, [], view={"hide_gpu": True})
    assert "gpu" in [b.name for b in shown.top]
    assert "gpu" not in [b.name for b in hidden.top]
