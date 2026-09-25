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


def test_render_nice_shows_the_raw_value_on_posix(fields):
    rows = render({"data": [_proc(pid=1, nice=19)], "_levels": {}}, fields)
    assert rows[1].cells[NICE_COL].text.strip() == "19"


def test_render_nice_shows_windows_priority_class_as_a_label(fields, monkeypatch):
    """Windows reports the Win32 priority class, not a nice value (#3672)."""
    monkeypatch.setattr("glances.plugins.processlist.render_curses_v5.WINDOWS", True)
    # 32768 = ABOVE_NORMAL_PRIORITY_CLASS. Rendered raw it is a meaningless
    # number too wide for the NI column.
    rows = render({"data": [_proc(pid=1, nice=32768)], "_levels": {}}, fields)
    assert rows[1].cells[NICE_COL].text.strip() == "AN"


def test_render_nice_keeps_an_unmapped_windows_value_numeric(fields, monkeypatch):
    """A priority class Windows adds later stays a number instead of vanishing."""
    monkeypatch.setattr("glances.plugins.processlist.render_curses_v5.WINDOWS", True)
    rows = render({"data": [_proc(pid=1, nice=7)], "_levels": {}}, fields)
    assert rows[1].cells[NICE_COL].text.strip() == "7"


def test_render_nice_cell_keeps_its_level_colour_on_windows(fields, monkeypatch):
    """The label is display-only: the alert still comes from the raw value."""
    monkeypatch.setattr("glances.plugins.processlist.render_curses_v5.WINDOWS", True)
    payload = {
        "data": [_proc(pid=1, nice=32768)],
        "_levels": {1: {"nice": {"level": "warning", "prominent": False}}},
    }
    rows = render(payload, fields)
    assert rows[1].cells[NICE_COL].text.strip() == "AN"
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


# ---------------------------------------------------------- responsive columns
#
# The renderer drops fixed columns (order a→h: VIRT, TIME+, RES, USER, PID,
# THR, S, NI) until the flexible ``Command`` column has at least 8 chars,
# based on ``view["right_width"]``. CPU%, MEM%, R/s, W/s and Command are
# never dropped. Absent ``right_width`` keeps every column.

ALL_LABELS = ("CPU%", "MEM%", "VIRT", "RES", "PID", "USER", "THR", "NI", "S", "TIME+", "R/s", "W/s", "Command")


def _has_col(rows, label):
    # rows[0] is the header; its cell labels are the reliable signal.
    # Match the column label exactly (stripped) — a substring test would
    # false-match "S" against "RES", "NI" against ... etc.
    return any(c.text.strip() == label for c in rows[0].cells)


def test_wide_keeps_all_columns(payload, fields):
    rows = render(payload, fields, view={"right_width": 400})
    for label in ALL_LABELS:
        assert _has_col(rows, label), label


def test_no_width_keeps_all_columns(payload, fields):
    # Backward compatible: no right_width → all columns (today's behaviour).
    full = render(payload, fields)
    wide = render(payload, fields, view={"right_width": 400})
    assert full == wide


def test_narrow_drops_in_order_virt_first(payload, fields):
    # Width chosen so VIRT (a) must go but RES (c) is still present. `_W_CPU`
    # (7 characters) is part of every column's `used` total, so this width
    # was found by sweeping the actual renderer rather than derived by hand.
    rows = render(payload, fields, view={"right_width": 77})
    assert not _has_col(rows, "VIRT")  # (a) dropped first
    assert _has_col(rows, "RES")  # (c) still present at this width
    assert _has_col(rows, "Command")


def test_very_narrow_drops_cascade(payload, fields):
    rows = render(payload, fields, view={"right_width": 30})
    # By this width VIRT/TIME+/RES/USER at least are gone; never CPU%/MEM%/Command.
    for gone in ("VIRT", "TIME+", "RES", "USER"):
        assert not _has_col(rows, gone), gone
    for kept in ("CPU%", "MEM%", "Command"):
        assert _has_col(rows, kept), kept


