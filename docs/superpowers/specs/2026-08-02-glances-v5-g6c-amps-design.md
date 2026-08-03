# Glances v5 — G6C-amps design (amps)

**Date:** 2026-08-02
**Phase:** 2, group **G6C-amps** (order G0→G1→G2→G3→G4A→G4B→G5→G6A→G6B→**G6C-amps**→G6C→G7)
**Status:** design — decisions below are approved; awaiting spec review before plans.

## 1. Goal & scope

Port the v4 `amps` plugin (Application Monitoring Processes) to the Glances
v5 asyncio architecture.

`amps` was pulled out of G6B into its own cycle
(`2026-07-18-glances-v5-g6b-design.md` §8) because it is not a probe plugin
but a mini scheduler-of-plugins, with three axes no other plugin has:

1. **dynamic code loading** — `__import__` on a directory basename, with
   `glances/amps/` injected into the global `sys.path`;
2. **per-sub-component scheduling** — every AMP carries its own `Timer` and
   its own `refresh`;
3. **unbounded external I/O** — `subprocess.communicate()` /
   `check_output()` with no timeout at all (only the nginx AMP sets one),
   fired from one unmanaged, unpooled, un-joined thread per AMP per cycle.

This cycle settles all three, plus the carry-forward of CVE-2026-53925 /
GHSA-59fj-m2j6-hcxh to the AMP command surface.

Out of scope: `irq`, `cloud`, `mpp` (the rest of G6C) and `alert` (G7).

## 2. Global constraints (apply to every task)

- **Mirror v4**: read the v4 `msg_curse()` + grabber before writing the
  renderer/model; divergent "clean generic" layouts are regressions.
- **The v4 AMP contract is frozen** — third-party AMP scripts written for v4
  must keep working unmodified (§4.1).
- **Empty registry must stay valid** — no `[amp_*]` section, or every AMP
  disabled, yields an empty payload and no TUI block, not a crash.
- **Alerts fire on `warning`+ only**; `careful` is colour-only. `amps` emits
  none at all (§5.4).
- **Plugin titles and column headers are ALWAYS `ColorRole.HEADER`** — never
  escalate a header's colour from `_levels`.
- **No dead code**, no speculative config keys, surgical edits.
- **Do not touch `NEWS.rst`** during development (release-time only).
- **No commits/push/PR** — stage only.

## 3. File scope

**New**

| File | Content |
|---|---|
| `glances/amps_list_v5.py` | `AmpsListV5` — loader, per-AMP cadence, bounded execution |
| `glances/plugins/amps/model_v5.py` | `PluginModel(GlancesPluginBase[list])` — thin projection + levels |
| `glances/plugins/amps/render_curses_v5.py` | v4 `msg_curse` transposition |
| `tests/test_amps_list_v5.py` | loader / cadence / in-flight guard |
| `tests/test_plugin_amps_v5.py` | projection + level ladder |
| `tests/test_plugin_amps_render_curses_v5.py` | 3-column layout |

**Modified — additive only, default behaviour unchanged**

| File | Change |
|---|---|
| `glances/config_v5.py` | add `items()` and `get_float_value()` (§4.2) |
| `glances/secure.py` | `secure_popen(..., timeout=None)` (§6.1) |
| `glances/amps/amp.py` | `timeout()` accessor on `GlancesAmp` |
| `glances/amps/{default,systemv}/__init__.py` | forward `timeout=self.timeout()` to `secure_popen` |
| `glances/amps/systemd/__init__.py` | forward `timeout=` to `check_output` |
| `glances/amps/nginx/__init__.py` | `self.timeout() or 15` instead of the hardcoded 15 |
| `conf/glances.conf` | document the optional `timeout` key (commented) |
| `docs/aoa/amps.rst` | document the optional `timeout` key |
| `tests/test_amp_secure_popen.py` | cover the new `timeout` parameter |

**Reused verbatim**: `glances/amps/amp.py::GlancesAmp` (the class contract —
only the additive `timeout()` accessor is appended), and the four embedded
AMPs `default`, `nginx`, `systemd`, `systemv`.

**Untouched**: `glances/amps_list.py` (v4), `glances/plugins/amps/__init__.py`
(v4), `glances/plugins/plugin/base_v5.py`, `glances/outputs/curses_renderer_v5.py`.

