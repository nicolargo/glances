#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `network` plugin (collection)."""

from __future__ import annotations

from collections import namedtuple
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.network.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5

# psutil result stubs ------------------------------------------------------

NetIO = namedtuple(
    "snetio",
    ["bytes_sent", "bytes_recv", "packets_sent", "packets_recv", "errin", "errout", "dropin", "dropout"],
)
NetIfStats = namedtuple("snicstats", ["isup", "duplex", "speed", "mtu", "flags"])


def _io(rx: int = 0, tx: int = 0, errin: int = 0, errout: int = 0, dropin: int = 0, dropout: int = 0) -> NetIO:
    return NetIO(
        bytes_sent=tx,
        bytes_recv=rx,
        packets_sent=0,
        packets_recv=0,
        errin=errin,
        errout=errout,
        dropin=dropin,
        dropout=dropout,
    )


def _stats(isup: bool = True, speed: int = 1000) -> NetIfStats:
    """`speed` is in Mbit/s — psutil convention."""
    return NetIfStats(isup=isup, duplex=2, speed=speed, mtu=1500, flags="")


def _patch_psutil(io_counters: dict, if_stats: dict) -> ExitStack:
    """Patch psutil.net_io_counters and psutil.net_if_stats with deterministic values."""
    stack = ExitStack()
    stack.enter_context(patch("glances.plugins.network.model_v5.psutil.net_io_counters", return_value=io_counters))
    stack.enter_context(patch("glances.plugins.network.model_v5.psutil.net_if_stats", return_value=if_stats))
    return stack


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


def _fake_now(monkeypatch) -> list[float]:
    """Patch base_v5.time.monotonic with a mutable list slot."""
    slot = [100.0]
    import glances.plugins.plugin.base_v5 as base_module

    monkeypatch.setattr(base_module.time, "monotonic", lambda: slot[0])
    return slot


# ---------------------------------------------------------- contract


def test_plugin_identity(store, config):
    plugin = PluginModel(store, config)
    assert plugin.plugin_name == "network"
    assert plugin.IS_COLLECTION is True
    assert plugin._primary_key == "interface_name"


def test_schema_watched_fields(store, config):
    fields = PluginModel(store, config)._fields
    for name in ("bytes_recv", "bytes_sent", "errors_in", "errors_out"):
        assert fields[name]["watched"] is True, name
        # Network watched fields are never prominent (no reverse-video) —
        # the alert plugin already surfaces the event, the sidebar should
        # stay readable.
        assert fields[name]["prominent"] is False, name
        assert fields[name]["rate"] is True, name


def test_schema_bandwidth_fields_normalize_by_speed(store, config):
    fields = PluginModel(store, config)._fields
    assert fields["bytes_recv"]["normalize_by"] == "bytes_speed_rate_per_sec"
    assert fields["bytes_sent"]["normalize_by"] == "bytes_speed_rate_per_sec"
    # Error fields use absolute thresholds — no normalize_by.
    assert "normalize_by" not in fields["errors_in"]
    assert "normalize_by" not in fields["errors_out"]


def test_schema_dropped_fields_are_rate_only(store, config):
    fields = PluginModel(store, config)._fields
    for name in ("dropped_in", "dropped_out"):
        assert fields[name]["rate"] is True, name
        assert fields[name].get("watched", False) is False, name


# ---------------------------------------------------------- update pipeline


async def test_grab_stats_returns_one_dict_per_interface(store, config):
    plugin = PluginModel(store, config)
    with _patch_psutil(
        io_counters={"eth0": _io(rx=1000, tx=500), "lo": _io(rx=0, tx=0)},
        if_stats={"eth0": _stats(speed=1000), "lo": _stats(speed=0)},
    ):
        await plugin.update()
    data = store.get("network")["data"]
    names = sorted(item["interface_name"] for item in data)
    assert names == ["eth0", "lo"]


async def test_bytes_speed_rate_per_sec_computed_from_speed(store, config):
    """speed=1000 Mbit/s → bytes_speed_rate_per_sec = 1e9/8/2 = 62.5e6 B/s."""
    plugin = PluginModel(store, config)
    with _patch_psutil(
        io_counters={"eth0": _io(rx=0, tx=0)},
        if_stats={"eth0": _stats(speed=1000)},
    ):
        await plugin.update()
    item = store.get("network")["data"][0]
    assert item["bytes_speed_rate_per_sec"] == 62_500_000.0


async def test_bytes_speed_rate_per_sec_is_zero_for_unknown_speed(store, config):
    """psutil returns speed=0 for loopback, virtual interfaces → field is 0."""
    plugin = PluginModel(store, config)
    with _patch_psutil(
        io_counters={"lo": _io(rx=0, tx=0)},
        if_stats={"lo": _stats(speed=0)},
    ):
        await plugin.update()
    assert store.get("network")["data"][0]["bytes_speed_rate_per_sec"] == 0.0


