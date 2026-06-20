# Glances v5 — processlist responsive columns

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Checkbox (`- [ ]`) steps.
>
> **PROJECT RULE — never commit.** Stage with `git add` ONLY, then STOP. No `git commit` / `git push` / `Co-Authored-By`. Suggest a commit message. Tests: `.venv/bin/python -m pytest`. Lint: `.venv/bin/python -m ruff check` / `ruff format`.

**Goal:** When the terminal is too narrow to show at least 8 characters of the processlist `Command` column, drop columns one at a time, in this order, until `Command` has ≥8 chars (or all are dropped):
(a) VIRT · (b) TIME+ · (c) RES · (d) USER · (e) PID · (f) THR · (g) S · (h) NI.
Columns never dropped: CPU%, MEM%, R/s, W/s, Command.

**Architecture:** The processlist block lives in the RIGHT sidebar; it is painted at `right_width = max_x − left_sidebar_width − gap`. `TuiV5` computes that width and passes it as `view["proclist_width"]`; the processlist renderer drops the lowest-priority columns until `Command` fits. Default (no `proclist_width`) keeps all columns — byte-identical to today. Low-risk approach: keep the existing cell-building code, tag each fixed column with a key, and FILTER header + rows by the active key set (no `ColumnSpec` rewrite).

**Tech stack:** v5 curses renderer (`Cell`/`Row`), `TuiV5` painter.

---

## Background — required reading

