# TUI v5 — `now` plugin moved to the far right of the header banner

- **Date**: 2026-07-25
- **Branch**: `develop-v5`
- **Scope**: TUI v5 layout only (no engine, no REST, no Web UI change)

## 1. Problem

In the v5 TUI, the `now` plugin (current date/time) is the last block of the
**left sidebar** (`LEFT_SLOT` in `glances/outputs/curses_renderer_v5.py`),
mirroring v4 where `now.msg_curse` is bottom-aligned in the left column
(`self.align = 'bottom'`).

Two issues with that placement:

1. The date is a header-class piece of information (like `system`, `ip`,
   `uptime`), not a per-subsystem metric. It belongs in the top banner.
2. Sitting in the left sidebar, it competes for vertical space with real
   metrics (`fs`, `sensors`, `network`…) that are far more valuable.

Goal: paint `now` at the **far right of the header banner**, and make it the
**least prioritary** header block when the terminal is too narrow.

## 2. Current state

`glances/outputs/curses_renderer_v5.py`:

```python
HEADER_SLOT: tuple[str, ...] = ("system", "ip", "uptime")
LEFT_SLOT: tuple[str, ...] = (..., "sensors", "now")
```

`glances/outputs/glances_curses_v5.py::_paint_header` lays the header out as:

- first block flush-left at `x = 0`
- middle blocks packed left-to-right after the first, separated by
  `_HEADER_GAP = 3`
- **last** block flush-right (`right_x = max(x + 1, max_x - last.width)`)

Narrow-terminal degradation is driven by `_HEADER_DEGRADE_STEPS`, applied
cumulatively by `_fit_header` until `_header_fits(frame, max_x)` holds:

```python
_HEADER_DEGRADE_STEPS = [
    ("hide_os_info", True),   # (1) drop the system OS-info string
    ("hide_ip", True),        # (2) hide the ip block
    ("hide_uptime", True),    # (3) hide the uptime block (last resort)
]
```

