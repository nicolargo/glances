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


def _cfg_with(tmp_path, monkeypatch, body: str) -> GlancesConfigV5:
    """Real config object built from a `[percpu]` section body (mirrors
    `test_plugin_quicklook_v5.py::_cfg_with`)."""
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    xdg = tmp_path / "xdg"
    cfg_dir = xdg / "glances"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "glances.conf").write_text(body)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    return GlancesConfigV5()


# ---------------------------------------------------------- contract


def test_plugin_identity(store, config):
    plugin = PluginModel(store, config)
    assert plugin.plugin_name == "percpu"
    assert plugin.IS_COLLECTION is True


def test_cpu_number_is_primary_key(store, config):
    schema = PluginModel(store, config)._fields["cpu_number"]
    assert schema["primary_key"] is True


def test_displayed_columns_are_watched_for_colour_only(store, config):
    """v4 colours every percpu cell (`get_alert(cpu[stat], header=stat)`), but
    never logs it: watched, font colour only, and no alert ingestion."""
    plugin = PluginModel(store, config)
    watched = {name for name, schema in plugin._fields.items() if schema.get("watched")}
    assert watched == {"total", "user", "system", "idle", "iowait", "irq", "nice", "steal", "guest", "dpc", "interrupt"}
    assert all(plugin._fields[name]["prominent"] is False for name in watched)
    assert PluginModel.EMITS_ALERTS is False


def test_only_user_and_system_have_default_thresholds(store, config):
    """v4 `config.py` `set_default_cwc('percpu', 'user'|'system')` — 50/70/90."""
    fields = PluginModel(store, config)._fields
    defaults = {name for name, schema in fields.items() if schema.get("default_thresholds")}
    assert defaults == {"user", "system"}
    assert fields["user"]["default_thresholds"] == {"careful": 50.0, "warning": 70.0, "critical": 90.0}


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


async def test_levels_colour_user_and_system_by_default(store, config):
    plugin = PluginModel(store, config)
    with _patch_sampler([_core(user=75.0, system=10.0), _core(user=10.0, system=95.0)]):
        await plugin.update()
    levels = store.get("percpu")["_levels"]
    assert levels[0]["user"] == {"level": "warning", "prominent": False}
    assert levels[0]["system"]["level"] == "ok"
    assert levels[1]["system"]["level"] == "critical"
    # No default for the other columns: uncoloured until configured.
    assert "iowait" not in levels[0] and "total" not in levels[0]


async def test_configured_column_thresholds_colour_that_column(tmp_path, monkeypatch, store):
    config = _cfg_with(tmp_path, monkeypatch, "[percpu]\niowait_careful=1\niowait_warning=5\nuser_critical=60\n")
    plugin = PluginModel(store, config)
    with _patch_sampler([_core(user=65.0)]):  # _core: iowait=2.0
        await plugin.update()
    levels = store.get("percpu")["_levels"][0]
    assert levels["iowait"]["level"] == "careful"
    assert levels["user"]["level"] == "critical"


async def test_the_model_publishes_the_effective_thresholds(tmp_path, monkeypatch, store):
    """The `CPU*` mean row has no `_levels`: renderers grade it from these."""
    config = _cfg_with(tmp_path, monkeypatch, "[percpu]\nuser_warning=60\niowait_critical=20\n")
    plugin = PluginModel(store, config)
    with _patch_sampler([_core()]):
        await plugin.update()
    thresholds = store.get("percpu")["thresholds"]
    assert thresholds["user"] == {"careful": 50.0, "warning": 60.0, "critical": 90.0}
    assert thresholds["iowait"] == {"critical": 20.0}
    assert "idle" not in thresholds


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


def test_the_model_publishes_the_configured_cap(tmp_path, monkeypatch, store):
    """The key lives in the [percpu] section (v4 parity: v4 reads
    `config.get_int_value('percpu', 'max_cpu_display', 4)`)."""
    cfg = _cfg_with(tmp_path, monkeypatch, "[percpu]\nmax_cpu_display=2\n")
    model = PluginModel(store, cfg)
    assert model._read_max_cpu_display() == 2


async def test_max_cpu_display_reaches_the_payload_and_the_api(tmp_path, monkeypatch, store):
    """A collection plugin's `_grab_stats()` returns the bare item list, not a
    dict `_build_store_payload()` can merge extra keys into directly — unlike
    a scalar plugin (e.g. quicklook), which just adds the key to the dict
    `_grab_stats()` returns. So `max_cpu_display` can only reach the envelope
    through the `_add_metadata()` override, which `_build_store_payload()`
    merges in via `**self._metadata` for both plugin shapes alike. This test
    drives a real `update()` cycle to prove that path, not just the reader.
    """
    cfg = _cfg_with(tmp_path, monkeypatch, "[percpu]\nmax_cpu_display=2\n")
    plugin = PluginModel(store, cfg)
    with _patch_sampler([_core(), _core(), _core()]):
        await plugin.update()
    assert store.get("percpu")["max_cpu_display"] == 2
    # Declared `internal: True` in fields_description (unlike fs's
    # free_space), so it also survives into the REST/MCP view.
    assert plugin.get_api_payload()["max_cpu_display"] == 2


async def test_the_model_publishes_the_resolved_stat_fields(monkeypatch, store, config):
    """Final review, Important 3: the browser cannot resolve `sys.platform`,
    so the model — which can — publishes the resolved column order, the same
    shape `max_cpu_display` already uses. Linux order, per
    `render_curses_v5._os_headers()`: user, system, iowait, idle, irq, nice,
    steal, guest.
    """
    monkeypatch.setattr("glances.plugins.percpu.model_v5.sys.platform", "linux")
    plugin = PluginModel(store, config)
    with _patch_sampler([_core()]):
        await plugin.update()
    expected = ["user", "system", "iowait", "idle", "irq", "nice", "steal", "guest"]
    assert store.get("percpu")["stat_fields"] == expected
    # Declared `internal: True`, so it also survives into the REST/MCP view.
    assert plugin.get_api_payload()["stat_fields"] == expected


async def test_get_export_strips_internals_per_item(store, config):
    plugin = PluginModel(store, config)
    with _patch_sampler([_core()]):
        await plugin.update()
    exported = plugin.get_export()
    # `time_since_update` is on the envelope — never on individual items.
    for item in exported:
        assert "time_since_update" not in item
        assert all(not k.startswith("_") for k in item)
