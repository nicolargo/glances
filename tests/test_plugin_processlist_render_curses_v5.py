"""Glances v5 — tests for the processlist plugin's curses renderer."""

from __future__ import annotations

import pytest

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.processlist.render_curses_v5 import render

# Cell index of each fixed column (header + data rows share this prefix).
# The command may span 1-3 cells (path / cmd / args), so it's at indices
# CMD_START onward — never refer to it by a fixed index.
CPU_COL = 0
MEM_COL = 1
VIRT_COL = 2
RES_COL = 3
PID_COL = 4
USER_COL = 5
THR_COL = 6
NICE_COL = 7
STATUS_COL = 8
TIME_COL = 9
RS_COL = 10
WS_COL = 11
CMD_START = 12


@pytest.fixture
def fields():
    return {
        "pid": {"unit": "number", "primary_key": True},
        "name": {"unit": "string"},
        "username": {"unit": "string"},
        "status": {"unit": "string", "watched": True, "threshold_type": "categorical"},
        "nice": {"unit": "number", "watched": True, "threshold_type": "categorical"},
        "num_threads": {"unit": "number"},
        "cpu_percent": {"unit": "percent", "watched": True, "prominent": False},
        "memory_percent": {"unit": "percent", "watched": True, "prominent": False},
        "cmdline": {"unit": "list"},
        "cpu_num": {"unit": "number"},
        "memory_info": {"unit": "byte", "internal": True},
        "io_counters": {"unit": "byte", "internal": True},
        "time_since_update": {"unit": "second", "internal": True},
    }


def _proc(**overrides):
    base = {
        "pid": 1234,
        "name": "python3",
        "username": "alice",
        "status": "S",
        "nice": 0,
        "num_threads": 4,
        "cpu_percent": 12.5,
        "memory_percent": 3.1,
        "cmdline": ["python3", "myscript.py"],
        "cpu_num": 2,
        "memory_info": {"rss": 32 * 1024**2, "vms": 120 * 1024**2},
        "io_counters": [0, 0, 0, 0, 1],  # io_tag=1, zero traffic
        "cpu_times": {"user": 1.0, "system": 0.5},
        "time_since_update": 1.0,
    }
    base.update(overrides)
    return base


@pytest.fixture
def payload():
    return {
        "data": [
            _proc(pid=1, cpu_percent=78.4, memory_percent=12.5, name="hot"),
            _proc(pid=42, cpu_percent=12.5, memory_percent=3.1, name="med"),
            _proc(pid=512, cpu_percent=0.5, memory_percent=0.2, username="root", name="sshd"),
        ],
        "_levels": {
            1: {
                "cpu_percent": {"level": "warning", "prominent": False},
                "memory_percent": {"level": "ok", "prominent": False},
            },
            42: {
                "cpu_percent": {"level": "ok", "prominent": False},
                "memory_percent": {"level": "ok", "prominent": False},
            },
            512: {
                "cpu_percent": {"level": "ok", "prominent": False},
                "memory_percent": {"level": "ok", "prominent": False},
            },
        },
    }


# ---------------------------------------------------------- structure


def test_render_header_first_row(payload, fields):
    rows = render(payload, fields)
    flat = " ".join(c.text for c in rows[0].cells)
    for col in ("CPU%", "MEM%", "VIRT", "RES", "PID", "USER", "THR", "NI", "S", "TIME+", "R/s", "W/s", "Command"):
        assert col in flat, col


def test_render_one_row_per_process_plus_header(payload, fields):
    rows = render(payload, fields)
    assert len(rows) == 4


def test_render_preserves_engine_sort_order(payload, fields):
    rows = render(payload, fields)
    pids = [int(r.cells[PID_COL].text.strip()) for r in rows[1:]]
    # Payload order = engine sorted order (cpu desc).
    assert pids == [1, 42, 512]


def test_render_cpu_cell_inherits_level_color(payload, fields):
    rows = render(payload, fields)
    assert rows[1].cells[CPU_COL].color == ColorRole.WARNING
    assert rows[1].cells[CPU_COL].prominent is False


def test_render_mem_cell_inherits_level_color(payload, fields):
    rows = render(payload, fields)
    assert rows[1].cells[MEM_COL].color == ColorRole.OK


def test_render_status_is_single_char(payload, fields):
    rows = render(payload, fields)
    for r in rows[1:]:
        assert len(r.cells[STATUS_COL].text.strip()) <= 1


# ---------------------------------------------------------- memory columns


def test_render_virt_column_shows_human_bytes(payload, fields):
    rows = render(payload, fields)
    # vms = 120 MiB → "120M"
    assert "M" in rows[1].cells[VIRT_COL].text


