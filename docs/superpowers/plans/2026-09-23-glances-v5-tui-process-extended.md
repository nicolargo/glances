# Glances v5 TUI — extended stats for the selected process (2.X-b3) — Implementation

**Design:** `docs/superpowers/specs/2026-09-23-glances-v5-tui-process-management-design.md`
(§3.5, §5.5)
**Branch:** `develop-v5`, on top of `3dbcfe0` (2.X-b1 + b2)
**Scope:** the `e` key. b4 (the filter, and `M` inside it) is not in this plan.
**Decided by the maintainer, 2026-09-23:** 2.X-b stays **TUI-only**. Design
§8.1 is closed — no WebUI for any of it, b4 included.

---

## Steps

### 1. The engine learns a PID, not a position (design §5.5)

`glances/processes.py`: `extended_pid` (None by default) plus one branch in
the update loop beside `is_selected_extended_process`. v4's position path is
untouched — `extended_pid` is None unless the v5 TUI set it.

A position is the wrong handle anyway: the list re-sorts every cycle, so the
extended block would describe a different process from one refresh to the next.

→ **verify:** the engine grabs extended stats for the pid it was given, and
does not when `extended_pid` is None (v4's behaviour, unchanged).

### 2. `e` toggles, and freezes the cursor while it is on

`ViewState.extended` + the `e` hotkey. It resolves the selection the same way
`k`/`+`/`-` do, so program view refuses with the same popup — but `e` is
read-only, so unlike them it may target Glances itself.

**The cursor freezes while extended is on**, as in v4
(`glances_curses.py:356`). Without it the extended block describes whatever
the cursor last landed on while the user is still moving it.

Turning it off clears BOTH `extended_pid` and `extended_process`, which also
stops the engine grabbing. v4 leaves `extended_process` set and keeps paying
for it after `e` is pressed again — the renderer just stops reading it.

`enable_extended()` calls `self.update()` synchronously (`processes.py:210`);
from the TUI thread that is a second full process collection racing the
collector's. v5 sets `disable_extended_tag` directly and lets the next cycle
pick it up.

→ **verify:** the toggle, the freeze, the clear-on-off, the program-view
refusal, and that `e` on Glances' own pid is allowed where `k` is not.

### 3. The data reaches the renderer through `view`, not through the singleton

`_build_view` publishes `view["extended_process"]` from
`glances_processes.extended_process`, and only when `e` is on AND the payload
matches the selected pid. The renderer stays pure — it is fed, it does not
fetch — and nothing new appears in the REST payload, which is what the
TUI-only decision requires.

### 4. The block itself

`processlist/render_curses_v5.py`, above the column header, v4's four lines:
pinned name, CPU min/max/mean + affinity + IO nice, MEM min/max/mean + memory
info + swap, and the Open counters.

**It takes its rows from the process list, one for one**: the vertical solver
(`plan_right_column`) models an elastic block as "one line per data row plus
one header", so a block that grows by four unmodelled rows overflows the body.
The renderer subtracts the extended rows from its own budget instead, leaving
`PluginBlock.height` exactly what the solver predicted. That is also what v4
does in effect — its extended block pushes processes off the bottom.

→ **verify:** the block renders its four lines from a real payload; the total
block height is unchanged by turning `e` on; absent `extended_process` in
`view` leaves the output byte-identical.

### 5. Tests, mutation testing, live smoke test

As b1/b2: every new guard mutation-tested, and a real pty run — `e` is an
interaction.

---

## A fourth v4 defect, found while reading the payload

v4's `maybe_add_ionice_line` (`processlist/__init__.py:728-742`) guards on
`hasattr(prog['ionice'], 'ioclass')`. But the engine stores
`namedtuple_to_dict(proc)` (`processes.py:669`), which turns psutil's `pionice`
namedtuple into a **dict** — and a dict has no `.ioclass`. So the guard is
always False and **v4 never renders its IO nice line**.

Checked empirically, not by reading: driving the real engine with extended
stats on gives `ionice = {'ioclass': <IOPriority.IOPRIO_CLASS_NONE: 0>,
'value': 0}`, and `hasattr(..., 'ioclass')` is False.

v5 reads the dict, so the line actually appears.