def test_command_gets_at_least_8_when_possible(payload, fields):
    # After dropping, the non-command fixed width must leave >=8 for Command.
    width = 64
    rows = render(payload, fields, view={"right_width": width})
    header = rows[0]
    non_cmd = [c for c in header.cells if "Command" not in c.text]
    used = sum(len(c.text) for c in non_cmd) + (len(header.cells) - 1)  # separators
    assert width - used >= 8


def test_header_and_rows_drop_consistently(fields):
    # Kernel-thread processes (empty cmdline) render Command as a single
    # ``[name]`` cell, so each row's total cell count equals the header's —
    # this isolates the fixed-column filter from the variable-width command
    # (which can span cmd + args cells).
    payload = {
        "data": [_proc(pid=1, cmdline=[], name="kt1"), _proc(pid=2, cmdline=[], name="kt2")],
        "_levels": {},
    }
    rows = render(payload, fields, view={"right_width": 64})
    ncols = len(rows[0].cells)
    for r in rows[1:]:
        assert len(r.cells) == ncols  # every data row matches the header column count


@pytest.mark.parametrize(
    ("cpu_percent", "expected"),
    [
        (12.3, "   12.3"),  # < 1000 → one decimal, as before
        (999.9, "  999.9"),  # last value that still fits with a decimal
        (1384.7, "   1385"),  # >= 1000 → integer form (rounded, as v4), column stays 7 wide
        (12345.6, "  12346"),
    ],
)
def test_cpu_percent_drops_decimal_above_1000(fields, cpu_percent, expected):
    """A process spread over many cores must not widen the CPU% column.

    The 1000 threshold is independent of `_W_CPU`'s own width: dropping the
    decimal above 1000 keeps every value inside the column regardless -- see
    `_format_percent`'s own docstring.
    """
    payload = {"data": [_proc(pid=1, cpu_percent=cpu_percent)], "_levels": {}}
    cell = render(payload, fields)[1].cells[CPU_COL]
    assert cell.text == expected
    assert len(cell.text) == 7  # never overflows the 7-wide column


# ---------------------------------------------------------- row_budget (vertical fit)


def _many_procs(n):
    return {"data": [_proc(pid=1000 + i, name=f"proc{i}") for i in range(n)], "_levels": {}}


def test_row_budget_caps_the_number_of_processes(fields):
    rows = render(_many_procs(50), fields, view={"row_budget": {"processlist": 7}})
    assert len(rows) == 1 + 7  # en-tête + 7 processus


def test_row_budget_above_the_default_shows_more_than_twenty(fields):
    """La règle principale : sur un terminal haut on dépasse _MAX_ROWS."""
    rows = render(_many_procs(50), fields, view={"row_budget": {"processlist": 45}})
    assert len(rows) == 1 + 45


def test_without_row_budget_the_default_cap_still_applies(fields):
    """Non-régression : sans budget, la sortie est celle d'aujourd'hui."""
    rows = render(_many_procs(50), fields)
    assert len(rows) == 1 + 20


def test_row_budget_zero_hides_the_block_entirely(fields):
    """Palier l de la cascade verticale : une alerte active a besoin de la
    place, la processlist disparaît en-tête comprise (parité `containers`)."""
    assert render(_many_procs(50), fields, view={"row_budget": {"processlist": 0}}) == []


@pytest.mark.parametrize("nice", [-20, -11, -5, 0, 19])
def test_render_nice_keeps_the_sign_and_fits_the_column(fields, nice):
    """NI used to keep only its last 2 characters: -20 read "20", making a
    high-priority process look low-priority. v4 renders it on 3 columns."""
    rows = render({"data": [_proc(pid=1, nice=nice)], "_levels": {}}, fields)
    text = rows[1].cells[NICE_COL].text
    assert text.strip() == str(nice)
    assert len(text) == len(rows[0].cells[NICE_COL].text)  # aligned with its header


def test_render_thread_count_is_never_truncated(fields):
    """1234 threads used to read "234"; v4 lets the value overflow instead."""
    rows = render({"data": [_proc(pid=1, num_threads=1234)], "_levels": {}}, fields)
    assert "1234" in [c.text.strip() for c in rows[1].cells]