def test_render_res_column_shows_human_bytes(payload, fields):
    rows = render(payload, fields)
    # rss = 32 MiB → "32.0M"
    assert "M" in rows[1].cells[RES_COL].text


def test_render_memory_info_missing_renders_question(fields):
    payload = {"data": [_proc(pid=1, memory_info=None)], "_levels": {}}
    rows = render(payload, fields)
    assert "?" in rows[1].cells[VIRT_COL].text
    assert "?" in rows[1].cells[RES_COL].text


# ---------------------------------------------------------- IO columns


def test_render_io_rate_zero_shows_0b(fields):
    rows = render({"data": [_proc(pid=1)], "_levels": {}}, fields)
    # io_tag=1 with zero traffic over 1 s → "0B"
    assert "0B" in rows[1].cells[RS_COL].text
    assert "0B" in rows[1].cells[WS_COL].text


def test_render_io_rate_computed_from_delta(fields):
    """Rate = (new - old) / time_since_update."""
    p = _proc(pid=1, io_counters=[1024 * 100, 1024 * 50, 0, 0, 1], time_since_update=1.0)
    rows = render({"data": [p], "_levels": {}}, fields)
    # 100K / 1 s → "100K" (or similar K-scaled).
    assert "K" in rows[1].cells[RS_COL].text
    assert "K" in rows[1].cells[WS_COL].text


def test_render_io_rate_unknown_when_tag_zero(fields):
    """io_tag=0 (access denied / first cycle) → '?'."""
    p = _proc(pid=1, io_counters=[100, 50, 0, 0, 0])
    rows = render({"data": [p], "_levels": {}}, fields)
    assert "?" in rows[1].cells[RS_COL].text
    assert "?" in rows[1].cells[WS_COL].text


def test_render_io_rate_unknown_when_no_io_counters(fields):
    p = _proc(pid=1, io_counters=None)
    rows = render({"data": [p], "_levels": {}}, fields)
    assert "?" in rows[1].cells[RS_COL].text


# ---------------------------------------------------------- TIME+ column


def test_render_time_under_one_hour_uses_minutes_seconds(fields):
    """``cpu_times.user + .system`` < 1h → ``MM:SS`` (v4 parity)."""
    p = _proc(pid=1, cpu_times={"user": 60.0, "system": 30.0})  # 1m30s
    rows = render({"data": [p], "_levels": {}}, fields)
    assert "1:30" in rows[1].cells[TIME_COL].text


def test_render_time_over_one_hour_uses_h_mm_ss(fields):
    """1h ≤ t < 100h → ``{H}h{MM:SS}``."""
    p = _proc(pid=1, cpu_times={"user": 3600.0 + 5 * 60 + 30, "system": 0.0})  # 1h05:30
    rows = render({"data": [p], "_levels": {}}, fields)
    assert "1h05:30" in rows[1].cells[TIME_COL].text


def test_render_time_missing_renders_question(fields):
    """No cpu_times → ``?`` (v4 parity)."""
    p = _proc(pid=1, cpu_times=None)
    rows = render({"data": [p], "_levels": {}}, fields)
    assert "?" in rows[1].cells[TIME_COL].text


def test_render_time_tuple_format_supported(fields):
    """psutil pcputimes namedtuple comes through as a (user, system, ...) tuple."""
    p = _proc(pid=1, cpu_times=(2.0, 1.0, 0.0, 0.0))  # 3s total
    rows = render({"data": [p], "_levels": {}}, fields)
    assert "0:03" in rows[1].cells[TIME_COL].text


# ---------------------------------------------------------- sort indicator (view)


def test_render_sort_indicator_underlines_active_column(payload, fields):
    """The active sort column header is underlined (v4 'SORT' decoration)."""
    rows = render(payload, fields, view={"sort_key": "memory_percent"})
    header = rows[0].cells
    assert header[MEM_COL].underline is True
    assert header[CPU_COL].underline is False


def test_render_sort_indicator_cpu_default(payload, fields):
    rows = render(payload, fields, view={"sort_key": "cpu_percent"})
    assert rows[0].cells[CPU_COL].underline is True


def test_render_sort_indicator_io_underlines_both_rate_columns(payload, fields):
    """`io_counters` sort underlines the R/s and W/s pair."""
    rows = render(payload, fields, view={"sort_key": "io_counters"})
    header = rows[0].cells
    assert header[RS_COL].underline is True
    assert header[WS_COL].underline is True


def test_render_sort_indicator_name_underlines_command(payload, fields):
    rows = render(payload, fields, view={"sort_key": "name"})
    assert rows[0].cells[CMD_START].underline is True


def test_render_sort_indicator_time_underlines_time_column(payload, fields):
    rows = render(payload, fields, view={"sort_key": "cpu_times"})
    assert rows[0].cells[TIME_COL].underline is True


