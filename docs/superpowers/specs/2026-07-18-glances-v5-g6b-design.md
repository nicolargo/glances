# Glances v5 — G6B design (connections + folders + ports)

**Date:** 2026-07-18
**Phase:** 2, group **G6B** (order G0→G1→G2→G3→G4A→G4B→G5→G6A→**G6B**→G6C→G7)
**Status:** design — decisions below are approved; awaiting spec review before plans.

## 1. Goal & scope

Port three v4 **probe** plugins to the Glances v5 asyncio architecture:
`connections`, `folders`, `ports`.

`amps` was in the original G6B group and has been **removed from it**. It is
not a plugin but a mini scheduler-of-plugins: it loads arbitrary Python via
`__import__` on a directory basename with `glances/amps/` injected into the
global `sys.path`; each AMP carries its own `Timer` cadence; and its leaf I/O
is unbounded blocking work (`subprocess.communicate()` and
`subprocess.check_output()` with **no timeout at all**; only the nginx AMP
sets one) fired from one unmanaged, unpooled, un-joined thread per AMP per
cycle. It also reaches directly into the `glances_processes` module singleton
and keeps its registry in a **class-level** `__amps_dict`. Those three axes —
dynamic code loading, per-sub-component scheduling, unbounded external I/O —
justify a dedicated design cycle. See §8.

## 2. Global constraints (apply to every task)

- **Mirror v4**: read the v4 `msg_curse()` + grabber before writing each
  renderer/model; divergent "clean generic" layouts are regressions.
- **Preserve v4 fetch behaviour** — reuse the v4 engines verbatim (§4). No
  rewrite of the scanning/timer machinery.
- All three render in the **LEFT sidebar** (34-char budget), not the MAIN
  column. All three are already listed in `LEFT_SLOT` in
  `curses_renderer_v5.py`, so **no orchestrator/layout change is needed**.
- **Empty registry / empty stats must stay valid** (no folder configured, no
  port configured, conntrack absent → empty payload, not a crash).
- **Alerts fire on `warning`+ only**; `careful` is colour-only.
- **Plugin titles and column headers are ALWAYS `ColorRole.HEADER`** — never
  escalate a header's colour from `_levels`. The alert lives on the value.
- **No dead code**, no speculative config keys, surgical edits.
- **Do not touch `NEWS.rst`** during development (release-time only).
- **No commits/push/PR** — stage only.
- Tests: `.venv/bin/python -m pytest`; lint `ruff check` + `ruff format`.

## 3. Common porting pattern

Each plugin provides, under `glances/plugins/<name>/`:

- `model_v5.py::PluginModel(GlancesPluginBase[...])` — `plugin_name`,
  `IS_COLLECTION`, `primary_key` (collections only), `fields_description`,
  `EMITS_ALERTS`, and `async _grab_stats()`.
- `render_curses_v5.py::render(payload, fields_desc=None, view=None)
  -> list[Row]` — built from `Cell` / `Row` / `ColorRole` / `_LEVEL_TO_ROLE`
  imported from `glances.outputs.curses_renderer_v5`.
- `tests/test_plugin_<name>_v5.py` and
  `tests/test_plugin_<name>_render_curses_v5.py`.

> **Note — this supersedes §3 of the G6A spec.** That section instructed
> renderers to colour their title via `title_role()`. `title_role`,
> `_max_prominent_level` and `_LEVEL_PRIORITY` have since been **removed**:
> v5 had invented title-colour escalation, which v4 never did. Do not
> reintroduce them; titles are plain `ColorRole.HEADER`.

Payload shapes:
- collection — `{"data": [...], **metadata, "_levels": {pk: {field: {level, prominent}}}}`
- scalar — `{**fields, "_levels": {field: {level, prominent}}}`

## 4. Decision: reuse the v4 engines verbatim

All three plugins do **blocking work on a cadence of their own**, which does
not map onto a single `_grab_stats()` coroutine driven by the scheduler:

