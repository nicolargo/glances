#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `vms` plugin (collection, disabled by default)."""

from __future__ import annotations

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.vms.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


def _cfg_with(tmp_path, monkeypatch, body: str) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    xdg = tmp_path / "xdg"
    cfg_dir = xdg / "glances"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "glances.conf").write_text(body)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    return GlancesConfigV5()


_FIELD_NAMES = (
    "name",
    "id",
    "release",
    "status",
    "cpu_count",
    "cpu_time",
    "memory_usage",
    "memory_total",
    "memory_percent",
    "load_1min",
    "load_5min",
    "load_15min",
    "ipv4",
    "engine",
    "engine_version",
)


class _FakeEngine:
    """Fake VM engine mirroring `watcher.update(all_tag) -> (version, list[dict])`."""

    def __init__(self, version, rows, raises=False):
        self._version = version
        self._rows = rows
        self._raises = raises

    def update(self, all_tag):
        if self._raises:
            raise RuntimeError("engine down")
        return self._version, [dict(r) for r in self._rows]


# ---------------------------------------------------------- identity / fields


def test_plugin_identity(store, config):
    p = PluginModel(store, config)
    assert p.plugin_name == "vms"
    assert p.IS_COLLECTION is True
    assert p.EMITS_ALERTS is True
    assert p._primary_key == "name"


def test_fields_description(store, config):
    fd = PluginModel(store, config).fields_description
    assert set(fd.keys()) == set(_FIELD_NAMES)
    assert fd["name"]["primary_key"] is True
    assert fd["cpu_time"]["rate"] is True
    # Watched fields (v4 f8657a0a): CPU/MEM/LOAD only, load_5min/15min excluded.
    watched = {name for name, schema in fd.items() if schema.get("watched") is True}
    assert watched == {"cpu_time", "memory_percent", "load_1min"}
    assert fd["cpu_time"]["threshold_field"] == "cpu"
    assert fd["memory_percent"]["threshold_field"] == "mem"
    assert fd["load_1min"]["threshold_field"] == "load"
    for name in ("cpu_time", "memory_percent", "load_1min"):
        assert fd[name]["watch_direction"] == "high", name
        assert fd[name].get("prominent") is False, name
    assert "default_thresholds" not in fd["cpu_time"]
    assert "default_thresholds" not in fd["memory_percent"]
    assert "default_thresholds" not in fd["load_1min"]


# ---------------------------------------------------------- disabled by default


def test_disabled_by_default(config):
    # v4 ships `[vms] disable=True`. The gate is generic:
    # `main_v5.discover_plugins()` does not even instantiate the plugin.
    assert PluginModel.DISABLED_BY_DEFAULT is True
    assert PluginModel.is_disabled(config) is True


# ---------------------------------------------------------- engine merge


@pytest.mark.asyncio
async def test_enabled_merges_engines(store, tmp_path, monkeypatch):
    config = _cfg_with(tmp_path, monkeypatch, "[vms]\ndisable=False\n")
    p = PluginModel(store, config)
    p.watchers = {
        "multipass": _FakeEngine(
            "1.13",
            [
                {
                    "name": "vm-a",
                    "status": "running",
                    "cpu_count": 2,
                    "cpu_time": None,
                    "memory_usage": 1024,
                    "memory_total": 4096,
                    "load_1min": None,
                }
            ],
        ),
        "virsh": _FakeEngine(
            "9.0",
            [
                {
                    "name": "vm-b",
                    "status": "running",
                    "cpu_count": 4,
                    "cpu_time": 1000,
                    "memory_usage": 2048,
                    "memory_total": 8192,
                    "load_1min": None,
                }
            ],
        ),
    }
    out = await p._grab_stats()
    assert len(out) == 2
    by_name = {v["name"]: v for v in out}
    assert by_name["vm-a"]["engine"] == "multipass"
    assert by_name["vm-a"]["engine_version"] == "1.13"
    assert by_name["vm-b"]["engine"] == "virsh"
    assert by_name["vm-b"]["engine_version"] == "9.0"


