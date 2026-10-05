#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `gpu` plugin (collection)."""

from __future__ import annotations

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.gpu.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    return GlancesConfigV5()


class _FakeBackend:
    def __init__(self, cards):
        self._cards = cards

    def get_device_stats(self):
        return self._cards

    def exit(self):
        pass


class _BoomBackend:
    def get_device_stats(self):
        raise OSError("no device")

    def exit(self):
        pass


def _card(gpu_id="nvidia0", name="GeForce", mem=40, proc=30, temp=55):
    return {
        "key": "gpu_id",
        "gpu_id": gpu_id,
        "name": name,
        "mem": mem,
        "proc": proc,
        "temperature": temp,
        "fan_speed": 20,
    }


def test_plugin_identity(store, config):
    p = PluginModel(store, config)
    assert p.plugin_name == "gpu"
    assert p.IS_COLLECTION is True
    assert p._primary_key == "gpu_id"


def test_fields_watched_and_internal():
    fd = PluginModel.fields_description
    for key in ("proc", "mem", "temperature"):
        assert fd[key]["watched"] is True
        assert fd[key]["watch_direction"] == "high"
        assert set(fd[key]["default_thresholds"]) == {"careful", "warning", "critical"}
    assert fd["gpu_id"].get("primary_key") is True
    assert fd["name"].get("internal") is True
    assert fd["fan_speed"].get("internal") is True
    assert fd["fan_speed"].get("watched", False) is False


def test_gpu_temperature_thresholds_mirror_v4():
    t = PluginModel.fields_description["temperature"]["default_thresholds"]
    assert t == {"careful": 60.0, "warning": 70.0, "critical": 80.0}


@pytest.mark.asyncio
async def test_grab_stats_concatenates_backends(store, config):
    p = PluginModel(store, config)
    p._backends = [
        _FakeBackend([_card("nvidia0", "A")]),
        _FakeBackend([_card("amd0", "B")]),
    ]
    out = await p._grab_stats()
    assert [c["gpu_id"] for c in out] == ["nvidia0", "amd0"]


@pytest.mark.asyncio
async def test_grab_stats_survives_backend_failure(store, config):
    p = PluginModel(store, config)
    p._backends = [_BoomBackend(), _FakeBackend([_card("amd0", "B")])]
    out = await p._grab_stats()
    assert [c["gpu_id"] for c in out] == ["amd0"]


@pytest.mark.asyncio
async def test_grab_stats_empty_when_no_backend(store, config):
    p = PluginModel(store, config)
    p._backends = []
    assert await p._grab_stats() == []


class _ExitSpy(_FakeBackend):
    def __init__(self, calls, error=None):
        super().__init__([])
        self._calls = calls
        self._error = error

    def exit(self):
        self._calls.append(self)
        if self._error:
            raise self._error


def test_stop_calls_every_backend_exit_even_if_one_raises(store, config):
    """v4 `exit()` closes each card API (nvmlShutdown...) on shutdown; one
    failing must not leave the others open."""
    calls = []
    p = PluginModel(store, config)
    p._backends = [_ExitSpy(calls, OSError("nvml")), _ExitSpy(calls)]
    p.stop()
    assert calls == p._backends


def test_build_backends_skips_a_constructor_that_raises(monkeypatch):
    """v5 form of v4's None backend: a vendor whose init fails is left out."""
    from glances.plugins.gpu import model_v5
    from glances.plugins.gpu.cards import nvidia

    def boom():
        raise RuntimeError("no driver")

    monkeypatch.setattr(nvidia, "NvidiaGPU", boom)
    names = [type(b).__name__ for b in model_v5._build_backends()]
    assert names == ["AmdGPU", "IntelGPU", "ArmGPU"]
