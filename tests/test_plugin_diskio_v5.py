#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `diskio` plugin (collection)."""

from __future__ import annotations

from collections import namedtuple
from unittest.mock import patch

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.diskio.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5

# psutil stub ------------------------------------------------------

DiskIo = namedtuple(
    "sdiskio",
    ["read_count", "write_count", "read_bytes", "write_bytes", "read_time", "write_time"],
)


def _io(rc: int = 0, wc: int = 0, rb: int = 0, wb: int = 0, rt: int = 0, wt: int = 0) -> DiskIo:
    return DiskIo(rc, wc, rb, wb, rt, wt)


# ----------------------------------------------------------- fixtures


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
    assert plugin.plugin_name == "diskio"
    assert plugin.IS_COLLECTION is True


def test_disk_name_is_primary_key(store, config):
    fields = PluginModel(store, config)._fields
    assert fields["disk_name"].get("primary_key") is True


def test_read_write_bytes_are_rate_counters(store, config):
    fields = PluginModel(store, config)._fields
    for name in ("read_bytes", "write_bytes"):
        assert fields[name].get("rate") is True, name


def test_read_write_bytes_are_watched_but_not_prominent_with_strict(store, config):
    """Opt-in alerts: watched=True so the framework wires levels when the
    user sets thresholds, but no defaults — and strict_thresholds=True so
    bare ``careful``/``warning``/``critical`` keys in ``[diskio]`` do NOT
    spill onto these per-disk rates."""
    fields = PluginModel(store, config)._fields
    for name in ("read_bytes", "write_bytes"):
        assert fields[name].get("watched") is True, name
        assert fields[name].get("prominent") is False, name
        assert fields[name].get("strict_thresholds") is True, name
        assert "default_thresholds" not in fields[name], name


def test_read_write_count_are_rate_internal(store, config):
    """read_count / write_count are kept in the payload for IOPS export but
    flagged ``internal`` so the generic renderer skips them."""
    fields = PluginModel(store, config)._fields
    for name in ("read_count", "write_count"):
        assert fields[name].get("rate") is True, name
        assert fields[name].get("internal") is True, name


# ---------------------------------------------------------- update pipeline


async def test_update_yields_one_entry_per_disk(store, config):
    plugin = PluginModel(store, config)
    iomap = {"sda": _io(rc=10, wc=5), "sdb": _io(rc=20, wc=15)}
    with patch("glances.plugins.diskio.model_v5.psutil.disk_io_counters", return_value=iomap):
        await plugin.update()
    payload = store.get("diskio")
    names = sorted(i["disk_name"] for i in payload["data"])
    assert names == ["sda", "sdb"]


async def test_first_cycle_strips_rate_fields(store, config):
    plugin = PluginModel(store, config)
    iomap = {"sda": _io(rc=10, wc=5, rb=1000, wb=500)}
    with patch("glances.plugins.diskio.model_v5.psutil.disk_io_counters", return_value=iomap):
        await plugin.update()
    item = store.get("diskio")["data"][0]
    # No baseline yet → rate fields stripped.
    for name in ("read_bytes", "write_bytes", "read_count", "write_count"):
        assert name not in item, name


async def test_second_cycle_computes_byte_rates(store, config, monkeypatch):
    plugin = PluginModel(store, config)
    fake_now = [100.0]
    import glances.plugins.plugin.base_v5 as base_module

    monkeypatch.setattr(base_module.time, "monotonic", lambda: fake_now[0])

    psutil_path = "glances.plugins.diskio.model_v5.psutil.disk_io_counters"
    with patch(psutil_path, return_value={"sda": _io(rc=0, wc=0, rb=0, wb=0)}):
        await plugin.update()
    fake_now[0] = 101.0
    with patch(psutil_path, return_value={"sda": _io(rc=10, wc=5, rb=10_000, wb=5_000)}):
        await plugin.update()

    item = next(i for i in store.get("diskio")["data"] if i["disk_name"] == "sda")
    assert item["read_bytes"] == 10_000.0  # 10_000 B / 1 s
    assert item["write_bytes"] == 5_000.0
    assert item["read_count"] == 10.0
    assert item["write_count"] == 5.0