def test_render_no_view_means_no_underline(payload, fields):
    """Export / tests pass no view → no header is marked."""
    rows = render(payload, fields)
    assert all(c.underline is False for c in rows[0].cells)


def test_render_sort_indicator_unmarked_column_not_underlined(payload, fields):
    """A sort key with no matching column (cpu_num) underlines nothing."""
    rows = render(payload, fields, view={"sort_key": "cpu_num"})
    assert all(c.underline is False for c in rows[0].cells)


# ---------------------------------------------------------- categorical colour


def test_render_status_cell_inherits_categorical_level(fields):
    """When _levels carries status, the status cell picks up the colour."""
    payload = {
        "data": [_proc(pid=1, status="Z")],
        "_levels": {1: {"status": {"level": "critical", "prominent": False}}},
    }
    rows = render(payload, fields)
    assert rows[1].cells[STATUS_COL].color == ColorRole.CRITICAL


def test_render_nice_cell_inherits_categorical_level(fields):
    payload = {
        "data": [_proc(pid=1, nice=-5)],
        "_levels": {1: {"nice": {"level": "warning", "prominent": False}}},
    }
    rows = render(payload, fields)
    assert rows[1].cells[NICE_COL].color == ColorRole.WARNING


def test_render_status_default_color_without_level(fields):
    rows = render({"data": [_proc(pid=1)], "_levels": {}}, fields)
    assert rows[1].cells[STATUS_COL].color == ColorRole.DEFAULT


# ---------------------------------------------------------- command (v4 split_cmdline)


def test_render_command_cmd_is_bold(fields):
    """When cmdline[0] starts with name, the head is the cmd (no path)."""
    p = _proc(pid=1, name="python3", cmdline=["python3", "myscript.py"])
    rows = render({"data": [p], "_levels": {}}, fields)
    cmd_cells = rows[1].cells[CMD_START:]
    # First cmd cell is bold; arguments follow as non-bold.
    bold_cells = [c for c in cmd_cells if c.bold]
    assert any("python3" in c.text for c in bold_cells)


def test_render_command_path_stripped_in_default_view(fields):
    """v4 short-name view (default, no view passed): ``/usr/bin/python3
    script.py`` → only ``python3`` (bold) + ``script.py`` is shown — the
    path prefix is dropped. The full-path view (``/`` hotkey) is covered by
    the ``full-path view`` section below."""
    p = _proc(pid=1, name="python3", cmdline=["/usr/bin/python3", "script.py"])
    rows = render({"data": [p], "_levels": {}}, fields)
    cmd_cells = rows[1].cells[CMD_START:]
    flat = "".join(c.text for c in cmd_cells)
    # No path leak.
    assert "/usr/bin" not in flat
    # cmd is bold.
    bold_cells = [c for c in cmd_cells if c.bold]
    assert any(c.text == "python3" for c in bold_cells)
    # Arguments follow.
    plain_cells = [c for c in cmd_cells if not c.bold]
    assert any("script.py" in c.text for c in plain_cells)


def test_render_command_args_have_no_leading_space(fields):
    """The args cell must not carry a leading space — the painter already
    inserts exactly one separator space between cmd and args (regression:
    'python3  /usr/bin/x' double space → single space)."""
    p = _proc(pid=1, name="python3", cmdline=["python3", "/usr/bin/terminator"])
    rows = render({"data": [p], "_levels": {}}, fields)
    cmd_cells = rows[1].cells[CMD_START:]
    args_cells = [c for c in cmd_cells if not c.bold]
    assert args_cells, "expected an args cell"
    assert not args_cells[0].text.startswith(" ")
    assert args_cells[0].text == "/usr/bin/terminator"


def test_render_full_path_view_glues_command_to_path(fields, monkeypatch):
    """In full-path view the bold command is glued (no separating space) to
    the plain path prefix so it reads '/usr/bin/python3'."""
    import glances.plugins.processlist.render_curses_v5 as mod

    monkeypatch.setattr(mod.os.path, "isdir", lambda p: True)
    p = _proc(pid=1, name="python3", cmdline=["/usr/bin/python3", "script.py"])
    rows = render({"data": [p], "_levels": {}}, fields, view={"process_short_name": False})
    cmd_cells = rows[1].cells[CMD_START:]
    glued = [c for c in cmd_cells if c.glue]
    assert any(c.text == "python3" and c.bold for c in glued)


def test_render_command_arguments_are_non_bold(fields):
    p = _proc(pid=1, name="python3", cmdline=["python3", "script.py", "--flag"])
    rows = render({"data": [p], "_levels": {}}, fields)
    args_cells = [c for c in rows[1].cells[CMD_START:] if not c.bold]
    flat = " ".join(c.text for c in args_cells)
    assert "script.py --flag" in flat


