# Skill: Glances v5 — Authoring a plugin (`GlancesPluginBase[T]`)

Use the v5 plugin base class (`glances.plugins.plugin.base_v5.GlancesPluginBase`)
for any new plugin in `develop-v5`. It lives next to the v4 base class
(`glances/plugins/plugin/model.py`), which is kept untouched during the
transition. Concrete v4 plugins under `glances/plugins/` are migrated one
by one.

## Two flavours

| Flavour | Type parameter | Examples | Store payload |
|---|---|---|---|
| Scalar | `GlancesPluginBase[dict]` | cpu, mem, load | `{**stats, **metadata, "_levels": {...}}` |
| Collection | `GlancesPluginBase[list]` | network, fs, containers | `{"data": [...], **metadata, "_levels": {...}}` |

The flavour is also carried at runtime by the `IS_COLLECTION` class
attribute — Python erases the `T` type parameter at runtime, so
`IS_COLLECTION` is the source of truth for branching code in the base class.

## Minimal scalar plugin

```python
from glances.plugins.plugin.base_v5 import GlancesPluginBase

import psutil
import asyncio


class MemPlugin(GlancesPluginBase[dict]):
    plugin_name = "mem"
    IS_COLLECTION = False

    fields_description = {
        "percent": {
            "description": "Usage percentage.",
            "unit": "percent",
            "label": "MEM",
            "history": True,
            "thresholds": {"careful": 50.0, "warning": 70.0, "critical": 90.0},
        },
        "total": {
            "description": "Total physical memory.",
            "unit": "bytes",
            "label": "total",
        },
    }

    async def _grab_stats(self) -> dict:
        vm = await asyncio.to_thread(psutil.virtual_memory)
        return {"percent": vm.percent, "total": vm.total}
```

That's it. The base class handles everything else.

## Minimal collection plugin

```python
class NetworkPlugin(GlancesPluginBase[list]):
    plugin_name = "network"
    IS_COLLECTION = True

    fields_description = {
        "interface_name": {
            "description": "Interface name.",
            "unit": "string",
            "primary_key": True,
        },
        "rx": {"description": "Bytes received.", "unit": "bytespers"},
        "tx": {"description": "Bytes sent.",     "unit": "bytespers"},
    }

    async def _grab_stats(self) -> list:
        counters = await asyncio.to_thread(psutil.net_io_counters, pernic=True)
        return [
            {"interface_name": iface, "rx": c.bytes_recv, "tx": c.bytes_sent}
            for iface, c in counters.items()
        ]
```

## The `update()` pipeline (architecture §3.1)

Implemented once in the base class. **Never override.**

```
update()
├── self._stats_previous = self._stats
├── self._stats = await _grab_stats()           ← only mandatory plugin hook
├── _validate_stats_type()                       ← guard against wrong type
├── _add_metadata()                              ← time_since_update, etc.
├── _transform()                                 ← pipeline of 4 sub-steps
│   ├── _transform_gauge()      (optional override — counter→rate)
│   ├── _expand_parameters()    (optional override — split compound fields)
│   ├── _derived_parameters()   (optional override — derived + _levels)
│   └── _remove_parameters()    (final — strip undeclared / internal keys)
└── store.set(plugin_name, build_payload())
```

A plugin overrides only the steps specific to its data model (e.g.
`_transform_gauge()` for network rate computation, `_expand_parameters()`
for `cpu_times` → `user/system/iowait`).

### Resilience

Any exception inside the pipeline is logged at `WARNING` level and
**swallowed**. The asyncio gather loop must never crash because of a single
plugin. The store is **not** updated for that cycle — the previous payload
stays in place (stale handling lands in Phase 3).

## `fields_description` schema (architecture §3.2)

| Key | Type | Notes |
|---|---|---|
| `description` | str | Used by `/api/5/<plugin>/info` and `--api-doc` |
| `unit` | str | `bytes`, `percent`, `bytespers`, `seconds`, `string`, … |
| `label` | str | Compact label for TUI/WebUI (replaces v4 `short_name`) |
| `history` | bool | Min/max/mean tracked when `True` (replaces v4 `mmm`) |
| `watched` | bool | If `True`, this field gets a `_levels` entry computed each cycle. Default `False`. |
| `watch_direction` | `"high"` / `"low"` | Threshold direction. `"high"` (default) alerts on `value >= threshold`; `"low"` alerts on `value <= threshold` (e.g. fs free). |
| `prominent` | bool | When `True`, the field is rendered with **background highlight** (TUI/WebUI) and every level transition is tagged `prominent: True` in the alert event feed. Replaces v4 `_log` flag. Default `True` for watched fields. |
| `default_thresholds` | dict | `{"careful": …, "warning": …, "critical": …}` — plugin-author defaults. Overridable per-level via `glances.conf [<plugin>] careful=N` (or `<field>_careful=N` for multi-watched plugins). |
| `normalize_by` | str | Optional. Name of another field whose value divides this field before threshold comparison: `level = compute_level(value / stats[normalize_by], …)`. Used for per-core normalisation (`load.min15` ÷ `cpucore`, `cpu.ctx_switches` ÷ `cpucore`). Falls back to `1` when the divisor is missing or zero. |
| `rate` | bool | When `True`, the field is a cumulative counter; the base class converts it to a per-second rate via `_transform_gauge` (`(current - previous) / time_since_update`). On the first cycle the field is **absent** from the payload (no previous sample). Counter wrap or reboot clamps to `0.0`. |
| `primary_key` | bool | Marks the join key for `_levels` indexing in collection plugins |
| `exportable` | bool | Defaults to `True`. Set `False` for internal fields. |

