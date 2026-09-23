# Glances v5 TUI — the process filter (2.X-b4) — Implementation

**Design:** `docs/superpowers/specs/2026-09-23-glances-v5-tui-process-management-design.md`
(§3.4, §3.6, §8.1)
**Branch:** `develop-v5`, on top of `b7413d8`
**Closes 2.X-b.**

---

## §8.1's last open question answers itself

Whether the filter reaches the browser was the one part of the design still
undecided, on the grounds that it is **engine-global**: a filter typed in one
tab would change what the TUI and every other consumer sees.

Two facts, both checked rather than argued:

1. **v4's web UI has no process filter.** Grepping its components for
   `process_filter` finds only `help.vue`, which documents the *terminal*
   key. So there is no parity to keep.
2. **v5's TUI and REST API are mutually exclusive.** `main_v5.assemble` is
   `if args.server: … elif not no_tui: …` — when the TUI runs there is no
   FastAPI app in the process at all. The leak the objection was about cannot
   happen.

So b4 is TUI-only, and not as a judgement call. Putting a filter in v5's
browser would be a **new feature**, not parity, and it would need the
per-viewer design the engine cannot give it today.

---

## Steps

### 1. A third popup: text input

`_popup_input(stdscr, message, value)`, beside `_popup_info` and
`_popup_yesno` from b2. Own loop rather than `curses.textpad.Textbox` (which
v4 wraps in `GlancesTextbox` to make Enter submit, `glances_curses.py:1426`):
Textbox has no cancel, and ESC must cancel — the alternative is a user who
opened the filter by accident having to clear it by hand.

### 2. `ENTER`, `E`

`ENTER` is `_SPECIAL_HOTKEYS[10]` (plus `curses.KEY_ENTER`) so the help
overlay prints "ENTER" and not a line break. Both are modal verbs, like
`k`/`+`/`-`: they reach the terminal.

**An invalid pattern is reported.** `GlancesFilter.filter`'s setter catches
the `re.compile` failure, sets `_filter = None` and logs
(`glances/filter.py:140-145`) — so in v4 a typo is a keypress that does
nothing at all, with no feedback anywhere the user is looking. v5 compares
what it set against what came back and says so.

### 3. `-f` / `--process-filter`

v4's own spelling (`main.py:513-519`). Applied in `assemble`, TUI mode only —
`glances_processes.process_filter` is the same property the key writes.

### 4. The filtered summary, and `M`

v4 draws three rows under the process table when a filter is on
(`processlist/__init__.py:909-1000`): current, min, max, aligned to the
process columns, with `('M' to reset)` on the last two. `M` resets the
accumulator (§3.6 — which is why `M` could not ship before this chantier: its
flag is read INSIDE `if process_filter is not None`).

v4 keeps the min/max **on the plugin instance** — a stateful renderer. v5's
renderers are pure, so the accumulator lives in the TUI (like `_cursor_max`)
and the sums arrive through `view`, computed once by a pure helper the
renderer exports.

**The rows cost budget**, like the `e` block: `plan_right_column`'s
`process_extra_rows` must count them too, or the body overflows by four.

---

## Out of scope

The WebUI (above). `--process-focus`, which is a different filter
(`_filter_focus`) with its own precedence. `F5`/`Ctrl-R` and the sort arrow
keys — §10's own separate bullet.