## 4. Decisions taken before the design

### 4.1 The v4 AMP contract is kept verbatim

`GlancesAmp` stays the base class, `update(process_list)` stays
**synchronous**, `set_result()` stays the way an AMP publishes. v5 runs it
through `asyncio.to_thread`.

Rejected: a v5-native `async def update()` base (breaks every third-party
AMP — a documented extension point, `docs/aoa/amps.rst`), and a dual
contract with async detection plus a v4 fallback (two execution paths to
maintain and test for zero async consumer on day one — YAGNI).

Consequence: **`AmpsList` (v4) cannot be reused verbatim**, unlike
`ThreadScanner` / `FolderList` / `GlancesPortsList` in G6B. Its loader and
its runner are precisely what this cycle replaces. Only the AMP-facing
contract is frozen, not the orchestrator.

### 4.2 `GlancesConfigV5` gaps — same family as the G6B `get_value` fix

`GlancesAmp.load_config()` — reused verbatim — calls two v4 config methods
that `GlancesConfigV5` does not implement:

```python
for param, _ in config.items(amp_section):          # AttributeError
    try:
        self.configs[param] = config.get_float_value(amp_section, param)   # AttributeError
    except ValueError:
        self.configs[param] = config.get_value(amp_section, param).split(',')
```

**Decision:** add both to `glances/config_v5.py`, with **exact v4 semantics**.

- `items(section) -> list[tuple[str, Any]]` — the section's `(key, value)`
  pairs, empty list when the section is absent.
- `get_float_value(section, option, default=0.0) -> float` — returns
  `float(default)` when the option is **absent**, and `float(raw)` when it is
  present. The `float()` conversion **must raise `ValueError` on a
  non-numeric value** rather than falling back to the default: `load_config`
  depends on that exception to route string and comma-list values to the
  `except ValueError` branch. Swallowing it would turn every `regex=`,
  `command=` and `enable=` value into `0.0` — every AMP would silently break.

This mirrors the G6B decision on `get_value` (design §4): fix it once in the
config layer, never as a per-plugin shim.

`get_int_value` / `get_bool_value` are **not** added — no v5 caller needs
them, and speculative API is dead code.

### 4.3 Loading: qualified `importlib`, no `sys.path` mutation

`importlib.import_module(f"glances.amps.{name}")`, falling back to
`glances.amps.default` when the module does not exist — same drop location
for the user as v4 (`glances/amps/<name>/`), so no operator-visible change.

Rejected: v4's `sys.path.insert(1, amps_path)` + `__import__(basename)`. It
mutates the global import path for the whole process, so a section named
after a stdlib module (`[amp_email]` → `glances/amps/email/`) shadows that
module process-wide. Also rejected: a configurable external AMP directory —
not requested, YAGNI.

The AMP name is validated with `str.isidentifier()` before the import
attempt; a rejected name logs a warning and falls back to `default`.

### 4.4 Bounded execution: one run in flight per AMP

v4 spawns a thread per AMP **per cycle**, never joins it, and neither
`secure_popen` nor `check_output` carries a timeout. A command that hangs
therefore leaks one thread every `refresh` seconds, forever.

**Decision:** an AMP whose previous run is still in flight is **skipped** for
this cycle instead of being started a second time. Default behaviour is
unchanged — no command is ever interrupted — and the leak is bounded to one
thread per AMP instead of one per cycle.

An optional per-section `timeout=N` key is added on top, shipped **commented
out** so the default stays v4's (no timeout). See §6.1.

Rejected: a hard 30 s default timeout (silently kills legitimately slow
commands that worked in v4 — a breaking change), and `timeout = refresh`
(breaks any AMP whose command is slower than its own period, e.g.
`refresh=3` with a slow `dropbox status`).

### 4.5 Process list source: the `glances_processes` singleton

`AmpsListV5` reads `glances_processes.get_list()` — exactly v4, and already
the v5 precedent (`glances/plugins/processlist/model_v5.py::_grab_stats`
reads the same singleton). Read-only: it never triggers an engine refresh,
that remains `processcount`'s job.

The v4 coupling is inherited as-is: with `processcount` disabled the list is
empty, so regex-based AMPs match nothing.

