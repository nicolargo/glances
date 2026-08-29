"""Glances v5 — tests for the pure curses renderer."""

from __future__ import annotations

from datetime import datetime, timezone

from glances.outputs.curses_renderer_v5 import (
    _MAX_WORKLOADS,
    _NOMINAL_ALERTS,
    _NOMINAL_PROCESSES,
    Cell,
    ColorRole,
    Frame,
    PluginBlock,
    Row,
    _alert_block_height,
    _derive_incidents,
    _humanise_target,
    _reset_plugin_renderer_cache,
    _split_workloads,
    build_frame,
    plan_right_column,
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


def test_render_alert_block_handles_empty_history():
    rows = render_alert_block([], limit=10)
    assert len(rows) >= 1


def test_render_alert_block_empty_history_shows_no_alert_detected_when_settled():
    """Settled (initializing=False), empty history → a single line
    ``ALERT (no alert detected)``. No separate placeholder row, no
    ``0 ongoing / 0 total`` count.

    Only the state fragment is green — the all-clear signal. ``ALERT`` stays
    HEADER, like the ``ALERTS`` prefix of the populated title, so the line
    still reads as a block heading."""
    rows = render_alert_block([], limit=10, is_initializing=False)
    assert len(rows) == 1
    assert _line(rows[0]) == "ALERT (no alert detected)"
    assert [(c.text, c.color) for c in rows[0].cells] == [
        ("ALERT ", ColorRole.HEADER),
        ("(no alert detected)", ColorRole.OK),
    ]
    assert "initializing" not in _line(rows[0])
    assert "ongoing" not in _line(rows[0])


def test_render_alert_block_empty_history_shows_initializing_during_warmup():
    """is_initializing=True (warmup), empty history → a single line
    ``ALERT (initializing)`` so the user knows alerts can't have fired yet.

    The state fragment is neutral, NOT green: warmup is not an all-clear.
    Claiming a healthy system before the engine can even fire would be a lie."""
    rows = render_alert_block([], limit=10, is_initializing=True)
    assert len(rows) == 1
    assert _line(rows[0]) == "ALERT (initializing)"
    assert [(c.text, c.color) for c in rows[0].cells] == [
        ("ALERT ", ColorRole.HEADER),
        ("(initializing)", ColorRole.DEFAULT),
    ]
    assert not any(c.color == ColorRole.OK for c in rows[0].cells)
    assert "no alert detected" not in _line(rows[0])


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


def test_format_alert_time_other_day_returns_full_date_within_8_columns():
    """Another day → `YY-MM-DD`, not the old 14-char `MM-DD HH:MM:SS`.

    Approved divergence (design §6.2): the fixed grid gives TIME 8 columns and
    the DURATION column now carries the age (`2d04h`), so the full timestamp
    is redundant. The year is kept — `08-14` alone is ambiguous next to the
    `HH:MM:SS` of the same-day rows, and `YY-MM-DD` reads in the same
    descending order.
    """
    from datetime import datetime, timezone

    from glances.outputs.curses_renderer_v5 import _format_alert_time

    now_utc = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    result = _format_alert_time("2026-08-14T09:30:00+00:00", now=now_utc)
    assert len(result) == 8
    assert result == "26-08-14"


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


def test_format_duration_compact_seconds():
    from glances.outputs.curses_renderer_v5 import _format_duration_compact

    assert _format_duration_compact(0) == "0s"
    assert _format_duration_compact(43) == "43s"
    assert _format_duration_compact(59.9) == "59s"


def test_format_duration_compact_minutes():
    from glances.outputs.curses_renderer_v5 import _format_duration_compact

    assert _format_duration_compact(60) == "1m00s"
    assert _format_duration_compact(178) == "2m58s"


def test_format_duration_compact_hours():
    from glances.outputs.curses_renderer_v5 import _format_duration_compact

    assert _format_duration_compact(3600) == "1h00m"
    assert _format_duration_compact(4380) == "1h13m"


def test_format_duration_compact_days():
    from glances.outputs.curses_renderer_v5 import _format_duration_compact

    assert _format_duration_compact(86400) == "1d00h"
    assert _format_duration_compact(187200) == "2d04h"


def test_format_duration_compact_never_exceeds_eight_columns():
    """The DURATION column is 8 wide; nothing plausible may overflow it."""
    from glances.outputs.curses_renderer_v5 import _format_duration_compact

    assert len(_format_duration_compact(999 * 86400)) <= 8


def test_incident_duration_ongoing_measures_from_begin_to_now():
    from datetime import datetime, timezone

    from glances.outputs.curses_renderer_v5 import _incident_duration

    now = datetime(2026, 8, 16, 10, 3, 0, tzinfo=timezone.utc)
    incident = {"begin": "2026-08-16T10:00:00+00:00", "end": None, "ongoing": True, "partial": False}
    assert _incident_duration(incident, now=now) == "3m00s"


def test_incident_duration_closed_measures_begin_to_end():
    """A resolved incident freezes its duration — it must not keep ticking."""
    from datetime import datetime, timezone

    from glances.outputs.curses_renderer_v5 import _incident_duration

    now = datetime(2026, 8, 16, 23, 0, 0, tzinfo=timezone.utc)
    incident = {
        "begin": "2026-08-16T10:00:00+00:00",
        "end": "2026-08-16T10:00:43+00:00",
        "ongoing": False,
        "partial": False,
    }
    assert _incident_duration(incident, now=now) == "43s"


def test_incident_duration_partial_is_prefixed_with_a_lower_bound_marker():
    """Opener evicted → the duration is a floor, and says so."""
    from datetime import datetime, timezone

    from glances.outputs.curses_renderer_v5 import _incident_duration

    now = datetime(2026, 8, 16, 10, 3, 0, tzinfo=timezone.utc)
    incident = {"begin": "2026-08-16T10:00:00+00:00", "end": None, "ongoing": True, "partial": True}
    assert _incident_duration(incident, now=now) == ">3m00s"


def test_incident_duration_unknown_begin_returns_none():
    from glances.outputs.curses_renderer_v5 import _incident_duration

    incident = {"begin": None, "end": None, "ongoing": True, "partial": True}
    assert _incident_duration(incident) is None


def test_incident_duration_malformed_begin_returns_none():
    from glances.outputs.curses_renderer_v5 import _incident_duration

    incident = {"begin": "not-a-timestamp", "end": None, "ongoing": True, "partial": False}
    assert _incident_duration(incident) is None


def test_incident_duration_future_begin_returns_none():
    """Clock skew must not print a negative duration."""
    from datetime import datetime, timezone

    from glances.outputs.curses_renderer_v5 import _incident_duration

    now = datetime(2026, 8, 16, 10, 0, 0, tzinfo=timezone.utc)
    incident = {"begin": "2026-08-16T11:00:00+00:00", "end": None, "ongoing": True, "partial": False}
    assert _incident_duration(incident, now=now) is None


def test_incident_duration_naive_begin_assumed_utc():
    from datetime import datetime, timezone

    from glances.outputs.curses_renderer_v5 import _incident_duration

    now = datetime(2026, 8, 16, 10, 1, 0, tzinfo=timezone.utc)
    incident = {"begin": "2026-08-16T10:00:00", "end": None, "ongoing": True, "partial": False}
    assert _incident_duration(incident, now=now) == "1m00s"


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
    # The LEVEL cell renders the level upper-cased (design §6.2).
    assert "CAREFUL" in flat


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
    # One resolved incident, one row, resolved glyph — the real thing this
    # test claims to check (the header's "0 ongoing" substring was true by
    # construction and bit nothing on its own).
    assert len(rows) == 3
    assert rows[2].cells[0].text == "○"
    # The title is several glued cells now, so read the painted line.
    assert "0 ongoing" in _line(rows[0])


def _evt(ts, plugin, field, level, previous="ok", key=None, prominent=False, is_initial=False):
    """Minimal alert event, shaped like GlancesAlerts._build_event's output."""
    return {
        "ts": ts,
        "plugin": plugin,
        "key": key,
        "field": field,
        "level": level,
        "previous_level": previous,
        "value": 1.0,
        "prominent": prominent,
        "is_initial": is_initial,
        "hostname": "h",
    }


def _line(row):
    """Paint one Row the way PluginBlock.width measures it: one space between
    cells unless the cell is glued."""
    out = ""
    for i, cell in enumerate(row.cells):
        if i and not cell.glue:
            out += " "
        out += cell.text
    return out


# Chronological, like the engine's deque: fs alerts and recovers, then
# containers and cpu alert and stay active.
_GRID_HISTORY = [
    _evt("2026-08-16T13:58:40+00:00", "fs", "percent", "warning", key="/"),
    _evt("2026-08-16T13:59:23+00:00", "fs", "percent", "ok", previous="warning", key="/"),
    _evt("2026-08-16T14:01:03+00:00", "containers", "mem_usage", "warning", key="nginx"),
    _evt("2026-08-16T14:02:11+00:00", "cpu", "total", "critical"),
]
_GRID_ONGOING = {
    ("cpu", None, "total"): "critical",
    ("containers", "nginx", "mem_usage"): "warning",
}
_GRID_NOW = datetime(2026, 8, 16, 14, 5, 9, tzinfo=timezone.utc)


def test_render_alert_block_full_grid_columns_are_aligned():
    """Every row lands TIME at 2, DURATION ending at 19, TARGET at 22."""
    rows = render_alert_block(_GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61)
    data = [_line(r) for r in rows[2:]]
    assert data, "expected data rows below the title and column header"
    for line in data:
        assert line[1] == " "
        assert line[10:12] == "  "
        assert line[20:22] == "  "
    assert len({len(line) for line in data}) == 1


def test_render_alert_block_ongoing_rows_come_first():
    """§5.3 — a resolved incident must never push an ongoing one out of view."""
    rows = render_alert_block(_GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61)
    data = [_line(r) for r in rows[2:]]
    assert "Cpu total" in data[0]
    assert "Containers nginx mem usage" in data[1]
    # `percent` is a generic field name and is dropped — `Fs /` says it all.
    assert "Fs /" in data[2]


def test_render_alert_block_resolved_incident_takes_one_row_not_two():
    """§5.4 — the `→ ok` transition resolves a row, it does not add one."""
    rows = render_alert_block(_GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61)
    assert len(rows) == 2 + 3  # title + column header + 3 incidents (4 events)


def test_render_alert_block_glyphs_distinguish_ongoing_from_resolved():
    rows = render_alert_block(_GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61)
    glyphs = [r.cells[0].text for r in rows[2:]]
    assert glyphs == ["●", "●", "○"]


def test_render_alert_block_ascii_fallback_emits_no_unicode():
    """--disable-unicode → the whole block is pure ASCII (§6.5)."""
    rows = render_alert_block(
        _GRID_HISTORY,
        limit=10,
        now=_GRID_NOW,
        ongoing=_GRID_ONGOING,
        width=61,
        unicode_ok=False,
    )
    painted = "\n".join(_line(r) for r in rows)
    assert painted.isascii()
    assert [r.cells[0].text for r in rows[2:]] == ["*", "*", "-"]


def test_render_alert_block_glyph_carries_the_level_colour():
    rows = render_alert_block(_GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61)
    assert rows[2].cells[0].color == ColorRole.CRITICAL
    assert rows[3].cells[0].color == ColorRole.WARNING


def test_render_alert_block_resolved_level_is_neutral_but_glyph_keeps_its_colour():
    """Colour in the LEVEL column means "still happening".

    A resolved incident's level text goes neutral so the eye lands on the
    active rows, but its glyph keeps the level colour so the severity it
    reached stays readable. Rows are [ongoing cpu, ongoing containers,
    resolved fs] — cells are [glyph, TIME, DURATION, TARGET, LEVEL].
    """
    rows = render_alert_block(_GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61)
    ongoing_row, resolved_row = rows[2], rows[4]

    assert ongoing_row.cells[0].text == "●"
    assert ongoing_row.cells[-1].text.strip() == "CRITICAL"
    assert ongoing_row.cells[-1].color == ColorRole.CRITICAL

    assert resolved_row.cells[0].text == "○"
    assert resolved_row.cells[-1].text.strip() == "WARNING"
    assert resolved_row.cells[-1].color == ColorRole.DEFAULT
    # The glyph is the survivor: past severity must not be erased.
    assert resolved_row.cells[0].color == ColorRole.WARNING


def test_humanise_target_reads_as_prose_not_as_an_identifier():
    """The TARGET column addresses an operator, not a parser."""
    assert _humanise_target("cpu", None, "system") == "Cpu system"
    assert _humanise_target("containers", "nginx", "mem_usage") == "Containers nginx mem usage"
    assert _humanise_target("network", "eth0", "bytes_recv") == "Network eth0 bytes recv"


def test_humanise_target_drops_a_generic_field_name():
    """`value` and `percent` identify nothing — the plugin and key already do."""
    assert _humanise_target("sensors", "i915 0", "value") == "Sensors i915 0"
    assert _humanise_target("fs", "/", "percent") == "Fs /"
    # No key either: the plugin name alone is the whole target.
    assert _humanise_target("mem", None, "percent") == "Mem"


def test_humanise_target_matches_generic_names_whole_not_as_a_suffix():
    """A field merely ENDING in a generic word keeps every part of its name.

    Substring matching here would silently turn `memory_usage_percent` into
    something indistinguishable from a plain percentage.
    """
    assert _humanise_target("containers", "web", "memory_usage_percent") == "Containers web memory usage percent"
    assert _humanise_target("gpu", "0", "mem_value") == "Gpu 0 mem value"


def test_humanise_target_capitalises_only_the_plugin_name():
    """No acronym table — `gpu` renders as `Gpu`, deliberately. Keys are kept
    verbatim: a mountpoint or container name is already human-readable, and
    rewriting it would misreport what the engine watched."""
    assert _humanise_target("gpu", None, "proc") == "Gpu proc"
    assert _humanise_target("fs", "/var/lib/DOCKER", "used") == "Fs /var/lib/DOCKER used"
    assert _humanise_target("sensors", "Core 0", "value") == "Sensors Core 0"


def test_humanise_target_survives_degenerate_input():
    """The renderer must not crash on a malformed incident."""
    assert _humanise_target("cpu", None, "") == "Cpu"
    assert _humanise_target("cpu", "", "system") == "Cpu system"
    assert _humanise_target("", None, "system") == "system"


def test_render_alert_block_duration_cell_is_exact():
    """End-to-end duration wiring: the row-level tests only checked the
    DURATION region was non-empty, which would still pass if `end` were used
    where `begin` belongs, or the wrong `now` reached the renderer. Pin the
    exact value: `cpu.total` opened at 14:02:11, `_GRID_NOW` is 14:05:09 →
    2m58s elapsed — cells are [glyph, TIME, DURATION, TARGET, LEVEL]."""
    rows = render_alert_block(_GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61)
    assert rows[2].cells[2].text.strip() == "2m58s"


def test_render_alert_block_partial_incident_duration_has_lower_bound_marker():
    """`is_initial`'s only remaining observable effect is the `partial` flag
    (§5.6, since arrows are gone) — this is covered at `_derive_incidents`
    unit level already, but never end-to-end through the renderer."""
    history = [_evt("2026-08-16T14:00:00+00:00", "cpu", "total", "critical", previous="warning")]
    rows = render_alert_block(history, limit=10, now=_GRID_NOW, ongoing={("cpu", None, "total"): "critical"}, width=61)
    assert rows[2].cells[2].text.strip().startswith(">")


def test_render_alert_block_title_counts_ongoing_and_resolved():
    rows = render_alert_block(_GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61)
    title = _line(rows[0])
    assert title.startswith("ALERTS")
    assert "2 ongoing" in title
    assert "1 resolved" in title
    assert rows[0].cells[0].color == ColorRole.HEADER


def test_render_alert_block_title_is_never_level_coloured():
    """Standing TUI rule: a block title is never ESCALATED by an alert level.

    The ongoing-count fragment may be `ok` (green, all clear) or `default`;
    neither is an escalation. What must never happen is a title element
    turning careful/warning/critical because something fired — the alert lives
    on the value, not on the heading.
    """
    escalations = {ColorRole.CAREFUL, ColorRole.WARNING, ColorRole.CRITICAL}
    for history, ongoing in ((_GRID_HISTORY, _GRID_ONGOING), (_GRID_HISTORY, {})):
        rows = render_alert_block(history, limit=10, now=_GRID_NOW, ongoing=ongoing, width=61)
        assert not any(c.color in escalations for c in rows[0].cells)
        # The column-header row is a heading too: always HEADER, no exceptions.
        assert all(c.color == ColorRole.HEADER for c in rows[1].cells)


def test_render_alert_block_title_count_is_green_only_when_nothing_is_ongoing():
    """The ongoing-count fragment is the block's at-a-glance state signal."""
    quiet = render_alert_block(_GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing={}, width=61)
    busy = render_alert_block(_GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61)

    def count_cell(rows):
        return next(c for c in rows[0].cells if "ongoing" in c.text)

    assert "0 ongoing" in count_cell(quiet).text
    assert count_cell(quiet).color == ColorRole.OK
    assert "2 ongoing" in count_cell(busy).text
    assert count_cell(busy).color == ColorRole.DEFAULT
    # `ALERTS` and the trailing rule stay HEADER in both states, so the block
    # still reads as a titled block rather than a coloured banner.
    for rows in (quiet, busy):
        assert rows[0].cells[0].text.startswith("ALERTS")
        assert rows[0].cells[0].color == ColorRole.HEADER
        assert rows[0].cells[-1].color == ColorRole.HEADER


def test_render_alert_block_title_text_is_unchanged_by_the_cell_split():
    """Splitting the title into glued cells must not shift a single column.

    Without `glue` the painter would insert a separator between every
    fragment; this pins the rendered text across the whole degradation ladder,
    including the cross-cell hard truncation at the bottom.
    """
    expected = {
        61: "ALERTS  2 ongoing · 1 resolved " + "─" * 30,
        43: "ALERTS  2 ongoing · 1 resolved " + "─" * 12,
        31: "ALERTS  2 ongoing · 1 resolved",
        30: "ALERTS  2 ongoing · 1 resolved",
        29: "ALERTS  2 ongoing",
        17: "ALERTS  2 ongoing",
        12: "ALERTS  2 on",
    }
    for width, text in expected.items():
        rows = render_alert_block(_GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=width)
        assert _line(rows[0]) == text, f"width={width}"


def test_render_alert_block_title_degrades_instead_of_cutting_mid_word():
    """§6.3 — the title shortens rule-first, then drops the `resolved`
    clause; it must never hard-truncate mid-word while a cleaner
    degradation step is available."""
    full = _line(render_alert_block(_GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=96)[0])
    assert full.startswith("ALERTS  2 ongoing · 1 resolved")  # full title, width to spare

    title = _line(render_alert_block(_GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=24)[0])
    assert title == "ALERTS  2 ongoing"
    assert "resolved" not in title
    assert not title.endswith(" ")

    narrower = _line(render_alert_block(_GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=20)[0])
    assert narrower == "ALERTS  2 ongoing"


def test_render_alert_block_drops_level_below_43_columns():
    """§6.3 first step — TARGET has a 12-column floor."""
    wide = render_alert_block(_GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=43)
    narrow = render_alert_block(_GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=42)
    assert "CRITICAL" in _line(wide[2])
    assert "CRITICAL" not in _line(narrow[2])


def test_render_alert_block_drops_duration_below_34_columns():
    """§6.3 second step."""
    wide = render_alert_block(_GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=34)
    narrow = render_alert_block(_GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=33)
    assert _line(wide[2])[12:20].strip()
    assert "Cpu total" in _line(narrow[2])
    assert len(_line(narrow[2])) <= 33


def test_render_alert_block_never_exceeds_the_given_width():
    """§11 — no emitted row may overflow the block at any tested width."""
    for width in (96, 61, 43, 34, 30, 24):
        rows = render_alert_block(_GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=width)
        for row in rows:
            assert len(_line(row)) <= width, f"overflow at width={width}"


def test_alert_block_height_matches_render_alert_block_row_count():
    """`_alert_block_height` is the planner's cost mirror of
    `render_alert_block` — if they ever disagree the RIGHT column overflows
    and silently clips its bottom row (a real bug found and fixed during
    G7 execution). Assert the invariant directly, across the three regimes
    the height function distinguishes."""
    # Regime 1: no incidents at all.
    rows = render_alert_block([], limit=10, now=_GRID_NOW, ongoing={}, width=61)
    assert len(rows) == _alert_block_height(0, 10)

    # Regime 2: incidents exist but the quota is zero.
    rows = render_alert_block(_GRID_HISTORY, limit=0, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61)
    n_incidents = len(_derive_incidents(_GRID_HISTORY, _GRID_ONGOING))
    assert len(rows) == _alert_block_height(n_incidents, 0)

    # Regime 3: quota smaller than the incident count.
    rows = render_alert_block(_GRID_HISTORY, limit=2, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61)
    assert len(rows) == _alert_block_height(n_incidents, 2)


def test_render_alert_block_truncates_target_with_an_ellipsis():
    """58-character target in a 30-column TARGET cell → cut, and visibly so.

    `memory_usage_percent` merely ENDS in a generic word, so humanising keeps
    every part of it — the target stays far too long for the column."""
    history = [
        _evt(
            "2026-08-16T14:00:00+00:00",
            "containers",
            "memory_usage_percent",
            "warning",
            key="a-very-long-container-name",
        )
    ]
    ongoing = {("containers", "a-very-long-container-name", "memory_usage_percent"): "warning"}
    rows = render_alert_block(history, limit=10, now=_GRID_NOW, ongoing=ongoing, width=61)
    # cells: glyph, TIME, DURATION, TARGET, LEVEL
    target_cell = rows[2].cells[3]
    assert len(target_cell.text) == 30
    assert target_cell.text.endswith("…")
    assert len(_line(rows[2])) == 61


def test_render_alert_block_ascii_truncation_uses_a_dot():
    """ASCII mode must not leak `…` through the truncation path."""
    history = [
        _evt(
            "2026-08-16T14:00:00+00:00",
            "containers",
            "memory_usage_percent",
            "warning",
            key="a-very-long-container-name",
        )
    ]
    ongoing = {("containers", "a-very-long-container-name", "memory_usage_percent"): "warning"}
    rows = render_alert_block(history, limit=10, now=_GRID_NOW, ongoing=ongoing, width=61, unicode_ok=False)
    target_cell = rows[2].cells[3]
    assert target_cell.text.endswith(".")
    assert _line(rows[2]).isascii()


def test_render_alert_block_forwards_prominent_onto_the_level_cell():
    """§11 — the G6B defect class must not reappear."""
    history = [_evt("2026-08-16T14:00:00+00:00", "cpu", "total", "critical", prominent=True)]
    rows = render_alert_block(
        history,
        limit=10,
        now=_GRID_NOW,
        ongoing={("cpu", None, "total"): "critical"},
        width=61,
    )
    assert rows[2].cells[-1].prominent is True


def test_render_alert_block_forwards_prominent_onto_the_glyph_when_level_is_dropped():
    """Narrow terminal: `prominent` moves rather than disappearing."""
    history = [_evt("2026-08-16T14:00:00+00:00", "cpu", "total", "critical", prominent=True)]
    rows = render_alert_block(
        history,
        limit=10,
        now=_GRID_NOW,
        ongoing={("cpu", None, "total"): "critical"},
        width=36,
    )
    assert rows[2].cells[0].prominent is True


def test_render_alert_block_shows_no_transition_arrow():
    """§3.1.2 — the level text no longer duplicates the colour, and there is
    no `previous → level` sentence any more."""
    rows = render_alert_block(_GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61)
    painted = "\n".join(_line(r) for r in rows)
    assert "→" not in painted
    assert "ongoing for" not in painted


def test_render_alert_block_limit_counts_incidents_not_events():
    """`limit` is a DATA-row budget; two events of one incident cost one row."""
    rows = render_alert_block(_GRID_HISTORY, limit=2, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61)
    assert len(rows) == 2 + 2


def test_render_alert_block_limit_zero_emits_the_title_only():
    """The vertical shrink ladder's step (h) — header only."""
    rows = render_alert_block(_GRID_HISTORY, limit=0, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61)
    assert len(rows) == 1
    assert _line(rows[0]).startswith("ALERTS")


def test_render_alert_block_without_width_still_aligns():
    """Export / direct calls pass no width: pad TARGET to its natural maximum
    rather than degrading."""
    rows = render_alert_block(_GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING)
    data = [_line(r) for r in rows[2:]]
    assert len({len(line) for line in data}) == 1


def test_render_alert_block_fully_evicted_ongoing_alert_is_still_shown():
    """The reason `ongoing` exists at all (§5.6)."""
    rows = render_alert_block(
        [],
        limit=10,
        now=_GRID_NOW,
        ongoing={("cpu", None, "total"): "critical"},
        width=61,
    )
    painted = "\n".join(_line(r) for r in rows)
    assert "Cpu total" in painted
    assert "--:--:--" in painted


def test_render_alert_block_empty_history_and_no_ongoing_still_collapses():
    """§11 — the single-line collapse survives the redesign."""
    rows = render_alert_block([], limit=10, is_initializing=False, ongoing={}, width=61)
    assert len(rows) == 1
    assert _line(rows[0]) == "ALERT (no alert detected)"


def test_derive_incidents_single_open_incident():
    """One entry transition, still active → one ongoing incident."""
    history = [_evt("2026-08-16T10:00:00+00:00", "mem", "percent", "warning")]
    ongoing = {("mem", None, "percent"): "warning"}
    incidents = _derive_incidents(history, ongoing)
    assert len(incidents) == 1
    inc = incidents[0]
    assert inc["plugin"] == "mem"
    assert inc["field"] == "percent"
    assert inc["level"] == "warning"
    assert inc["begin"] == "2026-08-16T10:00:00+00:00"
    assert inc["end"] is None
    assert inc["ongoing"] is True
    assert inc["partial"] is False


def test_derive_incidents_escalation_keeps_one_row_at_max_level():
    """warning → critical is ONE incident whose level is the peak reached."""
    history = [
        _evt("2026-08-16T10:00:00+00:00", "cpu", "total", "warning"),
        _evt("2026-08-16T10:02:00+00:00", "cpu", "total", "critical", previous="warning"),
    ]
    incidents = _derive_incidents(history, {("cpu", None, "total"): "critical"})
    assert len(incidents) == 1
    assert incidents[0]["level"] == "critical"
    assert incidents[0]["begin"] == "2026-08-16T10:00:00+00:00"


def test_derive_incidents_deescalation_keeps_the_peak_level():
    """critical → warning, still active: the journal keeps CRITICAL (v4 parity §2.6)."""
    history = [
        _evt("2026-08-16T10:00:00+00:00", "cpu", "total", "critical"),
        _evt("2026-08-16T10:05:00+00:00", "cpu", "total", "warning", previous="critical"),
    ]
    incidents = _derive_incidents(history, {("cpu", None, "total"): "warning"})
    assert len(incidents) == 1
    assert incidents[0]["level"] == "critical"
    assert incidents[0]["ongoing"] is True


def test_derive_incidents_resolution_closes_the_row_instead_of_adding_one():
    """The `→ ok` transition must NOT occupy a row of its own (§5.4)."""
    history = [
        _evt("2026-08-16T10:00:00+00:00", "mem", "percent", "warning"),
        _evt("2026-08-16T10:03:00+00:00", "mem", "percent", "ok", previous="warning"),
    ]
    incidents = _derive_incidents(history, {})
    assert len(incidents) == 1
    assert incidents[0]["ongoing"] is False
    assert incidents[0]["begin"] == "2026-08-16T10:00:00+00:00"
    assert incidents[0]["end"] == "2026-08-16T10:03:00+00:00"


def test_derive_incidents_unpaired_ok_produces_no_incident():
    """A bare `→ ok` whose opener aged out of the ring buffer closes nothing
    — there is no open incident to pop, so it produces ZERO incidents, not a
    visible "resolved, unknown start" row. Real, user-visible behaviour: the
    block collapses to `ALERT (no alert detected)` for this history — a
    pre-existing render_alert_block test built exactly this fixture and
    expected a visible resolved row before the incident model existed; that
    assumption no longer holds and nothing else pinned the new one."""
    history = [_evt("2026-08-16T10:05:00+00:00", "mem", "percent", "ok", previous="warning")]
    incidents = _derive_incidents(history, {})
    assert incidents == []


def test_derive_incidents_same_tuple_twice_gives_two_rows():
    """One row per INCIDENT, not per tuple: alert, recover, alert again = 2."""
    history = [
        _evt("2026-08-16T10:00:00+00:00", "mem", "percent", "warning"),
        _evt("2026-08-16T10:03:00+00:00", "mem", "percent", "ok", previous="warning"),
        _evt("2026-08-16T10:10:00+00:00", "mem", "percent", "warning"),
    ]
    incidents = _derive_incidents(history, {("mem", None, "percent"): "warning"})
    assert len(incidents) == 2
    assert [i["ongoing"] for i in incidents] == [True, False]
    assert incidents[0]["begin"] == "2026-08-16T10:10:00+00:00"
    assert incidents[1]["end"] == "2026-08-16T10:03:00+00:00"


def test_derive_incidents_evicted_opener_is_marked_partial():
    """First surviving event has previous_level != ok → the incident started earlier."""
    history = [
        _evt("2026-08-16T10:02:00+00:00", "cpu", "total", "critical", previous="warning"),
    ]
    incidents = _derive_incidents(history, {("cpu", None, "total"): "critical"})
    assert len(incidents) == 1
    assert incidents[0]["partial"] is True
    assert incidents[0]["begin"] == "2026-08-16T10:02:00+00:00"


def test_derive_incidents_is_initial_is_not_partial():
    """An `is_initial` event IS the start — Glances just found the system already hot.

    `previous="warning"` here is defensive-only: the real engine only ever sets
    `is_initial=True` together with `previous_level="ok"` (`_reconcile` sets it
    on the first commit out of the default `committed_level="ok"`), but using
    that combination would leave `is_initial` untested since `previous != "ok"`
    would already be `False` on its own.
    """
    history = [
        _evt("2026-08-16T10:00:00+00:00", "cpu", "total", "critical", previous="warning", is_initial=True),
    ]
    incidents = _derive_incidents(history, {("cpu", None, "total"): "critical"})
    assert incidents[0]["partial"] is False


def test_derive_incidents_fully_evicted_ongoing_tuple_is_synthesized():
    """Engine says active, history has nothing → still a row, with no begin."""
    incidents = _derive_incidents([], {("cpu", None, "total"): "critical"})
    assert len(incidents) == 1
    inc = incidents[0]
    assert inc["plugin"] == "cpu"
    assert inc["field"] == "total"
    assert inc["level"] == "critical"
    assert inc["begin"] is None
    assert inc["ongoing"] is True
    assert inc["partial"] is True


def test_derive_incidents_history_says_open_but_engine_says_recovered():
    """Defensive: the engine is the authority, so the incident is closed."""
    history = [_evt("2026-08-16T10:00:00+00:00", "mem", "percent", "warning")]
    incidents = _derive_incidents(history, {})
    assert incidents[0]["ongoing"] is False
    assert incidents[0]["end"] is None


def test_derive_incidents_ongoing_level_wins_when_higher_than_history():
    """Engine escalated but the escalation event was evicted → show the engine's level."""
    history = [_evt("2026-08-16T10:00:00+00:00", "cpu", "total", "warning")]
    incidents = _derive_incidents(history, {("cpu", None, "total"): "critical"})
    assert incidents[0]["level"] == "critical"


def test_derive_incidents_sorts_ongoing_first_then_newest_first():
    """§5.3: a long-running ongoing incident must not sink below newer resolved ones."""
    history = [
        _evt("2026-08-16T09:00:00+00:00", "cpu", "total", "critical"),
        _evt("2026-08-16T10:00:00+00:00", "mem", "percent", "warning"),
        _evt("2026-08-16T10:01:00+00:00", "mem", "percent", "ok", previous="warning"),
        _evt("2026-08-16T11:00:00+00:00", "fs", "percent", "warning", key="/"),
        _evt("2026-08-16T11:01:00+00:00", "fs", "percent", "ok", previous="warning", key="/"),
    ]
    incidents = _derive_incidents(history, {("cpu", None, "total"): "critical"})
    assert [(i["plugin"], i["ongoing"]) for i in incidents] == [
        ("cpu", True),
        ("fs", False),
        ("mem", False),
    ]


def test_derive_incidents_keeps_prominent_if_any_transition_had_it():
    """`prominent` must survive the collapse — the G6B defect class (§11)."""
    history = [
        _evt("2026-08-16T10:00:00+00:00", "cpu", "total", "warning", prominent=True),
        _evt("2026-08-16T10:02:00+00:00", "cpu", "total", "critical", previous="warning", prominent=False),
    ]
    incidents = _derive_incidents(history, {("cpu", None, "total"): "critical"})
    assert incidents[0]["prominent"] is True


def test_derive_incidents_distinguishes_keys_of_the_same_plugin():
    """fs[/] and fs[/home] are different tuples, hence different incidents."""
    history = [
        _evt("2026-08-16T10:00:00+00:00", "fs", "percent", "warning", key="/"),
        _evt("2026-08-16T10:01:00+00:00", "fs", "percent", "warning", key="/home"),
    ]
    incidents = _derive_incidents(
        history,
        {("fs", "/", "percent"): "warning", ("fs", "/home", "percent"): "warning"},
    )
    assert len(incidents) == 2
    assert {i["key"] for i in incidents} == {"/", "/home"}


def test_derive_incidents_no_ongoing_argument_defaults_to_history_only():
    """`ongoing=None` → derive purely from the history (export / direct calls)."""
    history = [_evt("2026-08-16T10:00:00+00:00", "mem", "percent", "warning")]
    incidents = _derive_incidents(history)
    assert len(incidents) == 1
    assert incidents[0]["ongoing"] is True


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
    assert "Mem" in flat


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


def test_data_count_is_none_for_scalar_plugin():
    """A scalar plugin has no `data` list — data_count stays None."""
    frame = build_frame(
        store_snapshot={"uptime": {"seconds": 42}},
        fields_by_plugin={"uptime": {"seconds": {"unit": "second", "label": "Uptime"}}},
        registry=[("uptime", False)],
        alerts_history=[],
    )
    blocks = [b for b in frame.header + frame.top + frame.left + frame.right if b.name == "uptime"]
    assert blocks, "uptime block missing"
    assert blocks[0].data_count is None


def test_data_count_counts_collection_items():
    """A collection plugin exposes its FULL item count, even when the
    renderer truncates the rows it emits."""
    data = [{"name": f"c{i}", "status": "running"} for i in range(25)]
    frame = build_frame(
        store_snapshot={"containers": {"data": data, "_levels": {}, "disable_stats": []}},
        fields_by_plugin={"containers": {}},
        registry=[("containers", True)],
        alerts_history=[],
    )
    blocks = [b for b in frame.right if b.name == "containers"]
    assert blocks, "containers block missing"
    assert blocks[0].data_count == 25


def test_data_count_on_alert_block_is_incident_count_not_history_length():
    """The synthesized alert block carries the INCIDENT count, not the raw
    event count — `plan_right_column` sizes the block off `data_count`, and
    the block now renders one row per incident, not one row per event.

    17 events sharing one `(plugin, key, field)` tuple collapse into a
    single open incident (§5.4) — so `data_count` must be 1, not 17."""
    history = [
        {
            "ts": "2026-08-05T10:00:00+00:00",
            "plugin": "cpu",
            "key": None,
            "field": "total",
            "level": "warning",
            "previous_level": "ok",
        }
        for _ in range(17)
    ]
    frame = build_frame(
        store_snapshot={},
        fields_by_plugin={},
        registry=[],
        alerts_history=history,
    )
    alert_blocks = [b for b in frame.right if b.name == "alert"]
    assert alert_blocks[0].data_count == 1


def test_data_count_on_alert_block_counts_distinct_incidents():
    """17 DISTINCT `(plugin, key, field)` tuples → 17 incidents, one row
    each — `data_count` follows the incident count up in this direction too."""
    history = _alert_history(17)
    frame = build_frame(
        store_snapshot={},
        fields_by_plugin={},
        registry=[],
        alerts_history=history,
    )
    alert_blocks = [b for b in frame.right if b.name == "alert"]
    assert alert_blocks[0].data_count == 17


# --------------------------------------------------------------- plan_right_column


def test_split_workloads_leftover_goes_to_the_other_block():
    """3 VMs + 20 containers, budget 10 → les 3 VMs tiennent, containers prend le reste."""
    assert _split_workloads(10, 3, 20) == (3, 7)


def test_split_workloads_equal_demand_splits_evenly():
    assert _split_workloads(10, 12, 12) == (5, 5)


def test_split_workloads_single_block_takes_everything():
    assert _split_workloads(10, 0, 30) == (0, 10)
    assert _split_workloads(10, 30, 0) == (10, 0)


def test_split_workloads_never_exceeds_demand():
    assert _split_workloads(10, 2, 3) == (2, 3)


def test_split_workloads_odd_leftover_goes_to_vms_first():
    """Biais documenté : le reliquat impair est proposé d'abord à `vms`
    (ordre de RIGHT_SLOT)."""
    assert _split_workloads(5, 10, 10) == (3, 2)


def test_split_workloads_zero_quota_hides_both():
    assert _split_workloads(0, 5, 5) == (0, 0)


def _plan(body_height, **overrides):
    """Solveur avec un décor réaliste : 1 ligne processcount, pas d'AMP,
    4 VMs, 30 containers, 400 processus, 40 alertes."""
    kwargs = {
        "body_height": body_height,
        "static_heights": {"processcount": 1},
        "amps_height": 0,
        "n_vms": 4,
        "n_containers": 30,
        "n_processes": 400,
        "n_alerts": 40,
    }
    kwargs.update(overrides)
    return plan_right_column(**kwargs)


def _cost(plan, *, n_vms=4, n_containers=30, n_processes=400, n_alerts=40, static=1, amps=0):
    """Hauteur réellement occupée par un plan — miroir de _paint_sidebar :
    somme des hauteurs des blocs visibles + une ligne vide entre blocs."""
    heights = []
    if n_vms and plan["vms"]:
        heights.append(1 + min(n_vms, plan["vms"]))
    if n_containers and plan["containers"]:
        heights.append(1 + min(n_containers, plan["containers"]))
    if static:
        heights.append(static)
    amps_rows = plan.get("amps", amps)
    if amps_rows:
        heights.append(amps_rows)
    if n_processes and plan["processlist"]:
        heights.append(1 + min(n_processes, plan["processlist"]))
    heights.append(_alert_block_height(n_alerts, plan["alert"]))
    return sum(heights) + max(0, len(heights) - 1)


def test_plan_nominal_on_a_comfortable_terminal():
    """Assez de place → valeurs nominales, sauf les workloads qui regagnent
    la seule ligne de mou disponible (palier de croissance A) : le coût au
    palier nominal est 50 (< 51) — l'alerte compte deux lignes d'en-tête,
    titre + en-têtes de colonnes (`_alert_block_height`) — et l'unique ligne
    de surplus va aux workloads avant que les processus n'en voient la
    couleur (palier A avant B, cf. `test_plan_workloads_grow_before_processes`)."""
    plan = _plan(51)
    assert plan["vms"] + plan["containers"] == 11
    assert plan["alert"] == 10
    assert plan["processlist"] >= _NOMINAL_PROCESSES


def test_plan_processes_absorb_all_the_surplus():
    """Le seul bloc élastique remplit le terminal, sans le dépasser."""
    plan = _plan(60)
    assert _cost(plan) <= 60
    grown = dict(plan, processlist=plan["processlist"] + 1)
    assert _cost(grown) > 60, "une ligne de plus aurait encore tenu"


def test_plan_workloads_grow_before_processes():
    """Palier A avant B : sur un terminal haut les workloads regagnent de la
    place avant que la processlist n'avale tout."""
    plan = _plan(90)
    assert plan["vms"] + plan["containers"] == _MAX_WORKLOADS


def test_plan_workloads_never_exceed_the_growth_ceiling():
    plan = _plan(400)
    assert plan["vms"] + plan["containers"] == _MAX_WORKLOADS


def _first_height_where(predicate):
    """Plus grande hauteur (en descendant) où `predicate(plan)` devient vrai.

    Balayer plutôt que coder en dur une hauteur rend les tests robustes au
    décor : c'est bien l'ORDRE des paliers qui est vérifié, pas une valeur
    arithmétique fragile.
    """
    for height in range(80, 0, -1):
        if predicate(_plan(height)):
            return height
    return None


def test_plan_shrink_ladder_follows_the_documented_order():
    """Les paliers a→k se déclenchent dans l'ordre du spec, jamais l'inverse.

    Seuls les paliers workloads (a, d, g) et alertes (b, e, h) sont observables
    par un quota : les paliers processus (c, f, i, k) ne sont que des
    concessions temporaires, remboursées juste après par la croissance
    (cf. `test_plan_processes_always_absorb_the_slack`).
    """
    steps = {
        "a": lambda p: p["vms"] + p["containers"] <= 5,
        "b": lambda p: p["alert"] <= 5,
        "d": lambda p: p["vms"] + p["containers"] <= 3,
        "e": lambda p: p["alert"] <= 3,
        "g": lambda p: p["vms"] + p["containers"] == 0,
        "h": lambda p: p["alert"] == 0,
    }
    heights = {name: _first_height_where(pred) for name, pred in steps.items()}
    assert all(h is not None for h in heights.values()), heights
    ordered = [heights[name] for name in "abdegh"]
    # Hauteurs décroissantes : un palier ne peut pas se déclencher avant celui
    # qui le précède dans la cascade.
    assert ordered == sorted(ordered, reverse=True), heights


def test_plan_processes_always_absorb_the_slack():
    """Contrat R4 sur les DEUX branches : à chaque hauteur, le nombre de
    processus est le plus grand qui tienne encore — une ligne de plus
    déborderait, sauf si tous les processus sont déjà affichés."""
    for height in range(80, 0, -1):
        plan = _plan(height)
        if plan["processlist"] >= 400:
            continue
        grown = dict(plan, processlist=plan["processlist"] + 1)
        assert _cost(grown) > height, f"une ligne de processus de plus tenait encore à body_height={height}"


def test_plan_step_a_shrinks_workloads_alone():
    """Juste sous le seuil nominal, SEULS les workloads reculent : les alertes
    restent au nominal et les processus ne perdent rien (ils récupèrent même
    les lignes que le palier a libérées en trop)."""
    height = _first_height_where(lambda p: p["vms"] + p["containers"] < 10)
    plan = _plan(height)
    assert plan["vms"] + plan["containers"] == 5
    assert plan["alert"] == 10
    assert plan["processlist"] >= 20


def test_plan_cascade_is_monotonic():
    """Réduire la hauteur ne peut jamais augmenter le quota d'un bloc que la
    cascade fait reculer définitivement (workloads, alertes), et le plan tient
    toujours dans la hauteur disponible tant qu'on n'a pas épuisé la cascade.

    Les processus, eux, ne sont PAS monotones : quand un palier libère plus que
    le déficit, ils récupèrent le surplus, donc leur quota peut remonter d'une
    hauteur à la suivante (cf. `test_plan_processes_always_absorb_the_slack`).
    """
    previous = None
    for height in range(60, 14, -1):
        plan = _plan(height)
        assert _cost(plan) <= height, f"plan déborde à body_height={height}"
        if previous is not None:
            assert plan["vms"] + plan["containers"] <= previous["workloads"]
            assert plan["alert"] <= previous["alert"]
        previous = {
            "workloads": plan["vms"] + plan["containers"],
            "alert": plan["alert"],
        }


def test_plan_step_g_hides_workloads_entirely():
    plan = _plan(12)
    assert plan["vms"] == 0
    assert plan["containers"] == 0


def test_plan_step_h_leaves_alert_header_only():
    plan = _plan(10)
    assert plan["alert"] == 0


def test_plan_keeps_five_processes_until_the_alert_block_is_a_header():
    """Le plancher 5 processus est plus fort que les alertes : il ne tombe
    qu'une fois workloads masqués (g) et alertes réduites à l'en-tête (h)."""
    plan = _plan(11)
    assert plan["processlist"] >= 5


def test_plan_breaks_the_process_floor_only_at_the_very_end():
    plan = _plan(7)
    assert plan["processlist"] < 5
    assert plan["processlist"] >= 1


def test_plan_never_returns_zero_processes():
    plan = _plan(1)
    assert plan["processlist"] == 1


def test_plan_step_j_truncates_amps_before_the_last_process_step():
    """Un AMP bavard est rogné plutôt que de faire disparaître la
    processlist."""
    plan = _plan(14, amps_height=30, n_vms=0, n_containers=0)
    assert plan.get("amps") is not None
    assert plan["amps"] < 30
    assert plan["processlist"] >= 1


def test_plan_leaves_amps_untouched_when_they_fit():
    plan = _plan(60, amps_height=3)
    assert "amps" not in plan


def test_plan_absent_blocks_free_room_for_processes():
    """Sans containers ni VMs, les paliers a/d/g sont des no-op : la place
    qu'ils auraient prise revient à la processlist."""
    with_workloads = _plan(40)
    without = _plan(40, n_vms=0, n_containers=0)
    assert without["vms"] == 0
    assert without["containers"] == 0
    assert without["processlist"] > with_workloads["processlist"]


def test_plan_programlist_mirrors_processlist():
    """Les deux vues sont mutuellement exclusives et partagent le budget."""
    plan = _plan(40)
    assert plan["programlist"] == plan["processlist"]


def test_plan_on_a_degenerate_height_does_not_crash():
    for height in (0, -5):
        plan = plan_right_column(
            body_height=height,
            static_heights={},
            amps_height=0,
            n_vms=0,
            n_containers=0,
            n_processes=10,
            n_alerts=0,
        )
        assert plan["processlist"] >= 1


def test_plan_floor_keeps_active_alerts_visible():
    """Une alerte ACTIVE est toujours affichée : les paliers b/e/h ne peuvent
    pas descendre le quota sous le nombre d'alertes en cours.

    Borne basse à 7 : c'est le coût plancher de 3 alertes une fois tout le
    reste masqué (processcount 1 + ligne vide 1 + bloc alerte 2+3). En dessous
    la géométrie l'interdit et le palier m reprend la main
    (cf. `test_plan_reduces_active_alerts_only_once_everything_else_is_gone`).
    """
    for height in range(60, 6, -1):
        plan = _plan(height, n_ongoing=3)
        assert plan["alert"] >= 3, f"une alerte active a été coupée à body_height={height}"


def test_plan_floor_is_capped_at_the_nominal_maximum():
    """Le plancher ne peut pas dépasser le plafond de 10 lignes d'alertes."""
    plan = _plan(60, n_ongoing=25)
    assert plan["alert"] == _NOMINAL_ALERTS


def test_plan_floor_takes_the_rows_from_the_other_blocks():
    """« Au détriment du reste » : à la hauteur où la cascade réduisait les
    alertes, ce sont désormais les workloads et les processus qui paient."""
    height = 10
    without = _plan(height)
    active = _plan(height, n_ongoing=4)
    assert without["alert"] == 0
    assert active["alert"] == 4
    assert active["vms"] + active["containers"] == 0
    assert active["processlist"] < without["processlist"]


def test_plan_hides_the_process_block_for_an_active_alert():
    """Palier l : la processlist disparaît entièrement (en-tête comprise)
    plutôt que de rogner une alerte active.

    14 lignes = exactement le coût de processcount (1) + ligne vide (1) + le
    bloc alerte complet (2 en-têtes + 10 lignes). Un seul processus coûterait
    3 lignes de plus (ligne vide + en-tête + la ligne) : il saute.
    """
    plan = _plan(14, n_ongoing=10)
    assert plan["processlist"] == 0
    assert plan["alert"] == 10


def test_plan_new_steps_are_inert_without_active_alerts():
    """Conservatisme : sans alerte active, les paliers l/m ne se déclenchent
    jamais et la cascade historique s'arrête au palier k (1 processus)."""
    for height in range(80, 0, -1):
        assert _plan(height)["processlist"] >= 1, f"palier l déclenché à tort à body_height={height}"


def test_plan_reduces_active_alerts_only_once_everything_else_is_gone():
    """Palier m : le plancher ne cède qu'après la disparition des workloads,
    des AMP et de la processlist."""
    plan = _plan(6, n_ongoing=10, amps_height=4)
    assert plan["alert"] < 10
    assert plan["vms"] + plan["containers"] == 0
    assert plan["processlist"] == 0
    assert plan["amps"] == 1


def test_plan_always_fits_when_alerts_are_active():
    """Garantie dure : dès qu'une alerte est active, le plan tient TOUJOURS
    dans la hauteur disponible, à partir de 3 lignes (processcount + ligne
    vide + en-tête alerte).

    `n_ongoing=0` est exclu volontairement : sans alerte active les paliers
    l/m restent inertes et la cascade historique peut encore déborder, ce que
    le peintre tronque (cf. `test_plan_new_steps_are_inert_without_active_alerts`).
    """
    for height in range(3, 61):
        for n_ongoing in range(1, 16):
            plan = _plan(height, n_ongoing=n_ongoing)
            assert _cost(plan) <= height, f"plan déborde à body_height={height}, n_ongoing={n_ongoing}"


def _alert_history(n):
    # Distinct `key` per event so each opens its own incident (§5.4) — a
    # repeated `(plugin, key, field)` tuple would collapse into one.
    return [
        {
            "ts": f"2026-08-05T10:{i:02d}:00+00:00",
            "plugin": "cpu",
            "key": f"core{i}",
            "field": "total",
            "level": "warning",
            "previous_level": "ok",
        }
        for i in range(n)
    ]


def test_alert_limit_zero_renders_the_header_only():
    """Piège : `history[-0:]` renvoie TOUT l'historique. Le palier h doit
    court-circuiter explicitement."""
    rows = render_alert_block(_alert_history(27), limit=0)
    assert len(rows) == 1
    assert "ALERTS" in "".join(c.text for c in rows[0].cells)


def test_alert_limit_is_read_from_the_row_budget():
    frame = build_frame(
        store_snapshot={},
        fields_by_plugin={},
        registry=[],
        alerts_history=_alert_history(27),
        view={"row_budget": {"alert": 4}},
    )
    alert_block = [b for b in frame.right if b.name == "alert"][0]
    # title + column header + 4 data rows.
    assert len(alert_block.rows) == 2 + 4


def test_alert_without_row_budget_keeps_the_default_limit():
    frame = build_frame(
        store_snapshot={},
        fields_by_plugin={},
        registry=[],
        alerts_history=_alert_history(27),
    )
    alert_block = [b for b in frame.right if b.name == "alert"][0]
    # title + column header + 10 data rows (the default limit).
    assert len(alert_block.rows) == 2 + 10


# ------------------------------------------- ongoing_since (history eviction)


def test_derive_incidents_uses_ongoing_since_for_a_fully_evicted_alert():
    """`_history` is bounded: a long-running alert outlives its opening event.
    The engine's `get_ongoing_since()` is then the only source for `begin`."""
    incidents = _derive_incidents(
        [],
        ongoing={("cpu", None, "total"): "critical"},
        ongoing_since={("cpu", None, "total"): "2026-08-16T09:00:00+00:00"},
    )
    assert len(incidents) == 1
    assert incidents[0]["begin"] == "2026-08-16T09:00:00+00:00"
    # The start is known exactly, so the duration is no longer a lower bound.
    assert incidents[0]["partial"] is False


def test_derive_incidents_ongoing_since_overrides_a_partial_begin():
    """When only an ESCALATION survived the eviction, `begin` is a lower bound
    (`partial`). The engine knows the real start — it wins."""
    history = [_evt("2026-08-16T13:00:00+00:00", "mem", "percent", "critical", previous="warning")]
    incidents = _derive_incidents(
        history,
        ongoing={("mem", None, "percent"): "critical"},
        ongoing_since={("mem", None, "percent"): "2026-08-16T09:00:00+00:00"},
    )
    assert len(incidents) == 1
    assert incidents[0]["begin"] == "2026-08-16T09:00:00+00:00"
    assert incidents[0]["partial"] is False


def test_derive_incidents_ongoing_since_leaves_resolved_incidents_alone():
    """A resolved incident has no entry in `ongoing_since`; its history-derived
    `begin` and its `partial` lower bound must survive untouched."""
    history = [
        _evt("2026-08-16T13:00:00+00:00", "fs", "percent", "critical", previous="warning", key="/"),
        _evt("2026-08-16T13:30:00+00:00", "fs", "percent", "ok", previous="critical", key="/"),
    ]
    incidents = _derive_incidents(history, ongoing={}, ongoing_since={})
    assert len(incidents) == 1
    assert incidents[0]["ongoing"] is False
    assert incidents[0]["begin"] == "2026-08-16T13:00:00+00:00"
    assert incidents[0]["partial"] is True


def test_render_alert_block_fully_evicted_alert_shows_its_real_start():
    """End to end: the `--:--:--` regression the engine timestamp fixes."""
    rows = render_alert_block(
        [],
        limit=10,
        now=_GRID_NOW,
        ongoing={("cpu", None, "total"): "critical"},
        ongoing_since={("cpu", None, "total"): "2026-08-16T09:00:00+00:00"},
        width=61,
    )
    painted = "\n".join(_line(r) for r in rows)
    assert "Cpu total" in painted
    assert "--:--:--" not in painted
    # 5h05m of alert, and no `>` lower-bound marker.
    assert "5h05m" in painted
    assert ">" not in painted


def test_data_pinned_on_alert_block_counts_only_the_active_incidents():
    """`plan_right_column` a besoin du nombre d'alertes ACTIVES pour son
    plancher : le bloc le publie via `data_pinned`, dérivé de la même liste
    d'incidents que `data_count` (donc jamais désynchronisé).

    3 incidents ouverts, 2 déjà résolus → 5 incidents, 3 épinglés."""
    history = _alert_history(3) + [
        {
            "ts": "2026-08-05T11:00:00+00:00",
            "plugin": "mem",
            "key": f"m{i}",
            "field": "percent",
            "level": level,
            "previous_level": previous,
        }
        for i in range(2)
        for level, previous in (("warning", "ok"), ("ok", "warning"))
    ]
    frame = build_frame(
        store_snapshot={},
        fields_by_plugin={},
        registry=[],
        alerts_history=history,
    )
    alert = next(b for b in frame.right if b.name == "alert")
    assert alert.data_count == 5
    assert alert.data_pinned == 3


def test_data_pinned_defaults_to_zero_for_ordinary_blocks():
    """Seul le bloc alerte épingle des lignes ; tout le reste vaut 0."""
    assert PluginBlock(name="cpu").data_pinned == 0
