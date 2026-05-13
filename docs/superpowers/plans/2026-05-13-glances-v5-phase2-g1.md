# Glances v5 Phase 2 — G1 (per-plugin TUI renderers for the 4 remaining Phase 1 plugins) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Replicate v4's `msg_curse()` layout for the 4 remaining Phase 1 plugins (mem, load, network, percpu) by adding a `render_curses_v5.py` module to each, using the discovery mechanism shipped in G0.5 (commit `<G0.5-discovery-hash>`).

**Background — what already exists (G0.5):**
- `glances/outputs/curses_renderer_v5.py::build_frame` discovers `glances.plugins.<name>.render_curses_v5.render` and uses it when present; falls back to the generic 2-col / N-col table renderer otherwise. Commit `5601322c`.
- `glances/plugins/cpu/render_curses_v5.py` — first reference implementation (3-col × 4-row grid). Commit `76f53646`.
- `tests/test_plugin_cpu_render_curses_v5.py` — testing pattern.
- `docs/architecture/tui-v4-rendering-patterns.md` — v4 per-plugin catalogue (read this BEFORE writing each renderer).
- Convention documented in `.claude/skills/SKILL-plugin.md` (commit `d2d338fe`).

**Hard rule** (per project memory `feedback-tui-v5-must-mirror-v4`): read the v4 `msg_curse()` in `glances/plugins/<name>/__init__.py` AND the catalogue entry BEFORE writing the v5 renderer. Don't design "generic/clean" — replicate v4.

---

## File Structure

| Path | Responsibility | Action |
|---|---|---|
| `glances/plugins/mem/render_curses_v5.py` | TUI block: title + percent + 4-line two-column byte stats grid (matches v4) | Create |
| `glances/plugins/load/render_curses_v5.py` | TUI block: title + core count + 3-line "N min" load average list | Create |
| `glances/plugins/network/render_curses_v5.py` | TUI block: per-interface Rx/Tx table with bit/byte unit toggling and rate/cumul modes | Create |
| `glances/plugins/percpu/render_curses_v5.py` | TUI block: transposed grid (CPU rows × field columns) with CPU* overflow row | Create |
| `tests/test_plugin_mem_render_curses_v5.py` | unit tests for mem renderer | Create |
| `tests/test_plugin_load_render_curses_v5.py` | unit tests for load renderer | Create |
| `tests/test_plugin_network_render_curses_v5.py` | unit tests for network renderer | Create |
| `tests/test_plugin_percpu_render_curses_v5.py` | unit tests for percpu renderer | Create |

Each task is **one commit** so the visual progression is reviewable plugin-by-plugin.

---

## Task 1: mem `render_curses_v5.py`

**Reference:**
- v4 source: `glances/plugins/mem/__init__.py::msg_curse`
- Catalogue: `docs/architecture/tui-v4-rendering-patterns.md` §mem

**Expected v4-equivalent output:**

```
MEM   74.2%      active   5.3G
total          14.9G   inactive   2.1G
avail           4.8G   buffers  120.0M
free            3.1G   cached    1.4G
```

- Line 1: `MEM` (HEADER) + trend arrow (` ↑` / ` ↓` / `  ` — optional, defer if no trend data) + `{:>7.1%}` percent (HEADER decoration from `_levels.percent`) + `active` label + `auto_unit(active)`.
- Line 2: `total` + `auto_unit(total)`     |     `inactive` + `auto_unit(inactive)`
- Line 3: `avail` (or `used`) + `auto_unit(available)`  |  `buffers` + `auto_unit(buffers)`
- Line 4: `free` + `auto_unit(free)`        |     `cached` + `auto_unit(cached)`

Two-column grid for lines 2–4 (col 1: 15 chars, col 2: 16 chars in v4).

**Steps:**

- [ ] **Step 1: Read v4 source + catalogue.** Required by `feedback-tui-v5-must-mirror-v4`.
- [ ] **Step 2: Write failing tests.** `tests/test_plugin_mem_render_curses_v5.py` — assertions on:
  - First row contains `MEM` (HEADER role) and the formatted percent value.
  - First row contains `active` label and its formatted bytes value.
  - 4-row output.
  - Lines 2–4 form a 4-cell row (2 label/value pairs).
  - Per-column alignment (same width across rows).
  - `avail` shown when `available` in payload, otherwise `used`.
  - Empty payload → 1 header-only row.
