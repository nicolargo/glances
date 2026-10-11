# Glances v5 TUI — cursor + acting on the selection (2.X-b1 + b2) — Implementation

**Design:** `docs/superpowers/specs/2026-09-23-glances-v5-tui-process-management-design.md`
**Branch:** `develop-v5`, on top of `4177990`
**Scope:** chantiers b1 and b2 of the four the design splits 2.X-b into (§7).
b3 (`e`) and b4 (the filter, and `M` inside it) are NOT in this plan.

---

## Why b1 and b2 ship together

A cursor that can select but not act is not smoke-testable — the maintainer
would be asked to verify an underline. And the popup machinery b2 needs is the
honest cost of the first destructive key, not of the cursor. Shipping them
apart would mean one commit of scaffolding and one of consequence; together
they are one reviewable feature: *select a process, do something to it.*

---

## Steps

### 1. `_SPECIAL_HOTKEYS` — a keycode-addressed table (design §5.1)

`glances_curses_v5.py`. A second dict keyed by curses keycode, same
`group`/`desc` shape plus `label`. Entries: `KEY_UP`/`65`, `KEY_DOWN`/`66`.
`_handle_key` consults it before `chr()`; `_help_lines` iterates both.

→ **verify:** `_handle_key(curses.KEY_UP)` dispatches; the help overlay lists
`↑` and `↓`; the existing `_HOTKEYS` drift test still passes untouched.

### 2. `ViewState.cursor_position` + the clamp (design §5.2, §5.3)

- `cursor_position: int = 0` on `ViewState`.
- `TuiV5._cursor_max: int` recorded in `_repaint` from the painted frame —
  the processlist block's row count minus its header row.
- `UP` floors at 0; `DOWN` ceilings at `_cursor_max - 1`.
- `--disable-cursor` (new CLI flag + constructor kwarg) makes every cursor key
  return `"ignored"` and suppresses the decoration.

→ **verify:** clamp at both ends; a short terminal cannot push the cursor
below the fold (frame-level test, not `_handle_key`); `--disable-cursor`
neutralises the keys.

### 3. The decoration (design §5.7)

`processlist/render_curses_v5.py`: `view["cursor_position"]` marks that item
row's command cells `color=OK, underline=True`. Absent key → output unchanged.
`_build_view` publishes it, and only when the cursor is enabled.

→ **verify:** the marked row is the one asked for; no key in `view` leaves
every existing snapshot byte-identical; mutation check on the index.

### 4. Popups (design §5.4)

`_popup_info(stdscr, message)` and `_popup_yesno(stdscr, message) -> bool`.
Centred bordered window, sized to the message, refusing to draw when the
terminal is smaller than the popup (v4's guard, `glances_curses.py:1041-1043`).
Info dismisses on any key or after a timeout — v4 naps for the full duration
and ignores `stop()`.

`_handle_key` stays pure: it sets `self._pending` and returns the new result
kind `"modal"`; `_loop` runs `_run_pending(stdscr)` and repaints.

→ **verify:** `_handle_key` sets `_pending` and performs no curses call (the
existing terminal-free tests are the guard); `"modal"` is handled in `_loop`.

### 5. `k`, `+`, `-` (design §5.6, §8.3)

`_SPECIAL_HOTKEYS` gains nothing here — all three are characters, so they are
plain `_HOTKEYS` entries with a new action verb each.

Resolution order, identical for the three: program view → refuse (§8.3); not
standalone → refuse; no process under the cursor → refuse; own pid → refuse.
Then capture the pid **once**, and for `k` confirm naming it before acting on
the captured value.

Guards around the engine call: `NoSuchProcess`, `AccessDenied`, and a catch-all
— each reported in an info popup rather than only in the log (§5.6 divergence
#4).

→ **verify:** the pid is captured before the popup and not re-resolved after
it (the mutation test that matters); one refusal test per guard; engine calls
patched — no test kills anything.

### 6. CLI + help

`--disable-cursor` in `main_v5.py`, forwarded to `TuiV5`.

`docs/cmds.rst` needs **no change**: its Interactive Commands list already
documents `k`, `+`, `-`, `UP` and `DOWN` — it describes v4's key set, and this
chantier is v5 catching up to it. Checked rather than assumed
(`docs/cmds.rst:239-440`).

### 6b. The live smoke test found a defect the design had not predicted

Pressing Down quit Glances: ncurses handed the escape sequence back
unassembled and 27 means quit. `_read_key` resolves it in the loop. Design
§5.7 records the mechanism; it is why this plan grew a step it did not start
with.

### 7. Architecture record

`…decisions.md` §10: the Phase 2.X process-management bullet gains what
shipped, the four-way split, and the two v4 bugs this chantier found (§8.3 and
the `M`/filter coupling of design §3.6).

---

## Out of this plan

`e` (b3), `ENTER`/`E`/`M` (b4), the WebUI (design §8.1), `F5`/`Ctrl-R`, the
sort arrow keys, `LEFT`/`RIGHT` command scrolling.