# ------------------------------------------------- selection cursor (2.X-b)


def _decorated_rows(rows):
    """Row indices (0 = header) whose command cells carry the selection mark."""
    return [
        i for i, row in enumerate(rows) if any(c.underline and c.color is ColorRole.OK for c in row.cells[CMD_START:])
    ]


def test_no_cursor_in_the_view_decorates_nothing(payload, fields):
    """Export, tests and `--disable-cursor` all reach the renderer as an
    ABSENT key — the pre-2.X-b output, byte for byte."""
    assert _decorated_rows(render(payload, fields)) == []
    assert _decorated_rows(render(payload, fields, view={"sort_key": "cpu_percent"})) == []


@pytest.mark.parametrize("position", [0, 1, 2])
def test_the_cursor_decorates_the_row_it_names(position, payload, fields):
    """Row 0 is the column header, so process *i* is drawn at row *i+1*."""
    rows = render(payload, fields, view={"cursor_position": position})
    assert _decorated_rows(rows) == [position + 1]


def test_the_decoration_is_v4s_underlined_green_command(payload, fields):
    """v4 marks the command cells and nothing else, with `PROCESS_SELECTED` =
    `OK | A_UNDERLINE` (`processlist/__init__.py:553`,
    `outputs/glances_colors.py:154`). Not a reverse-video bar."""
    rows = render(payload, fields, view={"cursor_position": 0})
    selected = rows[1]

    command = selected.cells[CMD_START:]
    assert command and all(c.underline and c.color is ColorRole.OK for c in command)
    # The numeric columns keep their own colours — including the warning-level
    # CPU cell, which the selection must not overwrite.
    assert not any(c.underline for c in selected.cells[:CMD_START])
    assert selected.cells[CPU_COL].color is ColorRole.WARNING


def test_a_cursor_past_the_last_row_decorates_nothing(payload, fields):
    """The TUI clamps, but the renderer must not raise if it ever gets an
    index it cannot honour (a frame built between a shrink and its re-clamp)."""
    assert _decorated_rows(render(payload, fields, view={"cursor_position": 99})) == []


# ------------------------------------------- extended stats block (2.X-b3)


def _extended_payload(**overrides):
    """The shape the real engine produces — verified against it, not invented.

    `ionice` and `memory_info` are DICTS by the time a renderer sees them:
    the engine stores `namedtuple_to_dict(proc)` (`processes.py:669`).
    """
    base = {
        "pid": 1,
        "name": "hot",
        "cpu_min": 0.5,
        "cpu_max": 78.4,
        "cpu_mean": 12.25,
        "memory_min": 1.0,
        "memory_max": 12.5,
        "memory_mean": 6.0,
        "cpu_affinity": [0, 1, 2, 3],
        "ionice": {"ioclass": 2, "value": 4},
        "memory_info": {"rss": 32 * 1024**2, "vms": 120 * 1024**2},
        "memory_swap": 4 * 1024**2,
        "num_threads": 20,
        "num_fds": 45,
        "tcp": 3,
        "udp": 1,
    }
    base.update(overrides)
    return base


def _flat(rows):
    return [" ".join(c.text for c in r.cells) for r in rows]


def test_no_extended_payload_renders_nothing_extra(payload, fields):
    """Absent from `view` (export, tests, `e` off) → the output is what it was
    before 2.X-b3, byte for byte."""
    assert len(render(payload, fields, view={})) == 4
    assert len(render(payload, fields)) == 4


def test_the_extended_block_renders_v4s_four_lines(payload, fields):
    rows = render(payload, fields, view={"extended_process": _extended_payload()})
    lines = _flat(rows)

    assert "Pinned thread" in lines[0] and "hot" in lines[0] and "'e' to unpin" in lines[0]
    assert "CPU Min/Max/Mean" in lines[1]
    assert "MEM Min/Max/Mean" in lines[2]
    assert lines[3].startswith(" Open:")
    # ... and the process table still follows.
    assert "CPU%" in lines[4]