- [ ] **Step 3: Implement** `glances/plugins/mem/render_curses_v5.py`. Reuse `_cell_for_field` and the `_align_grid` pattern from cpu.
- [ ] **Step 4: `make test-v5`** — all green.
- [ ] **Step 5: Smoke render** (no curses): print the rendered rows to stdout, eyeball against v4.
- [ ] **Step 6: Commit** with a message replicating the v4 layout in the body.

---

## Task 2: load `render_curses_v5.py`

**Reference:**
- v4 source: `glances/plugins/load/__init__.py::msg_curse`
- Catalogue: `docs/architecture/tui-v4-rendering-patterns.md` §load

**Expected v4-equivalent output:**

```
LOAD  4core
1 min     0.72
5 min     1.45
15 min    1.23
```

- Line 1: `LOAD` (HEADER, 4 chars) + trend arrow (defer) + ` 4core` (cpucore prefix).
- Lines 2–4: each load average (`min1`, `min5`, `min15`) as `{:7} {:>6.2f}` (label left-padded 7 chars, value right 6 chars).
- **Irix mode** (`args.disable_irix` + cores > 0): values shown as `{value / cores * 100:>5.1f}%` instead. Defer this — v5 doesn't have the flag yet; comment out / no-op.
- Color rule: each line uses `_levels[minN]` decoration. `min1`/`min5`/`min15` independent thresholds.

**Steps:**

- [ ] **Step 1: Read v4 source + catalogue.**
- [ ] **Step 2: Failing tests** — `tests/test_plugin_load_render_curses_v5.py`:
  - 4-row output (header + 3 load averages).
  - `LOAD` HEADER, `4core` (or `Ncore`) shown.
  - Three label rows: `1 min`, `5 min`, `15 min`.
  - Load average colors come from `_levels[minN]`.
  - Empty payload → header-only.
  - `cpucore` is **internal** — appears as `Ncore` suffix on header, not as its own row.
- [ ] **Step 3: Implement** `glances/plugins/load/render_curses_v5.py`. Note: `cpucore` is already flagged `internal: True` and excluded by the generic renderer — but here we *use* it in the header, just don't render it as its own row.
- [ ] **Step 4–6:** test, smoke, commit.

---

## Task 3: network `render_curses_v5.py`

**Reference:**
- v4 source: `glances/plugins/network/__init__.py::msg_curse`
- Catalogue: `docs/architecture/tui-v4-rendering-patterns.md` §network

**Expected v4-equivalent output (default — rate, two columns, bits):**

```
NETWORK              Rx/s    Tx/s
eth0                1.2Mb   256Kb
wlp0s20f3            45Kb    12Kb
lo                      0       0
```

- Header line: plugin name (left-aligned to `name_max_width`) + `Rx/s` + `Tx/s` (right-aligned, 7 chars each).
- One row per interface (filtered upstream: `is_up=True`, non-zero rate, has previous sample).
- `name_max_width = max_width - 12` (need to receive `max_width` from the painter or hardcode for now — see step 1).
- Default unit: **bits/s** (multiply by 8, suffix `b`). `--byte` toggles to bytes (suffix `''`).
- Cumulative mode (`--network-cumul`): show total bytes transferred, header labels become `Rx`/`Tx`.
- Sum mode (`--network-sum`): single 14-char column `Rx+Tx/s` or `Rx+Tx`.
- Color from `_levels[<if_name>][bytes_recv|bytes_sent]`.

**Steps:**

- [ ] **Step 1: Read v4 source + catalogue.** Especially the `auto_unit` for bit/byte computation.
- [ ] **Step 2: Decide on `max_width` and mode args plumbing.** v5 `render()` currently takes only `(payload, fields_desc)`. Options:
  - (a) extend the signature to `render(payload, fields_desc, max_width=None, args=None)` and propagate from `build_frame` / `TuiV5._paint`.
  - (b) hardcode `name_max_width=20`, default mode = rate-bits-2col (G1 scope).
  Pick (b) for G1, leave (a) as a follow-up TODO in a code comment.
