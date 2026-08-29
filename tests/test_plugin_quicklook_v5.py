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


def _cfg_with(tmp_path, monkeypatch, body: str) -> GlancesConfigV5:
    """Real config object built from a `[quicklook]` section body."""
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    xdg = tmp_path / "xdg"
    cfg_dir = xdg / "glances"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "glances.conf").write_text(body)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    return GlancesConfigV5()


def test_plugin_identity(store, config):
    p = PluginModel(store, config)
    assert p.plugin_name == "quicklook"
    assert p.IS_COLLECTION is False


def test_quicklook_opts_out_of_alerts(store, config):
    """quicklook colours its bars from cpu/mem/swap/load `_levels` but must
    NOT emit alerts events / actions: those aggregate signals are already
    watched by the cpu/mem/memswap/load plugins, so ingesting quicklook too
    would duplicate every alert. See base ``EMITS_ALERTS`` doc."""
    assert PluginModel.EMITS_ALERTS is False


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


class _NoGpuSampler:
    cpu_count = 1

    async def get_aggregate(self):
        class _A:
            idle = 100.0

        return _A()

    async def get_per_core(self):
        return []


@pytest.mark.asyncio
async def test_gpu_means_from_store(store, config, monkeypatch):
    """quicklook computes gpu_mem/gpu_proc as the mean of the gpu plugin's cards."""
    await store.set(
        "gpu",
        [
            {"gpu_id": "n0", "mem": 40, "proc": 20},
            {"gpu_id": "n1", "mem": 60, "proc": 40},
        ],
    )
    p = PluginModel(store, config)

    import glances.plugins.quicklook.model_v5 as mod

    monkeypatch.setattr(mod, "_collect_sync", lambda: {})
    monkeypatch.setattr(mod, "sampler", _NoGpuSampler())

    stats = await p._grab_stats()
    assert stats["gpu_mem"] == 50.0
    assert stats["gpu_proc"] == 30.0


@pytest.mark.asyncio
async def test_no_gpu_keys_when_store_empty(store, config, monkeypatch):
    p = PluginModel(store, config)
    import glances.plugins.quicklook.model_v5 as mod

    monkeypatch.setattr(mod, "_collect_sync", lambda: {})
    monkeypatch.setattr(mod, "sampler", _NoGpuSampler())

    stats = await p._grab_stats()
    assert "gpu_mem" not in stats
    assert "gpu_proc" not in stats


@pytest.mark.asyncio
async def test_no_gpu_keys_when_all_none(store, config, monkeypatch):
    await store.set("gpu", [{"gpu_id": "n0", "mem": None, "proc": None}])
    p = PluginModel(store, config)
    import glances.plugins.quicklook.model_v5 as mod

    monkeypatch.setattr(mod, "_collect_sync", lambda: {})
    monkeypatch.setattr(mod, "sampler", _NoGpuSampler())

    stats = await p._grab_stats()
    assert "gpu_mem" not in stats
    assert "gpu_proc" not in stats


def test_gpu_fields_declared_watched():
    fd = PluginModel.fields_description
    for key in ("gpu_mem", "gpu_proc"):
        assert fd[key]["watched"] is True
        assert fd[key]["unit"] == "percent"


