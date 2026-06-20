# Glances v5 — TUI top-row responsive layout + quicklook justify

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.
>
> **PROJECT RULE — never commit.** Stage with `git add` ONLY, then STOP. No `git commit` / `git push` / `Co-Authored-By`. Report a suggested commit message. Tests run via `.venv/bin/python -m pytest`; lint via `.venv/bin/python -m ruff check` / `ruff format`.
>
> **PROJECT RULE — mirror v4.** The TUI must reproduce v4 behaviour. The degradation cascade below is the v4 behaviour the maintainer specified.

**Goal:** (1) Quicklook bars "justify" to the width of the block's first line (the CPU name/frequency header). (2) The TOP plugin row degrades gracefully when the terminal is too narrow, instead of curses clipping the last block (LOAD). Degradation is **measure-driven** (computed from the real block widths each cycle, not fixed width thresholds), applying these steps **in order** until the row fits:
- (a) hide MEM's 2nd column
- (b) hide CPU's 3rd column
- (c) hide CPU's 2nd column
- (d) replace the CPU name with `"Frequency "` and shrink the quicklook block accordingly
- (e) hide the quicklook block
- (f) hide the swap (memswap) block

**Architecture:** A new `view` contract carries degradation flags (`cpu_cols`, `mem_cols`, `quicklook_freq_only`, `hide_quicklook`, `hide_memswap`). The cpu/mem renderers gain a `view` param to drop columns; the quicklook renderer self-justifies bars to its header width and honours `quicklook_freq_only`; `build_frame` skips `hide_*` blocks. `TuiV5` runs a measure-and-degrade loop (`_build_fitted_frame`) that rebuilds the (pure, cheap) frame with escalating flags until `Σ block widths + min gaps ≤ max_x`.

**Tech stack:** Python 3, the v5 curses renderer (`Cell`/`Row`/`PluginBlock`/`Frame`/`build_frame`), `TuiV5` painter.

---

## Background — required reading

- `glances/outputs/glances_curses_v5.py` — `TuiV5`: `_repaint` (gets `max_x` via `getmaxyx`), `_build_frame(max_x)`, `_build_view(max_x)`, `_paint`, `_paint_top_row`, `_top_row_gaps`, `_TOP_GAP_MIN`, `_QUICKLOOK_COMPACT_WIDTH`.
- `glances/outputs/curses_renderer_v5.py` — `build_frame(... view=...)` (registry loop ~line 724, already skips `_FULL_QUICKLOOK_HIDDEN` when `view["full_quicklook"]`), `Frame.top`, `PluginBlock.width` (natural width property ~line 211), `_discover_plugin_renderer`, `_accepts_view`.
- `glances/plugins/cpu/render_curses_v5.py` — `render(payload, fields_desc)` (NO view yet). 3-column grid; line 1 = title+total | idle | ctx_sw; col1 user/system/iowait, col2 irq/nice/steal, col3 interrupts/sw_int/guest.
- `glances/plugins/mem/render_curses_v5.py` — `render(payload, fields_desc)` (NO view yet). line 1 = title+percent | active; col1 total/(available|used)/free, col2 inactive/buffers/cached.
- `glances/plugins/quicklook/render_curses_v5.py` — already takes `view`; `_bar_width`, `_bar_cells`, `_header_row`.

### Key facts (verified)
- `PluginBlock.width` = max printable row width (accounts for `glue`). Available immediately after building a block.
- The painter fits the top row iff `sum(block.width) + (n-1)*_TOP_GAP_MIN ≤ max_x`; otherwise gaps collapse to 1 and curses CLIPS the rightmost block (the bug).
- `view` reaches a renderer only if it declares `view` (or `**kwargs`) — `_accepts_view`. cpu/mem must ADD a `view` param.
- `build_frame` is pure and cheap → calling it a handful of times per cycle to measure is acceptable (2 s refresh).

### View contract (this plan)
| key | type | default | meaning |
|---|---|---|---|
| `cpu_cols` | int | 3 | number of CPU grid columns to render (3→2→1) |
| `mem_cols` | int | 2 | number of MEM grid columns to render (2→1) |
| `quicklook_freq_only` | bool | False | header shows `"Frequency "` instead of the CPU name; bars shrink to match |
| `hide_quicklook` | bool | False | `build_frame` skips the quicklook block |
| `hide_memswap` | bool | False | `build_frame` skips the memswap block |