- `folders` — `folder_size()` walks a directory tree, gated by one `Timer`
  **per folder** (`folder_N_refresh`, default 30 s inside `FolderList`).
- `ports` — a `ThreadScanner` thread sweeps every item; v4's `update()` only
  relaunches the thread when it is dead and returns immediately.
- `connections` — no self-cadence, but `psutil.net_connections()` is
  expensive on a host with a large socket table.

**Decision:** keep `FolderList` (`glances/folder_list.py`), `ThreadScanner`,
`GlancesPortsList` (`glances/ports_list.py`) and `GlancesWebList`
(`glances/web_list.py`) **unchanged**, and wrap them:

| Plugin | `_grab_stats()` |
|---|---|
| `folders` | `await asyncio.to_thread(FolderList.update, ...)` then `.get()`; per-folder gating stays inside the engine |
| `ports` | read the current list and relaunch `ThreadScanner` if it is dead — **non-blocking**, exactly as v4 |
| `connections` | `await asyncio.to_thread(...)` around `psutil.net_connections()` and the two `/proc` reads |

This mirrors the Option A decision taken on G6A for `containers`: no
performance regression, minimal diff, reviewable.

**Accepted consequences** (deliberate, do not "fix" during G6B):
- `ports` keeps its hardcoded `time.sleep(1)` between ICMP scans and its
  unpooled thread.
- `ports` honours only a global `refresh`; the per-port `refresh` field is
  stored but not used as a per-item timer (v4 behaviour).
- `FolderList.__default_refresh` is 30 while `conf/glances.conf` documents
  60. Left as-is; the plugin only reads `folder_N_refresh`.

## 4bis. Prerequisite: `GlancesConfigV5.get_value` must accept a missing default

`GlancesConfigV5.get_value(section, option, default: T)` requires `default`
and derives the coercion type from it. Every frozen v4 engine — `FolderList`,
`GlancesPortsList`, `GlancesWebList` — calls `get_value(section, option)` with
two arguments, the untyped `ConfigParser.get()` shape of v4. Today that raises:

```
TypeError: GlancesConfigV5.get_value() missing 1 required positional argument: 'default'
```

**Decision:** fix it once, in `glances/config_v5.py` — `default` becomes
optional and `default=None` returns the **raw, uncoerced** value (v4
semantics). Not a per-plugin shim: `folders` and `ports` both need it, and
`amps` will too in G6C, since `amps_list.py` uses the same v4 config API.
Three copies of the same workaround would violate DRY and would be rejected
at final review.

**Execution ordering:** this fix lands in **Task 1 of the `folders` plan**.
The `ports` plan depends on it and must NOT introduce its own adapter. Run the
`folders` plan first.

This extends the spec's file scope: `glances/config_v5.py` is modified.
`base_v5.py` remains untouched.

## 5. Per-plugin design

### 5.1 `connections` — SCALAR

The **only scalar** of the group. Do not model it by analogy with the other
two.

- `IS_COLLECTION = False`, no `primary_key`.
- Fields: `net_connections_enabled`, `nf_conntrack_enabled`, the per-status
  counters (`LISTEN`, `ESTABLISHED`), `initiated`, `terminated`,
  `nf_conntrack_count`, `nf_conntrack_max`, `nf_conntrack_percent`.
- **Not `prominent`.** `nf_conntrack_percent` declares `prominent: False`,
  so the `Tracked` row is colour-coded but never gets the highlighted badge.
  All three plugins of this group are `prominent: False` — none is a
  permanently-watched signal in the sense `cpu` or `mem` are. The renderer
  still forwards whatever `_levels` carries (and a test locks that), so the
  flag remains the single place the decision is expressed.
- **Watched:** `nf_conntrack_percent` only, via the standard numeric ladder
  (`nf_conntrack_percent_careful|warning|critical`, shipped as 70/80/90).
  The connection-state counters carry **no** thresholds — v4 parity.
