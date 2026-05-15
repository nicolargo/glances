# Glances v5 Phase 2 — G2 (TUI vs REST mode dispatch) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Move v5 from REST-first (where the FastAPI app + uvicorn always
start, and the TUI is an optional add-on thread) to **mode-dispatched**:
TUI by default, REST API only when explicitly requested via `-s`, MCP
endpoint only when also requested via `--enable-mcp`. Restores the v4
mental model (`glances` = TUI; `glances -s` = server; `glances --enable-mcp`
= MCP) and removes the unexpected default network exposure.

**Why single-phase:** the global CLAUDE.md "two-phase refactor" rule is
designed to protect *existing deployments*. v5 is still in alpha — no
production users — so the parallel-mechanism phase has no value. We
ship the new dispatch in one PR.

---

## Design alignment (from user, 2026-05-15)

| Mode | Flag(s) | Scheduler | TUI | REST | MCP |
|---|---|---|---|---|---|
| **TUI** (default) | _(none)_ | ✅ | ✅ | ❌ | ❌ |
| **Server** | `-s` / `--server` | ✅ | ❌ | ✅ | ❌ |
| **Server + MCP** | `-s --enable-mcp` | ✅ | ❌ | ✅ | ✅ |
| **Legacy** | `--quiet` / `--no-tui` | _(open point — see Task 1)_ | — | — | — |

User answers verbatim:
1. *"oui on garde cela"* — `-s` is headless (TUI off).
2. *"ok"* — default mode does not launch uvicorn at all.
3. *"Par defaut (-s) le serveur MCP ne doit pas être lancé. L'utilisateur doit forcer sont lancement avec l'option (--enable-mcp)"* — MCP requires explicit opt-in even in server mode.
4. *"Je n'ai pas les idées claire sur cette option. Pour l'instant lancer comme cela et mettre un point ouvert dessus pour plus tard."* — `--quiet` / `--no-tui` fate deferred.

---

## File Structure

| Path | Responsibility | Action |
|---|---|---|
| `glances/main_v5.py` | CLI parser + `assemble()` + `serve()` mode dispatch | Modify |
| `glances/webserver_v5.py` | gate MCP mount on a config flag (read from a CLI-derived overlay) | Modify |
| `glances/outputs/glances_mcp.py` | unchanged (the mount point is gated, not the implementation) | _no change_ |
| `Makefile` | adjust `run-v5` (TUI-only), add `run-v5-server` and `run-v5-mcp` targets | Modify |
| `docs/architecture/glances-v5-architecture-decisions.md` | document mode dispatch in §1 + flag matrix | Modify |
| `tests/test_main_v5.py` | cover default/server/server+mcp modes | Modify |
| `tests/test_webserver_v5.py` | assert MCP mount only when flag set | Modify |
| `tests/test_security_v5.py` | confirm default mode does not bind a socket | Modify |
| `tests/test_cli_v5.py` | new — argparse-level tests for `-s` / `--enable-mcp` mutual constraints | Create |

Each Task = 1 commit. The visual smoke is end-of-plan only (no UI changes here).

---

## Task 1: CLI flags + validation

**Reference:** `glances/main_v5.py::build_parser`

**Steps:**

- [ ] **Step 1: Add `-s` / `--server`.**
  ```python
  parser.add_argument(
      "-s", "--server",
      dest="server",
      action="store_true",
      help="Run as a REST API server (FastAPI on bind_address:port). Headless — no curses TUI.",
  )
  ```
- [ ] **Step 2: Add `--enable-mcp`.**
  ```python
  parser.add_argument(
      "--enable-mcp",
      dest="enable_mcp",
      action="store_true",
      help="Mount the MCP endpoint at /mcp. Requires --server. Off by default.",
  )
  ```
- [ ] **Step 3: Add `--quiet` / `--no-tui` deprecation note.** Keep the
  flag working (for now), but emit a `DeprecationWarning` and a log line
  pointing users to `-s` when it is set without `-s`. Open point
  resolution in a later phase — see Plan §"Open points".
- [ ] **Step 4: Argument validation in `main()`.** After parsing:
  - `--enable-mcp` without `-s` → error: "MCP requires --server".
  - `--server` *and* `--quiet`/`--no-tui` → no error (equivalent, but log
    a hint that `-s` already implies headless).