`glances/plugins/now/render_curses_v5.py` renders one row: the `custom` date
string padded to 23 chars (`_NOW_PAD = 23`, v4's process-list padding).

## 3. Design

### 3.1 Header slot split into two alignment groups

The header slot becomes two explicit groups. The renderer stays the single
source of truth for slot membership and order; the painter only consumes it.

```python
HEADER_SLOT_LEFT:  tuple[str, ...] = ("system", "ip")
HEADER_SLOT_RIGHT: tuple[str, ...] = ("uptime", "now")   # painted right-aligned
HEADER_SLOT = HEADER_SLOT_LEFT + HEADER_SLOT_RIGHT
```

`"now"` is removed from `LEFT_SLOT`, so `slot_for("now") == "header"`.

Resulting banner on a wide terminal:

```
hostname (Ubuntu 24.04 64bit)   IP 192.168.1.10/24      Uptime: 3 days, 2:15:00  2026-07-25 11:30:00
└──────────── left-packed group ──────────────────┘      └────── right-aligned group ─────────────┘
```

`uptime` keeps its v4-equivalent position hugging the right edge; `now` is the
last block, flush with the right edge.

### 3.2 Degradation flag

`build_frame` gains one filter, next to the existing `hide_ip` / `hide_uptime`
ones:

```python
if view and view.get("hide_now") and plugin_name == "now":
    continue
```

### 3.3 Painter — right-aligned tail group

`_paint_header` generalises "last block flush-right" into "the blocks
belonging to `HEADER_SLOT_RIGHT` are right-aligned as one group":

1. Partition the received blocks into a left group and a right group by
   membership in `HEADER_SLOT_RIGHT`, preserving frame order.
2. Paint the left group packed from `x = 0`, each block separated by
   `_HEADER_GAP`; stop if it runs past `max_x` (existing behaviour).
3. Compute the right group's total width
   (`sum(widths) + (n - 1) * _HEADER_GAP`) and its start
   `right_x = max(left_end + 1, max_x - group_width)` — the existing
   never-overlap guard, applied to the group instead of a single block.
4. Paint the right group left-to-right from `right_x`, separated by
   `_HEADER_GAP`.
5. Return the tallest painted block's height (unchanged, normally 1).

**Backwards compatibility**: with 1 or 2 blocks (`system`, `uptime`) or 3
blocks (`system`, `ip`, `uptime`), the output is byte-for-byte identical to the
current painter, because `uptime` alone forms the right group and a
single-element group's `right_x` reduces to `max_x - last.width`. The existing
regression guards (`test_paint_header_two_blocks_unchanged`,
`test_paint_header_packs_middle_block_between_first_and_last`) therefore stay
valid unmodified.

`_header_fits` is unchanged: `sum(widths) + (len(widths) - 1) * _HEADER_GAP`
is exactly the minimum requirement whether the blocks are packed left,
right-aligned, or split between the two groups.

### 3.4 Display priority on narrow terminals

`now` is the least prioritary header block — dropped first:

```python
_HEADER_DEGRADE_STEPS = [
    ("hide_now", True),       # (1) drop the current date — least priority
    ("hide_os_info", True),   # (2) drop the system OS-info string
    ("hide_ip", True),        # (3) hide the ip block
    ("hide_uptime", True),    # (4) hide the uptime block (last resort)
]
```

Consequence: as soon as the terminal is too narrow for the four blocks, the
banner degrades to exactly today's `system … ip … uptime` layout. Constrained
terminals see **no** regression from this change.

### 3.5 `now` renderer — drop the fixed padding

`_NOW_PAD = 23` existed to align the left-sidebar one-liner with the process
list (v4 parity). Out of the sidebar it is harmful: trailing spaces in a
right-aligned block push the visible date away from the right edge and inflate
the width measured by `_header_fits`.

```python
def render(payload, fields_desc):
    custom = payload.get("custom") if payload else None
    if not custom:
        return []
    return [Row(cells=[Cell(text=str(custom))])]
```

The empty-payload contract (no rows) is unchanged. The `iso` field remains
REST-only. Module docstring updated: header block, far right.

## 4. Files touched

| File | Change |
|---|---|
| `glances/outputs/curses_renderer_v5.py` | `HEADER_SLOT_LEFT` / `HEADER_SLOT_RIGHT` / `HEADER_SLOT`; `"now"` removed from `LEFT_SLOT`; `hide_now` filter in `build_frame`; docstrings |
| `glances/outputs/glances_curses_v5.py` | `_paint_header` right-aligned tail group; `hide_now` first in `_HEADER_DEGRADE_STEPS`; docstrings |
| `glances/plugins/now/render_curses_v5.py` | drop `_NOW_PAD`; docstring |
| `tests/test_curses_renderer_v5.py` | slot routing + `hide_now` filter tests |
| `tests/test_curses_v5.py` | 4-block painter test + degrade-order test |
| `tests/test_plugin_now_render_curses_v5.py` | no-padding assertion, test renamed |

Not touched: collection/scheduling, REST API, MCP, Web UI, config keys,
`NEWS.rst` (release-time only).

## 5. Test plan

New / updated tests:

1. `slot_for("now") == "header"` and `"now" not in LEFT_SLOT`.
2. `HEADER_SLOT == HEADER_SLOT_LEFT + HEADER_SLOT_RIGHT` (guards against the
   two group tuples drifting from the flat one).
3. `build_frame(..., view={"hide_now": True})` produces no `now` block in
   `frame.header`.
4. Painter, four blocks (`system`, `ip`, `uptime`, `now`) at `max_x = 120`:
   - `system` at `x = 0`;
   - `ip` packed strictly between `system.width` and the right group;
   - `now`'s right edge is exactly `max_x` (`x == max_x - now.width`);
   - `uptime` painted at `now_x - _HEADER_GAP - uptime.width`, strictly right
     of the `ip` block.
5. Painter, narrow terminal: the right group never overlaps the left group
   (the `max(left_end + 1, …)` guard holds).
6. `_fit_header` on a terminal too narrow for four blocks hides `now` first —
   `uptime`, `ip` and the OS info are still present in the resulting frame.
7. `now` renderer returns the raw `custom` string with no trailing padding;
   empty payload still yields no rows.

Existing suites must stay green, in particular the two header painter
regression guards and the full `tests/` suite
(`python -m pytest tests/ -q`).

Manual smoke check: `glances` (v5 TUI) on a wide terminal → date at the far
right of the banner, nothing left in the sidebar where it used to be; shrink
the terminal progressively → the date disappears first, then the OS info,
then the IP, then the uptime.

## 6. v4 divergence to log

In v4, `now` is the bottom block of the left sidebar (`align = 'bottom'` in
`glances/plugins/now/__init__.py`). Moving it to the header banner is a
**deliberate, approved v4 divergence**. It joins the divergence list kept for
the v5 release changelog. No user-visible configuration changes, so nothing to
document in `docs/`.

## 7. Non-goals

- No `[outputs]`-configurable slot lists (the "configurable later" note in
  `curses_renderer_v5.py` stays a later item).
- No change to the `now` plugin model, its `strftime_format` config key, or
  its REST payload.
- No change to the left sidebar layout beyond `now`'s removal.