- `EMITS_ALERTS = True` (standard `get_alert()` path).
- Disabled by default: `[connections] disable=True` ships in `conf/glances.conf`
  (documented as CPU-heavy).
- Feature flags **retry every cycle**. v4's `update()` opens with
  `stats = self.get_init_value()`, which returns a copy of
  `stats_init_value` — so both flags are reset to `True` on every cycle, and
  the `stats['*_enabled'] = False` writes only affect the dict being built,
  which is discarded next cycle. Mirror that: do **not** make the flags
  sticky.

  This matters beyond parity. A permanent failure (no permission for
  `psutil.net_connections()`) costs one caught exception per cycle — and
  `connections` ships disabled by default, so the cost is marginal. A sticky
  flag, by contrast, kills the plugin for the life of the process on a
  *transient* failure; the concrete case is the `nf_conntrack` module being
  loaded after Glances starts, which v4 picks up and a sticky v5 never would.

**Bug fix (approved):** `glances/plugins/connections/__init__.py:123` iterates
`self.initiated_states` where it must iterate `self.terminated_states`, so
`terminated` is today an exact copy of `initiated`, and `terminated_states`
(lines 79-86) is dead code. The v5 model uses `terminated_states`.

The displayed value changes by an order of magnitude: `initiated`
(SYN_SENT + SYN_RECV) is usually near zero, whereas the terminated states
(FIN_WAIT1/2, TIME_WAIT, CLOSE, CLOSE_WAIT, LAST_ACK) commonly number in the
hundreds. This is expected — it is the correct value.

A guard test must lock the two state lists as distinct, so the fix cannot
silently regress.

*Out of scope, tracked separately:* the same one-word fix on `develop` for
v4.x (§8).

**Render** (mirror v4): title `TCP CONNECTIONS`; then one row per status in
the fixed order `Listen`, `Initiated`, `Established`, `Terminated` (each
skipped when its key is absent); then, when conntrack is enabled and both
count and max are present, a `Tracked` row showing `count/max` — the **only**
coloured row, driven by the `nf_conntrack_percent` level.

### 5.2 `folders` — COLLECTION

- `primary_key = "path"`, up to 10 folders (`folder_1..10_path`).
- Config per folder: `folder_N_path`, `folder_N_refresh`,
  `folder_N_careful|warning|critical`, `folder_N_{level}_action`.
- **Watched:** `size`, with **per-folder** thresholds.

  The base's generic per-primary-key override does **not** apply here: it
  keys config as `<pk_value>_<field>_<level>` — i.e. `<path>_size_critical` —
  whereas v4 keys thresholds by **list position** (`folder_1_critical`),
  never by path. Override `_derived_parameters()` instead (the same hook
  `raid`, `sensors` and `wifi` already use) and call the base's pure
  `thresholds_v5.compute_level()` against each item's own embedded MB
  thresholds. This reuses the base's computation core without abusing its
  config-key convention.
- **Unit conversion is the trap:** thresholds are configured in **MB** and
  compared against a **byte** count (`int(threshold) * 1e6` in v4). The
  conversion must be explicit and covered by a test — a silent factor-1e6
  error would make every threshold either never or always fire.
- `errno != 0` takes priority over the size ladder, and **raises no alert**.

  v4 calls this state `ERROR`, which has no v5 `Level` equivalent. An earlier
  revision of this spec mapped it to `critical` to preserve the priority —
  that was **wrong**, and is corrected here. `folders` has
  `EMITS_ALERTS = True`, so `critical` made a missing directory fire a real
  alert into the history and dispatch actions. v4 does neither: `get_alert`
  returns the `ERROR` decoration, which `glances_colors.py:167` maps to
  `SELECTED` → `curses.A_BOLD` — bold, no colour, no alert.

  v5 mirrors that: the model emits **no `_levels` entry at all** for a
  broken folder (short-circuiting before the ladder, so it is never also
  `warning` on size), and the renderer draws the cell `bold=True` with
  `ColorRole.DEFAULT`, keeping the `?` prefix. Priority over the ladder is
  preserved; only the alertable half was the error.
