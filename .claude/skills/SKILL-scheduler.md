# Skill: Glances v5 — Asyncio scheduler (`AsyncScheduler`)

The asyncio scheduler (`glances.scheduler_v5.AsyncScheduler`) is the
component that actually runs registered plugins concurrently. It owns one
`asyncio.Task` per plugin and calls `plugin.update()` at each plugin's
`refresh_time`.

Phase 0.6 ships **manual registration only** — auto-discovery of concrete
plugins lands when the first concrete plugin does (Phase 1+).

## Lifecycle

```python
import asyncio
from glances.config_v5 import GlancesConfigV5
from glances.scheduler_v5 import AsyncScheduler
from glances.stats_store_v5 import StatsStoreV5

store = StatsStoreV5()
config = GlancesConfigV5()

scheduler = AsyncScheduler(store, config)
scheduler.register(MemPlugin(store, config))
scheduler.register(NetworkPlugin(store, config), refresh_time=5.0)

# Blocks until cancelled.
await scheduler.run_forever()
```

To stop from another coroutine:

```python
await scheduler.stop()
```

`run_forever()` returns cleanly once `stop()` finishes.

## `refresh_time` precedence

When you call `scheduler.register(plugin, refresh_time=...)` the resolved
interval comes from the first match in this order:

1. Explicit `refresh_time=` argument
2. `[<plugin_name>] refresh_time = …` from `glances.conf`
3. `[global] refresh_time = …` from `glances.conf`
4. Hardcoded fallback: `2.0` seconds (matches v4 default)

Negative or zero values raise `ValueError` — the scheduler refuses
intervals that would busy-loop or block forever.

## Resilience

The scheduler is the second safety net for plugin failures:

| Layer | Behaviour |
|---|---|
| `GlancesPluginBase.update()` | Catches every exception, logs at WARNING, leaves the previous payload in the store |
| `AsyncScheduler._plugin_loop()` | Defensive try/except around `update()` — catches anything a future `update()` override might leak |
| `AsyncScheduler.run_forever()` | `asyncio.gather(*, return_exceptions=True)` — one task crashing never tears down the others |

In other words: **a single misbehaving plugin can never crash the
scheduler**. It can only stop producing fresh data for itself; every other
plugin keeps refreshing on its own cadence.

## Cancellation

`stop()` calls `task.cancel()` on every plugin loop and awaits clean
termination via `asyncio.gather(..., return_exceptions=True)` — the
`CancelledError` raised by cancellation is absorbed, no exception escapes.

## Registration guards

| Situation | Behaviour |
|---|---|
| `register()` called twice with the same plugin instance | `ValueError` |
| `register()` called while the scheduler is running | `RuntimeError` |
| `run_forever()` called with no registered plugins | `RuntimeError` |
| `run_forever()` called while already running | `RuntimeError` |

## What's deferred

- **Auto-discovery of concrete plugins** — Phase 1+ when concrete plugins land
- **Drift / phase compensation** (subtract update duration from sleep) — only if needed
- **Hot reload of `refresh_time`** — Phase 4 (architecture §1.2 / §2)
- **`export_refresh_time`** for exporters — Phase 1 with exporter base class
- **Per-plugin task supervision** beyond the gather safety net — only if real-world failure modes warrant

## Testing the scheduler

Test stack: `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`) +
`unittest.mock` (architecture decision §9). Style: pytest-native top-level
functions with fixtures and `assert` statements.

Pattern: register fake plugins with very short `refresh_time` (e.g.
`0.01`), `asyncio.create_task(scheduler.run_forever())`, sleep briefly,
`await scheduler.stop()`, then assert on the store and on per-plugin call
counters. See `tests/test_scheduler_v5.py` for reference fakes
(`FastPlugin`, `SlowPlugin`, `RaisingPlugin`).

## Module path

```
glances/scheduler_v5.py        # AsyncScheduler implementation
tests/test_scheduler_v5.py     # contract + smoke tests
```

The v4 scheduling model lives in `glances/main.py` / `glances/standalone.py`
and is **not modified**, **not imported**, **not subclassed** by v5.