- [ ] **Step 5: Tests** — `tests/test_cli_v5.py`:
  - parser accepts `-s` and `--enable-mcp` independently;
  - `--enable-mcp` alone (no `-s`) exits non-zero with a clear error message;
  - `-s` and `--server` are aliases (same `args.server`);
  - `--quiet`/`--no-tui` still sets `args.no_tui=True`.
- [ ] **Step 6: Commit.**

---

## ~~Task 2: webserver_v5 — gate the MCP mount~~ — DROPPED (deferred to G3-MCP)

**Status (2026-05-15):** Dropped from G2 scope after discovery that MCP
is **not currently wired into v5** (`glances/outputs/glances_mcp.py`
exists, but `webserver_v5.build_app` does not mount it — the only
caller is `glances/outputs/glances_restful_api.py`, which is v4).

There is no `/mcp` mount to gate yet. The `--enable-mcp` CLI flag +
validation introduced in Task 1 already prevent the user from passing
the flag in any nonsensical way (`--enable-mcp` without `-s` exits
with a clear error). The flag becomes operationally meaningful when
MCP is ported into v5 — a dedicated **G3-MCP plan** will cover:

- porting `GlancesMcpServer` to read from `StatsStoreV5` instead of
  the v4 `GlancesStats` object;
- mounting `/mcp` in `build_app` gated on `[outputs] enable_mcp`;
- propagating `args.enable_mcp` into the config overlay (like
  `args.api_doc` does today);
- transport security + allowed-hosts configuration;
- integration tests against a live MCP client.

Rationale for the split — keeps G2 focused on the mode-dispatch
surgery (cf. global CLAUDE.md "édits chirurgicales / atomiques"
principle). MCP wiring is its own non-trivial chunk and deserves a
dedicated plan rather than being smuggled into G2.

---

## Task 3: main_v5 — mode-dispatched lifecycle

**Reference:** `glances/main_v5.py::assemble` and `::serve`

**Current shape (REST-first):**

```python
def assemble(args, config):
    plugins = discover_plugins(...)
    scheduler = AsyncScheduler(...)
    app = build_app(config, ...)              # always built
    tui = TuiV5(...) if not args.no_tui else None
    return app, scheduler, host, port, tui

async def serve(app, scheduler, host, port, tui):
    if tui is not None:
        tui.start()
    uvi_config = uvicorn.Config(app, ...)
    server = uvicorn.Server(uvi_config)
    try:
        await asyncio.gather(server.serve(), scheduler.run())
    finally:
        if tui is not None:
            tui.stop(); tui.join(timeout=2.0)
```

**Target shape (mode-dispatched):**

```python
def assemble(args, config):
    plugins = discover_plugins(...)
    scheduler = AsyncScheduler(...)
    if args.server:
        app = build_app(config, ...)          # only when REST requested
        tui = None                             # -s is headless (alignment #1)
    else:
        app = None                             # default: no FastAPI app
        tui = TuiV5(...) if not args.no_tui else None
    return app, scheduler, host, port, tui

async def serve(args, app, scheduler, host, port, tui):
    if not args.server:
        # TUI-only mode: scheduler + (optionally) TUI thread, no uvicorn.
        if tui is not None:
            tui.start()
        try:
            await scheduler.run()              # awaits SIGINT
        finally:
            if tui is not None:
                tui.stop(); tui.join(timeout=2.0)
        return

    # Server mode: scheduler + uvicorn, no TUI.
    assert app is not None
    uvi_config = uvicorn.Config(app, ...)
    server = uvicorn.Server(uvi_config)
    try:
        await asyncio.gather(server.serve(), scheduler.run())
    except Exception:
        ...
```

**Steps:**

- [ ] **Step 1: Refactor `assemble()`** to branch on `args.server`.
- [ ] **Step 2: Refactor `serve()`** to branch on `args.server` —
  TUI-only path does not import `uvicorn` machinery if possible (defer
  the import to keep cold-start lean for the default mode).