Defaults preserve today's output exactly (no regression when the terminal is wide).

---

## Task 1: CPU renderer honours `view["cpu_cols"]`

**Files:** Modify `glances/plugins/cpu/render_curses_v5.py`; Test `tests/test_plugin_cpu_render_curses_v5.py`.

- [ ] **Step 1: Write failing tests** (append). Use the file's existing payload/fields fixtures.

```python
def test_cpu_cols_2_drops_third_column(cpu_payload_linux, cpu_fields):
    full = render(cpu_payload_linux, cpu_fields)
    two = render(cpu_payload_linux, cpu_fields, view={"cpu_cols": 2})
    full_text = "\n".join("".join(c.text for c in r.cells) for r in full)
    two_text = "\n".join("".join(c.text for c in r.cells) for r in two)
    # Column 3 labels (interrupts / soft_interrupts / ctx_switches / guest) gone.
    assert "interrupts" in full_text
    assert "interrupts" not in two_text
    # Column 1 + 2 survive.
    assert "user" in two_text and "irq" in two_text
    # Narrower block.
    assert max(len(r) for r in two_text.splitlines()) < max(len(r) for r in full_text.splitlines())


def test_cpu_cols_1_keeps_only_first_column(cpu_payload_linux, cpu_fields):
    one = render(cpu_payload_linux, cpu_fields, view={"cpu_cols": 1})
    text = "\n".join("".join(c.text for c in r.cells) for r in one)
    assert "user" in text          # col1 stays
    assert "irq" not in text        # col2 gone
    assert "interrupts" not in text # col3 gone
    assert "CPU" in text and "%" in text  # title + total stay


def test_cpu_default_is_three_columns(cpu_payload_linux, cpu_fields):
    assert render(cpu_payload_linux, cpu_fields) == render(cpu_payload_linux, cpu_fields, view={"cpu_cols": 3})
```

- [ ] **Step 2: Run** `.venv/bin/python -m pytest tests/test_plugin_cpu_render_curses_v5.py -k cpu_cols -v` → FAIL (render takes no `view`).

- [ ] **Step 3: Implement.** Add `view: dict | None = None` to `render`'s signature. Read `n_cols = int((view or {}).get("cpu_cols", 3))` clamped to 1..3. Then:
  - Line 1: keep `CPU`+total always. Include the idle (col-2) label/value pair only when `n_cols >= 2`; include the ctx_sw (col-3) pair only when `n_cols >= 3` (replace the dropped pairs with nothing — do not emit empty placeholder cells, so the block is genuinely narrower).
  - Grid lines 2-4: emit col1 always; col2 only if `n_cols >= 2`; col3 only if `n_cols >= 3`.
  - Feed only the surviving columns into `_align_grid` so width shrinks.
  IMPORTANT: read the real `render` body and adapt — the column cells are built as `col1_keys_labels` / `col2_keys_labels` / `col3_keys_labels` and `line1_cells`. Gate each column's contribution on `n_cols`. Keep the default (`n_cols==3`) byte-identical to today.

- [ ] **Step 4: Run** the whole file → all pass (existing + 3 new). `ruff check`+`format` clean.
- [ ] **Step 5: Stage** the two files. Msg: `feat(v5/tui): cpu renderer honours view["cpu_cols"] for responsive layout`.

---

## Task 2: MEM renderer honours `view["mem_cols"]`

**Files:** Modify `glances/plugins/mem/render_curses_v5.py`; Test `tests/test_plugin_mem_render_curses_v5.py`.