Rejected: reading `store.get("processlist")`. The published payload has
already been through `[processlist] show/hide` filtering, so AMP matching
would silently change with a display setting, and `amps` would gain a
dependency on another disableable plugin.

### 4.6 Orchestration lives in a dedicated module

`glances/amps_list_v5.py` holds `AmpsListV5`; `model_v5.py` stays thin.
Follows the `*_v5.py` convention used throughout, leaves v4 untouched, and
keeps the runner testable without store/config plumbing.

Rejected: everything inside `model_v5.py` (mixes dynamic loading, scheduling
and projection in the module the plugin discovery imports — exactly the
entanglement that got `amps` pulled out of G6B), and sharing a single
`glances/amps_list.py` between v4 and v5 (every loader/runner change becomes
a regression risk for the 4.5.x branch still in production).

## 5. Plugin design

### 5.1 `AmpsListV5` — loader

Walk `config.sections()`, keep those starting with `amp_`; the AMP name is
the section name minus that prefix.

For each: validate the name, `import_module("glances.amps.<name>")` with
fallback to `glances.amps.default`, instantiate `module.Amp(name=name,
args=<shim>)`, then `amp.load_config(config)`.

The registry is an **instance** attribute. v4's `AmpsList.__amps_dict` is a
**class** attribute, so every instance shares one dict — an anti-pattern that
breaks test isolation and any future config reload.

The `regex` of each AMP is **compiled once at load time** and cached. v4
passes the pattern string to `re.search` for every process on every cycle;
with 500+ processes and several AMPs that is a measurable hot path.

`args` shim: `GlancesAmp.allow_operators()` reads
`getattr(self.args, 'disable_config_exec', False)`, and v5 has no argparse
object on the plugin side. `AmpsListV5` builds a minimal namespace from
`[global] disable_config_exec` — the key `main_v5` already overlays when
`--disable-config-exec` is passed (`main_v5.py:386-392`).

### 5.2 `AmpsListV5` — cadence and execution

Each AMP keeps its v4 `Timer` and `should_update()`. The plugin declares
`SCHEDULE_AT_GLOBAL_REFRESH = True`, so `update()` runs at the global
cadence while each AMP only fires when its own `[amp_x] refresh` has
elapsed — the v4 semantics, transposed exactly as `ports` does.

Per cycle, per **enabled** AMP, mirroring `AmpsList.update()` branch for
branch:

1. **No regex configured** (issue #1690): force the count to 0 and *run
   anyway* with an empty process list.
2. **Regex configured, at least one match**: `set_count(len(matching))`,
   then run with the matching list.
3. **Regex configured, no match**: `set_count(0)`, and if `countmin` is set
   and greater than 0, set the result to `"No running process"`. **The AMP
   is not run** — v4 does not run it either on this branch.

"Run" in 1 and 2 means: only if `amp.should_update()` fires **and** no run
is in flight for this AMP, launch `asyncio.to_thread(amp.update, matching)`
as a task recorded in an in-flight map; a done-callback clears the entry and
logs any exception. `_grab_stats` itself never awaits it.

The count is set **synchronously** on every cycle, outside the thread. It is
pure CPU (one regex sweep, no I/O) and v4 refreshes it every cycle too — it
spawns a thread whose first statement is `set_count`.

Note that v5 calls `amp.update()` directly, not `amp.update_wrapper()`,
because `set_count` and `should_update` are now decided by the caller.
That is contract-safe: `update()` is the method the AMP contract requires a
script to implement, `update_wrapper()` is v4 plumbing that no AMP overrides.

`_grab_stats()` never awaits an AMP run — it publishes whatever results the
AMPs have produced so far, exactly as `ports` publishes its partially-filled
scan list.

**Divergence (mechanism, not behaviour):** v4 spawns a thread even when the
timer has not fired, purely to set an integer. v5 sets it inline. Same
observable result, no thread churn.

**Bug fixed:** v4's `AmpsList._build_amps_list` assigns `ret` inside a `try`
and returns it unconditionally, so any `TypeError`/`KeyError` raised while
building the list turns into an `UnboundLocalError`. `AmpsListV5` returns an
empty list on that path.

### 5.3 `PluginModel` — projection

`IS_COLLECTION = True`, primary key `name`. Fields carried over from the v4
plugin unchanged: `name`, `result`, `refresh`, `timer`, `count`, `countmin`,
`countmax`, and `regex` (a **boolean**: "a regex is configured", used by the
renderer to decide whether the count column is shown).

`DISABLED_BY_DEFAULT = False` — v4 ships no `[amps]` section and the plugin
is active; every shipped `[amp_*]` carries `enable=false`, so nothing is
displayed out of the box. An empty list means `build_frame` renders no
block at all (no lonely header), which is v4 parity.

### 5.4 Levels

`_derived_parameters()` is **bespoke** — the level depends on `count`
compared against two *other* fields, which neither the numeric ladder nor
the categorical mapping of `base_v5.py` expresses. Same precedent as
`ports` (G6B §5.3): `base_v5.py` is NOT modified.

Transposition of v4 `AmpsPlugin.get_alert`:

| Condition | Level |
|---|---|
| `count` is `None` | no entry — unreachable in practice, `load_config` initialises `count` to 0 |
| `count > 0` and `countmin ≤ count ≤ countmax` | `ok` |
| `count > 0` otherwise | `warning` |
| `count == 0` and `countmin` absent or `0` | `ok` |
| `count == 0` and `countmin > 0` | `critical` |

`countmin`/`countmax` absent default to `count` itself (v4), which is what
makes an unconfigured AMP always `ok`.

The level is attached to the **`count`** field — the process count is what
alerts — and the renderer paints the *name* cell with it, as v4 does.
`prominent: False`: v4 colours the text only, never the background.

`EMITS_ALERTS = False`. v4 calls its own `get_alert()`, not
`get_alert_log()`: the level colours the TUI and is never written to the
event history nor dispatched to an action. Same family as `ports` and
`processlist`.

## 6. Security

### 6.1 `secure_popen(..., timeout=None)`

`glances/secure.py` gains an optional `timeout` parameter, threaded down to
`Popen.communicate(timeout=...)` with a kill on expiry. `None` is the
default, so **v4 behaviour is bit-for-bit unchanged**. It is what makes the
`[amp_x] timeout=N` key of §4.4 actually able to terminate a hung command
rather than merely refusing to start a second one.

The parameter is added to the shared v4 module rather than reimplemented in
a v5 runner: a second implementation of the same restricted grammar, on a
security-sensitive path, would inevitably drift.

### 6.2 The restricted grammar is preserved — do not align on `ShellAction`

`secure_popen` does **not** use a shell. It interprets exactly three
operators (`&&`, `|`, `>`) by splitting the string and wiring `Popen`
objects itself, so `;`, backticks and `$()` stay literal.

The v5 `ShellAction` (`glances/actions_v5/shell/__init__.py`) uses
`asyncio.create_subprocess_shell` instead. **Do not align `amps` on it.**
Doing so would make `;`, `$()` and backticks interpretable in `glances.conf`
where v4 does not interpret them — a widening of the CVE-2026-53925 attack
surface, not a simplification.

### 6.3 `--disable-config-exec` (CVE-2026-68519 family)

`GlancesAmp.allow_operators()` already implements the gate; it only lacked
an `args` object under v5, which §5.1's shim provides. Once wired, an
operator running `--disable-config-exec` gets AMP commands executed as a
single process with the three operators passed verbatim as arguments.

This closes the AMP half of the two "Carry forward (AMP …)" rows in
`docs/architecture/glances-v5-architecture-decisions.md` §CVE table
(CVE-2026-53925 and GHSA-59fj-m2j6-hcxh); the actions half is already done.
**Update those two rows** as part of this cycle.

### 6.4 stdlib shadowing

Dropped as a side effect of §4.3. Not a CVE, but a real vector: under v4 an
`[amp_email]` section makes `glances/amps/email/` shadow the stdlib `email`
module for the entire process.

## 7. TUI

`amps` is already listed in `RIGHT_SLOT` (`curses_renderer_v5.py:75-83`), so
**no orchestrator or layout change is needed** — only
`glances/plugins/amps/render_curses_v5.py`.

Transposition of v4 `msg_curse`: name column on 16 chars (coloured from the
`count` level), count column on 4 chars (blank when no regex is configured),
then the result. One `Row` per line of the result string; the name and count
cells appear on the first line only. An AMP whose `result` is `None` is
skipped entirely (v4 verbatim).

**Divergence:** v4 marks the result line `splittable=True`, allowing it to
wrap. The v5 `Cell` has no such attribute, so an over-long result line is
clipped by curses instead of wrapped. Adding wrapping to
`curses_renderer_v5.py` for a single caller is out of scope; log it as debt
if the manual smoke test shows it hurts.

**Divergence:** v4 hides the whole block when `args.disable_process`. v5 has
no such coupling — the AMP block does not depend on the process list being
displayed. `[amps] disable` is the control.

## 8. Testing

| File | Covers |
|---|---|
| `tests/test_amps_list_v5.py` | named-module load, `default` fallback, invalid name → fallback, `enable` gating, per-AMP cadence, in-flight guard, count refreshed every cycle, regex-less path (#1690), `"No running process"` when `countmin > 0`, `_build_amps_list` no longer raises `UnboundLocalError` |
| `tests/test_plugin_amps_v5.py` | field projection, the five level rules of §5.4, empty registry → `[]` |
| `tests/test_plugin_amps_render_curses_v5.py` | 3-column layout, multi-line result, count column hidden without regex, colour taken from the level |
| `tests/test_amp_secure_popen.py` (extended) | `timeout` kills on expiry; `timeout=None` changes nothing |
| `tests/test_config_v5.py` (extended) | `items()` on present/absent section; `get_float_value` default on absent option **and `ValueError` on a non-numeric value** |

The whole existing suite must stay green — run it before and after, and
report the count in the final review, as every previous group did.

## 9. Known limitation, stated not hidden

`asyncio.to_thread` is not cancellable. An AMP that blocks past its
`timeout` — or with no `timeout` configured — keeps its thread alive, and as
in v4 those threads are not daemons, so interpreter shutdown waits for them.
The in-flight guard bounds the leak to one thread per AMP instead of one per
cycle, which is the operational regression that matters. Going further would
require a dedicated bounded pool with forced termination: out of scope here,
and worth revisiting only if field reports justify it.

A second, related consequence of reusing `asyncio.to_thread`: it dispatches
to the event loop's single default `ThreadPoolExecutor`
(`max_workers = min(32, cpu_count + 4)` — 6 on a 2-vCPU box), which is shared
by ~41 other `to_thread` call sites across the v5 runtime, including
`AsyncScheduler.stop()`. The in-flight guard bounds AMPs to one parked thread
each, but several AMPs hung on a command with no `timeout` configured can
together occupy every worker in that pool: other plugins' `to_thread` calls
then queue behind them, the TUI stalls on stale data, and quitting can hang
because `scheduler.stop()` itself needs a free worker to run. Mitigation is
operational, not code: document that any AMP command touching a network
resource, a remote mount, or a daemon socket should set `timeout=` (see
`docs/aoa/amps.rst`). A dedicated executor for AMPs would close this
structurally but is the same out-of-scope tradeoff as the paragraph above.

## 10. Deliverables for the release changelog

- New optional config key `[amp_*] timeout` (shipped commented; default
  unchanged).
- Behaviour: one AMP execution in flight at a time (v4 started one per
  cycle unconditionally).
- Behaviour: long AMP result lines are clipped rather than wrapped.
- Fix: an AMP named after a stdlib module no longer shadows it.
- Fix: `UnboundLocalError` when the AMP process-match list fails to build.
- Fix: a broken `[amp_*]` section (bad `load_config()`) now skips only that
  AMP instead of aborting construction of the whole registry.
- Fix: an invalid `regex=` now disables that AMP with a warning instead of
  raising `re.error` out of the loader.
- Security: AMP commands honour `--disable-config-exec` under v5
  (CVE-2026-53925 / GHSA-59fj-m2j6-hcxh carry-forward closed).

## 11. Out of scope

- `irq`, `cloud`, `mpp` — the rest of G6C, separate cycle.
- `alert` — G7, and not a plugin port
  (`2026-08-01-glances-v5-g7-alert-design.md`).
- Any change to `base_v5.py` or `curses_renderer_v5.py`.
- Result-line wrapping in the TUI renderer.
- A configurable external AMP directory.
- `get_int_value` / `get_bool_value` on `GlancesConfigV5`.