def test_the_cpu_line_carries_min_max_mean_affinity_and_io_nice(payload, fields):
    line = _flat(render(payload, fields, view={"extended_process": _extended_payload()}))[1]
    assert "0.5" in line and "78.4" in line and "12.2" in line
    assert "4 cores" in line
    assert "Best Effort" in line


def test_v4_never_renders_its_io_nice_line_and_v5_does(payload, fields):
    """v4 guards on `hasattr(prog['ionice'], 'ioclass')`
    (`processlist/__init__.py:728-742`), but the engine already converted the
    `pionice` namedtuple to a dict — which has no attribute of that name. So
    the guard is always False. Confirmed against the live engine."""
    from glances.plugins.processlist.render_curses_v5 import _ionice_text

    live_shape = {"ioclass": 0, "value": 0}
    assert not hasattr(live_shape, "ioclass")  # what v4 tests, on the real shape
    assert _ionice_text(live_shape) is not None  # what v5 does instead


def test_the_io_nice_value_is_shown_only_when_it_is_set(payload, fields):
    from glances.plugins.processlist.render_curses_v5 import _ionice_text

    assert "value 4/7" in _ionice_text({"ioclass": 2, "value": 4})
    assert "value" not in _ionice_text({"ioclass": 2, "value": 0})
    assert _ionice_text({"value": 3}) is None
    assert _ionice_text(None) is None


def test_the_mem_line_carries_the_memory_breakdown_and_swap(payload, fields):
    line = _flat(render(payload, fields, view={"extended_process": _extended_payload()}))[2]
    assert "rss" in line and "vms" in line
    assert "32.0M" in line and "120M" in line
    assert "4.0M" in line and "swap" in line


def test_the_open_line_counts_only_what_the_platform_reports(payload, fields):
    """`num_fds` is Unix, `num_handles` is Windows — neither is invented."""
    rows = render(payload, fields, view={"extended_process": _extended_payload(num_fds=None)})
    line = _flat(rows)[3]
    assert "20 threads" in line
    assert "fds" not in line
    assert "3 tcp" in line and "1 udp" in line


def test_a_missing_field_does_not_break_the_block(payload, fields):
    """The engine sets `extended_stats: False` and leaves the rest out when
    the grab failed (`processes.py:397-400`)."""
    rows = render(payload, fields, view={"extended_process": {"pid": 1, "name": "hot"}})
    lines = _flat(rows)
    assert "Pinned thread" in lines[0]
    assert "0.0" in lines[1]  # min/max/mean fall back to zero, as in v4


def test_the_budget_still_buys_process_rows_with_the_block_on(payload, fields):
    """The block does NOT spend the process budget. It cannot: four rows do
    not fit in a budget of three, and truncating a stats block is worse than
    useless. The vertical solver is told the cost instead
    (`extended_block_height` → `plan_right_column(process_extra_rows=…)`), so
    the budget that arrives here has already paid for them."""
    view = {"row_budget": {"processlist": 3}}
    rows = render(payload, fields, view={**view, "extended_process": _extended_payload()})

    assert len(rows) == 4 + 1 + 3  # block + column header + the full budget


def test_the_declared_height_is_what_the_block_actually_renders(payload, fields):
    """Derived, not a constant: a fifth line added to the block must move this
    number by itself, or the solver would under-reserve and the body overflow."""
    from glances.plugins.processlist.render_curses_v5 import extended_block_height

    extended = _extended_payload()
    declared = extended_block_height(extended)
    plain = render(payload, fields, view={})
    with_block = render(payload, fields, view={"extended_process": extended})

    assert declared == len(with_block) - len(plain)


def test_nothing_is_declared_when_the_block_is_off(payload, fields):
    from glances.plugins.processlist.render_curses_v5 import extended_block_height

    assert extended_block_height(None) == 0
    assert extended_block_height({}) == 0


def test_an_empty_payload_renders_no_block_at_all(payload, fields):
    """An empty dict is not "a process with unknown values" — it is no
    process. Rendering four lines of `?` for it would contradict the height
    declared to the solver, which counts it as zero."""
    assert len(render(payload, fields, view={"extended_process": {}})) == 4


