#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `mem` plugin."""

from __future__ import annotations

from collections import namedtuple
from pathlib import Path
from unittest.mock import patch

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.fs.zfs import zfs_enable, zfs_stats
from glances.plugins.mem.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5

_ZFS_DIR = Path(__file__).parent.parent / "tests-data" / "plugins" / "fs" / "zfs"

# psutil.virtual_memory() returns a namedtuple — replicate its shape.
VMTuple = namedtuple(
    "svmem",
    ["total", "available", "percent", "used", "free", "active", "inactive", "buffers", "cached", "shared", "slab"],
)


def _make_vm(percent: float = 50.0) -> VMTuple:
    return VMTuple(
        total=16_000_000_000,
        available=8_000_000_000,
        percent=percent,
        used=8_000_000_000,
        free=4_000_000_000,
        active=3_000_000_000,
        inactive=1_000_000_000,
        buffers=500_000_000,
        cached=2_000_000_000,
        shared=100_000_000,
        slab=200_000_000,
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


def _config_with(tmp_path, monkeypatch, body: str) -> GlancesConfigV5:
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
    assert plugin.plugin_name == "mem"
    assert plugin.IS_COLLECTION is False


def test_plugin_declares_percent_as_watched(store, config):
    plugin = PluginModel(store, config)
    schema = plugin._fields["percent"]
    assert schema["watched"] is True
    assert schema["watch_direction"] == "high"
    assert schema["prominent"] is True
    assert "default_thresholds" in schema


# ---------------------------------------------------------- update pipeline


async def test_update_writes_psutil_fields_to_store(store, config):
    plugin = PluginModel(store, config)
    with patch("glances.plugins.mem.model_v5.psutil.virtual_memory", return_value=_make_vm(50.0)):
        await plugin.update()

    payload = store.get("mem")
    assert payload is not None
    assert payload["percent"] == 50.0
    assert payload["total"] == 16_000_000_000
    assert payload["available"] == 8_000_000_000
    assert payload["used"] == 8_000_000_000
    assert payload["free"] == 4_000_000_000
    assert payload["active"] == 3_000_000_000
    assert payload["inactive"] == 1_000_000_000
    assert payload["buffers"] == 500_000_000
    assert payload["cached"] == 2_000_000_000


async def test_update_drops_undeclared_fields(store, config):
    """If psutil exposes a field not in fields_description it is filtered."""
    Vm = namedtuple("svmem", ["total", "percent", "available", "used", "free", "future_field"])
    fake = Vm(total=1, percent=10.0, available=1, used=0, free=1, future_field="surprise")
    plugin = PluginModel(store, config)
    with patch("glances.plugins.mem.model_v5.psutil.virtual_memory", return_value=fake):
        await plugin.update()

    payload = store.get("mem")
    assert "future_field" not in payload


async def test_used_is_total_minus_available(store, config):
    """v4 redefines `used` as `total - available` (`mem/__init__.py:216`), not psutil's platform `used`."""
    vm = _make_vm(50.0)._replace(used=5_000_000_000)
    plugin = PluginModel(store, config)
    with patch("glances.plugins.mem.model_v5.psutil.virtual_memory", return_value=vm):
        await plugin.update()

    payload = store.get("mem")
    assert payload["used"] == 8_000_000_000
    assert payload["used"] + payload["available"] == payload["total"]


async def test_available_above_total_clamps_used_and_percent(store, config):
    """LXC/cgroup-v2: `available > total` must not publish a negative `used` or `percent` (v4 parity)."""
    vm = _make_vm(-6.2)._replace(available=17_000_000_000)
    plugin = PluginModel(store, config)
    with patch("glances.plugins.mem.model_v5.psutil.virtual_memory", return_value=vm):
        await plugin.update()

    payload = store.get("mem")
    assert payload["used"] == 0
    assert payload["percent"] == 0.0


async def test_percent_is_clamped_to_100(store, config):
    plugin = PluginModel(store, config)
    with patch("glances.plugins.mem.model_v5.psutil.virtual_memory", return_value=_make_vm(120.0)):
        await plugin.update()

    assert store.get("mem")["percent"] == 100.0


# ---------------------------------------------------------- ZFS ARC (issue #3979)


def test_zfs_helpers_read_the_arcstats_file():
    assert zfs_enable(str(_ZFS_DIR))
    stats = zfs_stats([str(_ZFS_DIR / "arcstats")])
    assert stats["arcstats.c_min"] == 2_637_352_832
    assert stats["arcstats.size"] == 41_321_273_080


async def test_zfs_arc_counts_as_cached_and_its_shrinkable_part_as_available(store, config):
    """v4 `mem/__init__.py:179-210`: ARC size -> cached, size - c_min -> available, out of used."""
    vm = _make_vm()._replace(total=128_000_000_000, available=20_000_000_000)
    with patch("glances.plugins.mem.model_v5.zfs_enable", return_value=True):
        plugin = PluginModel(store, config)
    with (
        patch("glances.plugins.mem.model_v5.psutil.virtual_memory", return_value=vm),
        patch("glances.plugins.mem.model_v5.zfs_stats", return_value=zfs_stats([str(_ZFS_DIR / "arcstats")])),
    ):
        await plugin.update()

    shrink = 41_321_273_080 - 2_637_352_832
    payload = store.get("mem")
    assert payload["cached"] == 2_000_000_000 + 41_321_273_080
    assert payload["available"] == 20_000_000_000 + shrink
    assert payload["used"] == 128_000_000_000 - 20_000_000_000 - shrink
    assert payload["percent"] == round((128_000_000_000 - payload["available"]) / 128_000_000_000 * 100, 1)


async def test_no_zfs_leaves_psutil_values(store, config):
    with patch("glances.plugins.mem.model_v5.zfs_enable", return_value=False):
        plugin = PluginModel(store, config)
    with patch("glances.plugins.mem.model_v5.psutil.virtual_memory", return_value=_make_vm(50.0)):
        await plugin.update()

    payload = store.get("mem")
    assert payload["cached"] == 2_000_000_000
    assert payload["available"] == 8_000_000_000
    assert payload["percent"] == 50.0


# ---------------------------------------------------------- [mem] available


async def test_available_display_is_off_by_default(store, config):
    """v4 shows `used` unless `[mem] available=True` (`mem/__init__.py:131`)."""
    plugin = PluginModel(store, config)
    with patch("glances.plugins.mem.model_v5.psutil.virtual_memory", return_value=_make_vm(50.0)):
        await plugin.update()
    assert store.get("mem")["_show_available"] is False


async def test_available_config_key_reaches_the_payload(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[mem]\navailable=True\n")
    plugin = PluginModel(store, config)
    with patch("glances.plugins.mem.model_v5.psutil.virtual_memory", return_value=_make_vm(50.0)):
        await plugin.update()
    assert store.get("mem")["_show_available"] is True
    assert "_show_available" not in plugin.get_export()


# ---------------------------------------------------------- _levels


@pytest.mark.parametrize(
    "percent, expected_level",
    [
        (10.0, "ok"),
        (50.0, "careful"),
        (70.0, "warning"),
        (90.0, "critical"),
        (95.0, "critical"),
    ],
)
async def test_default_thresholds_drive_percent_level(store, config, percent, expected_level):
    plugin = PluginModel(store, config)
    with patch("glances.plugins.mem.model_v5.psutil.virtual_memory", return_value=_make_vm(percent)):
        await plugin.update()
    entry = store.get("mem")["_levels"]["percent"]
    assert entry == {"level": expected_level, "prominent": True}


async def test_user_config_overrides_default_threshold(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[mem]\ncritical=95\n")
    plugin = PluginModel(store, config)

    # 91 was critical with defaults (90), but should now be warning.
    with patch("glances.plugins.mem.model_v5.psutil.virtual_memory", return_value=_make_vm(91.0)):
        await plugin.update()
    assert store.get("mem")["_levels"]["percent"]["level"] == "warning"


async def test_only_percent_field_is_levelled(store, config):
    plugin = PluginModel(store, config)
    with patch("glances.plugins.mem.model_v5.psutil.virtual_memory", return_value=_make_vm(50.0)):
        await plugin.update()
    levels = store.get("mem")["_levels"]
    assert list(levels.keys()) == ["percent"]


# ---------------------------------------------------------- export


async def test_get_export_strips_internals(store, config):
    plugin = PluginModel(store, config)
    with patch("glances.plugins.mem.model_v5.psutil.virtual_memory", return_value=_make_vm(50.0)):
        await plugin.update()
    exported = plugin.get_export()
    assert "_levels" not in exported
    assert "time_since_update" not in exported  # exportable: False on metadata
    assert exported["percent"] == 50.0
