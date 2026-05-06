#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `percpu` plugin (collection)."""

from __future__ import annotations

from collections import namedtuple
from unittest.mock import AsyncMock, patch

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.percpu.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5

CpuTimesPercent = namedtuple(
    "scputimes_percent",
    ["user", "system", "idle", "nice", "iowait", "irq", "softirq", "steal", "guest", "guest_nice"],
)


def _core(idle: float = 70.0, user: float = 10.0, system: float = 15.0) -> CpuTimesPercent:
    return CpuTimesPercent(
        user=user,
        system=system,
        idle=idle,
        nice=0.5,
        iowait=2.0,
        irq=0.1,
        softirq=0.1,
        steal=0.0,
        guest=0.0,
        guest_nice=0.0,
    )


# ---------------------------------------------------------- fixtures


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


def _patch_sampler(per_core: list[CpuTimesPercent]):
    return patch(
        "glances.plugins.percpu.model_v5.sampler.get_per_core",
        new_callable=AsyncMock,
        return_value=per_core,
    )


# ---------------------------------------------------------- contract


def test_plugin_identity(store, config):
    plugin = PluginModel(store, config)
    assert plugin.plugin_name == "percpu"
    assert plugin.IS_COLLECTION is True


def test_cpu_number_is_primary_key(store, config):
    schema = PluginModel(store, config)._fields["cpu_number"]
    assert schema["primary_key"] is True


def test_no_field_is_watched(store, config):
    """Per-core fields must not trigger alerts (cpu plugin handles aggregate alerts)."""
    fields = PluginModel(store, config)._fields
    for name, schema in fields.items():
        if name == "time_since_update":
            continue
        assert schema.get("watched", False) is False, f"{name} should not be watched"


# ---------------------------------------------------------- update pipeline


async def test_update_writes_one_entry_per_core(store, config):
    plugin = PluginModel(store, config)
    with _patch_sampler([_core(idle=70.0), _core(idle=60.0), _core(idle=50.0), _core(idle=40.0)]):
        await plugin.update()
    payload = store.get("percpu")
    assert "data" in payload
    assert len(payload["data"]) == 4


async def test_update_assigns_cpu_number_zero_based(store, config):
    plugin = PluginModel(store, config)
    with _patch_sampler([_core(), _core(), _core()]):
        await plugin.update()
    data = store.get("percpu")["data"]
    assert [c["cpu_number"] for c in data] == [0, 1, 2]


async def test_total_is_one_hundred_minus_idle(store, config):
    plugin = PluginModel(store, config)
    with _patch_sampler([_core(idle=70.0), _core(idle=20.0)]):
        await plugin.update()
    data = store.get("percpu")["data"]
    assert data[0]["total"] == 30.0
    assert data[1]["total"] == 80.0


async def test_update_drops_undeclared_fields(store, config):
    """Each per-core entry is filtered against fields_description."""
    Future = namedtuple("scputimes_percent", ["user", "system", "idle", "future_attr"])
    fake = Future(user=10.0, system=15.0, idle=75.0, future_attr=99.9)

    plugin = PluginModel(store, config)
    with _patch_sampler([fake]):
        await plugin.update()
    data = store.get("percpu")["data"]
    assert "future_attr" not in data[0]


# ---------------------------------------------------------- _levels


async def test_levels_stay_empty_for_collection(store, config):
    """Collection-level alert computation is deferred to Phase 1.3."""
    plugin = PluginModel(store, config)
    with _patch_sampler([_core(), _core()]):
        await plugin.update()
    assert store.get("percpu")["_levels"] == {}


# ---------------------------------------------------------- export


async def test_get_export_returns_list(store, config):
    plugin = PluginModel(store, config)
    with _patch_sampler([_core(idle=70.0), _core(idle=60.0)]):
        await plugin.update()
    exported = plugin.get_export()
    assert isinstance(exported, list)
    assert len(exported) == 2
    assert exported[0]["cpu_number"] == 0
    assert exported[0]["total"] == 30.0


async def test_get_export_strips_internals_per_item(store, config):
    plugin = PluginModel(store, config)
    with _patch_sampler([_core()]):
        await plugin.update()
    exported = plugin.get_export()
    # `time_since_update` is on the envelope — never on individual items.
    for item in exported:
        assert "time_since_update" not in item
        assert all(not k.startswith("_") for k in item)