def test_the_io_nice_classes_mirror_v4s_table():
    """v4 `get_headers` (`processlist/__init__.py:719-726`): on Linux class 0
    is the bare "no priority" wording, the others carry "Class is"; Windows
    keeps 0/1/2 with entirely different meanings."""
    from glances.plugins.processlist.render_curses_v5 import (
        _IONICE_CLASSES,
        _IONICE_CLASSES_WINDOWS,
        _ionice_text,
    )

    assert _IONICE_CLASSES[0] == "No specific I/O priority"
    assert _IONICE_CLASSES[2] == "Class is Best Effort"
    assert _IONICE_CLASSES_WINDOWS[2] == "No specific I/O priority"
    assert _IONICE_CLASSES_WINDOWS[0] == "Class is Very Low"
    # An unknown class is named, not dropped.
    assert _ionice_text({"ioclass": 9}) == "Class is 9"


# ------------------------------------ the filtered summary (2.X-b4)


_SUMMARY = {
    "current": {"cpu_percent": 12.5, "memory_percent": 3.1, "vms": 33554432, "rss": 1048576, "read": 0.0, "write": 0.0},
    "min": {"cpu_percent": 1.0, "memory_percent": 0.5, "vms": 1024, "rss": 512, "read": 0.0, "write": 0.0},
    "max": {"cpu_percent": 90.0, "memory_percent": 9.9, "vms": 67108864, "rss": 2097152, "read": 0.0, "write": 0.0},
}


def test_no_summary_key_renders_nothing_extra(payload, fields):
    """Absent from `view` (no filter, export, tests) → the output is what it
    was before 2.X-b4, byte for byte."""
    assert len(render(payload, fields, view={})) == 4


def test_the_summary_adds_a_rule_and_three_rows(payload, fields):
    rows = render(payload, fields, view={"filter_summary": _SUMMARY})
    assert len(rows) == 4 + 4
    lines = _flat(rows)
    assert set(lines[4].strip()) == {"_"}
    assert lines[5].endswith("< current")
    assert "< min" in lines[6] and "('M' to reset)" in lines[6]
    assert "< max" in lines[7] and "('M' to reset)" in lines[7]


def test_the_summary_carries_the_aggregate_values(payload, fields):
    line = _flat(render(payload, fields, view={"filter_summary": _SUMMARY}))[5]
    assert "12.5" in line and "3.1" in line
    assert "32.0M" in line and "1.0M" in line


def test_the_summary_follows_the_columns_that_survived_the_cascade(payload, fields):
    """A narrow block drops columns; the aggregate row has to drop the same
    ones or the numbers land under the wrong headers."""
    view = {"filter_summary": _SUMMARY, "right_width": 60}
    rows = render(payload, fields, view=view)
    header_cells = len(rows[0].cells)
    # The summary row is the fixed columns that survived, plus its `< label`.
    assert len(rows[-1].cells) <= header_cells + 1
    assert "VIRT" not in " ".join(c.text for c in rows[0].cells)
    assert "32.0M" not in _flat(rows)[-1]


def test_the_summary_is_declared_to_the_vertical_solver(payload, fields):
    """Four unmodelled rows would overflow the body by four, exactly as the
    `e` block would."""
    from glances.plugins.processlist.render_curses_v5 import process_extra_rows

    assert process_extra_rows({"filter_summary": _SUMMARY}) == 4
    assert process_extra_rows({}) == 0
    assert process_extra_rows(None) == 0


def test_the_two_extra_blocks_cost_the_solver_their_sum(payload, fields):
    """`e` and the filter can be on at once; the solver needs ONE number."""
    from glances.plugins.processlist.render_curses_v5 import process_extra_rows

    both = {"filter_summary": _SUMMARY, "extended_process": _extended_payload()}
    assert process_extra_rows(both) == 4 + 4

    rows = render(payload, fields, view=both)
    assert len(rows) == 4 + 1 + 3 + 4  # block + header + processes + summary


