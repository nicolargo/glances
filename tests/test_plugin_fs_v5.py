#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `fs` plugin (collection)."""

from __future__ import annotations

from collections import namedtuple
from unittest.mock import patch

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.fs.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5

# psutil stubs ------------------------------------------------------

Partition = namedtuple("sdiskpart", ["device", "mountpoint", "fstype", "opts"])
DiskUsage = namedtuple("sdiskusage", ["total", "used", "free", "percent"])


def _root(percent: float = 25.0) -> tuple[Partition, DiskUsage]:
    total = 500 * 1024**3
    used = int(total * percent / 100.0)
    return Partition("/dev/sda1", "/", "ext4", "rw,relatime"), DiskUsage(total, used, total - used, percent)


def _home(percent: float = 50.0) -> tuple[Partition, DiskUsage]:
    total = 1 * 1024**4
    used = int(total * percent / 100.0)
    return Partition("/dev/sda2", "/home", "ext4", "rw,relatime"), DiskUsage(total, used, total - used, percent)


# ----------------------------------------------------------- fixtures


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


def _patch_psutil(parts_and_usage):
    """Build patches for psutil.disk_partitions + disk_usage from a list of
    (Partition, DiskUsage) pairs. Returns an ExitStack-like context."""
    from contextlib import ExitStack

    stack = ExitStack()
    partitions = [p for p, _ in parts_and_usage]
    usages = {p.mountpoint: u for p, u in parts_and_usage}

    stack.enter_context(patch("glances.plugins.fs.model_v5.psutil.disk_partitions", return_value=partitions))
    stack.enter_context(patch("glances.plugins.fs.model_v5.psutil.disk_usage", side_effect=lambda mp: usages[mp]))
    return stack


# ---------------------------------------------------------- contract


def test_plugin_identity(store, config):
    plugin = PluginModel(store, config)
    assert plugin.plugin_name == "fs"
    assert plugin.IS_COLLECTION is True


def test_mnt_point_is_primary_key(store, config):
    fields = PluginModel(store, config)._fields
    assert fields["mnt_point"].get("primary_key") is True


def test_percent_is_watched_prominent(store, config):
    schema = PluginModel(store, config)._fields["percent"]
    assert schema["watched"] is True
    assert schema["prominent"] is True
    assert schema["unit"] == "percent"


def test_size_used_free_are_bytes_not_watched(store, config):
    fields = PluginModel(store, config)._fields
    for name in ("size", "used", "free"):
        assert fields[name]["unit"] == "bytes", name
        assert fields[name].get("watched", False) is False, name


def test_fs_type_and_options_are_internal(store, config):
    """fs_type and options are kept in the payload for export but never
    surfaced in the UI."""
    fields = PluginModel(store, config)._fields
    assert fields["fs_type"].get("internal") is True
    assert fields["options"].get("internal") is True


# ---------------------------------------------------------- update pipeline


async def test_update_yields_one_entry_per_partition(store, config):
    plugin = PluginModel(store, config)
    with _patch_psutil([_root(), _home()]):
        await plugin.update()
    payload = store.get("fs")
    items = payload["data"]
    mnts = sorted(i["mnt_point"] for i in items)
    assert mnts == ["/", "/home"]


async def test_update_carries_size_used_free_percent(store, config):
    plugin = PluginModel(store, config)
    with _patch_psutil([_root(percent=30.0)]):
        await plugin.update()
    root = next(i for i in store.get("fs")["data"] if i["mnt_point"] == "/")
    assert root["percent"] == 30.0
    assert root["size"] == 500 * 1024**3
    assert root["used"] > 0
    assert root["free"] > 0
    assert root["device_name"] == "/dev/sda1"
    assert root["fs_type"] == "ext4"


async def test_update_skips_partition_when_disk_usage_raises(store, config):
    """A disk_usage() OSError on one partition (e.g. lazy-unmount) must
    not propagate — the partition is dropped from the payload."""
    plugin = PluginModel(store, config)

    parts = [_root()[0], _home()[0]]
    usages = {"/": _root()[1]}  # /home raises

    def fake_usage(mp):
        if mp == "/home":
            raise OSError("ejected")
        return usages[mp]

    with patch("glances.plugins.fs.model_v5.psutil.disk_partitions", return_value=parts):
        with patch("glances.plugins.fs.model_v5.psutil.disk_usage", side_effect=fake_usage):
            await plugin.update()

    mnts = [i["mnt_point"] for i in store.get("fs")["data"]]
    assert "/" in mnts
    assert "/home" not in mnts


async def test_update_handles_permission_error_globally(store, config):
    """psutil.disk_partitions() can raise PermissionError on locked-down
    hosts — model returns an empty list, not a crash."""
    plugin = PluginModel(store, config)
    with patch("glances.plugins.fs.model_v5.psutil.disk_partitions", side_effect=PermissionError("denied")):
        await plugin.update()
    payload = store.get("fs")
    assert payload["data"] == []


# ---------------------------------------------------------- _levels


async def test_levels_indexed_by_mnt_point(store, config):
    plugin = PluginModel(store, config)
    with _patch_psutil([_root(percent=75.0), _home(percent=30.0)]):
        await plugin.update()
    levels = store.get("fs")["_levels"]
    # 75% → warning, 30% → ok
    assert levels["/"]["percent"]["level"] == "warning"
    assert levels["/"]["percent"]["prominent"] is True
    assert levels["/home"]["percent"]["level"] == "ok"


# ---------------------------------------------------------- export


async def test_get_export_strips_levels_but_keeps_metadata(store, config):
    """``get_export`` filters ``_*`` keys and ``exportable=False`` fields,
    not ``internal=True``. fs_type / options stay exportable — useful for
    InfluxDB / Prometheus / ... downstream consumers."""
    plugin = PluginModel(store, config)
    with _patch_psutil([_root()]):
        await plugin.update()
    exported = plugin.get_export()
    assert isinstance(exported, list)
    item = exported[0]
    assert "_levels" not in item
    assert "time_since_update" not in item
    # internal flag affects UI only — these fields ARE exported.
    assert item["fs_type"] == "ext4"
    assert "options" in item
    # user-facing fields present
    assert item["mnt_point"] == "/"
    assert item["percent"] == 25.0