def test_render_command_kthread_fallback(fields):
    """Empty cmdline → ``[name]`` (kernel thread)."""
    p = _proc(pid=1, name="kworker/0:1", cmdline=[])
    rows = render({"data": [p], "_levels": {}}, fields)
    cmd_text = " ".join(c.text for c in rows[1].cells[CMD_START:])
    assert "[kworker/0:1]" in cmd_text


def test_render_command_when_cmdline_none(fields):
    p = _proc(pid=1, name="ghost", cmdline=None)
    rows = render({"data": [p], "_levels": {}}, fields)
    cmd_text = " ".join(c.text for c in rows[1].cells[CMD_START:])
    assert "[ghost]" in cmd_text


# ---------------------------------------------------------- full-path view ('/')


def test_render_full_path_view_shows_path_prefix(fields, monkeypatch):
    """`process_short_name=False` + real dir → plain ``path/`` before bold cmd."""
    import glances.plugins.processlist.render_curses_v5 as mod

    monkeypatch.setattr(mod.os.path, "isdir", lambda p: True)
    p = _proc(pid=1, name="python3", cmdline=["/usr/bin/python3", "script.py"])
    rows = render({"data": [p], "_levels": {}}, fields, view={"process_short_name": False})
    cmd_cells = rows[1].cells[CMD_START:]
    flat = "".join(c.text for c in cmd_cells)
    assert "/usr/bin/" in flat
    # The path prefix is plain; the command stays bold.
    assert any(c.text == "/usr/bin/" and not c.bold for c in cmd_cells)
    assert any(c.text == "python3" and c.bold for c in cmd_cells)


def test_render_full_path_view_skips_nonexistent_path(fields, monkeypatch):
    """`isdir` False → no path prefix even in full view (v4 guard)."""
    import glances.plugins.processlist.render_curses_v5 as mod

    monkeypatch.setattr(mod.os.path, "isdir", lambda p: False)
    p = _proc(pid=1, name="python3", cmdline=["/weird/python3", "script.py"])
    rows = render({"data": [p], "_levels": {}}, fields, view={"process_short_name": False})
    flat = "".join(c.text for c in rows[1].cells[CMD_START:])
    assert "/weird" not in flat


def test_render_short_name_view_strips_path_with_view(fields):
    """`process_short_name=True` via view keeps the v4 short behaviour."""
    p = _proc(pid=1, name="python3", cmdline=["/usr/bin/python3", "script.py"])
    rows = render({"data": [p], "_levels": {}}, fields, view={"process_short_name": True})
    flat = "".join(c.text for c in rows[1].cells[CMD_START:])
    assert "/usr/bin" not in flat
    assert any(c.text == "python3" and c.bold for c in rows[1].cells[CMD_START:])


# ---------------------------------------------------------- truncation / alignment


def test_render_long_username_truncated(fields):
    payload = {"data": [_proc(pid=1, username="averylongusername_indeed")], "_levels": {}}
    rows = render(payload, fields)
    assert rows[1].cells[USER_COL].text.rstrip().endswith("+")


def test_render_caps_at_top_20(fields):
    payload = {"data": [_proc(pid=i + 1, cpu_percent=100.0 - i) for i in range(50)], "_levels": {}}
    rows = render(payload, fields)
    assert len(rows) == 21


def test_render_handles_empty_data(fields):
    rows = render({"data": [], "_levels": {}}, fields)
    assert len(rows) == 1


def test_render_handles_empty_payload(fields):
    rows = render({}, fields)
    assert len(rows) == 1
    flat = " ".join(c.text for c in rows[0].cells)
    assert "CPU%" in flat


def test_render_handles_missing_numeric_fields(fields):
    payload = {
        "data": [_proc(pid=1, num_threads=None, nice=None, cpu_percent=None, memory_percent=None)],
        "_levels": {},
    }
    rows = render(payload, fields)
    flat = " ".join(c.text for c in rows[1].cells)
    assert "?" in flat


def test_render_pid_width_scales_with_largest_pid(fields):
    payload = {"data": [_proc(pid=1), _proc(pid=1234567)], "_levels": {}}
    rows = render(payload, fields)
    widths = {len(r.cells[PID_COL].text) for r in rows}
    assert len(widths) == 1
    assert next(iter(widths)) >= 7


def test_render_fixed_columns_align_across_rows(payload, fields):
    """Every row shares the same widths for the fixed prefix (cols 0..CMD_START-1)."""
    rows = render(payload, fields)
    for col in range(CMD_START):
        widths = {len(r.cells[col].text) for r in rows if col < len(r.cells)}
        assert len(widths) == 1, f"col {col} widths differ: {widths}"
