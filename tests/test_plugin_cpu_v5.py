#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `cpu` plugin (scalar)."""

from __future__ import annotations

from collections import namedtuple
from unittest.mock import AsyncMock, patch

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.cpu.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5

# psutil result stubs ------------------------------------------------------

CpuTimesPercent = namedtuple(
    "scputimes_percent",
    ["user", "system", "idle", "nice", "iowait", "irq", "softirq", "steal", "guest", "guest_nice"],
)

CpuStats = namedtuple("scpustats", ["ctx_switches", "interrupts", "soft_interrupts", "syscalls"])


def _agg(idle: float = 70.0, system: float = 15.0, user: float = 10.0, steal: float = 0.0) -> CpuTimesPercent:
    return CpuTimesPercent(
        user=user,
        system=system,
        idle=idle,
        nice=0.5,
        iowait=2.0,
        irq=0.1,
        softirq=0.1,
        steal=steal,
        guest=0.0,
        guest_nice=0.0,
    )


def _stats(ctx: int = 12_000) -> CpuStats:
    return CpuStats(ctx_switches=ctx, interrupts=2_000, soft_interrupts=1_000, syscalls=0)


# ---------------------------------------------------------- fixtures


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


def _config_with(tmp_path, monkeypatch, body: str) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    xdg = tmp_path / "xdg"
    cfg_dir = xdg / "glances"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "glances.conf").write_text(body)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    return GlancesConfigV5()


def _patch_sampler(agg=None, stats=None, cpu_count: int = 4):
    """Patch the module-level sampler used by cpu/model_v5.py.

    Returns an ExitStack — usable as a `with` block — that wires
    `get_aggregate`, `get_stats` and `cpu_count` to deterministic values
    for the duration of the test.
    """
    from contextlib import ExitStack

    # Reset the cached cpu_count on the module-level singleton so the
    # patched psutil.cpu_count is honoured for this test.
    from glances.cpu_sampler_v5 import sampler

    sampler._cpu_count = None

    stack = ExitStack()
    stack.enter_context(
        patch(
            "glances.plugins.cpu.model_v5.sampler.get_aggregate",
            new_callable=AsyncMock,
            return_value=agg if agg is not None else _agg(),
        )
    )
    stack.enter_context(
        patch(
            "glances.plugins.cpu.model_v5.sampler.get_stats",
            new_callable=AsyncMock,
            return_value=stats if stats is not None else _stats(),
        )
    )
    # cpu_count is a property on the singleton; patch the underlying
    # psutil call so the sampler computes the desired value lazily.
    stack.enter_context(patch("glances.cpu_sampler_v5.psutil.cpu_count", return_value=cpu_count))
    return stack


# ---------------------------------------------------------- contract


def test_plugin_identity(store, config):
    plugin = PluginModel(store, config)
    assert plugin.plugin_name == "cpu"
    assert plugin.IS_COLLECTION is False


def test_total_is_watched_prominent(store, config):
    schema = PluginModel(store, config)._fields["total"]
    assert schema["watched"] is True
    assert schema["prominent"] is True


def test_system_user_dpc_are_watched_non_prominent(store, config):
    fields = PluginModel(store, config)._fields
    for name in ("system", "user", "dpc"):
        assert fields[name]["watched"] is True, name
        assert fields[name]["prominent"] is False, name


def test_iowait_is_watched_prominent(store, config):
    """iowait surfaces as prominent — sustained I/O wait is worth highlighting."""
    schema = PluginModel(store, config)._fields["iowait"]
    assert schema["watched"] is True
    assert schema["prominent"] is True


def test_steal_is_watched_non_prominent_with_strict_thresholds(store, config):
    schema = PluginModel(store, config)._fields["steal"]
    assert schema["watched"] is True
    assert schema["prominent"] is False
    # Strict — any non-trivial steal is worth surfacing (level only, not prominent).
    assert schema["default_thresholds"]["critical"] == 30.0


def test_ctx_switches_is_rate_watched_with_absolute_thresholds(store, config):
    """``ctx_switches`` is watched with **absolute** thresholds (not per-core).

    Diverges from v4 doc (``50000 * cpucore``) — the v4 fallback chain
    silently never resolves the default, so v4 ships effectively no
    threshold. v5 ships a real system-wide scheduler-pressure signal.
    """
    schema = PluginModel(store, config)._fields["ctx_switches"]
    assert schema["rate"] is True
    assert schema["watched"] is True
    assert schema["prominent"] is False
    assert "normalize_by" not in schema
    assert schema["default_thresholds"] == {"careful": 10000.0, "warning": 15000.0, "critical": 20000.0}


def test_interrupts_and_soft_interrupts_and_syscalls_are_rate_only(store, config):
    fields = PluginModel(store, config)._fields
    for name in ("interrupts", "soft_interrupts", "syscalls"):
        assert fields[name].get("rate") is True, name
        assert fields[name].get("watched", False) is False, name


# ---------------------------------------------------------- update pipeline


async def test_update_writes_aggregate_fields(store, config):
    plugin = PluginModel(store, config)
    with _patch_sampler():
        await plugin.update()
    payload = store.get("cpu")
    assert payload["user"] == 10.0
    assert payload["system"] == 15.0
    assert payload["idle"] == 70.0
    # total = 100 - idle (single source of truth, no extra psutil call)
    assert payload["total"] == 30.0
    assert payload["cpucore"] == 4


