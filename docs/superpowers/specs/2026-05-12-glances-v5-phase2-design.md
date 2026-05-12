# Glances v5 — Phase 2 design

**Status:** Approved — ready for `writing-plans`
**Date:** 2026-05-12
**Branch:** `develop-v5`
**Predecessor:** Phase 1 (core plugins + REST API skeleton, completed — TUI v5 deferred)
**Successor:** Phase 3 (remote client + browser mode)

---

## 1. Goals

Deliver feature parity with v4 for local monitoring on `develop-v5`:

1. Migrate every remaining v4 plugin to the `model_v5` contract defined in §3 of
   `docs/architecture/glances-v5-architecture-decisions.md`.
2. Ship the curses TUI v5 (a Phase 1 carry-over) and wire each migrated plugin
   into it.
3. Keep `/api/5/*` routes (already implemented in Phase 1.6) automatically
   serving every newly registered plugin.

Phase 2 is **plugins + TUI only**. Export modules, WebUI served by FastAPI,
remote client, and browser mode are out of scope (see §2).

## 2. Out of scope

Pushed to Phase 2.X late or to Phase 3:

- **Export modules** (InfluxDB, Prometheus, CSV, JSON, plus all other v4
  exporters) — migrated after every plugin has landed.
- **WebUI served by FastAPI** — final slot of Phase 2, after all plugins and
  TUI integration are done. Validation during Phase 2 happens via TUI + REST.
- **`GlancesPluginRemote`** (client/server REST) — Phase 3.
- **Browser mode + serverslist + zeroconf** — Phase 3.

The architecture document already locks the design for these items; Phase 2
does not revisit them.

## 3. Constraints (non-negotiable)

- **No regression on v4 defaults.** The v4 codebase stays untouched on
  `develop-v5`; v4 unit tests must remain green at every PR.
- **No dead code.** A plugin migrated to v5 must be wired into the scheduler,
  the REST registry, and the TUI within its own PR. Dropping a plugin (e.g.
  `profiler`) means *not creating* a `model_v5.py` — the v4 file stays until
  the final `develop-v5 → develop` merge in Phase 4.
- **Surgical edits.** Each PR ≤ ~600 lines added (excluding tests). Split if a
  single plugin exceeds.
- **TUI parity with v4.** Default rendering of each migrated plugin in v5 must
  match the v4 visual output. See §7.
- **Perf budget.** No more than +20% on the refresh-time end-to-end vs the v4
  equivalent for any migrated plugin. Blocking criterion.
- **`develop → develop-v5` weekly merge** stays active. Each PR rebases on the
  latest `develop-v5` before review.

## 4. Group decomposition

Migration ordered by increasing complexity, per
`glances-v5-architecture-decisions.md` §3.9.

| Group | Plugins | Count | Estimated PRs |
|---|---|---|---|
| **G0 — Phase 1 closure** | TUI v5 scaffold + wiring for cpu, mem, load, network, percpu | (infra + 5) | 1 (split G0-A / G0-B if > 700 lines) |
| **G1 — Trivials** | uptime, system, core, version, psutilversion, now | 6 | 1 |
| **G2 — Simple scalars** | memswap, quicklook (CPU + MEM + load + cores, **no GPU**) | 2 | 1 |
| **G3 — Simple psutil collections** | fs, diskio | 2 | 1 |
| **G4 — Hardware / system** | sensors, gpu, npu, wifi, ip, raid, smart, **quicklook GPU addendum** | 7 + addendum | 2 (G4A: sensors+gpu+npu+quicklook GPU / G4B: raid+smart+wifi+ip+SSRF) |
| **G5 — Process** | processcount, processlist, programlist | 3 | 1–2 (G5A: processcount + processlist / G5B: programlist — split only if G5A hits the line budget) |
| **G6 — External integrations** | containers, vms, amps, folders, connections, ports, irq, cloud, mpp | 9 | 3 (G6A: containers+vms / G6B: ports+connections+amps+folders / G6C: irq+cloud+mpp) |
| **G7 — Alert presentation plugin** | alert (reads `alerts.get_history()` / `/api/5/alert`) | 1 | 1 |