async def test_update_handles_psutil_failure(store, config):
    """psutil.disk_io_counters may return None on locked-down hosts or
    raise on transient kernel hiccups — model degrades gracefully."""
    plugin = PluginModel(store, config)
    with patch("glances.plugins.diskio.model_v5.psutil.disk_io_counters", side_effect=OSError("boom")):
        await plugin.update()
    assert store.get("diskio")["data"] == []


async def test_update_handles_none_return(store, config):
    """psutil returns ``None`` on platforms without disk I/O support."""
    plugin = PluginModel(store, config)
    with patch("glances.plugins.diskio.model_v5.psutil.disk_io_counters", return_value=None):
        await plugin.update()
    assert store.get("diskio")["data"] == []


# ---------------------------------------------------------- thresholds


async def test_no_levels_without_user_thresholds(store, config, monkeypatch):
    """No ``[diskio] read_bytes_*`` in conf → no _levels entries."""
    plugin = PluginModel(store, config)
    fake_now = [100.0]
    import glances.plugins.plugin.base_v5 as base_module

    monkeypatch.setattr(base_module.time, "monotonic", lambda: fake_now[0])

    psutil_path = "glances.plugins.diskio.model_v5.psutil.disk_io_counters"
    with patch(psutil_path, return_value={"sda": _io()}):
        await plugin.update()
    fake_now[0] = 101.0
    with patch(psutil_path, return_value={"sda": _io(rb=1_000_000, wb=500_000)}):
        await plugin.update()

    levels = store.get("diskio")["_levels"]
    # Either no entry for sda or entry with no read/write_bytes keys.
    sda = levels.get("sda", {})
    assert "read_bytes" not in sda
    assert "write_bytes" not in sda


async def test_bare_level_keys_do_not_leak_onto_per_disk_rates(tmp_path, monkeypatch, store):
    """Regression guard: ``[diskio] careful=50`` (bare) must NOT trigger
    on read_bytes/write_bytes — they ship ``strict_thresholds=True``."""
    config = _config_with(tmp_path, monkeypatch, "[diskio]\ncareful=50\nwarning=70\ncritical=90\n")
    plugin = PluginModel(store, config)
    fake_now = [100.0]
    import glances.plugins.plugin.base_v5 as base_module

    monkeypatch.setattr(base_module.time, "monotonic", lambda: fake_now[0])

    psutil_path = "glances.plugins.diskio.model_v5.psutil.disk_io_counters"
    with patch(psutil_path, return_value={"sda": _io()}):
        await plugin.update()
    fake_now[0] = 101.0
    with patch(psutil_path, return_value={"sda": _io(rb=1_000, wb=1_000)}):
        await plugin.update()

    sda = store.get("diskio")["_levels"].get("sda", {})
    assert "read_bytes" not in sda
    assert "write_bytes" not in sda


async def test_read_bytes_threshold_from_config_triggers_level(tmp_path, monkeypatch, store):
    """User-set per-field thresholds wire through normally."""
    config = _config_with(
        tmp_path,
        monkeypatch,
        "[diskio]\nread_bytes_careful=5000\nread_bytes_warning=10000\nread_bytes_critical=20000\n",
    )
    plugin = PluginModel(store, config)
    fake_now = [100.0]
    import glances.plugins.plugin.base_v5 as base_module

    monkeypatch.setattr(base_module.time, "monotonic", lambda: fake_now[0])

    psutil_path = "glances.plugins.diskio.model_v5.psutil.disk_io_counters"
    with patch(psutil_path, return_value={"sda": _io()}):
        await plugin.update()
    fake_now[0] = 101.0
    with patch(psutil_path, return_value={"sda": _io(rb=15_000)}):  # 15_000 B/s → warning
        await plugin.update()

    sda = store.get("diskio")["_levels"]["sda"]
    assert sda["read_bytes"]["level"] == "warning"
    assert sda["read_bytes"]["prominent"] is False