- `EMITS_ALERTS = True` — v4 calls `glances_events.add(...)`.

**Render** (mirror v4): title `FOLDERS`; `name_max_width = max_width - 7`;
the path is truncated **from the left** with a leading `_` when too long
(keeping the significant tail); size via `auto_unit`, right-aligned on 9,
prefixed with `?` when `errno` is set.

### 5.3 `ports` — COLLECTION, bespoke thresholds

- `primary_key = "indice"` (`port_0`, `port_1`, `web_1`…). `port_0` is
  reserved for the auto-added default-gateway ICMP entry.
- One list holds **two item kinds**: port-scan items (`host`/`port`) and
  web items (`url`). The renderer and the level logic must branch on kind.
- Config: `refresh` (60), `timeout` (3), `port_default_gateway`, then
  `port_i_host|port|description|timeout|rtt_warning` and
  `web_i_url|description|timeout|rtt_warning|ssl_verify|http_proxy|https_proxy`.
- `EMITS_ALERTS = False` — v4 runs `get_p_alert(log=False)` and never writes
  to the event history.

  **Known consequence — per-port actions no longer fire.** v5's flag couples
  two things v4 keeps separate: `alerts_v5` returns early on
  `EMITS_ALERTS=False`, skipping *both* history ingestion *and* action
  dispatch, whereas v4's `get_p_alert` calls `manage_action()`
  unconditionally, `log=False` or not. So v4 `ports` fires configured actions
  while writing nothing to the history; v5 `ports` does neither.

  Setting `EMITS_ALERTS=True` would restore actions but would also start
  feeding the alert history, which v4 never does — an unreachable port would
  then appear in the alert panel continuously. Decoupling the two in
  `base_v5.py` was rejected as out of scope (the spec forbids touching it,
  and it would affect every v5 plugin).

  **Decision: keep `False`, document the loss** in `docs/aoa/ports.rst`
  alongside the action-key change of §5bis. Flag for the release changelog —
  this is the group's second breaking change.

**Decision — bespoke level logic, `base_v5.py` untouched.** `status` is a
heterogeneous union (`None` while scanning, `0` on timeout, a float RTT, or
an HTTP status code). Its level depends on the value's *type* as much as its
magnitude, so neither the numeric ladder nor the categorical mapping
describes it. The model computes `_levels` itself, mirroring v4:

| Kind | Condition | Level |
|---|---|---|
| port | `status is None` | careful (still scanning) |
| port | `status == 0` | critical (timeout / closed) |
| port | `status > rtt_warning` | warning |
| web | `status is None` | careful — **see below** |
| web | `status not in (200, 301, 302)` | critical |
| web | `elapsed > rtt_warning` | warning |

**Approved divergence — a URL being scanned is `careful`, not `critical`.**
v4's `get_default_ret_value` builds `{'ret': key for key, cond in conds.items() if cond}`,
reusing one dict key, so the **last truthy condition wins** in
CAREFUL → CRITICAL → WARNING order. For a web item with `status is None`,
CAREFUL is true but so is CRITICAL (`None not in [200, 301, 302]`), so v4
returns **CRITICAL**: every configured URL shows red for the whole first scan
window, and the CAREFUL branch is unreachable — dead code the project's rules
forbid. Port items are unaffected (`status is None` makes only CAREFUL true).

v5: `status is None` short-circuits to `careful` for **both** kinds. v4's
last-truthy-wins precedence is preserved for every non-`None` value, so an
HTTP 500 that is also slower than `rtt_warning` still resolves to `warning`,
not `critical`. Lock that precedence with a dedicated test.

