# Glances v5 TUI — process management (Phase 2.X-b)

**Date:** 2026-09-23
**Branch:** `develop-v5`, on top of `4177990` (WebUI connection-lost overlay)
**Group:** Phase 2.X — TUI interactive surface
(`docs/architecture/glances-v5-architecture-decisions.md` §10)
**Follows:** 2.X-a (`…-tui-show-hide-toggles-design.md`), which deferred `e`
to this chantier, and 2.X-c (the data-type toggles).

---

## 1. Scope

The half of v4's interactive surface that acts on **a process the user has
selected**, plus the two things that surface needs and v5 has neither of: a
selection cursor, and modal popups.

§10 lists the group as one line:

> **Process management**: selection cursor (`UP`/`DOWN`), `k` kill, `+`/`-`
> nice, `ENTER`/`E` filter, `e` extended stats, `M` min/max reset.

That line is six features with three different prerequisites, and one of them
(`M`) turns out not to work at all without another (`ENTER`) — §3.6. This spec
designs the whole group and **splits it into four shippable chantiers** (§7),
because shipping it as one commit would mean a destructive action landing in
the same push as its own scaffolding.

**TUI only.** The WebUI is out of scope and §8.1 records why that is a
maintainer decision rather than an omission.

---

## 2. What v5 has today

| Piece | State | Proof |
|---|---|---|
| Hotkey table | `_HOTKEYS` keyed by **character** — `chr(key)` (`glances_curses_v5.py:178`, dispatch `:360`) | An arrow key has no character. §5.1. |
| Help overlay | generated from `_HOTKEYS` (`:1289`), so a bound key cannot go undocumented | Holds only if non-character keys join the same table. §5.1. |
| `_handle_key` | **pure — no curses I/O**, stated at `:360` and relied on by every unit test | A popup is curses I/O. §5.4. |
| View state | `ViewState` (`:109`) — booleans, a set, one tri-state | No cursor field. |
| Process order | re-sorted per cycle on a snapshot copy, `_apply_live_sort` (`:878`) | The index the cursor addresses is rebuilt every frame. §5.2. |
| Row budget | the vertical-fit pass decides how many process rows are drawn (`_PREFIT_ROW_BUDGET`, `:925`) | The bound the cursor must respect. §5.3. |
| Engine wiring | `glances_processes.set_args()` (`processes.py:157`) is **never called** by `main_v5.py` | Confirmed by grep: the only v5 engine calls are `set_sort_key` (`main_v5.py:478`) and the alerts hand-off (`:674`). §5.5. |
| Popups | none, of any kind | v4: `display_popup` (`glances_curses.py:1003`), three types. §5.4. |
| Process filter | nothing. No `-f`, no `--process-filter`, no filter UI | `processlist/model_v5.py` says so in its own docstring. |

The engine already carries every *action* this group needs — `kill`
(`processes.py:780`), `nice_increase` (`:769`), `nice_decrease` (`:758`),
`process_filter` setter (`:287`), `enable_extended` / `disable_extended`
(`:204`, `:209`). **Nothing in this group needs new collection code.** What is
missing is entirely on the TUI side: a cursor, a way to ask the user, and a
way to draw the answer.

---

## 3. The six features, read against v4's code

### 3.1 The cursor — `UP` / `DOWN`

v4: `_handle_cursor_up` / `_handle_cursor_down` (`glances_curses.py:414-420`)
move `args.cursor_position`, clamped at 0 and at
`glances_processes.processes_count`. Bound in the non-character dict
(`:289-290`), which also accepts the raw ANSI codes `65` / `66`.

The selected row is decorated `PROCESS_SELECTED` on the **command cells only**
(`processlist/__init__.py:553`) — which is `OK | A_UNDERLINE`
(`glances_colors.py:154`). Not a reverse-video bar: an underlined green
command.

`--disable-cursor` (`main.py:336-342`) turns the whole thing off, and every
cursor-dependent key is guarded by it in the dispatch dict (`:279-290`).

### 3.2 `k` — kill