- [ ] **Step 3: Failing tests** — `tests/test_plugin_network_render_curses_v5.py`:
  - Header `NETWORK` + `Rx/s` + `Tx/s`.
  - One row per interface in `data`.
  - Interface name left-aligned, rates right-aligned.
  - Rate values use bit-unit (`b` suffix) by default.
  - Color comes from per-interface `_levels`.
  - Empty `data` → header-only.
- [ ] **Step 4: Implement** `glances/plugins/network/render_curses_v5.py`.
- [ ] **Step 5–6:** test, smoke, commit.

---

## Task 4: percpu `render_curses_v5.py`

**Reference:**
- v4 source: `glances/plugins/percpu/__init__.py::msg_curse`
- Catalogue: `docs/architecture/tui-v4-rendering-patterns.md` §percpu

**Expected v4-equivalent output (Linux, 4 cores, quicklook disabled):**

```
CPU    user system iowait   idle    irq   nice  steal  guest
CPU0   12.5%   3.2%   0.5%  83.8%   0.0%   0.0%   0.0%   0.0%
CPU1    8.1%   2.0%   0.1%  89.8%   0.0%   0.0%   0.0%   0.0%
CPU2   15.0%   4.5%   1.2%  79.3%   0.0%   0.0%   0.0%   0.0%
CPU3    6.3%   1.8%   0.0%  91.9%   0.0%   0.0%   0.0%   0.0%
```

**Transposed layout** — fields as columns, CPU cores as rows. Distinct from every other plugin.

- Header construction depends on OS (`define_headers_from_os()`): Linux gets `[user, system, iowait, idle, irq, nice, steal, guest]`, etc.
- When quicklook disabled (G1 assumption): prepend `total` column + `CPU` title.
- CPU id label: `CPU{id}` for id<10, else `{id:4}` (5 chars, left-padded).
- Each value: `{:6.1f}%` (7 chars including `%`).
- `max_cpu_display` (default 4): show top-N by `total`, then `CPU*` overflow row with means of the rest.

**Steps:**

- [ ] **Step 1: Read v4 source + catalogue.** percpu's layout is fundamentally different.
- [ ] **Step 2: Confirm v5 percpu payload shape.** `payload["data"]` is a list of dicts, one per CPU, with the same `user/system/...` fields. Each item has its own `_levels`.
- [ ] **Step 3: Failing tests** — `tests/test_plugin_percpu_render_curses_v5.py`:
  - Header row contains column labels (`user`, `system`, ...).
  - One data row per CPU.
  - `CPUn` label first cell of each data row.
  - Per-CPU value coloring from `_levels[cpu_id][field]`.
  - `max_cpu_display=2` collapses extras into `CPU*` mean row.
  - Empty payload → header-only.
- [ ] **Step 4: Implement** `glances/plugins/percpu/render_curses_v5.py`. Read `max_cpu_display` from config when available; default to 4.
- [ ] **Step 5–6:** test, smoke, commit.

---

## Task 5: Update the v4 catalogue + NEWS.rst

- [ ] **Step 1:** Mark each migrated plugin in `docs/architecture/tui-v4-rendering-patterns.md` with a "✅ v5 renderer at `glances/plugins/<name>/render_curses_v5.py`" footer line under each section.
- [ ] **Step 2:** Append a NEWS.rst entry under `5.0.0a3 (Phase 2 G1)`:
  - mem, load, network, percpu now ship per-plugin TUI renderers replicating v4 `msg_curse()` layouts.
  - Visual parity contract enforced via the catalogue.
- [ ] **Step 3:** Commit.

---

## Task 6: Final sweep

- [ ] **Step 1:** `make test-v5` — all green.
- [ ] **Step 2:** `make test` — v4 non-regression check, all green.
- [ ] **Step 3:** `make lint && make format` — clean.
- [ ] **Step 4:** `make run-v5` — visual smoke test against v4 (side-by-side). Capture screenshots for the PR description.
- [ ] **Step 5:** Open PR, attach screenshots, request review.

---

## Wrap-up

After merge:
1. Update project memory: `project_v5_g1_per_plugin_renderers.md` — "Phase 2 G1 done: cpu/mem/load/network/percpu each have a `render_curses_v5.py` replicating v4 layout."
2. Subsequent plugin migrations (Phase 2 G2+) follow the same pattern: model_v5 first, then render_curses_v5 (if v4's layout requires it).