- [ ] **Step 3: Cursor / SIGINT plumbing.** Verify the existing SIGINT
  handler (TUI `q` → `os.kill(pid, SIGINT)` → uvicorn stop) still works
  in TUI-only mode. In TUI-only mode SIGINT must cancel `scheduler.run()`.
  Add the cursor-restore safety net to both paths (already there per
  prior fix; just make sure both branches go through it).
- [ ] **Step 4: Tests** — `tests/test_main_v5.py`:
  - `assemble(args.server=False)` returns `app is None`;
  - `assemble(args.server=True)` returns `tui is None` and a real `app`;
  - `serve(args.server=False, …)` does not bind any TCP socket — assert
    via a `socket.socket().getsockname()` check or by patching
    `uvicorn.Server` and verifying it is never instantiated.
- [ ] **Step 5: Commit.**

---

## Task 4: Makefile + env-config

**Reference:** `Makefile` (`run-v5`, `run-v5-debug`)

**Steps:**

- [ ] **Step 1:** `run-v5` stays the canonical "user mode": launch the
  TUI without REST. Update the help string.
- [ ] **Step 2:** New `run-v5-server`: `python -m glances.main_v5 -C $(CONF) -s`.
- [ ] **Step 3:** New `run-v5-mcp`: `python -m glances.main_v5 -C $(CONF) -s --enable-mcp`.
- [ ] **Step 4:** New `run-v5-debug-server`: server mode + `-d`.
- [ ] **Step 5: Commit.**

---

## Task 5: Architecture doc

**Reference:** `docs/architecture/glances-v5-architecture-decisions.md`

**Steps:**

- [ ] **Step 1:** New section "§1.5 Mode dispatch" with the alignment
  table from this plan reproduced verbatim and a small ASCII diagram
  showing the three paths through `assemble()` / `serve()`.
- [ ] **Step 2:** Update §4 (REST API) to note it is now opt-in via `-s`.
- [ ] **Step 3:** Update §X (MCP) to note opt-in via `--enable-mcp`.
- [ ] **Step 4: Commit.**

---

## Task 6: Final sweep

- [ ] **Step 1:** `make test-v5` — green.
- [ ] **Step 2:** `make test` — v4 non-regression, green.
- [ ] **Step 3:** `make lint && make format` — clean.
- [ ] **Step 4:** Manual checks (maintainer-driven):
  - `make run-v5` — TUI works, `ss -tlnp | grep 61208` shows nothing.
  - `make run-v5-server` — no TUI, REST reachable on `:61208`, `/mcp` returns 404.
  - `make run-v5-mcp` — REST + `/mcp` reachable.
- [ ] **Step 5: Stop at the local-commit boundary.** Per project memory
  [[feedback-never-push-or-open-pr]], do NOT push or open a PR — the
  maintainer handles that.

---

## Open points (carried forward — not in scope for G2)

1. **Fate of `--quiet` / `--no-tui`.** Currently this flag means "REST
   only, no TUI" — which `-s` now expresses canonically. Three options
   on the table for a follow-up:
   - alias `--no-tui` ↔ `-s` (one canonical, one legacy);
   - remove `--no-tui` once the deprecation cycle completes;
   - repurpose `--no-tui` to mean "headless even in default mode" (i.e.
     scheduler only, no TUI, no REST — useful for `--export` or
     test rigs).
   To be decided after a few weeks of dogfooding the new defaults.
2. **`--client` mode.** v4 has a client mode that connects to a remote
   v4 server. Not yet ported to v5 — orthogonal to this plan.
3. **Authentication interaction.** The default exposing-no-API mode
   removes the unauthenticated-default footgun for casual TUI users.
   Server-mode auth posture stays as-is (cf. `feedback-tui-v5-must-mirror-v4`
   and the CLAUDE.md security philosophy).

---

## Wrap-up

After merge:
1. Update project memory: add `project_v5_mode_dispatch.md` — note that
   `glances-v5` default no longer binds a socket; `-s` is required for
   REST; `--enable-mcp` for MCP.
2. Subsequent v5 work (Phase 2 G3+) can rely on the dispatch — e.g.
   when porting `--export` modes, decide whether they belong in TUI
   mode, server mode, both, or a new sub-mode.