v4: `_handle_kill_process` (`:371`) only sets a flag; the work happens in
`display()` (`:646-650`) → `kill()` (`:668`), which resolves
`get_raw()[cursor_position]`, shows a yes/no popup naming the process, and on
confirmation calls `glances_processes.kill(pid)` per pid.

Two details worth carrying over and one worth fixing:

- It kills the `childrens` list when the item has one (`:676-679`), not just
  the single pid — a program-view row is a set of pids.
- It is refused outside standalone mode (`:648`).
- **The fix:** v4 resolves the pid by index, shows the popup, and the pid it
  kills is the one captured before the popup. That is already correct. v5 must
  not regress it into a re-resolve after confirmation — between the two the
  list may have re-sorted under a different process. §5.6.

`glances_processes.kill` guards self-murder with a bare `assert`
(`processes.py:782`), which `python -O` strips. v5 checks before calling.

### 3.3 `+` / `-` — nice

v4: same deferred-flag shape (`:365-369`), consumed at `:637-642`, calling
`glances_processes.nice_increase/decrease(pid)`. No confirmation.

Both engine methods build `psutil.Process(pid)` **outside** their `try`
(`processes.py:762`, `:773`), so a process that exited between the paint and
the keypress raises `NoSuchProcess` out of the engine. v4 does not catch it.
v5 will — §5.6.

### 3.4 `ENTER` / `E` — the process filter

v4: `ENTER` is a **character** entry (`'\n'`, `glances_curses.py:42`) that
raises `edit_filter`; the input popup is drawn in `display()` (`:617-631`) with
a six-line example block, seeded from `process_filter_input`, and its result is
assigned to `glances_processes.process_filter`. `E` erases it (`:358-359`).
Standalone-only (`:631-632`).

This is the one feature of the group that mutates **engine-global** state:
`_filter.filter` changes what `get_list()` returns for *every* consumer — the
REST API and the WebUI included. §8.1.

### 3.5 `e` — extended stats

v4: `_handle_process_extended` (`:350-356`) flips `enable_process_extended`,
calls `glances_processes.enable_extended()` / `disable_extended()`, and — the
part that is easy to miss — **sets `disable_cursor = enable_process_extended`
in standalone mode**. Turning extended stats on *freezes the cursor*, so the
selected process cannot change under the extended block.

The engine picks its subject in `is_selected_extended_process`
(`processes.py:474`): it reads `args.programs`, `args.enable_process_extended`,
`args.cursor_position` and `args.disable_cursor` off `self.args`. With
`self.args` unset — v5 today — `hasattr` fails on the first test and the
function is a constant `False`. **`e` is inert in v5 not by accident but by
absence of `set_args`.** §5.5.

The display side is `_msg_curse_extended_process`
(`processlist/__init__.py:659`), ~130 lines: cpu/mem min/max/mean, affinity,
ionice, context switches, fds, swap, tcp/udp counts.

### 3.6 `M` — reset min/max, and why it is not a standalone feature

`M` is a plain `switch` on `reset_minmax_tag` (`glances_curses.py:76`). The
only consumer is `processlist/__init__.py:649` — and it sits **inside**
`if glances_processes.process_filter is not None:` (`:648`).

So `M` resets the min/max of the **filtered-processes summary**, and that
summary (`_msg_curse_sum`, three rows: current / min / max) is only drawn when
a filter is active. With no filter set, `M` in v4 does nothing at all.

**Consequence for the split: `M` cannot ship before `ENTER`.** It is not a
sixth peer feature; it is a sub-feature of the filter, and it drags in
`_msg_curse_sum` + `_mmm_reset`, a summary block v5's processlist has no
equivalent of. §7.

---

## 4. What the group is really made of

Stripped of the roadmap's phrasing, there are **two pieces of new machinery**
and **four features** that consume them:

```
  machinery            feature
  ---------            -------
  cursor ────────────► k (kill)          ─┐ needs yes/no popup
         ────────────► +/- (nice)         │ needs nothing else
         ────────────► e (extended)       │ needs a render block + set_args
  popups ────────────► ENTER/E (filter)  ─┘ needs input popup + summary + M
```