**Total: ~10–11 PRs**, sequential on `develop-v5`.

### 4.1 Special cases — explicit decisions

- **`quicklook`** — Split delivery: G2 ships the v4 base (CPU + MEM + load
  bars + per-core sparkline). G4A adds the GPU section (mem + proc) once the
  `gpu` plugin is migrated. Both sub-deliveries are independently testable.
- **`help`** — **Removed as a plugin in v5.** Becomes a pure TUI/WebUI
  overlay. No `glances/plugins/help/model_v5.py`. Documented as a breaking
  change in `NEWS.rst` at 5.0.0.
- **`profiler`** — **Removed in v5.** Not migrated. Documented in `NEWS.rst`.
  The v4 `glances/plugins/profiler/` directory stays until Phase 4 cleanup.
- **`alert`** (G7) — Presentation-only in v5: reads `alerts.get_history()`
  (already in `alerts_v5.py`) and exposes it via `/api/5/alert` (already
  implemented in Phase 1.6). Its `model_v5.py` is thin — likely a dict view
  with TUI integration. Scope to be confirmed at G7 start.
- **`ip`** (G4B) — Includes **CVE-2026-35587 SSRF mitigation** in the same
  PR: validate URL scheme (`http`/`https` only); reject loopback / link-local
  / RFC1918 / cloud metadata IPs unless `public_api_allow_internal=true`;
  never forward `public_username`/`public_password` to a hostname off the
  allowlist. Documented in `NEWS.rst`.

### 4.2 Order of execution

G0 → G1 → G2 → G3 → G4A → G4B → G5A → (G5B) → G6A → G6B → G6C → G7

Sequential; one PR merged before the next starts review. No parallel branches.

## 5. Per-PR template (G1 onwards)

Every plugin-migration PR includes:

```
glances/plugins/<name>/model_v5.py          ← v5 plugin (asyncio, inherits GlancesPluginBase[T])
tests/test_plugin_<name>_v5.py              ← pytest-async unit tests
tests/test_perf_v5.py                       ← perf check (incremental update for this plugin)
glances/outputs/glances_curses_v5.py        ← TUI registry/layout entry for this plugin
docs/                                        ← only if a public API or config key changes
NEWS.rst                                     ← entry under 5.0.0-aN
```

### 5.1 Done bar — merge checklist

1. **Code** — `fields_description` complete (description, unit, label,
   watched, watch_direction, prominent, default_thresholds, primary_key for
   collections, exportable, rate where applicable).
2. **Tests v5 green** — `make test-v5`. Coverage on `_grab_stats`,
   `_transform` (gauge, expand, derived, remove), `_levels`,
   `fields_description` shape.
3. **Tests v4 not regressed** — `make test` on the corresponding
   `tests/test_plugin_<name>.py` still passes.
4. **REST smoke** — `GET /api/5/<plugin>` and `GET /api/5/<plugin>/info`
   return the expected payload. Tested via `tests/test_routes_v5.py` extended
   per plugin (programmatic), not curl-driven.
5. **TUI wired** — manual screenshot v4 vs v5 attached to the PR description,
   same data set on both sides.
6. **Perf check** — `tests/test_perf_v5.py` measures refresh-time end-to-end
   for the migrated plugin; **block merge if regression > 20%** vs v4.
7. **Lint / format** — `make lint && make format` clean.
8. **NEWS.rst** — entry added if any visible-API change (datamodel,
   threshold defaults, config key rename).
9. **Rebase on latest `develop-v5`** before review.

### 5.2 Size cap

PR ≤ ~600 added lines (excluding test files). If a single plugin (typically
`processlist`, `containers`) exceeds, split by responsibility:

- PR-A: `_grab_stats` + transformation scaffold + tests
- PR-B: TUI rendering + perf check

