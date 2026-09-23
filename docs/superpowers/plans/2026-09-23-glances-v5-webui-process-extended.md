# Glances v5 WebUI — click a process to pin it (2.X-b3-web) — Implementation

**Design:** `docs/superpowers/specs/2026-09-23-glances-v5-tui-process-management-design.md` §8.1
**Branch:** `develop-v5`, on top of `c717a4d` (2.X-b3, the TUI side)

**The decision this implements**, and the correction it carries: the
maintainer's "TUI-only" ruling covered `k`, `+` and `-` — the keys that *act
on* a process. `e` only looks, and v4's web UI already offers it as a **click
on the process row**. I had recorded the ruling as covering the whole group,
which would have silently dropped a v4 feature. Corrected in §8.1 and in
`…decisions.md` before this chantier.

---

## What v4 does, read from its source

- `plugin-processlist.vue:59` — the column header reads **"Command (click to
  pin)"**.
- `:720` — `fetch("api/4/processes/extended/" + pid, {method: "POST"})` pins.
- `:726` — `fetch("api/4/processes/extended/disable", {method: "POST"})`
  unpins, behind an **Unpin** button in the block.
- `:460-463` — the block's data is found by scanning the process list for the
  item whose `extended_stats === true`: **v4 ships the extended fields inside
  the processlist payload**, on the one pinned item.
- Server side: `glances_restful_api.py:1417-1445`, the two POST handlers, plus
  a `GET /processes/extended` its own web UI does not use.

The pin is **global server state** in v4 — a click in one browser changes what
the TUI and every other client shows. Keeping that: extended stats cost a
psutil grab per cycle, so one pinned process per server is a property worth
having, not an accident to design around.

---

## Steps

### 1. The payload rides in `/api/5/all` — no second request

`fetchAll` makes **one** request per tick, deliberately (api.js: "ONE request
per tick, not one per plugin… at 34 components and a 2 s cadence, per-plugin
fan-out is 17 req/s"). A per-tick `GET /processes/extended` would break that
for a feature that is off almost all the time.

v5's own mechanism for exactly this is plugin **payload metadata** —
`_add_metadata()`, which `fs` already uses to publish `free_space` to a
renderer that has no other way to reach it. `processlist` publishes
`extended` the same way, so the browser gets it inside `/api/5/all` with
everything else, at zero extra cost.

Not v4's shape (the fields merged into the pinned item): v5 filters every
collection item to `fields_description` (`_remove_parameters`), so v4's shape
would mean declaring ~15 fields that are null on every process but one.

→ **verify:** the envelope carries `extended` only while pinned; exporters
never see it (`get_export()` returns only `data` items); the payload is
JSON-serialisable (`ionice.ioclass` is a psutil IntEnum).

### 2. Two POST routes

`POST /api/5/processes/extended/{pid}` and `.../disable`, in `routes_v5.py`
beside the existing `POST /token`. They set the same `extended_pid` the TUI's
`e` sets — one pin, two ways to ask for it.

404 on a pid that is not in the current process list, as v4 does. v4 reaches
that through `int(pid)`, which raises `ValueError` → 500 on garbage; v5 lets
FastAPI's path type do the validation.

**Security posture, stated rather than assumed:** these change server state on
an API Glances leaves unauthenticated by default. What an unauthenticated
caller gains is one pinned pid's affinity, ionice, fd count, swap and
connection counts — of the same nature as the process list it can already
read, and exactly v4's exposure. No data on the host is modified. Recorded in
`…decisions.md` rather than left implicit.

### 3. The browser

- The Command header reads **"Command (click to pin)"**, as v4's does.
- A click on a row pins it; the row carries the pin affordance.
- The block above the table, mirroring the TUI's four lines, with an
  **Unpin** button.
- The pinned row is marked, the way the TUI underlines its selection.

### 4. Tests

Routes (pin, unpin, unknown pid, the payload shape), the model's metadata,
the JS block builder, and a live browser check — a click is an interaction,
and the TUI chantiers showed twice that only a real run finds what the tests
cannot.


---

## What the live browser found that the tests could not

Twice, which is the pattern these chantiers keep repeating.

**The header would have wrapped at nearly every width.** v4's wording,
"Command (click to pin)", needs 186px. Measured in Chromium, that column is
the elastic remainder and lands at **161px at 640, 72px at 900, 137px at
1280**. So the header stays "Command", as the terminal and the other two
process blocks have it, and the affordance is carried by `cursor: pointer`
and a `title` — neither of which costs a pixel of layout.

**A pinned process that exits froze the block forever.** Pin it, kill it, and
the browser kept showing its last numbers under a `extended_stats: True` that
had stopped being true. Nothing in the engine's update loop runs again for a
pid that has left the list, so `extended_process` is never refreshed and never
cleared — v4 has the same defect from the same lines. Fixed at the engine
rather than in the model's guard, because both surfaces read it there, and the
PIN is dropped with the accumulator: leaving it set would keep the TUI's cursor
frozen on a block it no longer draws.

And one thing measured rather than assumed: the block is titled with the
process **name**, not its command line. `glances_processes.extended_process`
carries no `cmdline` at all — the engine adds it after the extended grab. v4's
web UI titles with one only because it reads the published list ITEM instead.
