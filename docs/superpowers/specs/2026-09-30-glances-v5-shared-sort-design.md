# Glances v5 — one process sort, shared by the TUI and the WebUI

**Date:** 2026-09-30
**Branch:** `develop-v5`
**Status:** approved by the maintainer (option 2 of the 2026-09-30 discussion); implemented

## 1. Problem

The v5 WebUI cannot change the sort of the process, container and VM
tables. It only underlines the column matching `--sort-processes`, i.e. the
key the server was STARTED with (G9-9B §7.2). The v4 WebUI could re-sort by
clicking a header, so this is a regression.

Two divergences recorded by G9-9B (§10) and still open in the right-column
fit design (§9) come from the same gap:

- **#1** — the underline follows the startup key, not the live one.
- **#4** — `processcount`'s `sorted by …` indicator is omitted when
  `--sort-processes` was not given, and never says `automatically`.

Both exist because the live sort key (`glances_processes.sort_key` and
`.auto_sort`) is engine state that no route publishes and no route changes.

## 2. Decision

The engine's sort key stays the **single** source of truth, and it becomes
readable and writable over REST:

- **Write:** `POST /api/5/processes/sort/{key}`.
- **Read:** `processcount` publishes `sort_key` and `auto_sort` in its
  payload, every cycle.

Every surface reads and writes that one key:

| Surface | Changes the sort with | Reads the sort from |
|---|---|---|
| Standalone TUI | `a c m i t p u o`, arrows (unchanged) | the local engine (unchanged) |
| Client TUI (`-c`) | same keys: local engine **and** the server's route | the server's `processcount`, when it changes |
| WebUI | header click, `a c m i t p u o` | the server's `processcount` |

Containers and VMs already sort on the process key server-side
(`containers/model_v5.py::_sort`, `vms/model_v5.py::sort_vm_stats`), so they
follow with no change to their models.

**Accepted consequence.** The sort is global to the server, as the pin is
(2.X-b3): a click in one browser re-sorts every browser and every client TUI
attached to that server. That is what "one sort" means; per-viewer sorting
was option 1 and was not chosen.

## 3. Server

### 3.1 The route

```
POST /api/5/processes/sort/{key}      -> true
```

- `key` ∈ `sort_processes_stats_list` (`processes.py`) ∪ `{"auto"}` —
  imported, not retyped, as `--sort-processes` already does.
- `auto` → `set_sort_key("auto")`: `auto_sort` on, key reset to
  `cpu_percent`, then `GlancesAlerts` drives it again (v4 contract, same as
  the TUI's `a`).
- Any other valid key → `set_sort_key(key, False)`: manual, `auto_sort` off.
- Unknown key → `400`, with the accepted keys in the detail.
- Registered by its own `_register_sort_route`, right after the pin routes
  and before the `/{plugin_name}` family.

**Security posture.** Same as the pin. Glances is unauthenticated by default;
what an unauthenticated caller gains is the ORDER of a list it can already
read. Nothing on the host changes. Under `[outputs] password` the route is
behind the same auth middleware as every other one. A cross-site `POST` (no
body, so no CORS preflight) can re-sort the table; this is the pin's exposure
too, and it is harmless.

### 3.2 Publishing the key

`processcount` is the plugin that runs `engine.update()`, which is what sorts
the list. Right after it, `_add_metadata` records `sort_key` and `auto_sort`,
so the published key is the one this cycle's list was sorted with.

Declared in `fields_description` as `internal: True, exportable: False`:
the API keeps them (`_api_drop_fields` spares `internal`), the exporters drop
them (a string column in InfluxDB/CSV would be noise).

`/api/5/args` keeps serving the STARTUP `sort_processes_key`, unchanged: it
is the CLI namespace, not live state.

## 4. WebUI

### 4.1 The live key

`AppShell.effectiveArgs` already seeds values whose authority is a payload
rather than `/api/5/args` (`fs_free_space`). `sort_processes_key` and
`auto_sort` are seeded the same way, from `results.processcount` when present,
falling back to `serverArgs.sort_processes_key` for a server that predates
this change. Every consumer keeps reading `serverArgs.sort_processes_key`
(the prop is `effectiveArgs`), so the underline logic does not change.

### 4.2 Header clicks

- `processlist` / `programlist`: the headers `HEADER_SORT_KEY` maps
  (`CPU%`, `MEM%`, `USER`, `TIME+`, `R/s`, `W/s`, `Command`) become clickable.
  `PID`, `VIRT`, `RES`, `THR`, `NI`, `S`, `NPROCS` have no engine sort key and
  stay inert.
- `containers`: `CONTAINER` → `name`, `CPU%` → `cpu_percent`,
  `MEM` → `memory_percent` — the TUI's own `_HEADER_SORT_KEY`
  (`containers/render_curses_v5.py`). These headers also gain the underline
  they lacked in the browser.
- `vms`: `Name`, `CPU%`, `MEM/MAX`, same keys (`vms/render_curses_v5.py`
  `_HEADER_SORT_FIELD`), underline included.
- A clickable header shows a pointer cursor and a `title` ("Sort by …").

**No optimistic update**, as for the pin: the click POSTs and the next tick
shows the new order and the new underline together. A failed POST leaves the
page showing the truth. The order changes within one refresh period, because
the list is re-sorted by the engine's next `update()`.

### 4.3 `processcount` indicator

Rendered whenever a key is known, exactly as the TUI's
`_sort_indicator_cell`: `Threads sorted automatically by CPU consumption`, or
`… sorted by …` when `auto_sort` is false. Closes divergence #4.

### 4.4 Sort hotkeys

`a c m i t p u o`, mirroring the `sort` entries of `TuiV5._HOTKEYS`: a
`SORT_KEYS` table in `hotkeys.js`, held to the Python by the existing drift
test, listed in the `h` overlay under `SORT PROCESSES`. None of these keys is
bound in the browser today (the SHOW/HIDE and TOGGLE VIEW keys are
uppercase or other letters). The arrows are not ported: in the browser they
scroll the page.

## 5. Client TUI (`-c`)

- A sort key (letters or arrows) sets the local engine, as today, so the next
  repaint re-sorts immediately (`_apply_live_sort`), **and** calls
  `RemoteSource.set_sort(key)` → the server's route.
- The client follows the server: when the server's published
  (`sort_key`, `auto_sort`) differs from the last pair seen FROM THE SERVER,
  the local engine adopts it. Comparing with the last server value, not with
  the local key, is what stops a stale snapshot (published before the
  client's own POST landed) from reverting a key the user just pressed.
- A server without the route (older v5) answers 404/405: the key still
  applies locally, as before, and the refusal is logged, not shown.

## 6. Out of scope

- Sort DIRECTION. The engine has none to set (`sort_reverse` is derived from
  the key); neither the TUI nor v4 offers one.
- Sorting the other WebUI tables (fs, diskio, network…): the TUI does not
  sort them either.
- Per-viewer sort (option 1).

## 7. Tests

- Route: each valid key sets the engine; `auto` restores `auto_sort`; an
  unknown key is a 400 and changes nothing; the route sits behind the auth
  middleware when a password is set.
- `processcount`: `sort_key`/`auto_sort` in the API payload, absent from
  `get_export()`.
- WebUI (node): the hotkey drift test covers `SORT_KEYS`; header→key maps for
  containers/vms; the indicator text in both modes.
- Client TUI: a sort key POSTs; a changed server key is adopted; a stale
  snapshot does not revert a local key; a refused POST keeps the local sort.

## 8. Divergences closed

G9-9B #1 (underline follows the startup key) and #4 (indicator omitted / never
`automatically`).