- `glances/plugins/processlist/render_curses_v5.py` — `render(payload, fields_desc, view=None)`. Width constants `_W_CPU/_W_MEM/_W_VIRT/_W_RES/_W_USER/_W_THR/_W_NI/_W_STATUS/_W_TIME/_W_IO` (~lines 53-64); dynamic `_pid_width(items)` (~276). Header built as `header_cells = [...]` (~322-336); per-row `fixed_cells = [...]` then `Row(cells=fixed_cells + _command_cells(item, short_name))` (~339-363). `view` keys read: `sort_key`, `process_short_name`.
- `glances/outputs/glances_curses_v5.py` — body layout: `_sidebar_split(frame, max_x)` (~612, returns left width bounded ≤34 and ≤max_x//2), `_SIDEBAR_SEPARATOR_GAP`, `_paint_sidebar` (right painted at `right_width = max_x − left_width − gap`, ~604-609). `_build_view(max_x)` (~546), `_build_frame`/`_frame_for_view`/`_build_fitted_frame` (top-row cascade), `_repaint` calls `_build_fitted_frame`.
- Column display order (13): `CPU%, MEM%, VIRT, RES, PID, USER, THR, NI, S, TIME+, R/s, W/s, Command`. `Command` is the flexible last column (painter clips it). The 12 "fixed" columns precede it.

### Key facts
- v4 has NO ordered drop (it uses per-cell `optional`/`additional` flags) — the a→h order is this maintainer's v5 spec; nothing to mirror byte-for-byte.
- Header and data rows are built as two independent lists → both must be filtered by the same active-key set.
- `right_width` (processlist paint width) depends only on `frame.left` natural widths, NOT on processlist's own columns → compute once, one extra build.

---

## Task 1: processlist renderer drops columns by `view["proclist_width"]`

**Files:** Modify `glances/plugins/processlist/render_curses_v5.py`; Test `tests/test_plugin_processlist_render_curses_v5.py` (create if absent; otherwise append).

- [ ] **Step 1: Write failing tests.** Reuse the file's existing payload/fixtures if a test file exists; otherwise build a minimal realistic payload (≥1 process with cpu_percent/memory_percent/memory_info{vms,rss}/pid/username/num_threads/nice/status/cpu times/io). Helper to flatten a row to text + a painter-width helper.

```python
from glances.plugins.processlist.render_curses_v5 import render

def _row_text(row):
    return " ".join(c.text for c in row.cells)  # header labels are the reliable signal

def _has_col(rows, label):
    return any(label in c.text for c in rows[0].cells)  # rows[0] = header

def test_wide_keeps_all_columns(proc_payload, proc_fields):
    rows = render(proc_payload, proc_fields, view={"proclist_width": 400})
    for label in ("CPU%", "MEM%", "VIRT", "RES", "PID", "USER", "THR", "NI", "S", "TIME+", "R/s", "W/s", "Command"):
        assert _has_col(rows, label)

def test_no_width_keeps_all_columns(proc_payload, proc_fields):
    # Backward compatible: no proclist_width → all columns (today's behaviour).
    full = render(proc_payload, proc_fields)
    wide = render(proc_payload, proc_fields, view={"proclist_width": 400})
    assert full == wide

def test_narrow_drops_in_order_virt_first(proc_payload, proc_fields):
    # Width chosen so exactly VIRT must go for Command to reach 8 cols.
    rows = render(proc_payload, proc_fields, view={"proclist_width": 70})
    assert not _has_col(rows, "VIRT")      # (a) dropped first
    assert _has_col(rows, "RES")            # (c) still present at this width
    assert _has_col(rows, "Command")

def test_very_narrow_drops_cascade(proc_payload, proc_fields):
    rows = render(proc_payload, proc_fields, view={"proclist_width": 30})
    # By this width VIRT/TIME+/RES/USER/PID/THR at least are gone; never CPU%/MEM%/Command.
    for gone in ("VIRT", "TIME+", "RES", "USER"):
        assert not _has_col(rows, gone)
    for kept in ("CPU%", "MEM%", "Command"):
        assert _has_col(rows, kept)

def test_command_gets_at_least_8_when_possible(proc_payload, proc_fields):
    # After dropping, the non-command fixed width must leave >=8 for Command.
    width = 70
    rows = render(proc_payload, proc_fields, view={"proclist_width": width})
    header = rows[0]
    non_cmd = [c for c in header.cells if "Command" not in c.text]
    used = sum(len(c.text) for c in non_cmd) + (len(header.cells) - 1)  # separators
    assert width - used >= 8

def test_header_and_rows_drop_consistently(proc_payload, proc_fields):
    rows = render(proc_payload, proc_fields, view={"proclist_width": 70})
    ncols = len(rows[0].cells)
    for r in rows[1:]:
        assert len(r.cells) == ncols  # every data row matches the header column count
```

- [ ] **Step 2: Run** → FAIL (`proclist_width` ignored).

- [ ] **Step 3: Implement.** In `render_curses_v5.py`:
  - Add constants:
    ```python
    _MIN_COMMAND_WIDTH = 8
    # Drop order a→h (maintainer spec). Never includes CPU%/MEM%/R/s/W/s/Command.
    _DROP_ORDER = ["VIRT", "TIME+", "RES", "USER", "PID", "THR", "S", "NI"]
    # Fixed columns in display order (the 12 cells before Command).
    _FIXED_COL_KEYS = ["CPU%", "MEM%", "VIRT", "RES", "PID", "USER", "THR", "NI", "S", "TIME+", "R/s", "W/s"]
    ```
  - Add a helper that picks the visible fixed-column keys given the available width and the dynamic pid width:
    ```python
    def _visible_fixed_keys(available_width: int, pid_width: int) -> list[str]:
        widths = {
            "CPU%": _W_CPU, "MEM%": _W_MEM, "VIRT": _W_VIRT, "RES": _W_RES,
            "PID": pid_width, "USER": _W_USER, "THR": _W_THR, "NI": _W_NI,
            "S": _W_STATUS, "TIME+": _W_TIME, "R/s": _W_IO, "W/s": _W_IO,
        }
        active = list(_FIXED_COL_KEYS)

        def command_space() -> int:
            used = sum(widths[k] for k in active)
            n_cells = len(active) + 1  # + Command
            return available_width - used - (n_cells - 1)  # painter separators

        for key in _DROP_ORDER:
            if command_space() >= _MIN_COMMAND_WIDTH:
                break
            if key in active:
                active.remove(key)
        return active
    ```
  - In `render`: read `available = (view or {}).get("proclist_width")`. Compute `pid_width` as today. If `available` is an int, `active = _visible_fixed_keys(available, pid_width)`; else `active = list(_FIXED_COL_KEYS)` (keep all → today's behaviour).
  - Build the FULL header fixed cells and FULL per-row fixed cells exactly as today (12 cells, same formatting), then FILTER both by `active` using `_FIXED_COL_KEYS` as the index, then append the Command header / `_command_cells`. Concretely: zip the 12 fixed cells with `_FIXED_COL_KEYS`, keep those whose key is in `active`, preserving order. Do this for the header row AND every data row so they stay column-aligned. Keep `Command` always.
  - IMPORTANT: do not change any cell's formatting/text/glue — only which cells are included. Default path (all 12 keys active) must be byte-identical to today (locked by `test_no_width_keeps_all_columns`).

- [ ] **Step 4: Run** the file → all pass. `ruff check`+`format --check` clean.
- [ ] **Step 5: Stage.** Msg: `feat(v5/tui): processlist drops columns to keep Command >=8 chars (view["proclist_width"])`.

---

## Task 2: TuiV5 computes & passes `proclist_width`

**Files:** Modify `glances/outputs/glances_curses_v5.py`; Test `tests/test_curses_v5.py`.

- [ ] **Step 1: Read seams.** Confirm `_sidebar_split(frame, max_x)`, `_SIDEBAR_SEPARATOR_GAP`, and that `_build_fitted_frame(max_x)` returns the final top-fitted frame built via `_frame_for_view(view)`.

- [ ] **Step 2: Write failing tests** (append; reuse `make_tui_with_top` / fake fixtures, register `processlist` in the RIGHT slot with a realistic payload + at least one LEFT plugin like `network` so the split is non-trivial).

```python
def test_proclist_width_passed_and_narrows_columns(make_tui_with_body):
    tui = make_tui_with_body()
    frame = tui._build_fitted_frame(max_x=95)   # narrow → right sidebar small
    proc = next(b for b in frame.right if b.name == "processlist")
    header = proc.rows[0]
    # At this width some columns must have been dropped (fewer than the full 13).
    assert len(header.cells) < 13
    # Command still present.
    assert any("Command" in c.text for c in header.cells)


def test_wide_terminal_keeps_all_proclist_columns(make_tui_with_body):
    tui = make_tui_with_body()
    frame = tui._build_fitted_frame(max_x=400)
    proc = next(b for b in frame.right if b.name == "processlist")
    assert len(proc.rows[0].cells) == 13  # all columns
```

- [ ] **Step 3: Implement.** In `_build_fitted_frame(max_x)`, AFTER the top-row cascade has settled `view`/`frame`, compute the right-sidebar width and rebuild once if a processlist block is present:
```python
    # processlist (RIGHT slot) is painted at right_width; tell its renderer so
    # it can drop columns to keep Command readable.
    if any(b.name == "processlist" for b in frame.right):
        left_width = self._sidebar_split(frame, max_x)
        right_width = max(0, max_x - left_width - self._SIDEBAR_SEPARATOR_GAP)
        if right_width and view.get("proclist_width") != right_width:
            view["proclist_width"] = right_width
            frame = self._frame_for_view(view)
    return frame
```
  (Place this just before the existing `return frame`. `left_width` depends only on `frame.left`, so one rebuild suffices.)

- [ ] **Step 4: Run** `.venv/bin/python -m pytest tests/test_curses_v5.py tests/test_curses_renderer_v5.py -q` → all pass. Lint clean.
- [ ] **Step 5: Stage.** Msg: `feat(v5/tui): plumb right-sidebar width into processlist (view["proclist_width"])`.

---

## Task 3: docs

**Files:** Modify `docs/architecture/tui-v4-rendering-patterns.md`.

- [ ] **Step 1.** Add/extend the processlist section (or the responsive section) with: the `view["proclist_width"]` contract; the a→h drop order; the ≥8-char Command rule; that it's measure-driven from the right-sidebar width; defaults keep all columns. Verify symbol names against shipped code.
- [ ] **Step 2.** `grep -n "proclist_width\|Command" docs/architecture/tui-v4-rendering-patterns.md`.
- [ ] **Step 3. Stage.** Msg: `docs(v5): document processlist responsive column dropping`.

---

## Self-review (author)

- **Coverage:** a→h order = `_DROP_ORDER` (Task 1); ≥8 rule = `_visible_fixed_keys` (Task 1); width plumbing = Task 2; never-drop set = the keys absent from `_DROP_ORDER`.
- **No regression:** no `proclist_width` (or wide) → all 12 fixed keys active → byte-identical (locked by `test_no_width_keeps_all_columns`).
- **Header/rows consistency:** the SAME `active` set filters header and every data row (Task 1 `test_header_and_rows_drop_consistently`).
- **Correct width:** `right_width = max_x − _sidebar_split − _SIDEBAR_SEPARATOR_GAP` matches the painter's actual processlist paint width; `left_width` independent of processlist columns → single rebuild.
- **Adaptation points (flagged):** exact fixtures in the test files, the precise indices of the 12 fixed cells in the current header/row lists (zip with `_FIXED_COL_KEYS`), and the `make_tui_with_body` helper wiring — match to real code per each task.
- **Cost:** one extra `build_frame` when processlist is shown; none otherwise.
```