@pytest.mark.asyncio
async def test_one_engine_unavailable_still_returns_other(store, tmp_path, monkeypatch):
    config = _cfg_with(tmp_path, monkeypatch, "[vms]\ndisable=False\n")
    p = PluginModel(store, config)
    p.watchers = {
        "multipass": _FakeEngine("", [], raises=True),
        "virsh": _FakeEngine("9.0", [{"name": "vm-b", "status": "running", "cpu_count": 1}]),
    }
    out = await p._grab_stats()
    assert [v["name"] for v in out] == ["vm-b"]


@pytest.mark.asyncio
async def test_no_engine_returns_empty(store, tmp_path, monkeypatch):
    config = _cfg_with(tmp_path, monkeypatch, "[vms]\ndisable=False\n")
    p = PluginModel(store, config)
    p.watchers = {
        "multipass": _FakeEngine("", []),
        "virsh": _FakeEngine("", []),
    }
    out = await p._grab_stats()
    assert out == []


# ---------------------------------------------------------- metadata


@pytest.mark.asyncio
async def test_max_name_size_exposed_in_metadata(store, tmp_path, monkeypatch):
    config = _cfg_with(tmp_path, monkeypatch, "[vms]\ndisable=False\n")
    p = PluginModel(store, config)
    p.watchers = {
        "multipass": _FakeEngine("1.13", [{"name": "vm-a", "status": "running", "cpu_count": 2}]),
    }
    await p.update()
    payload = p.get_stats()
    assert payload["max_name_size"] == 20
    assert "sort_key" not in payload


# ---------------------------------------------------------- cpu_time rate


@pytest.mark.asyncio
async def test_cpu_time_rate_derived(store, tmp_path, monkeypatch):
    config = _cfg_with(tmp_path, monkeypatch, "[vms]\ndisable=False\n")
    p = PluginModel(store, config)

    fake_now = [100.0]
    import glances.plugins.plugin.base_v5 as base_module

    monkeypatch.setattr(base_module.time, "monotonic", lambda: fake_now[0])

    p.watchers = {"virsh": _FakeEngine("9.0", [{"name": "vm-b", "status": "running", "cpu_time": 1000}])}
    await p.update()
    item = next(i for i in p.get_stats()["data"] if i["name"] == "vm-b")
    # First cycle: rate field kept, value None (no baseline yet).
    assert "cpu_time" in item
    assert item["cpu_time"] is None

    fake_now[0] = 102.0
    p.watchers = {"virsh": _FakeEngine("9.0", [{"name": "vm-b", "status": "running", "cpu_time": 3000}])}
    await p.update()
    item = next(i for i in p.get_stats()["data"] if i["name"] == "vm-b")
    assert item["cpu_time"] == 1000.0  # (3000 - 1000) / 2.0


@pytest.mark.asyncio
async def test_multipass_cpu_time_none_stays_none(store, tmp_path, monkeypatch):
    config = _cfg_with(tmp_path, monkeypatch, "[vms]\ndisable=False\n")
    p = PluginModel(store, config)
    p.watchers = {"multipass": _FakeEngine("1.13", [{"name": "vm-a", "status": "running", "cpu_time": None}])}
    await p.update()
    item = next(i for i in p.get_stats()["data"] if i["name"] == "vm-a")
    assert "cpu_time" in item
    assert item["cpu_time"] is None


def test_sort_vm_stats_actually_orders():
    """Guard against the v4 no-op: sort_vm_stats must capture the sorted list.

    `sort_stats_processes` returns a NEW list (does not mutate in place), so a
    verbatim v4 port that drops the return value would leave `stats` unsorted.
    Here `sort_key` defaults to the cpu_time branch (reverse=True), so the
    highest cpu_time must come first regardless of input order.
    """
    from glances.plugins.vms import model_v5
    from glances.processes import glances_processes

    unsorted = [
        {"name": "low", "cpu_time": 10, "memory_usage": 1},
        {"name": "high", "cpu_time": 90, "memory_usage": 1},
        {"name": "mid", "cpu_time": 50, "memory_usage": 1},
    ]
    saved = glances_processes._sort_key  # `sort_key` is a read-only property
    try:
        glances_processes._sort_key = "cpu_percent"  # -> default cpu_time branch, reverse
        sort_by, ordered = model_v5.sort_vm_stats(list(unsorted))
    finally:
        glances_processes._sort_key = saved
    assert sort_by == "cpu_time"
    assert [i["name"] for i in ordered] == ["high", "mid", "low"]