async def test_first_cycle_strips_all_rate_fields(store, config):
    plugin = PluginModel(store, config)
    with _patch_psutil(
        io_counters={"eth0": _io(rx=1000, tx=500, errin=10, errout=5, dropin=2, dropout=1)},
        if_stats={"eth0": _stats(speed=1000)},
    ):
        await plugin.update()
    item = store.get("network")["data"][0]
    for name in ("bytes_recv", "bytes_sent", "errors_in", "errors_out", "dropped_in", "dropped_out"):
        assert name not in item, name


async def test_second_cycle_computes_per_interface_rates(store, config, monkeypatch):
    plugin = PluginModel(store, config)
    now = _fake_now(monkeypatch)

    with _patch_psutil(
        io_counters={
            "eth0": _io(rx=1_000, tx=500),
            "wlan0": _io(rx=2_000, tx=1_000),
        },
        if_stats={"eth0": _stats(speed=1000), "wlan0": _stats(speed=100)},
    ):
        await plugin.update()  # cycle 1

    now[0] = 102.0  # +2 s
    with _patch_psutil(
        io_counters={
            "eth0": _io(rx=3_000, tx=1_500),  # delta rx=2000 / 2s = 1000 B/s
            "wlan0": _io(rx=2_400, tx=1_200),  # delta rx=400 / 2s = 200 B/s
        },
        if_stats={"eth0": _stats(speed=1000), "wlan0": _stats(speed=100)},
    ):
        await plugin.update()

    items = {item["interface_name"]: item for item in store.get("network")["data"]}
    assert items["eth0"]["bytes_recv"] == 1000.0
    assert items["eth0"]["bytes_sent"] == 500.0
    assert items["wlan0"]["bytes_recv"] == 200.0
    assert items["wlan0"]["bytes_sent"] == 100.0


async def test_levels_indexed_by_interface_name(store, config, monkeypatch):
    """Each interface gets its own entry in `_levels`, keyed by interface_name."""
    plugin = PluginModel(store, config)
    now = _fake_now(monkeypatch)

    # 1 Gbit interface ; per-direction capacity = 62_500_000 B/s.
    # Pick rx delta to land between warning (0.8) and critical (0.9) of capacity.
    # 0.85 * 62_500_000 ≈ 53_125_000 B/s over 1 s.
    with _patch_psutil(
        io_counters={"eth0": _io(rx=0, tx=0)},
        if_stats={"eth0": _stats(speed=1000)},
    ):
        await plugin.update()

    now[0] = 101.0
    with _patch_psutil(
        io_counters={"eth0": _io(rx=53_125_000, tx=0)},
        if_stats={"eth0": _stats(speed=1000)},
    ):
        await plugin.update()

    levels = store.get("network")["_levels"]
    assert "eth0" in levels
    assert levels["eth0"]["bytes_recv"] == {"level": "warning", "prominent": False}


async def test_levels_skip_bandwidth_for_unknown_speed(store, config, monkeypatch):
    """An interface whose speed is 0 (lo) gets no bandwidth level — but errors still do."""
    plugin = PluginModel(store, config)
    now = _fake_now(monkeypatch)

    with _patch_psutil(
        io_counters={"lo": _io(rx=0, tx=0, errin=0, errout=0)},
        if_stats={"lo": _stats(speed=0)},
    ):
        await plugin.update()

    now[0] = 101.0
    with _patch_psutil(
        io_counters={"lo": _io(rx=10_000_000, tx=10_000_000, errin=20, errout=0)},
        if_stats={"lo": _stats(speed=0)},
    ):
        await plugin.update()

    levels = store.get("network")["_levels"].get("lo", {})
    assert "bytes_recv" not in levels  # divisor=0 → skipped
    assert "bytes_sent" not in levels
    # errors_in rate = 20/s → at the critical threshold (20).
    assert levels["errors_in"]["level"] == "critical"


async def test_errors_use_absolute_thresholds(store, config, monkeypatch):
    """errors_in / errors_out have no normalize_by — thresholds in absolute err/s."""
    plugin = PluginModel(store, config)
    now = _fake_now(monkeypatch)

    with _patch_psutil(
        io_counters={"eth0": _io(errin=0, errout=0)},
        if_stats={"eth0": _stats(speed=1000)},
    ):
        await plugin.update()

    now[0] = 101.0  # +1 s
    with _patch_psutil(
        io_counters={"eth0": _io(errin=6, errout=0)},  # 6 err/s — between warning (5) and critical (20)
        if_stats={"eth0": _stats(speed=1000)},
    ):
        await plugin.update()

    levels = store.get("network")["_levels"]["eth0"]
    assert levels["errors_in"]["level"] == "warning"