This is an exception path; the default is one plugin = one PR slice.

## 6. G0 — TUI v5 scaffold (Phase 1 closure)

The first deliverable of Phase 2. It bundles infrastructure work that
unblocks every subsequent group.

### 6.1 Deliverables

1. **`glances/outputs/glances_curses_v5.py`** — curses TUI v5 module:
   - Runs in a **dedicated thread** spawned by `main_v5.py` (per
     architecture §1.4).
   - Reads `StatsStoreV5` lockless, between scheduler cycles.
   - **Generic renderer** driven entirely by `fields_description`:
     - `unit` → default formatter (bytes → `B/K/M/G`, percent → `%4.1f%%`,
       bytespers → rate-aware, seconds → `1h 5m`, string → passthrough).
     - `label` → column header / row label.
     - `prominent` + `_levels` → coloration (font color for `prominent:False`,
       background highlight for `prominent:True`).
     - `format` (new, optional) — explicit format string override (e.g.
       `"%5.1f%%"`).
     - `column_width` (new, optional) — fixed column width override
       (default: auto from label + max content width).
   - **Layout** — two-column minimal:
     - Left: scalar plugins (cpu, mem, load, …) stacked vertically.
     - Right: collection plugins (network, fs, …) stacked vertically.
   - **Footer** — alerts feed reading `alerts.get_history()` (last N events,
     N from config, default 10).
   - **Key bindings** — `q`, `ESC`, `Ctrl-C` quit. Nothing else in G0.
   - **No 256-color advanced support** in G0 — fallback to base ANSI palette
     acceptable. Refined in a later PR if needed.
   - **No sparklines, no sort/filter hotkeys.** Added in G5 (processlist)
     when a real use case lands.

2. **`glances/main_v5.py`** — add `--no-tui` flag. TUI active by default in
   standalone mode.

3. **`tests/test_curses_v5.py`** — smoke tests with `curses` mocked: layout
   assertions, formatter outputs, color-rule resolution from `_levels`.

4. **`docs/architecture/tui-v4-rendering-patterns.md`** (new) — systematic
   catalogue of v4 `msg_curse()` patterns extracted from the ~30 v4 plugins:
   table of (plugin × column widths × alignments × format strings × color
   rules × separators × header/footer). This document is the contract the v5
   generic renderer must satisfy. See §7.

5. **`docs/architecture/glances-v5-architecture-decisions.md`** — update:
   - **§1.4** — flesh out the curses thread design (lockless reads, layout,
     formatter pipeline, quit handler).
   - **§3.2** — append `format` and `column_width` to the `fields_description`
     table as **optional** keys (do not revive `view_layout`).

6. **`.claude/skills/SKILL-plugin.md`** — extend with:
   - Renderer-hints documentation (`format`, `column_width`).
   - Visual-parity checklist (see §7).
   - Done-bar checklist (§5.1).

### 6.2 Cycle-0 wiring of Phase 1 plugins

G0 also wires `cpu`, `mem`, `load`, `network`, `percpu` into the TUI v5
registry. After the PR merges, `glances-v5` starts with a working TUI that
displays the four Phase 1 plugins, matching v4 visual output.

### 6.3 Size estimate

~500–700 lines for the curses module + tests + docs. If estimate is
exceeded during implementation, split:

- **G0-A** — curses scaffold (thread, lockless read loop, layout container,
  formatters, color rules) — no plugin wiring yet.
- **G0-B** — wiring of cpu/mem/load/network/percpu + `tui-v4-rendering-patterns.md`.

The split decision is taken at the end of the writing-plans pass on G0, not
upfront.

## 7. TUI visual parity (v4 → v5)

Strategy: **caractérisation v4 + renderer hints**.

1. **G0 study phase** — read every v4 plugin's `msg_curse()` (~30 files).
   Document patterns in `docs/architecture/tui-v4-rendering-patterns.md`:
   column widths, alignments, numeric format strings, separator characters,
   header/footer conventions, conditional color rules. This document is the
   reference renderer contract.