async def test_update_drops_undeclared_psutil_fields(store, config):
    """psutil fields not declared in fields_description are stripped."""

    class WeirdNamedTuple(tuple):
        # Simulate a future psutil attribute we don't know about.
        @property
        def some_future_field(self) -> float:
            return 99.9

    plugin = PluginModel(store, config)
    with _patch_sampler():
        await plugin.update()
    payload = store.get("cpu")
    assert "some_future_field" not in payload


async def test_first_cycle_strips_rate_fields(store, config):
    """Counter fields (ctx_switches, interrupts, ...) are absent on the first cycle."""
    plugin = PluginModel(store, config)
    with _patch_sampler():
        await plugin.update()
    payload = store.get("cpu")
    # `rate: True` fields stripped — no previous sample to diff against.
    assert "ctx_switches" not in payload
    assert "interrupts" not in payload
    assert "soft_interrupts" not in payload
    assert "syscalls" not in payload


async def test_second_cycle_computes_ctx_switches_rate(store, config, monkeypatch):
    """Second cycle: ctx_switches becomes a per-second rate."""
    plugin = PluginModel(store, config)

    fake_now = [100.0]
    import glances.plugins.plugin.base_v5 as base_module

    monkeypatch.setattr(base_module.time, "monotonic", lambda: fake_now[0])

    with _patch_sampler(stats=_stats(ctx=10_000)):
        await plugin.update()  # cycle 1 — ctx_switches absent

    fake_now[0] = 102.0  # +2 s elapsed
    with _patch_sampler(stats=_stats(ctx=10_500)):
        await plugin.update()  # cycle 2

    payload = store.get("cpu")
    # delta = 500 over 2 s = 250 events/s
    assert payload["ctx_switches"] == 250.0


# ---------------------------------------------------------- _levels


async def test_total_level_uses_default_thresholds(store, config):
    plugin = PluginModel(store, config)
    with _patch_sampler(agg=_agg(idle=20.0, user=50.0, system=30.0)):
        await plugin.update()
    payload = store.get("cpu")
    # total = 100 - 20 = 80 → between warning (70) and critical (90) → warning
    assert payload["total"] == 80.0
    assert payload["_levels"]["total"] == {"level": "warning", "prominent": True}


async def test_steal_strict_thresholds(store, config):
    """`steal=20` exceeds warning (15) but not critical (30)."""
    plugin = PluginModel(store, config)
    with _patch_sampler(agg=_agg(steal=20.0)):
        await plugin.update()
    assert store.get("cpu")["_levels"]["steal"] == {"level": "warning", "prominent": False}


async def test_ctx_switches_level_uses_absolute_thresholds(store, config, monkeypatch):
    """Absolute thresholds (10k/15k/20k) — no per-core normalisation.

    `ctx_switches` is a system-wide scheduler-pressure signal; the core
    count does not factor in.
    """
    plugin = PluginModel(store, config)

    fake_now = [100.0]
    import glances.plugins.plugin.base_v5 as base_module

    monkeypatch.setattr(base_module.time, "monotonic", lambda: fake_now[0])

    with _patch_sampler(stats=_stats(ctx=0), cpu_count=4):
        await plugin.update()

    fake_now[0] = 101.0  # +1 s — ctx rate = 16_000/s → warning (≥15_000, <20_000)
    with _patch_sampler(stats=_stats(ctx=16_000), cpu_count=4):
        await plugin.update()

    payload = store.get("cpu")
    assert payload["ctx_switches"] == 16_000.0
    assert payload["_levels"]["ctx_switches"] == {"level": "warning", "prominent": False}


async def test_ctx_switches_level_ok_at_typical_desktop_rate(store, config, monkeypatch):
    """Typical desktop ctx rate (~4k/s) must stay at level ``ok`` — regression
    guard against the Phase 1.2 default that produced spurious CRITICAL on
    every idle desktop because thresholds were normalised by cpucore.
    """
    plugin = PluginModel(store, config)

    fake_now = [100.0]
    import glances.plugins.plugin.base_v5 as base_module

    monkeypatch.setattr(base_module.time, "monotonic", lambda: fake_now[0])

    with _patch_sampler(stats=_stats(ctx=0), cpu_count=8):
        await plugin.update()

    fake_now[0] = 101.0  # +1 s — ctx rate = 4_000/s, well below careful=10_000
    with _patch_sampler(stats=_stats(ctx=4_000), cpu_count=8):
        await plugin.update()

    payload = store.get("cpu")
    assert payload["_levels"]["ctx_switches"]["level"] == "ok"


async def test_user_config_overrides_total_threshold(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[cpu]\ntotal_warning=85\n")
    plugin = PluginModel(store, config)
    with _patch_sampler(agg=_agg(idle=20.0)):
        await plugin.update()
    # total = 80, override warning to 85 → still careful (default 50)
    assert store.get("cpu")["_levels"]["total"]["level"] == "careful"


# ---------------------------------------------------------- export


async def test_get_export_strips_internals_and_levels(store, config):
    plugin = PluginModel(store, config)
    with _patch_sampler():
        await plugin.update()
    exported = plugin.get_export()
    assert "_levels" not in exported
    assert "time_since_update" not in exported
    assert exported["total"] == 30.0
