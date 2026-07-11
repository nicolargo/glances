# Glances v5 — `sensors` plugin port (G4A-2) — Design

> Status: approved 2026-07-11. Next: writing-plans.
> Mirror-v4 rule applies: the TUI layout and alerting semantics replicate
> the v4 `sensors` plugin; divergences are enumerated in §8.

## Goal

Port the v4 `sensors` plugin to the Glances v5 asyncio architecture as an
auto-discovered collection plugin (LEFT sidebar), reusing the v4 hardware
grabbers untouched, and incorporate the **generalized per-prefix "mean"
option** (issue #3604 / PR #3605) gated per sensor type, default off.

## Architecture

- Collection plugin: `PluginModel(GlancesPluginBase[list])`,
  `IS_COLLECTION=True`, `primary_key="label"`.
- Auto-discovered via `sensors/model_v5.py::PluginModel` +
  `sensors/render_curses_v5.py::render`. Not in `TOP_SLOT` → `slot_for`
  returns LEFT sidebar.
- The four sub-types are merged into one flat list of sensor dicts. The v4
  hardware grabbers are reused verbatim as pure collectors.

## 1. Files

- **Create** `glances/plugins/sensors/model_v5.py` — `PluginModel`.
- **Create** `glances/plugins/sensors/render_curses_v5.py` — `render`.
- **Reuse unchanged** (import, do not rewrite):
  - `glances.plugins.sensors.__init__.GlancesGrabSensors` — psutil
    `sensors_temperatures()` / `sensors_fans()`.
  - `glances.plugins.sensors.sensor.glances_hddtemp.GlancesGrabHDDTemp` —
    hddtemp daemon socket client.
  - `glances.plugins.sensors.sensor.glances_batpercent.GlancesGrabBat` —
    batinfo/psutil battery grabber.
  - `glances.plugins.sensors.__init__.sensors_definition` — the
    kind → `{type, unit}` map.
- **Tests**: `tests/test_plugin_sensors_v5.py`,
  `tests/test_plugin_sensors_render_curses_v5.py`.

Note on the reused grabbers: `GlancesGrabSensors` is a standalone class
(constructed from a `sensors_definition` entry, `.init` flag, `.update()`
→ `list[dict]`). `GlancesGrabHDDTemp` and `GlancesGrabBat` are standalone
too (`.get()` / `.update()+.get()`). The v4 *plugin wrappers*
(`HddtempPlugin`, `BatpercentPlugin`) are **not** reused — they are
`GlancesPluginModel` subclasses needing `args`/`config`/`input_method`.
The v5 model instantiates the bare grab classes directly.

## 2. Model — collection

`_grab_stats` runs the blocking work in `asyncio.to_thread` and merges the
four sub-types into a single `list[dict]`. Each dict:
`{label, unit, value, warning, critical, type[, status]}`.

- `temperature_core` ← `GlancesGrabSensors(sensors_definition['cpu_temp'])`
- `fan_speed` ← `GlancesGrabSensors(sensors_definition['fan_speed'])`
- `temperature_hdd` ← `GlancesGrabHDDTemp(...).get()`
- `battery` ← `GlancesGrabBat(); .update(); .get()` (carries `status`)

Each sub-grabber is guarded independently — one raising must not drop the
others (mirrors the v4 `ThreadPoolExecutor` per-future try/except). Failures
logged at debug. `type` is stamped onto each row from the sub-type it came
from (v4 `__set_type`).

The hddtemp host/port come from config:
`config.get("sensors", "host", "127.0.0.1")`,
`config.get("sensors", "port", 7634)` (v4 `HddtempPlugin` read the same
`[sensors] host`/`port` keys).

Sub-grabber instances are built once in `__init__` and reused each cycle
(v4 parity — the grab classes are constructed once).

## 3. `fields_description`

| field | flags |
| --- | --- |
| `label` | `primary_key: True` |
| `type` | `internal: True` (one of temperature_core, fan_speed, temperature_hdd, battery) |
| `unit` | `internal: True` |
| `value` | `watched: True`, `prominent: False`, `watch_direction: "high"`, **no `default_thresholds`** (see §5) |
| `warning` | `internal: True` (hardware warning threshold, per row) |
| `critical` | `internal: True` (hardware critical threshold, per row) |
| `status` | `internal: True` (battery charge status; absent for other types) |

`value` is `watched` so the alert pipeline sees it, but it deliberately
carries **no** `default_thresholds`: the generic `_derived_parameters`
would otherwise compute a fixed ladder. §5 overrides `_derived_parameters`
to resolve per-row thresholds instead.

`prominent: False` — sensor alerts render as **coloured text only, no
background highlight** (a room full of warm sensors must not fill the block
with reverse-video blocks). The `_derived_parameters` override reads this
flag from the field schema (single source of truth) rather than hardcoding
it, so flipping `prominent` in `fields_description` is enough to change the
look.

## 4. Transform pipeline

Order inside `update()` (base class, never overridden):
`grab → base hide/show filter (on raw label) → _expand_parameters → _derived_parameters`.

`_transform` calls `_transform_gauge()` (no-op here) → `_expand_parameters()`
→ `_derived_parameters()`.

### 4a. `_expand_parameters` override: alias then mean fold

**Alias** (mirror v4 `read_alias`/`__get_alias`): config key
`[sensors] alias=<label>:<name>,<label2>:<name2>` — comma-separated
`label:alias` pairs, label matched case-insensitively. Relabel each row's
`label` to its alias if present. Applied **before** the fold so folding and
per-row threshold keys operate on the display label (v4 parity: v4 aliases
before `update_views`/mean). Escaped colons follow v4 `split_esc(i, ':')`
semantics.

**Generalized mean fold, per type** — for each type whose gate
`config.get("sensors", f"{type}_mean", False)` is true (default false),
where `type ∈ {temperature_core, fan_speed, temperature_hdd, battery}`:

1. Select that type's rows.
2. Group by **prefix** = label with a trailing number stripped:
   `re.sub(r"\s*\d+\s*$", "", label)`.
3. For every group with **≥2** members, replace them with one folded row:
   - `label = f"{prefix} (mean)"`
   - `value = int(mean_of_values + 0.5)` (PR #3605 rounding)
   - `unit`, `warning`, `critical`, `type`, `status` copied from the
     **first** matched row (PR #3605 mechanics).
   - Rows whose value is non-numeric (ERR/SLP/UNK strings) are excluded
     from the mean and pass through unchanged.
4. Singletons (unique prefix, or a lone numbered sensor) pass through.

After folding across all enabled types, sort the full list by
`natural_keys(label)` (v4 parity).

### 4b. `_derived_parameters` override: per-row bespoke levels — see §5

## 5. Thresholds / alerts (mirror v4)

`_derived_parameters` is overridden to build `self._levels` as a
collection dict `{label: {"value": {"level", "prominent"}}}`. For each row
with a numeric value, resolve `(warning, critical)` from a **single
coherent tier** — mirroring v4 `update_views`, which selects one tier by
the presence of a *critical* limit and reads BOTH thresholds from that same
tier (never mixing config critical with a hardware warning):

1. **Per-sensor config** (#2058): if `[sensors] <type>_<label>_critical` is
   set, that tier wins — `careful`/`warning` come from
   `[sensors] <type>_<label>_careful` / `_warning` (either may be unset → None).
2. **Per-type config** (#3049): else if `[sensors] <type>_critical` is set,
   that tier wins — `careful`/`warning` from `[sensors] <type>_careful` /
   `_warning`.
3. **Hardware system thresholds**: else the row's own `warning` /
   `critical` (from psutil `feature.high` / `feature.critical`). The
   hardware tier has **no** `careful` (psutil exposes only high/critical).

Level from the resolved triple: `value >= critical → critical`,
`warning is not None and value >= warning → warning`,
`careful is not None and value >= careful → careful`, else `ok`;
`critical is None` (no tier supplied one) → **no level entry** (DEFAULT: no
colour, no alert). A config threshold of `0` is a real limit, not "unset".
The full `careful`/`warning`/`critical` ladder is preserved so the shipped
default `[sensors] temperature_core_careful=45` keeps its v4 behaviour.

**Battery** computes the level on `100 - value` (v4:
`get_alert(current=100 - value, header='battery')`), so a *low* battery
alerts. fan_speed and hdd use the same numeric precedence as temperature.

`EMITS_ALERTS = True` (default) → a crossing (e.g. CPU temperature critical)
is ingested into the v5 alert history and shown in the footer alert list.

Implementation note: thresholds resolution reads `[sensors]` config keys
directly (`config.get(...)`), not the generic `read_thresholds`, because
the fallback source is per-row hardware data, not a static ladder. Rows
with ERR/SLP/UNK/NOS (non-numeric value) get no level.

## 6. Renderer (mirror v4 `msg_curse`)

`render(payload, fields_desc=None, view=None) -> list[Row]`, LEFT-sidebar
format (block ≤ 34 chars), following the `fs`/`diskio` renderer pattern.

- Header row: `SENSORS` (`title_role`, bold), left-justified to
  `_NAME_MAX_WIDTH`.
- One row per sensor (already sorted by the model):
  `label` truncated/padded to `_NAME_MAX_WIDTH = 20`, then the value cell
  right-justified to `_VALUE_COL_WIDTH = 14`.
- Value cell colour from `payload["_levels"][label]["value"]` via
  `_LEVEL_TO_ROLE`; `prominent` from the level entry.
- **String sentinels** `ERR`/`SLP`/`UNK`/`NOS` (from hddtemp): render the
  string right-justified, coloured by level (v4 parity).
- **Fahrenheit**: when `view.get("fahrenheit")` is set **and** `type` is
  neither `battery` nor `fan_speed`, convert with
  `glances.globals.to_fahrenheit`, unit `F`, no trend.
- **Battery trend**: append `↑`/`↓`/`✓` (charging/discharging/full) from
  `status` via the unicode helpers; only in Celsius/no-fahrenheit path
  (v4 parity).
- **Empty battery**: a battery row whose value is `[]`/empty is skipped
  (v4: `if type == battery and value == []: continue`).
- Numeric value formatted `f"{value:.0f}{unit}{trend}"`, right-justified.

The renderer receives `view` (already plumbed for gpu/npu:
`--fahrenheit` → `view["fahrenheit"]`).

## 7. Config surface (documented in `conf/glances.conf`)

```ini
[sensors]
# Rename a sensor label (comma-separated label:alias pairs)
#alias=core 0:CPU Package
# Fold same-prefix sensors of a type into "<prefix> (mean)" (default false)
#temperature_core_mean=true
#fan_speed_mean=true
#temperature_hdd_mean=true
#battery_mean=true
# Hide sensors by label (regex, comma-separated) — handled by the base
#hide=ambient.*
# Per-type / per-sensor thresholds (optional)
#temperature_core_critical=80
#temperature_core_core 0_critical=90
# hddtemp daemon
#host=127.0.0.1
#port=7634
```

Documenting new keys in `conf/glances.conf` is part of the port; do **not**
touch `NEWS.rst` (release-time only).

## 8. Accepted divergences from v4 (documented)

1. The base hide/show filter matches the **raw** primary-key label, applied
   before aliasing — v4 matched the raw label *or* its alias. Hiding by the
   alias name will not work. Minor; documented.
2. The mean fold requires **≥2** members per prefix group. The v4 PR #3605
   folded even a single matched `Core` sensor; for the generalized
   per-prefix rule, folding a lone sensor into `(mean)` is nonsensical, so
   singletons pass through.
3. No SNMP input method (consistent with all v5 plugins).
4. The v4 module side effects (global mutable state) are not ported — v5
   publishes to the stats store only.
5. When a tier supplies `critical` but no lower level, and value falls
   below `critical`, the level is `ok` (green) — v4
   `__get_system_thresholds` (hardware path) returned `DEFAULT` (no colour)
   in that sub-case. Colour differs; alert emission does not. A config
   threshold of `0` is honoured as a real limit (v4 `get_alert` treated `0`
   as falsy). The `careful`/`warning`/`critical` config ladder is fully
   supported (matching v4 `get_alert`).

## 9. Testing

**Model** (`tests/test_plugin_sensors_v5.py`):
- Plugin identity: `plugin_name == "sensors"`, `IS_COLLECTION is True`,
  `primary_key == "label"`.
- `_grab_stats` merges all four sub-types into the documented row shape
  (fakes/monkeypatch the four grabbers).
- One sub-grabber raising → the others still returned (partial list).
- Alias relabels a row before fold.
- Mean fold: enabled type folds a ≥2 prefix group to `<prefix> (mean)`
  with `int(mean+0.5)`; disabled type unchanged; singleton unchanged;
  non-numeric (ERR) excluded from the mean and passed through.
- Threshold precedence: per-sensor (#2058) beats per-type (#3049) beats
  hardware; hardware `warning`/`critical` drives level when no config;
  `critical is None` → no level.
- Battery level computed on `100 - value`.
- `EMITS_ALERTS is True`.

**Renderer** (`tests/test_plugin_sensors_render_curses_v5.py`):
- Header `SENSORS` present.
- Long label truncated to width.
- ERR/SLP/UNK rendered as string, coloured by level.
- Fahrenheit converts temperature rows only (not battery/fan) when
  `view["fahrenheit"]`.
- Battery trend arrow from `status`.
- Empty-value battery row skipped.
- Level colour resolved from `payload["_levels"][label]["value"]`.
