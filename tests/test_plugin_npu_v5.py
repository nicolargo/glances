#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `npu` plugin (collection)."""

from __future__ import annotations

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.npu.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    return GlancesConfigV5()


class _FakeCard:
    def __init__(self, stats, available=True):
        self._stats = stats
        self._available = available
        self.disabled = False

    def is_available(self):
        return self._available

    def get_device_stats(self):
        return self._stats

    def disable(self):
        self.disabled = True
        self._available = False

    def exit(self):
        pass


class _BoomCard(_FakeCard):
    def get_device_stats(self):
        raise OSError("boom")


def _npu(npu_id="intel_1", name="NPU", load=45, freq=50):
    return {"npu_id": npu_id, "name": name, "load": load, "freq": freq, "mem": None}


def test_plugin_identity(store, config):
    p = PluginModel(store, config)
    assert p.plugin_name == "npu"
    assert p.IS_COLLECTION is True
    assert p._primary_key == "npu_id"


def test_fields_watched():
    fd = PluginModel.fields_description
    for key in ("load", "freq", "mem"):
        assert fd[key]["watched"] is True
    assert fd["npu_id"].get("primary_key") is True
    for key in ("freq_current", "freq_max", "temperature", "power", "name"):
        assert fd[key].get("internal") is True


@pytest.mark.asyncio
async def test_grab_stats_collects_available_cards(store, config, monkeypatch):
    p = PluginModel(store, config)
    # Plugin is default-disabled (mirrors v4 [npu] disable=True); enable it so
    # the collection path is exercised here.
    monkeypatch.setattr(p, "_is_enabled", lambda: True)
    p._backends = [_FakeCard(_npu("intel_1")), _FakeCard(_npu("amd_1"), available=False)]
    out = await p._grab_stats()
    assert [c["npu_id"] for c in out] == ["intel_1"]


@pytest.mark.asyncio
async def test_grab_stats_disables_card_on_error(store, config, monkeypatch):
    p = PluginModel(store, config)
    monkeypatch.setattr(p, "_is_enabled", lambda: True)
    boom = _BoomCard(_npu("rockship_1"))
    p._backends = [boom]
    out = await p._grab_stats()
    assert out == []
    assert boom.disabled is True


def test_npu_disabled_by_default(store, config):
    # Mirror v4 [npu] disable=True — no user config present here.
    p = PluginModel(store, config)
    assert p._is_enabled() is False


@pytest.mark.asyncio
async def test_grab_stats_empty_when_disabled(store, config):
    p = PluginModel(store, config)
    p._backends = [_FakeCard(_npu("intel_1"))]
    # default disabled -> collects nothing even with an available card
    assert await p._grab_stats() == []