async def test_user_config_overrides_bandwidth_threshold(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[network]\nbytes_recv_warning=0.95\n")
    plugin = PluginModel(store, config)
    now = _fake_now(monkeypatch)

    with _patch_psutil(
        io_counters={"eth0": _io(rx=0)},
        if_stats={"eth0": _stats(speed=1000)},
    ):
        await plugin.update()

    now[0] = 101.0
    # ratio = 0.85 — was warning by default (0.8) ; with override (0.95) → still careful (0.7).
    with _patch_psutil(
        io_counters={"eth0": _io(rx=53_125_000)},
        if_stats={"eth0": _stats(speed=1000)},
    ):
        await plugin.update()

    levels = store.get("network")["_levels"]["eth0"]
    assert levels["bytes_recv"]["level"] == "careful"


async def test_per_interface_threshold_overrides_field_wide(tmp_path, monkeypatch, store):
    """`[network] wlan0_bytes_recv_warning=0.50` applies to wlan0 only."""
    config = _config_with(
        tmp_path,
        monkeypatch,
        "[network]\nbytes_recv_warning=0.80\nwlan0_bytes_recv_warning=0.50\n",
    )
    plugin = PluginModel(store, config)
    now = _fake_now(monkeypatch)

    with _patch_psutil(
        io_counters={"eth0": _io(rx=0), "wlan0": _io(rx=0)},
        if_stats={"eth0": _stats(speed=1000), "wlan0": _stats(speed=1000)},
    ):
        await plugin.update()

    now[0] = 101.0
    # Both interfaces hit ratio 0.75 in this cycle.
    # eth0: 0.75 ≥ careful (default 0.7), 0.75 < warning (0.80 from field-wide) → careful
    # wlan0: 0.75 ≥ warning (0.50 from pk-specific), 0.75 < critical (default 0.9) → warning
    rate = int(0.75 * 62_500_000)
    with _patch_psutil(
        io_counters={"eth0": _io(rx=rate), "wlan0": _io(rx=rate)},
        if_stats={"eth0": _stats(speed=1000), "wlan0": _stats(speed=1000)},
    ):
        await plugin.update()

    levels = store.get("network")["_levels"]
    assert levels["eth0"]["bytes_recv"]["level"] == "careful"
    assert levels["wlan0"]["bytes_recv"]["level"] == "warning"


async def test_hide_drops_matching_interfaces(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[network]\nhide=lo,docker.*\n")
    plugin = PluginModel(store, config)
    with _patch_psutil(
        io_counters={"eth0": _io(), "lo": _io(), "docker0": _io()},
        if_stats={"eth0": _stats(), "lo": _stats(speed=0), "docker0": _stats(speed=0)},
    ):
        await plugin.update()
    names = [item["interface_name"] for item in store.get("network")["data"]]
    assert names == ["eth0"]


async def test_show_keeps_only_matching_interfaces(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[network]\nshow=^eth\n")
    plugin = PluginModel(store, config)
    with _patch_psutil(
        io_counters={"eth0": _io(), "eth1": _io(), "wlan0": _io()},
        if_stats={"eth0": _stats(), "eth1": _stats(), "wlan0": _stats()},
    ):
        await plugin.update()
    names = sorted(item["interface_name"] for item in store.get("network")["data"])
    assert names == ["eth0", "eth1"]


async def test_appearing_interface_has_no_rate_first_cycle(store, config, monkeypatch):
    """A new interface mid-flight has its rates absent on its first cycle."""
    plugin = PluginModel(store, config)
    now = _fake_now(monkeypatch)

    with _patch_psutil(
        io_counters={"eth0": _io(rx=1000, tx=500)},
        if_stats={"eth0": _stats(speed=1000)},
    ):
        await plugin.update()

    now[0] = 101.0
    with _patch_psutil(
        io_counters={"eth0": _io(rx=2000, tx=1000), "wlan0": _io(rx=500, tx=200)},
        if_stats={"eth0": _stats(speed=1000), "wlan0": _stats(speed=100)},
    ):
        await plugin.update()

    items = {item["interface_name"]: item for item in store.get("network")["data"]}
    assert items["eth0"]["bytes_recv"] == 1000.0
    assert "bytes_recv" not in items["wlan0"]


async def test_get_export_strips_internals_and_returns_list(store, config):
    plugin = PluginModel(store, config)
    with _patch_psutil(
        io_counters={"eth0": _io(rx=1000)},
        if_stats={"eth0": _stats(speed=1000)},
    ):
        await plugin.update()
    exported = plugin.get_export()
    assert isinstance(exported, list)
    assert exported[0]["interface_name"] == "eth0"
    assert "_levels" not in exported[0]
    assert "time_since_update" not in exported[0]


async def test_is_up_flows_through(store, config):
    plugin = PluginModel(store, config)
    with _patch_psutil(
        io_counters={"eth0": _io(), "wlan0": _io()},
        if_stats={"eth0": _stats(isup=True), "wlan0": _stats(isup=False)},
    ):
        await plugin.update()
    items = {item["interface_name"]: item for item in store.get("network")["data"]}
    assert items["eth0"]["is_up"] is True
    assert items["wlan0"]["is_up"] is False
