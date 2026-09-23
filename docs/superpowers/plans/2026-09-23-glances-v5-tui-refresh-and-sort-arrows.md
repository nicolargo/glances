# Glances v5 TUI — forced refresh and the arrow keys (Phase 2.X, last bullet)

**Branch:** `develop-v5`, on top of `bc542ef`
**Closes** §10's last open Phase 2.X line: "**`F5` / `Ctrl-R`** forced refresh
and the sort-navigation arrow keys."

---

## The four keys, read from v4

| v4 | Action | Source |
|---|---|---|
| `F5`, `Ctrl-R` (18) | `glances_processes.reset_internal_cache()` | `glances_curses.py:432-433` |
| SHIFT-LEFT / SHIFT-RIGHT | step the sort key through `sort_processes_stats_list` | `:406-412` |
| LEFT / RIGHT | scroll the command column's ARGUMENTS | `:374-379`, consumed `processlist/__init__.py:566-567` |
| `--arrow-keys-sort` | **swaps the two pairs** (issue #3385) | `main.py:343-348`, dispatch `glances_curses.py:281-288` |

Two details worth carrying, both easy to miss:

- The scroll moves **only the arguments**. The executable name (and its path
  prefix in full mode) stays put, and a `…` replaces the leading space once
  the offset is non-zero. Scrolling the whole cell would push the name — the
  one part that identifies the row — off the left edge.
- v4 guards the scroll pair with `not disable_cursor` and the sort pair
  without. Mirrored: `--disable-cursor` reads "disable cursor (process
  selection) in the UI", and scrolling a column is part of navigating that
  list even if it is not selection.

---

## Steps

### 1. The swappable pair, resolved once

`--arrow-keys-sort` means the same keycode does different things in two
configurations, so a static table would make the `h` overlay wrong in one of
them — and "the overlay cannot drift from what the TUI does" is the property
2.X-a built and every chantier since has kept.

So the four arrow entries are **computed**, by one method both `_handle_key`
and `_help_lines` call. The help then describes the binding that is actually
live, by construction rather than by care.

### 2. `F5` / `Ctrl-R`

Two keycodes, one verb, one engine call. It stays silent: nothing visible
happens until the next collection cycle, and a popup on every refresh would
be worse than saying nothing. The key is documented in the overlay, which is
where a user looks for it.

### 3. The command scroll

`ViewState.command_offset`, published in `view`, consumed by
`_command_cells` — which `programlist` imports verbatim, so both blocks
behave the same. Floors at 0; no ceiling, because the longest argument string
on screen is not knowable before the frame is built and clamping to the
longest would make the key stop working on a row the user cannot see.

### 4. The sort loop

`sort_processes_stats_list` (`processes.py:33-34`), the same list v4 steps
through, already imported by `main_v5`. Stepping wraps, as v4's `%` does.

---

## Out of scope

The WebUI: none of these four is a v4 web feature either (its sort is a
click on a column header, which v5 already has through `--sort-processes` and
`/api/5/args`). `--process-focus`.


---

## What the pty found that the tests could not

`SHIFT+arrow` worked immediately; plain `LEFT`/`RIGHT` did nothing at all.

The escape resolver 2.X-b1 added knew `[A`/`OA`/`[B`/`OB` — Up and Down —
because those were the only arrows bound at the time. An untranslated
`\x1b[C` therefore fell through to "unknown sequence, swallow", and the
command column never moved. The shifted pair was fine because its terminfo
entry (`kRIT`/`kLFT`) translates before the resolver ever sees it.

Two fixes, not one: the four directions are in the table now, and a test
asserts that **every plain arrow the dispatcher binds is one the resolver can
produce**. The first fixes this instance; the second is what would have caught
it by construction.

Also measured rather than assumed: a real pty announcing `xterm-256color`
delivers 393 / 402 / 269 / 18 for Shift-Left, Shift-Right, F5 and Ctrl-R —
exactly the keycodes bound, with no escape-sequence trouble on any of them.