2. **Generic v5 renderer** covers the common cases via `unit`, `label`,
   `_levels`, and `prominent`. Most plugins need nothing else.
3. **Optional escape hatch** in `fields_description`:
   - `format: str` — explicit format string when the unit-driven default
     does not match v4 (e.g. trailing space, three-digit padding).
   - `column_width: int` — explicit width when auto-sizing does not match
     v4.
   These are **purely declarative formatting hints**, not layout descriptors.
   They do *not* reintroduce the `view_layout` mechanism rejected in §3.6;
   per-plugin layout choices (column order, row layout, separators) remain
   the renderer's responsibility, not the plugin's.
4. **Per-PR check** — every plugin PR attaches v4 vs v5 screenshots
   side-by-side on the same data set. Reviewer arbitrates visual fidelity.
   Optional text-fixture diff in `tests/fixtures/tui_<plugin>_v5.txt` if the
   reviewer wants a CI guard for that specific plugin.
5. **No mandatory CI visual regression test** in Phase 2. Adding fixture
   diffs is at the discretion of each PR author. A systematic
   visual-regression CI pass may land in Phase 4 hardening if needed.

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| G0 scope creep — TUI scaffold > 1 week | Split into G0-A (scaffold) + G0-B (wiring + patterns doc) at the end of writing-plans. |
| `quicklook` composite plugin breaks under split | Split formally acknowledged in §4.1 (G2 base + G4A GPU). Each sub-delivery is independently testable. |
| `processlist` perf regression (G5) | Mandatory perf check at G5. If > 20% regression, study a shared sampler or TTL cache; do not merge until under threshold. |
| CVE-2026-35587 SSRF in `ip` | Mitigation co-shipped in G4B. PR description must list which checks are wired. Reviewed against §8 of the architecture document. |
| Weekly `develop → develop-v5` merge conflicts | Rebase systematique at PR start. Conflicts on `glances/outputs/glances_curses.py` (v4) vs `glances_curses_v5.py` are unlikely since they're separate files. |
| `alert` v4 plugin ≠ `alerts_v5.py` engine | G7 plugin `alert` is a presentation layer reading `alerts.get_history()`. Scope confirmed at G7 start, not now. |
| Tests v4 break when `help` / `profiler` are absent in v5 registry | Soft removal: v4 files stay until Phase 4 cleanup. `test_plugin_help.py` and `test_plugin_profiler.py` remain green because they exercise the v4 code untouched. |
| TUI parity perceived as subjective | Reviewer ownership documented in `SKILL-plugin.md`. If side-by-side screenshots are inconclusive, the reviewer asks for a text-fixture diff (escape hatch in §7). |

## 9. Deliverables (recap)

### 9.1 Per PR
- Code + tests + NEWS.rst (if breaking change visible).
- Screenshot v4 vs v5 in PR description.

### 9.2 At the end of G0
- `glances/outputs/glances_curses_v5.py` + `tests/test_curses_v5.py`.
- `docs/architecture/tui-v4-rendering-patterns.md` (new).
- `docs/architecture/glances-v5-architecture-decisions.md` — §1.4 + §3.2
  updates.
- `.claude/skills/SKILL-plugin.md` extended.

### 9.3 At the end of Phase 2 (all groups merged)
- `docs/architecture/glances-v5-architecture-decisions.md` — §10 Phase 2
  marked done with the list of migrated plugins.
- `NEWS.rst` — consolidated 5.0.0-aN entry (breaking changes, datamodel
  diff per plugin).
- `MEMORY.md` auto-memory — note on Phase 2 status update.

## 10. Approval

Sections 1–9 approved by the user on 2026-05-12. The next step is
`writing-plans` on G0 (TUI v5 scaffold + Phase 1 plugin wiring). Subsequent
groups (G1, G2, …) receive their own writing-plans pass at the start of
their slot.