# ---------------------------------------------------------- memory_percent derivation


@pytest.mark.asyncio
async def test_memory_percent_computed_from_usage_and_total(store, tmp_path, monkeypatch):
    config = _cfg_with(tmp_path, monkeypatch, "[vms]\ndisable=False\n")
    p = PluginModel(store, config)
    p.watchers = {
        "virsh": _FakeEngine("9.0", [{"name": "vm-b", "status": "running", "memory_usage": 2048, "memory_total": 8192}])
    }
    out = await p._grab_stats()
    assert out[0]["memory_percent"] == 25.0


@pytest.mark.asyncio
async def test_memory_percent_none_when_total_zero(store, tmp_path, monkeypatch):
    config = _cfg_with(tmp_path, monkeypatch, "[vms]\ndisable=False\n")
    p = PluginModel(store, config)
    p.watchers = {
        "virsh": _FakeEngine("9.0", [{"name": "vm-b", "status": "running", "memory_usage": 2048, "memory_total": 0}])
    }
    out = await p._grab_stats()
    assert out[0]["memory_percent"] is None


@pytest.mark.asyncio
async def test_memory_percent_none_when_total_missing(store, tmp_path, monkeypatch):
    config = _cfg_with(tmp_path, monkeypatch, "[vms]\ndisable=False\n")
    p = PluginModel(store, config)
    p.watchers = {
        "multipass": _FakeEngine(
            "1.13", [{"name": "vm-a", "status": "running", "memory_usage": None, "memory_total": None}]
        )
    }
    out = await p._grab_stats()
    assert out[0]["memory_percent"] is None


# ---------------------------------------------------------- thresholds / levels (v4 f8657a0a)


def test_cpu_critical_level(store, tmp_path, monkeypatch):
    config = _cfg_with(tmp_path, monkeypatch, "[vms]\ndisable=False\ncpu_careful=50\ncpu_warning=70\ncpu_critical=90\n")
    p = PluginModel(store, config)
    p._stats = [{"name": "vm-a", "cpu_time": 95.0}]
    p._derived_parameters()
    assert p._levels["vm-a"]["cpu_time"]["level"] == "critical"


def test_mem_level_uses_mem_prefix_thresholds(store, tmp_path, monkeypatch):
    config = _cfg_with(tmp_path, monkeypatch, "[vms]\ndisable=False\nmem_careful=20\nmem_warning=50\n")
    p = PluginModel(store, config)
    p._stats = [{"name": "vm-a", "memory_usage": 3000, "memory_total": 5000, "memory_percent": 60.0}]
    p._derived_parameters()
    assert p._levels["vm-a"]["memory_percent"]["level"] == "warning"


def test_per_vm_mem_override(store, tmp_path, monkeypatch):
    config = _cfg_with(tmp_path, monkeypatch, "[vms]\ndisable=False\nmem_careful=50\nvm-a_mem_careful=10\n")
    p = PluginModel(store, config)
    p._stats = [{"name": "vm-a", "memory_percent": 15.0}]
    p._derived_parameters()
    assert p._levels["vm-a"]["memory_percent"]["level"] == "careful"


def test_no_threshold_configured_no_level_produced(store, tmp_path, monkeypatch):
    # Shipped default: [vms] cpu_*/mem_*/load_* are commented out.
    config = _cfg_with(tmp_path, monkeypatch, "[vms]\ndisable=False\n")
    p = PluginModel(store, config)
    p._stats = [{"name": "vm-a", "cpu_time": 95.0, "memory_percent": 90.0, "load_1min": 999.0}]
    p._derived_parameters()
    assert p._levels == {}


def test_load_none_produces_no_level(store, tmp_path, monkeypatch):
    config = _cfg_with(tmp_path, monkeypatch, "[vms]\ndisable=False\nload_warning=100\n")
    p = PluginModel(store, config)
    p._stats = [{"name": "vm-a", "load_1min": None}]
    p._derived_parameters()
    assert "load_1min" not in p._levels.get("vm-a", {})
