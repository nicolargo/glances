#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the v5 raid plugin model."""

from __future__ import annotations

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.raid import model_v5 as raid_mod
from glances.plugins.raid.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    return GlancesConfigV5()


def test_plugin_identity(store, config):
    p = PluginModel(store, config)
    assert p.plugin_name == "raid"
    assert p.IS_COLLECTION is True
    assert p._primary_key == "name"


def test_fields_description_flags():
    fd = PluginModel.fields_description
    assert fd["name"]["primary_key"] is True
    # RAID level / status / components / config are internal metadata.
    for key in ("type", "status", "components", "config"):
        assert fd[key].get("internal") is True
        assert fd[key].get("watched", False) is False
    # Disk counters are exportable but not watched (levels are bespoke).
    for key in ("used", "available"):
        assert fd[key].get("internal", False) is False
        assert fd[key].get("watched", False) is False


def test_emits_alerts_true():
    # Deliberate divergence from v4 (colour-only): degraded/inactive RAID
    # is a real incident and must feed the alert pipeline.
    assert PluginModel.EMITS_ALERTS is True


_MD0 = {
    "type": "raid1",
    "status": "active",
    "used": 2,
    "available": 2,
    "components": {"sda1": "0", "sdb1": "1"},
    "config": "UU",
}
_MD1 = {
    "type": "raid5",
    "status": "active",
    "used": 3,
    "available": 4,
    "components": {"sdc1": "0", "sdd1": "1", "sde1": "2"},
    "config": "UUU_",
}


class _FakeMdStat:
    """Stand-in for pymdstat.MdStat — returns a fixed name-keyed arrays dict."""

    _arrays: dict = {}

    def get_stats(self):
        return {"arrays": self._arrays}


@pytest.mark.asyncio
async def test_grab_flattens_and_injects_name(store, config, monkeypatch):
    fake = type("F", (_FakeMdStat,), {"_arrays": {"md0": dict(_MD0), "md1": dict(_MD1)}})
    monkeypatch.setattr(raid_mod, "MdStat", fake)
    p = PluginModel(store, config)
    rows = await p._grab_stats()
    by_name = {r["name"]: r for r in rows}
    assert set(by_name) == {"md0", "md1"}
    assert by_name["md0"]["type"] == "raid1"
    assert by_name["md0"]["used"] == 2
    assert by_name["md1"]["available"] == 4
    # The original array dict must carry a `name` key now (primary key).
    assert by_name["md0"]["name"] == "md0"


@pytest.mark.asyncio
async def test_grab_import_error_returns_empty(store, config, monkeypatch):
    monkeypatch.setattr(raid_mod, "MdStat", None)
    p = PluginModel(store, config)
    assert await p._grab_stats() == []


@pytest.mark.asyncio
async def test_grab_runtime_failure_returns_empty(store, config, monkeypatch):
    class _Boom(_FakeMdStat):
        def get_stats(self):
            raise OSError("cannot read /proc/mdstat")

    monkeypatch.setattr(raid_mod, "MdStat", _Boom)
    p = PluginModel(store, config)
    assert await p._grab_stats() == []


def _levels(p, rows):
    p._stats = rows
    p._derived_parameters()
    return p._levels


def _array(name, type_, status, used, available):
    return {
        "name": name,
        "type": type_,
        "status": status,
        "used": used,
        "available": available,
        "components": {},
        "config": "",
    }


def test_level_raid0_is_ok(store, config):
    # raid0 has no redundancy; v4 raid_alert short-circuits to OK.
    p = PluginModel(store, config)
    lv = _levels(p, [_array("md0", "raid0", "active", 2, 2)])
    assert lv["md0"]["status"]["level"] == "ok"


def test_level_inactive_is_critical(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_array("md0", "raid1", "inactive", 2, 2)])
    assert lv["md0"]["status"]["level"] == "critical"


def test_level_degraded_is_warning(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_array("md0", "raid5", "active", 3, 4)])
    assert lv["md0"]["status"]["level"] == "warning"


def test_level_healthy_is_ok(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_array("md0", "raid1", "active", 2, 2)])
    assert lv["md0"]["status"]["level"] == "ok"


def test_level_none_when_counts_missing(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_array("md0", "raid1", "active", None, 2)])
    assert "md0" not in lv  # no threshold source -> DEFAULT (no entry)


def test_level_prominent_false(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_array("md0", "raid1", "inactive", 2, 2)])
    assert lv["md0"]["status"]["prominent"] is False