- [ ] **Step 1: Write failing tests** (append; reuse the file's fixtures).

```python
def test_mem_cols_1_drops_second_column(mem_payload, mem_fields):
    full = render(mem_payload, mem_fields)
    one = render(mem_payload, mem_fields, view={"mem_cols": 1})
    full_text = "\n".join("".join(c.text for c in r.cells) for r in full)
    one_text = "\n".join("".join(c.text for c in r.cells) for r in one)
    # 2nd column (inactive/buffers/cached) and the line-1 `active` pair gone.
    for label in ("inactive", "buffers", "cached"):
        if label in full_text:
            assert label not in one_text
    assert "total" in one_text  # col1 stays
    assert "MEM" in one_text and "%" in one_text
    assert max(len(r) for r in one_text.splitlines()) < max(len(r) for r in full_text.splitlines())


def test_mem_default_is_two_columns(mem_payload, mem_fields):
    assert render(mem_payload, mem_fields) == render(mem_payload, mem_fields, view={"mem_cols": 2})
```

- [ ] **Step 2: Run** → FAIL (no `view`).
- [ ] **Step 3: Implement.** Add `view=None`; `n_cols = int((view or {}).get("mem_cols", 2))` clamped 1..2. Drop column 2 (and the line-1 `active` pair) when `n_cols == 1`. Read the real body; adapt to its exact cell construction; default unchanged.
- [ ] **Step 4: Run** full file → pass. Lint clean.
- [ ] **Step 5: Stage.** Msg: `feat(v5/tui): mem renderer honours view["mem_cols"] for responsive layout`.

---

## Task 3: Quicklook justify-to-header + `quicklook_freq_only`

**Files:** Modify `glances/plugins/quicklook/render_curses_v5.py`; Test `tests/test_plugin_quicklook_render_curses_v5.py`.

Two changes: (1) in compact mode (NOT `full_quicklook`), bar rows justify to the header line width; (2) `view["quicklook_freq_only"]` makes the header show `"Frequency "` instead of the CPU name (step d) — which, combined with (1), shrinks every bar row.

- [ ] **Step 1: Write failing tests** (append).

```python
def test_freq_only_header_uses_frequency_label(_payload):
    p = _payload(cpu_name="A Very Long CPU Brand Name X", cpu_hz_current=2_000_000_000, cpu_hz=3_000_000_000)
    rows = render(p, FIELDS, view={"quicklook_freq_only": True})
    head = _text(rows[0])
    assert "A Very Long CPU Brand Name X" not in head
    assert head.startswith("Frequency")
    assert "GHz" in head


def test_bars_justify_to_header_width(_payload):
    # With a header present, every bar row width == header row width (justified).
    p = _payload(cpu_name="Chip", cpu_hz_current=2_000_000_000, cpu_hz=3_000_000_000)
    rows = render(p, FIELDS)
    def w(r):  # painter width = text + (non-glue separators)
        return sum(len(c.text) for c in r.cells) + sum(1 for i, c in enumerate(r.cells) if i > 0 and not c.glue)
    header_w = w(rows[0])
    bar_ws = [w(r) for r in rows[1:]]
    assert bar_ws and all(bw == header_w for bw in bar_ws)


def test_freq_only_is_narrower_than_named(_payload):
    p = _payload(cpu_name="A Very Long CPU Brand Name X", cpu_hz_current=2_000_000_000, cpu_hz=3_000_000_000)
    named = render(p, FIELDS)
    freq = render(p, FIELDS, view={"quicklook_freq_only": True})
    def block_w(rows):
        return max(sum(len(c.text) for c in r.cells) + sum(1 for i, c in enumerate(r.cells) if i > 0 and not c.glue) for r in rows)
    assert block_w(freq) < block_w(named)
```

> NOTE: confirm the test file already has a `_payload` fixture/helper and `FIELDS`/`_text`. Reuse them; if `_payload` is a plain function (not a fixture), call it directly rather than taking it as a param.

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.**
  - `_header_row(payload, freq_only=False)`: when `freq_only`, set `name = "Frequency"` regardless of `cpu_name`. (Keep returning `None` when `cpu_hz_current` is absent.)
  - `render`: read `freq_only = bool((view or {}).get("quicklook_freq_only"))`; pass to `_header_row`.
  - **Justify**: compute the header row's painter-width (text + non-glue separators). For compact mode (not `full_quicklook`), set the bar target width = `max(header_width, _DEFAULT_BAR_WIDTH_FLOOR)` and derive `bar_size = target - label_width(5) - 2` for `_bar_cells`. When `full_quicklook`, keep using `view["quicklook_width"]` (unchanged). When there is NO header (no freq), fall back to today's default width.
  - Make `_bar_cells`/`_bar_width` accept the computed target so every bar row equals the header width (justified). Keep `glue=True` on bracket/bar cells (do not regress the flush brackets).
- [ ] **Step 4: Run** full file → all pass (existing 11 + new). Lint clean.
- [ ] **Step 5: Stage.** Msg: `feat(v5/tui): quicklook bars justify to header width + freq-only mode (steps 1 & d)`.

---

## Task 4: `build_frame` honours `hide_quicklook` / `hide_memswap`

**Files:** Modify `glances/outputs/curses_renderer_v5.py`; Test `tests/test_curses_renderer_v5.py`.

- [ ] **Step 1: Write failing tests** (append). Mirror the existing full-quicklook hide tests.

```python
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
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** In `build_frame`'s registry loop, just after the existing `_FULL_QUICKLOOK_HIDDEN` skip, add:
```python
        if view and view.get("hide_quicklook") and plugin_name == "quicklook":
            continue
        if view and view.get("hide_memswap") and plugin_name == "memswap":
            continue
```
- [ ] **Step 4: Run** the file → all pass (existing + 2). Lint clean.
- [ ] **Step 5: Stage.** Msg: `feat(v5/tui): build_frame honours hide_quicklook / hide_memswap`.

---

## Task 5: measure-driven degradation loop in TuiV5

**Files:** Modify `glances/outputs/glances_curses_v5.py`; Test `tests/test_curses_v5.py`.

The painter computes the minimal degradation that makes the TOP row fit, then paints the fitted frame.

- [ ] **Step 1: Read the seams.** Confirm: `_repaint` calls `_build_frame(max_x)` then `_paint`; `_build_frame(max_x)` builds `view` via `_build_view(max_x)` then calls `build_frame(...)`. Confirm `_TOP_GAP_MIN` exists.

- [ ] **Step 2: Write failing tests** (append; reuse the file's `_make_tui`/fake fixtures).

```python
# Ordered degradation steps (a→f) — exported for the test + the loop.
def test_degrade_steps_order():
    from glances.outputs.glances_curses_v5 import _DEGRADE_STEPS
    assert _DEGRADE_STEPS == [
        ("mem_cols", 1), ("cpu_cols", 2), ("cpu_cols", 1),
        ("quicklook_freq_only", True), ("hide_quicklook", True), ("hide_memswap", True),
    ]


def test_wide_terminal_no_degradation(make_tui_with_top):
    tui = make_tui_with_top()
    frame = tui._build_fitted_frame(max_x=400)  # plenty of room
    # All TOP plugins present; no degradation flags needed.
    assert {"quicklook", "cpu", "mem", "load"} <= {b.name for b in frame.top}


def test_narrow_terminal_drops_load_never(make_tui_with_top):
    tui = make_tui_with_top()
    frame = tui._build_fitted_frame(max_x=120)
    names = {b.name for b in frame.top}
    # LOAD must survive (the whole point); degradation hits mem/cpu cols / swap / quicklook first.
    assert "load" in names
    # The fitted top row must actually fit.
    widths = [b.width for b in frame.top]
    assert sum(widths) + max(0, len(widths) - 1) * tui._TOP_GAP_MIN <= 120
```

> NOTE: `tests/test_curses_v5.py` already builds `TuiV5` with fake fixtures. Add a `make_tui_with_top` helper (or extend the existing one) that registers a realistic TOP set (`quicklook`, `cpu`, `mem`, `memswap`, `load`) with representative payloads so the widths are realistic. If wiring real payloads is heavy, assert the behaviour via `_build_fitted_frame` against whatever TOP plugins the existing fixture registers, but you MUST include `load` + at least one degradable block to exercise the cascade.

- [ ] **Step 3: Implement.**
```python
# Ordered cascade (a→f). Each entry mutates the view; applied one at a time
# until the TOP row fits. cpu_cols=1 subsumes the col-3 drop.
_DEGRADE_STEPS: list[tuple[str, Any]] = [
    ("mem_cols", 1),            # (a)
    ("cpu_cols", 2),            # (b)
    ("cpu_cols", 1),            # (c)
    ("quicklook_freq_only", True),  # (d)
    ("hide_quicklook", True),   # (e)
    ("hide_memswap", True),     # (f)
]


def _top_fits(self, frame, max_x: int) -> bool:
    widths = [b.width for b in frame.top]
    if not widths:
        return True
    return sum(widths) + (len(widths) - 1) * self._TOP_GAP_MIN <= max_x


def _build_fitted_frame(self, max_x: int) -> Frame:
    """Build the frame, degrading the TOP row (a→f) until it fits max_x."""
    view = self._build_view(max_x)
    frame = self._frame_for_view(view)
    # full_quicklook owns the whole width; its own sibling-hiding already runs.
    if self._full_quicklook or self._top_fits(frame, max_x):
        return frame
    for key, val in _DEGRADE_STEPS:
        view[key] = val
        frame = self._frame_for_view(view)
        if self._top_fits(frame, max_x):
            break
    return frame
```
  - Add `_frame_for_view(self, view)` = the body currently inside `_build_frame` that calls `build_frame(store_snapshot=..., fields_by_plugin=..., registry=..., alerts_history=..., view=view)`. Refactor `_build_frame(max_x)` to `view=self._build_view(max_x); return self._frame_for_view(view)` so existing call-sites/tests keep working.
  - Change `_repaint` to call `self._build_fitted_frame(max_x)` instead of `self._build_frame(max_x)`.
  - Keep `_build_frame(max_x)` (non-fitted) for the existing tests that call it directly.

- [ ] **Step 4: Run** `.venv/bin/python -m pytest tests/test_curses_v5.py -q` → all pass. Then the full TUI+plugin suite:
  `.venv/bin/python -m pytest tests/test_curses_v5.py tests/test_curses_renderer_v5.py tests/test_plugin_cpu_render_curses_v5.py tests/test_plugin_mem_render_curses_v5.py tests/test_plugin_quicklook_render_curses_v5.py -q`.
- [ ] **Step 5: Stage.** Msg: `feat(v5/tui): measure-driven TOP-row degradation cascade (never clip LOAD)`.

---

## Task 6: docs

**Files:** Modify `docs/architecture/tui-v4-rendering-patterns.md`.

- [ ] **Step 1.** Add a "TOP-row responsive degradation" subsection: the `view` flags (`cpu_cols`/`mem_cols`/`quicklook_freq_only`/`hide_quicklook`/`hide_memswap`), the measure-driven cascade order (a→f), the fit rule (`Σ width + (n-1)·gap ≤ max_x`), and that quicklook bars justify to the header width. Update the quicklook section's bar-width note to mention header-justify (compact) vs `quicklook_width` (full).
- [ ] **Step 2.** `grep -n "cpu_cols\|degrad\|justify" docs/architecture/tui-v4-rendering-patterns.md` to confirm.
- [ ] **Step 3. Stage.** Msg: `docs(v5): document TOP-row responsive degradation + quicklook justify`.

---

## Self-review notes (author)

- **Coverage:** point 1 = Task 3; point 2a-f = cpu_cols (Tasks 1,5), mem_cols (Tasks 2,5), quicklook_freq_only (Tasks 3,5), hide_quicklook/hide_memswap (Tasks 4,5); the loop = Task 5.
- **No regression:** every flag defaults to today's behaviour; wide terminals take the early-return (`_top_fits` true) so output is byte-identical. The non-fitted `_build_frame` is retained for existing tests.
- **Measure-driven (maintainer decision):** the cascade keys on real `PluginBlock.width`, so it adapts to CPU-name length — exactly the &lt;148-col case the maintainer hit.
- **v4 parity:** cascade order a→f is the maintainer's spec; `_TOP_GAP_MIN` reused so the measure matches the painter's actual fit test.
- **Adaptation points (flagged, not placeholders):** exact cpu/mem cell-construction to gate per column (Tasks 1-2), the `_payload`/`FIELDS` test helpers (Task 3), and the `make_tui_with_top` fixture wiring (Task 5) must be matched to the real code — each task says how.
- **Cost:** up to 7 pure `build_frame` calls on a too-narrow cycle; negligible at 2 s refresh. Wide terminals do exactly one.
```

