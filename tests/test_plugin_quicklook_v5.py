#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the v5 quicklook plugin model."""

from __future__ import annotations

from unittest.mock import mock_open

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.quicklook.model_v5 import PluginModel, _collect_sync, _cpu_name
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    # v5 idiom (mirrors tests/test_plugin_load_v5.py): real config object
    # with the system config path redirected to an empty tmp file.
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    return GlancesConfigV5()


def test_plugin_identity(store, config):
    p = PluginModel(store, config)
    assert p.plugin_name == "quicklook"
    assert p.IS_COLLECTION is False


def test_fields_description_keys():
    fd = PluginModel.fields_description
    for key in ("cpu", "mem", "swap", "load"):
        assert fd[key]["unit"] == "percent"
        assert fd[key].get("watched") is True
    # Render-support fields are internal + not watched (never level-computed).
    for key in ("percpu", "cpu_name", "cpu_hz", "cpu_hz_current", "cpu_log_core", "cpu_phys_core"):
        assert fd[key].get("internal") is True
        assert fd[key].get("watched", False) is False


@pytest.mark.asyncio
async def test_grab_stats_shape(store, config, monkeypatch):
    """_grab_stats returns the documented scalar shape with a percpu list."""
    p = PluginModel(store, config)

    class _Sample:
        idle = 80.0

    class _FakeSampler:
        cpu_count = 4

        async def get_aggregate(self):
            return _Sample()

        async def get_per_core(self):
            return [_Sample(), _Sample()]

    import glances.plugins.quicklook.model_v5 as mod

    monkeypatch.setattr(mod, "sampler", _FakeSampler())
    monkeypatch.setattr(
        mod,
        "_collect_sync",
        lambda: {
            "mem": 42.0,
            "swap": 10.0,
            "load": 25.0,
            "cpu_log_core": 4,
            "cpu_phys_core": 2,
            "cpu_name": "Test CPU",
            "cpu_hz_current": 2_000_000_000,
            "cpu_hz": 3_000_000_000,
        },
    )

    stats = await p._grab_stats()
    assert stats["cpu"] == 20.0  # 100 - idle(80)
    assert stats["mem"] == 42.0
    assert stats["swap"] == 10.0
    assert stats["load"] == 25.0
    assert isinstance(stats["percpu"], list) and len(stats["percpu"]) == 2
    assert stats["percpu"][0] == {"cpu_number": 0, "total": 20.0}
    assert stats["cpu_name"] == "Test CPU"


@pytest.mark.asyncio
async def test_grab_stats_survives_sampler_failure(store, config, monkeypatch):
    """A sampler raising OSError yields a partial dict, not an exception."""
    p = PluginModel(store, config)

    class _BoomSampler:
        cpu_count = 1

        async def get_aggregate(self):
            raise OSError("boom")

        async def get_per_core(self):
            raise OSError("boom")

    import glances.plugins.quicklook.model_v5 as mod

    monkeypatch.setattr(mod, "sampler", _BoomSampler())
    monkeypatch.setattr(mod, "_collect_sync", lambda: {})

    stats = await p._grab_stats()
    assert "cpu" not in stats
    assert "percpu" not in stats


def test_cpu_name_parses_proc_cpuinfo(monkeypatch):
    data = "processor\t: 0\nmodel name\t: Test Chip 9000\nflags\t: fpu\n"
    monkeypatch.setattr("builtins.open", mock_open(read_data=data))
    assert _cpu_name() == "Test Chip 9000"


def test_cpu_name_falls_back_on_oserror(monkeypatch):
    def _boom(*args, **kwargs):
        raise OSError("snap confinement")

    monkeypatch.setattr("builtins.open", _boom)
    monkeypatch.setattr("platform.processor", lambda: "FallbackCPU")
    assert _cpu_name() == "FallbackCPU"


def test_collect_sync_smoke():
    out = _collect_sync()
    assert isinstance(out, dict)
    assert "cpu_name" in out  # always set, even when other metrics fail