def test_a_partial_summary_renders_only_what_it_carries(payload, fields):
    """Defensive: the TUI always sends all three, but a row with no dict must
    not become a row of `None`s."""
    rows = render(payload, fields, view={"filter_summary": {"current": _SUMMARY["current"]}})
    assert len(rows) == 4 + 2


# ---------------------------------------------------------- summarise()


def test_summarise_adds_up_the_columns_that_matter():
    from glances.plugins.processlist.render_curses_v5 import summarise

    totals = summarise(
        [
            _proc(pid=1, cpu_percent=2.0, memory_percent=1.0, memory_info={"rss": 100, "vms": 200}),
            _proc(pid=2, cpu_percent=3.0, memory_percent=0.5, memory_info={"rss": 50, "vms": 100}),
        ]
    )
    assert totals["cpu_percent"] == 5.0
    assert totals["memory_percent"] == 1.5
    assert totals["rss"] == 150
    assert totals["vms"] == 300


def test_summarise_of_nothing_is_zero_not_an_error():
    from glances.plugins.processlist.render_curses_v5 import summarise

    assert summarise([])["cpu_percent"] == 0.0


def test_summarise_skips_a_value_it_cannot_add():
    """`cpu_percent` is -1 or None on a process psutil could not read."""
    from glances.plugins.processlist.render_curses_v5 import summarise

    totals = summarise([_proc(pid=1, cpu_percent=None), _proc(pid=2, cpu_percent=4.0)])
    assert totals["cpu_percent"] == 4.0


def test_summarise_ignores_an_unknown_io_rate():
    """An unknown rate renders `?` in the table; summing it as zero would be a
    quiet lie, and summing it as anything else impossible."""
    from glances.plugins.processlist.render_curses_v5 import summarise

    known = summarise([_proc(pid=1, io_counters=[2048, 1024, 0, 0, 1], time_since_update=1.0)])
    unknown = summarise([_proc(pid=1, io_counters=[2048, 1024, 0, 0, 0], time_since_update=1.0)])
    assert known["read"] == 2048
    assert unknown["read"] == 0.0


# ------------------------------- the command column's horizontal scroll


def _command_text(rows, index=1):
    from glances.plugins.processlist.render_curses_v5 import _FIXED_COL_KEYS

    return " ".join(c.text for c in rows[index].cells[len(_FIXED_COL_KEYS) :])


def test_no_offset_leaves_the_command_untouched(payload, fields):
    rows = render(payload, fields, view={"command_offset": 0, "process_short_name": True})
    assert _command_text(rows) == _command_text(render(payload, fields))


def test_the_offset_scrolls_the_arguments_only(payload, fields):
    """The executable name is what identifies the row; scrolling the whole
    cell would push it off the left edge. v4 scrolls the arguments alone
    (`processlist/__init__.py:566-567`)."""
    rows = render(payload, fields, view={"command_offset": 3})
    text = _command_text(rows)
    assert text.startswith("python3")  # the name stayed
    assert "…" in text
    assert "myscript.py" not in text  # ... and the arguments moved
    assert "cript.py" in text


def test_a_scrolled_row_keeps_its_marker_when_the_arguments_run_out(payload, fields):
    """Losing the column silently would leave a user with no clue that the
    text is off to the left."""
    rows = render(payload, fields, view={"command_offset": 500})
    text = _command_text(rows)
    assert text.startswith("python3")
    assert "…" in text


def test_a_row_with_no_arguments_gains_the_marker_too(fields):
    """Consistency: every row scrolls by the same amount, so a row that had
    nothing to scroll must still show that the column is scrolled."""
    payload = {"data": [_proc(pid=1, cmdline=["python3"])], "_levels": {}}
    assert "…" in _command_text(render(payload, fields, view={"command_offset": 2}))
    assert "…" not in _command_text(render(payload, fields))