The cursor is the load-bearing piece: three of the four features are
meaningless without it. The popups are load-bearing for two.

---

## 5. Design

### 5.1 D1 — a second, keycode-addressed hotkey table

`_HOTKEYS` is keyed by `chr(key)`. `UP` is `curses.KEY_UP` (259) — `chr(259)`
is a real character (`ă`), so an entry would technically *dispatch*, but the
help overlay would print `ă` as the key label and the table would be lying
about what it binds.

Add `_SPECIAL_HOTKEYS: dict[int, dict[str, Any]]`, keyed by the curses keycode,
carrying the same `group` / `desc` shape plus a `label` (`"↑"`, `"↓"`,
`"ENTER"`). `_handle_key` consults it **before** the `chr()` conversion;
`_help_lines` iterates both tables.

Why a second table rather than a `label` field on the existing one: the
existing table's key *is* the character to press, and every consumer relies on
that — including `hotkeys.js` and its drift test
(`tests/test_webui_v5_hotkeys_drift.py`), which iterates `_HOTKEYS` and expects
each key to be a pressable character. A keycode entry in the same dict would
have to be filtered out at four call sites. Two tables, one help generator.

`ENTER` is the exception that proves it: v4 binds it as the character `'\n'`
and so can v5 — `chr(10)` is well-defined. It still goes in
`_SPECIAL_HOTKEYS`, keyed by `10`, because its *label* must read "ENTER" and
not a line break. `curses.KEY_ENTER` (343) is accepted as an alias.

**The invariant this preserves:** a bound key is documented by construction.
That property is what made the 2.X-a and 2.X-c help screens trustworthy, and
it is the property the WebUI drift test leans on.

### 5.2 D2 — the cursor is an index into the *displayed* order, and that is a choice

`_apply_live_sort` (`:878`) re-sorts a snapshot copy every cycle. So "position
3" addresses a different process from one frame to the next whenever the sort
is volatile (`cpu_percent`, the default).

Three options were weighed:

1. **Index into the displayed order** (v4's behaviour). The cursor stays where
   it is on screen and the process under it changes.
2. **Pin to a pid.** The cursor follows the process as it moves in the list.
3. **Freeze the sort while the cursor is off row 0.**

**Chosen: (1).** Not because it is best in the abstract — (2) is arguably
kinder — but because it is what v4 does, this is a parity chantier, and (2)
changes the felt behaviour of `UP`/`DOWN` in a way a v4 user would report as a
bug. (3) is worse: it makes the whole display freeze as a side effect of a
navigation key.

The hazard (1) carries is real and is confined to exactly one place: `k`. §5.6
closes it there rather than by changing what the cursor means.

### 5.3 D3 — the cursor is clamped to what is drawn, not to the process count

v4 clamps at `glances_processes.processes_count` (`glances_curses.py:419`),
which is `min(_max_processes - 2, total - 1)` (`processes.py:247-254`).
`_max_processes` is set by v4's display class; **v5 never sets it, so the
property returns 0** (its own defensive guard, `:252`). v4's bound is not
available to v5, and reusing it would pin the cursor to row 0 forever.

v5 clamps at **the number of process rows the last frame actually drew**. The
TUI records it after `_build_fitted_frame`; the renderer is the authority
because only it knows what the vertical-fit pass left room for.

This is a divergence in route with a better property than v4's: **the selected
process is always on screen.** A cursor that can run past the visible window
would let `k` open a confirmation popup for a process the user cannot see —
which is the one thing a destructive action must never do. v4's bound happens
to achieve the same thing (`_max_processes` *is* the screen height); v5 reaches
it by asking the renderer instead of by a second copy of the geometry.

No scrolling. If the user wants a process that is below the fold, they sort for
it — same as v4.

### 5.4 D4 — popups run in the loop, `_handle_key` stays pure

`_handle_key` is documented pure (`:360`) and ~40 unit tests call it with no
terminal. A popup is `curses.newwin` + a blocking input loop.

v4 solved this by accident-of-architecture: the handler sets a flag
(`self.kill_process = True`) and `display()` does the I/O. v5 adopts the same
separation deliberately:

- `_handle_key` sets `self._pending: PendingAction | None` and returns a new
  result kind, `"modal"`.
- `_loop` (`:491`) sees `"modal"`, calls `self._run_pending(stdscr)`, and
  repaints unconditionally afterwards.

`"modal"` is a fifth result kind next to `quit` / `changed` / `repaint` /
`ignored`, and it is what keeps every popup out of the pure function. The
existing tests keep passing unchanged; the new ones assert on `self._pending`.

A popup blocks the TUI thread. The collector runs in its own thread and keeps
publishing to the store, so nothing stalls behind the popup — the frame painted
after it closes is simply the current one. This is strictly better than v4,
which is single-threaded and stops collecting while a popup is open.

### 5.5 D5 — `set_args` is not called; `e` gets an explicit subject instead

The tempting shortcut for `e` is `glances_processes.set_args(args)` in
`main_v5.py`, making `is_selected_extended_process` work as it does in v4.

Rejected. `set_args` (`processes.py:157-163`) also applies `process_focus`, and
it binds the engine to an argparse namespace that v5's engine has deliberately
never depended on — `main_v5.py` talks to it through two named calls and
nothing else. Handing it the whole namespace to get one integer through would
couple the shared engine to the TUI's arg shape for every future reader.

Instead the TUI sets exactly what it means:
`glances_processes.extended_pid = <pid>` — a pid, not a position. A pid is
stable across the re-sort that §5.2 leaves volatile, which is the property this
feature actually needs: the extended block must not describe a different
process each cycle.

That is a small addition to the shared engine (a field plus a branch in
`set_extended_stats`'s caller), and it is additive: v4's position-based path is
untouched, and `extended_pid` defaults to `None`.

`enable_extended()` (`:204`) calls `self.update()` synchronously — from the TUI
thread that would run a full process collection concurrently with the
collector's own. v5 sets `disable_extended_tag = False` directly and lets the
next cycle pick it up: one refresh interval of latency, no race.

**`e` freezes the cursor, as in v4** (§3.5). Without that, the extended block
describes whatever the cursor last landed on while the user is still moving it.

### 5.6 D6 — every mutation names its target before it acts

The rule for `k`, `+` and `-`:

1. Resolve the pid **from the frame the user is looking at**, at keypress time.
2. For `k`, display that pid and name in the confirmation.
3. Act on the **captured pid**. Never re-resolve by index afterwards.
4. Guard: `NoSuchProcess` (it exited between paint and press), `AccessDenied`
   (not ours to touch), and `pid == os.getpid()` (checked in v5 rather than
   trusting the engine's `assert`, which `-O` removes).

A failure is reported in an info popup, not swallowed into the log where a TUI
user will never see it. v4 logs and says nothing on screen
(`processes.py:767`, `:778`) — a user pressing `+` on someone else's process
sees precisely nothing happen and has no way to know why.

`p.wait(timeout=3)` inside `kill` (`processes.py:786`) blocks the TUI thread
for up to three seconds on a process that ignores SIGKILL. Accepted, as v4 does
— but the confirmation popup stays on screen while it blocks, so the UI is not
mysteriously frozen.

### 5.7 D7 — ESC is ambiguous, and binding the arrows is what made that matter

**Found in the live smoke test, not in the design.** Under a pty announcing
`xterm-256color`, pressing Down delivered `27, 91, 66` to `_handle_key` — three
separate keys. ncurses had not assembled the sequence, and 27 is `"quit"`
(`glances_curses_v5.py:488`), so **the first arrow key exited Glances.**

Why ncurses hands it back: `keypad(True)` translates the escape sequence its
terminfo entry lists. `xterm`'s `kcud1` is `\x1bOB` (APPLICATION cursor mode,
which ncurses itself switches on via `smkx` — the `\x1b[?1h\x1b=` visible in
the very first bytes the TUI writes). A terminal or multiplexer sending the
NORMAL-mode `\x1b[B` instead gets no translation, and the bytes arrive raw.

This was never only about arrows. A mouse report, a bracketed paste, an
Alt-combination and an unmapped function key are all ESC-prefixed, and every
one of them quit Glances. The defect predates this chantier; binding the arrows
is what turns it from a curiosity into the first thing a user hits.

`_read_key` resolves it in the loop, before dispatch, so `_handle_key` stays
pure: on a 27, one **non-blocking** peek. Nothing behind it → a real Esc →
quit. Something behind it → resolve `[A`/`OA`/`[B`/`OB` to `KEY_UP`/`KEY_DOWN`,
and swallow any other tail rather than quitting or dispatching its bytes as
separate keystrokes (`O` and `B` are both bound hotkeys). The peek costs a real
Esc nothing, and the tail is bounded so a terminal emitting garbage cannot hold
the loop.

### 5.8 D8 — the selected row is decorated, not inverted

v4 underlines the command cells in the OK colour (§3.1). `Cell` already carries
`underline` (`curses_renderer_v5.py:145-155`), added for the sort-column header.
The processlist renderer marks the selected row's command cells
`color=OK, underline=True` — byte-for-byte v4's decoration, no new Cell field,
no new ColorRole.

The renderer learns which row through `view["cursor_position"]`, published by
`_build_view` (`:933`) exactly as `sort_key` and `process_short_name` already
are. Absent from `view` (export, tests, `--disable-cursor`) → no row is marked,
which is the existing behaviour byte-for-byte.

---

## 6. Divergences from v4, recorded

| # | v4 | v5 | Why |
|---|---|---|---|
| 1 | Cursor bound by `processes_count` | bound by rows actually drawn | v4's bound reads 0 in v5 (§5.3); the v5 bound guarantees the target is visible |
| 2 | `e` subject chosen by **position** | chosen by **pid** | survives the per-cycle re-sort (§5.5) |
| 3 | `enable_extended()` collects synchronously | sets the tag, next cycle collects | no concurrent collection from the TUI thread (§5.5) |
| 4 | nice/kill failures logged only | reported in a popup | a TUI user cannot read the log (§5.6) |
| 5 | popup stops collection | collection continues | v5's collector is a separate thread (§5.4) |
| 6 | `k` refused when `cs_status is not None` (client mode) | refused when not standalone | v5 has no client mode yet; same guard, current spelling |
| 7 | `k`/`+`/`-` in program view act on the **process** list's row of the same index | refused in program view | v4 acts on a row other than the one displayed (§8.3); v5's `programlist` carries no pid |
| 8 | an untranslated escape sequence reaches the dispatcher byte by byte | resolved (or swallowed) before dispatch | 27 means quit, so an arrow key exited Glances (§5.7) |

---

## 7. The split

Four chantiers, each independently shippable and smoke-testable.
**b1 and b2 shipped 2026-09-23**; b3 and b4 remain.

**b1 — the cursor.** `_SPECIAL_HOTKEYS`, `ViewState.cursor_position`,
`--disable-cursor`, the clamp, the decoration, `view["cursor_position"]`.
Read-only: nothing can be mutated by any key it adds. Prerequisite for b2 and
b4.

**b2 — acting on the selection.** The popup machinery (info + yes/no), `k`,
`+`, `-`. Destructive, and the reason the popup machinery is worth building.

**b3 — extended stats (`e`).** `extended_pid` on the engine, the cursor
freeze, and the extended render block. Read-only, but the render block is the
largest single piece of new rendering in the group.

**b4 — the filter.** `ENTER` (input popup), `E`, `-f/--process-filter` CLI
wiring, the filtered summary block (`_msg_curse_sum` equivalent), and `M` which
resets it (§3.6). The only piece that mutates engine-global state, and the only
one whose effect is visible to the REST API and the WebUI.

b1+b2 ship together: a cursor with nothing to do is not smoke-testable, and the
popup machinery b2 builds is the honest cost of the first destructive key.
b3 and b4 follow, in that order — b4 last because it is the largest and the
only one with a cross-surface consequence to decide first (§8.1).

---

## 8. Open questions for the maintainer

### 8.1 Does any of this reach the WebUI? — **needs a decision before b4**

2.X-a and 2.X-c both ended up in the browser, by explicit reversal of the
TUI-only default. This group is not the same shape:

- **Cursor, `e`** — per-viewer, harmless. Could be browser-side with no server
  round-trip for the cursor; `e` would need an endpoint.
- **`k`, `+`, `-`** — destructive, and would require a mutating REST endpoint
  on an API that **Glances leaves unauthenticated by default** (CLAUDE.md, and
  `…decisions.md` records it as intentional). "Kill any process on the host"
  reachable by an unauthenticated POST is a different product decision from
  "show fewer plugins". My recommendation is **no**, or at minimum gated behind
  `--password`.
- **`ENTER`/`E`** — not destructive, but **engine-global**: a filter typed in
  one browser tab changes what the TUI and every other consumer sees (§3.4).
  Unlike the hidden-plugin sets, this cannot be per-viewer without giving the
  filter a per-request life the engine does not have.

Nothing in b1–b3 is blocked on this. b4 is.

### 8.2 `--disable-cursor` default

v4 defaults the cursor **on** (`main.py:336-342`, `store_true` on
`disable_cursor`). Keeping that. Flagging it only because it means `UP`/`DOWN`
change behaviour for every existing v5 user the moment b1 lands — they
currently do nothing outside the help overlay.

### 8.3 `k` on a program row — **resolved while writing this spec, and it is a v4 bug**

The question was whether v5's `programlist` payload carries `childrens` (§3.2).
It does not: its schema (`programlist/model_v5.py:61-134`) is keyed on `name`
and **has no `pid` field at all**, by design — a program is an aggregate.

Checking what v4 does with that turned up something worse. v4's mutating keys
read the pid from `stats.get_plugin('processlist')` unconditionally
(`glances_curses.py:638`, `:641`, `:647`) — **the `processlist` plugin, never
`programlist`, even while the program view is on screen.** So in v4, pressing
`+` on the third row of the *program* list adjusts the nice value of whatever
sits third in the *process* list. The row acted on is not the row shown. (`k`
survives it only because `programs.py:27` happens to give program items a
`childrens` list, so its own `'childrens' in process` branch catches the
program case first — the nice keys have no such branch.)

v5 does not reproduce this. **In program view, `k`, `+` and `-` are refused**
with an info popup naming the reason. The cursor itself still moves and still
decorates — it costs nothing and `j` back to the process view acts where the
user is looking. Divergence #7.

---

## 9. Test strategy

Per chantier, and each new guard gets a mutation check — the 2.X-a and 2.X-c
discipline.

- **Pure dispatch** (`_handle_key`): every new key, in both tables, including
  the clamp at both ends, `--disable-cursor` making every cursor key
  `"ignored"`, and the `"modal"` result kind setting `_pending`.
- **Help overlay**: the generated rows cover `_HOTKEYS ∪ _SPECIAL_HOTKEYS` —
  the same "no bound key is undocumented" assertion 2.X-a introduced, extended
  to the second table.
- **Renderer**: the selected row carries the decoration; no `cursor_position`
  in `view` leaves output byte-identical (the existing snapshot tests are the
  guard).
- **Clamp against the drawn count**: a short terminal must not let the cursor
  leave the visible window — a frame-level test, not a `_handle_key` one.
- **Mutations** (b2): the pid is captured before the popup and not re-resolved
  after it; a refusal path for each of `NoSuchProcess`, `AccessDenied`, own
  pid. Engine calls are patched — no test kills anything.
- **Headless frame check** for the decoration, as 2.X-a established after pyte
  proved unreliable on ncurses' optimised diff.
- **Live smoke test** in a real terminal for each chantier, since every feature
  here is an interaction.

---

## 10. Out of scope

The WebUI (§8.1). `F5`/`Ctrl-R` and the sort arrow keys — §10's own separate
bullet. `LEFT`/`RIGHT` command-column scrolling
(`args.cursor_process_name_position`, `glances_curses.py:375-379`): cursor-
adjacent but a display concern, and it belongs with the arrow-key bullet.
`--process-focus`. `g` (graph export), `w`/`x` (clean logs) — MISCELLANEOUS
rows no group owns yet. Fixing Part 3 of the parity inventory.