class TestStatsList:
    """`[quicklook] list` — v4 parity (glances/plugins/quicklook/__init__.py:110)."""

    def test_default_is_cpu_mem_load(self, tmp_path, monkeypatch, store):
        # Isolated config on purpose: the module-level `config` fixture only
        # redirects SYSTEM_CONFIG_PATH, so the developer's real
        # ~/.config/glances/glances.conf still leaks into it.
        cfg = _cfg_with(tmp_path, monkeypatch, "")
        assert PluginModel(store, cfg).stats_list == ["cpu", "mem", "load"]

    def test_a_plain_list_is_honoured(self, tmp_path, monkeypatch, store):
        cfg = _cfg_with(tmp_path, monkeypatch, "[quicklook]\nlist=cpu,swap\n")
        assert PluginModel(store, cfg).stats_list == ["cpu", "swap"]

    def test_config_order_is_preserved(self, tmp_path, monkeypatch, store):
        """v4 loops over the configured list, so the config drives bar order."""
        cfg = _cfg_with(tmp_path, monkeypatch, "[quicklook]\nlist=load,mem,cpu\n")
        assert PluginModel(store, cfg).stats_list == ["load", "mem", "cpu"]

    @pytest.mark.parametrize("value", ["cpu, mem, load", " cpu , mem , load ", "cpu,\tmem,\tload"])
    def test_whitespace_around_items_is_ignored(self, tmp_path, monkeypatch, store, value):
        cfg = _cfg_with(tmp_path, monkeypatch, f"[quicklook]\nlist={value}\n")
        assert PluginModel(store, cfg).stats_list == ["cpu", "mem", "load"]

    def test_a_typo_falls_back_to_the_default_not_to_everything(self, tmp_path, monkeypatch, store):
        """PR #3700 semantics: a config mistake must not display MORE than asked."""
        cfg = _cfg_with(tmp_path, monkeypatch, "[quicklook]\nlist=cpu,mem,typo\n")
        assert PluginModel(store, cfg).stats_list == PluginModel.DEFAULT_STATS_LIST

    def test_an_empty_list_falls_back_to_the_default(self, tmp_path, monkeypatch, store):
        cfg = _cfg_with(tmp_path, monkeypatch, "[quicklook]\nlist=\n")
        assert PluginModel(store, cfg).stats_list == PluginModel.DEFAULT_STATS_LIST

    def test_gpu_is_opt_in(self, tmp_path, monkeypatch, store):
        """v4 parity: no GPU bar unless the user lists it."""
        assert "gpu_mem" not in PluginModel.DEFAULT_STATS_LIST
        cfg = _cfg_with(tmp_path, monkeypatch, "[quicklook]\nlist=cpu,gpu_mem,gpu_proc\n")
        assert PluginModel(store, cfg).stats_list == ["cpu", "gpu_mem", "gpu_proc"]


class TestBarChar:
    """`[quicklook] bar_char` — v4 parity (`get_conf_value('bar_char', default=['|'])[0]`)."""

    def test_default_is_a_pipe(self, tmp_path, monkeypatch, store):
        cfg = _cfg_with(tmp_path, monkeypatch, "")
        assert PluginModel(store, cfg).bar_char == "|"

    def test_a_configured_char_is_used(self, tmp_path, monkeypatch, store):
        cfg = _cfg_with(tmp_path, monkeypatch, "[quicklook]\nbar_char=#\n")
        assert PluginModel(store, cfg).bar_char == "#"

    def test_only_the_first_item_is_kept(self, tmp_path, monkeypatch, store):
        """v4 reads the value as a list and takes `[0]` — not the first character."""
        cfg = _cfg_with(tmp_path, monkeypatch, "[quicklook]\nbar_char=#,@\n")
        assert PluginModel(store, cfg).bar_char == "#"

    def test_an_empty_value_falls_back_to_the_default(self, tmp_path, monkeypatch, store):
        cfg = _cfg_with(tmp_path, monkeypatch, "[quicklook]\nbar_char=\n")
        assert PluginModel(store, cfg).bar_char == "|"


class TestRenderSupportFields:
    """The selection reaches the custom renderer through the payload."""

    @pytest.mark.asyncio
    async def test_grab_publishes_stats_list_and_bar_char(self, tmp_path, monkeypatch, store):
        cfg = _cfg_with(tmp_path, monkeypatch, "[quicklook]\nlist=cpu,swap\nbar_char=#\n")
        p = PluginModel(store, cfg)
        out = await p._grab_stats()
        assert out["stats_list"] == ["cpu", "swap"]
        assert out["bar_char"] == "#"

    def test_they_are_internal_and_never_watched(self):
        fd = PluginModel.fields_description
        for key in ("stats_list", "bar_char"):
            assert fd[key].get("internal") is True
            assert fd[key].get("watched", False) is False