That `base_v5.py` is **not modified** by G6B is an explicit review criterion.
A generic threshold hook was considered and rejected as speculative: `ports`
would be its only known caller.

**Render** (mirror v4): `name_max_width = max_width - 7`; description
left-aligned and truncated, then the status string right-aligned on 9 —
`Scanning`, `Open`, `Timeout`, `{:.0f}ms`, `Code {n}`, `Error`.

**No title row — deliberate, do not "fix".** `ports` sits directly under
`network` in `LEFT_SLOT`; the two belong to the same functional domain and
read as one continuous block. The missing title is that continuity, not an
oversight. (Contrast with `vms`, whose title row was removed to align it with
`containers` — same goal, opposite mechanism.)

## 5bis. Per-item threshold actions are keyed by field, not by index

v4 keyed per-item actions by the item's **position** in the config file —
`folder_1_critical_action`, and the same shape for `ports`. v5 keys every
action by the field it belongs to: `alerts_v5._lookup_action_value` reads
`<pk>_<field>_<level>_<action>`, `<field>_<level>_<action>` or
`<level>_<action>`. So the folder's own path replaces the index:

```ini
# v4
folder_1_critical_action=notify-send "disk full"
# v5
/media/backup_size_critical_action=notify-send "disk full"
```

This is a consequence of v5's global action-key redesign, not of this port.
`folders` and `ports` are simply the plugins where v4 used an index, so the
migration is not mechanical for them.

**Decision: document, do not translate.** The v4 key shape is not read, and
each plugin's `docs/aoa/*.rst` carries a `.. warning::` giving the old and
new forms side by side. A silently-ignored action is the failure mode being
documented against, so the note must state explicitly that the old key is
ignored. Flag this for the release changelog — it is a breaking change for
anyone who configured per-item actions.

## 6. Testing

Two files per plugin (model + renderer), plus these targeted guards:

- `connections`: `terminated_states` and `initiated_states` are distinct, and
  `terminated` is computed from the former.
- `connections`: the sticky disable flag does not retry after a failure.
- `folders`: MB→byte conversion fires the threshold at the right magnitude.
- `folders`: `errno` outranks the size ladder.
- `ports`: all four bespoke level cases, for both item kinds.
- `ports`: no title row (locks §5.3 against a well-meaning "fix").
- All three: empty configuration yields an empty payload, not a crash.

## 7. File structure

```
glances/plugins/connections/model_v5.py      (new)
glances/plugins/connections/render_curses_v5.py (new)
glances/plugins/folders/model_v5.py          (new)
glances/plugins/folders/render_curses_v5.py  (new)
glances/plugins/ports/model_v5.py            (new)
glances/plugins/ports/render_curses_v5.py    (new)
tests/test_plugin_{connections,folders,ports}_v5.py            (new)
tests/test_plugin_{connections,folders,ports}_render_curses_v5.py (new)
docs/aoa/{connections,folders,ports}.rst     (v5 note, as G6A did)
```

Unchanged and reused: `glances/folder_list.py`, `glances/ports_list.py`,
`glances/web_list.py`, `glances/plugins/plugin/base_v5.py`,
`glances/outputs/curses_renderer_v5.py`.

**One execution plan per plugin** (mirrors G4B and G6A) so review checkpoints
stay crisp.

## 8. Out of scope

- **`amps`** — its own design cycle (G6C-amps). It should reuse whatever
  per-item cadence understanding G6B produces, and must additionally settle:
  dynamic AMP loading (`__import__` + `sys.path` mutation → `importlib`?),
  timeouts on AMP subprocesses, and whether AMPs receive a process snapshot
  or keep reaching into the `glances_processes` singleton.
- **v4 fix for the `terminated` bug** on `develop` — one word, separate cycle.
- `ports`' ICMP `sleep(1)` and unpooled thread.
- Any change to `base_v5.py`.