def test_the_path_prefix_does_not_scroll_in_full_mode(fields, monkeypatch):
    """In full mode the path is part of what names the process, so it stays
    with the executable rather than scrolling away."""
    monkeypatch.setattr("glances.plugins.processlist.render_curses_v5.os.path.isdir", lambda p: True)
    payload = {"data": [_proc(pid=1, cmdline=["/usr/bin/python3", "--flag", "value"])], "_levels": {}}

    text = _command_text(render(payload, fields, view={"command_offset": 2, "process_short_name": False}))
    assert text.startswith("/usr/bin/ python3")
    assert "…" in text


# ---------------------------------------------------------------- --process-focus


def test_the_focus_is_named_above_the_column_header():
    """v4 `_msg_curse_header` (`processlist/__init__.py:844-847`)."""
    from glances.plugins.processlist.render_curses_v5 import process_extra_rows, render

    payload = {"data": [{"pid": 1, "name": "python", "cmdline": ["python"]}], "_levels": {}}
    rows = render(payload, {}, view={"process_focus": [".*python.*", "sshd"]})
    assert rows[0].cells[0].text == "Focus on following processes: .*python.*, sshd"
    assert rows[1].cells[0].text.strip() == "CPU%"
    assert process_extra_rows({"process_focus": ["sshd"]}) == 1
    assert process_extra_rows({}) == 0


def test_no_focus_no_banner():
    from glances.plugins.processlist.render_curses_v5 import render

    rows = render({"data": [], "_levels": {}}, {})
    assert rows[0].cells[0].text.strip() == "CPU%"


# ---------------------------------------------------------------- Irix mode (`0`, v4 disable_irix)


def _irix_payload(cores=4):
    return {
        "data": [{"pid": 1, "name": "python", "cmdline": ["python"], "cpu_percent": 80.0}],
        "_levels": {1: {"cpu_percent": {"level": "critical", "prominent": False}}},
        "cpucore": cores,
    }


def test_irix_divides_the_cpu_by_the_core_count():
    """v4 `processlist/__init__.py:361,817-822`: `CPU%/4`, 80% -> 20%."""
    from glances.outputs.curses_renderer_v5 import ColorRole
    from glances.plugins.processlist.render_curses_v5 import render

    rows = render(_irix_payload(), {}, view={"load_irix": True})
    assert rows[0].cells[0].text.strip() == "CPU%/4"
    assert rows[1].cells[0].text.strip() == "20.0"
    # The colour stays the raw value's level.
    assert rows[1].cells[0].color is ColorRole.CRITICAL


def test_irix_says_cpui_from_ten_cores_up():
    from glances.plugins.processlist.render_curses_v5 import render

    assert render(_irix_payload(16), {}, view={"load_irix": True})[0].cells[0].text.strip() == "CPUi"


def test_irix_keeps_the_sort_underline_on_the_cpu_column():
    from glances.plugins.processlist.render_curses_v5 import render

    header = render(_irix_payload(), {}, view={"load_irix": True, "sort_key": "cpu_percent"})[0]
    assert header.cells[0].underline is True


def test_irix_is_inert_without_the_published_core_count():
    """An older server's payload has no `cpucore`: no division by a guess."""
    from glances.plugins.processlist.render_curses_v5 import render

    payload = _irix_payload()
    del payload["cpucore"]
    rows = render(payload, {}, view={"load_irix": True})
    assert rows[0].cells[0].text.strip() == "CPU%"
    assert rows[1].cells[0].text.strip() == "80.0"


def test_programlist_says_cpu_per_c_from_ten_cores_up():
    """v4 programlist `_cpu_header_msg`: `CPU%/<n>`, then `CPU%/C`."""
    from glances.plugins.programlist.render_curses_v5 import render

    payload = {"data": [{"name": "python", "cpu_percent": 80.0, "nprocs": 2}], "_levels": {}, "cpucore": 4}
    rows = render(payload, {}, view={"load_irix": True})
    assert rows[0].cells[0].text.strip() == "CPU%/4"
    assert rows[1].cells[0].text.strip() == "20.0"
    payload["cpucore"] = 12
    assert render(payload, {}, view={"load_irix": True})[0].cells[0].text.strip() == "CPU%/C"