`_levels` payload shape (architecture §3.3): each entry is a nested dict
carrying both the level and the prominence flag.

```python
"_levels": {"percent": {"level": "warning", "prominent": True}}
```

Consumers (TUI, WebUI, REST clients, `GlancesAlerts`) read both fields
from the same payload — no extra round-trip to `/api/5/<plugin>/info`
needed for alert rendering.

The base class injects `time_since_update` (with `exportable: False`) into
every plugin's `_fields` automatically — do not redeclare it.

Fields not declared in `fields_description` are **stripped** by
`_remove_parameters()`. Undeclared psutil fields never reach the store or
the API.

## Consumer access patterns

| Consumer | Method | Notes |
|---|---|---|
| REST API | `plugin.get_stats()` | Lockless read of the full store payload |
| Exporters | `plugin.get_export()` | **Only** permitted access path (architecture §7.2) |
| TUI thread | `plugin.get_stats()` | Lockless read, runs in a separate thread |

`get_export()` strips `_*` keys and fields with `exportable: False`. For
collection plugins it returns a `list[dict]` (the unwrapped `data` array),
not the dict envelope.

## Counter-to-rate fields (`rate: True`)

Plugins consuming psutil cumulative counters (cpu ctx_switches, network
bytes_recv, …) declare those fields with `rate: True`. The base class's
`_transform_gauge` walks every such scalar field and replaces the
cumulative value with `(current - previous) / time_since_update`.

```python
"ctx_switches": {
    "description": "Number of context switches per second.",
    "unit": "number",
    "rate": True,
    "watched": True,
    "prominent": True,
    "default_thresholds": {"careful": 50.0, "warning": 70.0, "critical": 90.0},
    "normalize_by": "cpucore",          # threshold compared against rate / cpucore
}
```

Behaviour:

- **First cycle** — the rate field is **absent** from the payload (no
  previous sample to diff against). Consumers must accept absence.
- **Counter wrap or reboot** — clamped to `0.0`, never negative.
- **Pipeline order** — `_transform_gauge` runs before `_derived_parameters`,
  so `normalize_by` and `_levels` see the per-second rate, not the raw
  counter.
- **Collection plugins** — per-item rates land in Phase 1.3 alongside
  the `network` plugin.

## Sharing psutil calls between sibling plugins (samplers)

When two plugins consume the same psutil source — `cpu` ↔ `percpu`,
or future `network` aggregate ↔ per-interface — pull the psutil call
into a shared sampler module so the cost is paid once per refresh
window, not twice. See architecture §3.7. First instance:
`glances/cpu_sampler_v5.py` exposes a module-level `sampler` singleton
that both `cpu/model_v5.py` and `percpu/model_v5.py` import. TTL-based
caching (default `1.0 s`) plus an `asyncio.Lock` for serialised access.

## What's deferred (out of scope for new plugins right now)

- **Collection `_levels` indexing by primary key** — Phase 1.3 (`network` plugin)
- **Collection rate fields** (per-item `_transform_gauge`) — Phase 1.3
- **`GlancesAlerts` ingestion of `_levels`** (stateful tracking, history feed) — Phase 1.4
- **Min/max/mean history** — Phase 2
- **Stale data handling** (`"stale": true`) — Phase 3 (remote client)
- **`msg_curse()` / `update_views()`** — rejected (architecture §3.6)
- **SNMP** — not ported to v5 (architecture §10)

## Testing a plugin

Test stack: `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`) +
`unittest.mock` (architecture decision §9). Style: pytest-native top-level
functions with fixtures and `assert` statements.

Pattern: instantiate the plugin against a real `StatsStoreV5` and
`GlancesConfigV5`, mock `_grab_stats()` to return a deterministic payload,
call `await plugin.update()`, assert on the store payload or
`plugin.get_export()`.

`tests/test_plugin_base_v5.py` provides reference fakes
(`FakeScalarPlugin`, `FakeCollectionPlugin`) demonstrating the pattern.

## Module path

```
glances/plugins/plugin/base_v5.py    # v5 base class (next to v4 model.py)
glances/plugins/plugin/model.py      # v4 base class — untouched
tests/test_plugin_base_v5.py         # v5 base class unit tests
```

Concrete plugin layout for Phase 1+ is decided when the first plugin lands
(likely `glances/plugins/<name>/v5.py` or `glances/plugins/<name>_v5.py`).

The v4 modules in `glances/plugins/` are **not modified**, **not
imported**, **not subclassed** by v5. The two base classes live side by
side in `glances/plugins/plugin/` but share no code.
