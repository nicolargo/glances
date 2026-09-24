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

import socket
from collections import namedtuple
from contextlib import ExitStack
from unittest.mock import patch

import psutil
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
NetAddr = namedtuple("snicaddr", ["family", "address", "netmask", "broadcast", "ptp"])


def _link_addr() -> NetAddr:
    return NetAddr(family=psutil.AF_LINK, address="aa:bb:cc:dd:ee:ff", netmask=None, broadcast=None, ptp=None)


def _ip_addr() -> NetAddr:
    return NetAddr(family=socket.AF_INET, address="192.0.2.1", netmask="255.255.255.0", broadcast=None, ptp=None)


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


def _patch_psutil(io_counters: dict, if_stats: dict, if_addrs: dict | None = None) -> ExitStack:
    """Patch psutil.net_io_counters and psutil.net_if_stats with deterministic values.

    ``if_addrs`` is only patched when given — ``hide_no_ip`` (the only
    consumer of ``psutil.net_if_addrs``) defaults to False, so most tests
    never need it and must not depend on the real psutil call.
    """
    stack = ExitStack()
    stack.enter_context(patch("glances.plugins.network.model_v5.psutil.net_io_counters", return_value=io_counters))
    stack.enter_context(patch("glances.plugins.network.model_v5.psutil.net_if_stats", return_value=if_stats))
    if if_addrs is not None:
        stack.enter_context(patch("glances.plugins.network.model_v5.psutil.net_if_addrs", return_value=if_addrs))
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
    """speed=1000 Mbit/s → bytes_speed_rate_per_sec = 1e9/8 = 125e6 B/s.

    Full duplex gives each direction the whole link speed — no split (v4 parity).
    """
    plugin = PluginModel(store, config)
    with _patch_psutil(
        io_counters={"eth0": _io(rx=0, tx=0)},
        if_stats={"eth0": _stats(speed=1000)},
    ):
        await plugin.update()
    item = store.get("network")["data"][0]
    assert item["bytes_speed_rate_per_sec"] == 125_000_000.0


async def test_bytes_speed_rate_per_sec_is_zero_for_unknown_speed(store, config):
    """psutil returns speed=0 for loopback, virtual interfaces → field is 0."""
    plugin = PluginModel(store, config)
    with _patch_psutil(
        io_counters={"lo": _io(rx=0, tx=0)},
        if_stats={"lo": _stats(speed=0)},
    ):
        await plugin.update()
    assert store.get("network")["data"][0]["bytes_speed_rate_per_sec"] == 0.0


async def test_first_cycle_rate_fields_are_none(store, config):
    plugin = PluginModel(store, config)
    with _patch_psutil(
        io_counters={"eth0": _io(rx=1000, tx=500, errin=10, errout=5, dropin=2, dropout=1)},
        if_stats={"eth0": _stats(speed=1000)},
    ):
        await plugin.update()
    item = store.get("network")["data"][0]
    for name in ("bytes_recv", "bytes_sent", "errors_in", "errors_out", "dropped_in", "dropped_out"):
        assert name in item, name
        assert item[name] is None, name


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

    # 1 Gbit interface ; per-direction capacity = 125_000_000 B/s.
    # Pick rx delta to land between warning (0.8) and critical (0.9) of capacity.
    # 0.85 * 125_000_000 = 106_250_000 B/s over 1 s.
    with _patch_psutil(
        io_counters={"eth0": _io(rx=0, tx=0)},
        if_stats={"eth0": _stats(speed=1000)},
    ):
        await plugin.update()

    now[0] = 101.0
    with _patch_psutil(
        io_counters={"eth0": _io(rx=106_250_000, tx=0)},
        if_stats={"eth0": _stats(speed=1000)},
    ):
        await plugin.update()

    levels = store.get("network")["_levels"]
    assert "eth0" in levels
    assert levels["eth0"]["bytes_recv"] == {"level": "warning", "prominent": False}


async def test_bandwidth_level_uses_full_link_speed_per_direction(store, config, monkeypatch):
    """425 Mbit/s received on a 1 Gbit full-duplex link is 42.5 % of capacity:
    OK, as in v4. Halving the capacity made it 0.85 → warning."""
    plugin = PluginModel(store, config)
    now = _fake_now(monkeypatch)

    with _patch_psutil(io_counters={"eth0": _io(rx=0, tx=0)}, if_stats={"eth0": _stats(speed=1000)}):
        await plugin.update()

    now[0] = 101.0
    with _patch_psutil(
        io_counters={"eth0": _io(rx=425_000_000 // 8, tx=0)},
        if_stats={"eth0": _stats(speed=1000)},
    ):
        await plugin.update()

    assert store.get("network")["_levels"]["eth0"]["bytes_recv"]["level"] == "ok"


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
        io_counters={"eth0": _io(rx=106_250_000)},
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
    rate = int(0.75 * 125_000_000)
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


async def test_hide_no_up_off_by_default_keeps_down_interfaces(store, config):
    """`[network] hide_no_up` defaults to False — v4 parity, `__init__.py:96`."""
    plugin = PluginModel(store, config)
    with _patch_psutil(
        io_counters={"eth0": _io(), "eth1": _io()},
        if_stats={"eth0": _stats(isup=True), "eth1": _stats(isup=False)},
    ):
        await plugin.update()
    names = sorted(item["interface_name"] for item in store.get("network")["data"])
    assert names == ["eth0", "eth1"]


async def test_hide_no_up_drops_down_interfaces_when_enabled(tmp_path, monkeypatch, store):
    """`hide_no_up=True` drops interfaces whose psutil status is not up
    (v4 `network/__init__.py:165-166`) — the item never reaches the payload."""
    config = _config_with(tmp_path, monkeypatch, "[network]\nhide_no_up=True\n")
    plugin = PluginModel(store, config)
    with _patch_psutil(
        io_counters={"eth0": _io(), "eth1": _io()},
        if_stats={"eth0": _stats(isup=True), "eth1": _stats(isup=False)},
    ):
        await plugin.update()
    names = [item["interface_name"] for item in store.get("network")["data"]]
    assert names == ["eth0"]


async def test_hide_no_ip_off_by_default_keeps_link_only_interfaces(store, config):
    """`[network] hide_no_ip` defaults to False — v4 parity, `__init__.py:97`."""
    plugin = PluginModel(store, config)
    with _patch_psutil(
        io_counters={"eth0": _io()},
        if_stats={"eth0": _stats()},
        if_addrs={"eth0": [_link_addr()]},
    ):
        await plugin.update()
    names = [item["interface_name"] for item in store.get("network")["data"]]
    assert names == ["eth0"]


async def test_hide_no_ip_drops_link_only_interfaces_when_enabled(tmp_path, monkeypatch, store):
    """`hide_no_ip=True` drops interfaces with no address of a family other
    than AF_LINK (v4 `network/__init__.py:167-172`)."""
    config = _config_with(tmp_path, monkeypatch, "[network]\nhide_no_ip=True\n")
    plugin = PluginModel(store, config)
    with _patch_psutil(
        io_counters={"eth0": _io(), "lo": _io()},
        if_stats={"eth0": _stats(), "lo": _stats()},
        if_addrs={"eth0": [_link_addr(), _ip_addr()], "lo": [_link_addr()]},
    ):
        await plugin.update()
    names = [item["interface_name"] for item in store.get("network")["data"]]
    assert names == ["eth0"]


async def test_hide_no_ip_drops_interface_absent_from_net_if_addrs(tmp_path, monkeypatch, store):
    """v4 also drops an interface missing from `net_if_addrs()` entirely
    (`k in net_addrs` guard, `network/__init__.py:169-171`)."""
    config = _config_with(tmp_path, monkeypatch, "[network]\nhide_no_ip=True\n")
    plugin = PluginModel(store, config)
    with _patch_psutil(
        io_counters={"eth0": _io(), "ghost": _io()},
        if_stats={"eth0": _stats(), "ghost": _stats()},
        if_addrs={"eth0": [_ip_addr()]},
    ):
        await plugin.update()
    names = [item["interface_name"] for item in store.get("network")["data"]]
    assert names == ["eth0"]


async def test_appearing_interface_has_none_rate_first_cycle(store, config, monkeypatch):
    """A new interface mid-flight has its rates set to None on its first cycle."""
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
    assert "bytes_recv" in items["wlan0"]
    assert items["wlan0"]["bytes_recv"] is None


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


# ---------------------------------------------------------- alias (design §5.5)


async def test_alias_published_for_matching_interface(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[network]\nalias=wlan0:HomeWifi\n")
    plugin = PluginModel(store, config)
    with _patch_psutil(
        io_counters={"eth0": _io(), "wlan0": _io()},
        if_stats={"eth0": _stats(), "wlan0": _stats()},
    ):
        await plugin.update()
    data = {item["interface_name"]: item for item in store.get("network")["data"]}
    assert data["wlan0"]["alias"] == "HomeWifi"
    assert "alias" not in data["eth0"]


async def test_alias_does_not_break_levels_or_per_item_override(tmp_path, monkeypatch, store):
    """[network] alias=wlan0:HomeWifi must not rename the primary key, nor
    change `_levels` keying, nor the per-interface threshold override
    (design §5.5) — same scenario as
    `test_per_interface_threshold_overrides_field_wide`, with an alias added."""
    config = _config_with(
        tmp_path,
        monkeypatch,
        "[network]\nalias=wlan0:HomeWifi\nbytes_recv_warning=0.80\nwlan0_bytes_recv_warning=0.50\n",
    )
    plugin = PluginModel(store, config)
    now = _fake_now(monkeypatch)

    with _patch_psutil(
        io_counters={"eth0": _io(rx=0), "wlan0": _io(rx=0)},
        if_stats={"eth0": _stats(speed=1000), "wlan0": _stats(speed=1000)},
    ):
        await plugin.update()

    now[0] = 101.0
    rate = int(0.75 * 125_000_000)
    with _patch_psutil(
        io_counters={"eth0": _io(rx=rate), "wlan0": _io(rx=rate)},
        if_stats={"eth0": _stats(speed=1000), "wlan0": _stats(speed=1000)},
    ):
        await plugin.update()

    data = {item["interface_name"]: item for item in store.get("network")["data"]}
    assert data["wlan0"]["interface_name"] == "wlan0"  # primary key untouched
    assert data["wlan0"]["alias"] == "HomeWifi"
    assert "alias" not in data["eth0"]

    levels = store.get("network")["_levels"]
    assert "wlan0" in levels  # keyed by the raw pk value, not "HomeWifi"
    assert "HomeWifi" not in levels
    assert levels["eth0"]["bytes_recv"]["level"] == "careful"
    assert levels["wlan0"]["bytes_recv"]["level"] == "warning"


# ---------------------------------------------------------- hide_zero / hide_threshold_bytes (design §5.1)


def test_hide_zero_fields_declared(store, config):
    assert PluginModel.HIDE_ZERO_FIELDS == ["bytes_recv", "bytes_sent"]


async def test_hide_zero_off_by_default_never_hides(store, config, monkeypatch):
    """`[network] hide_zero` ships False in conf/glances.conf — `hidden` stays False."""
    plugin = PluginModel(store, config)
    now = _fake_now(monkeypatch)

    with _patch_psutil(io_counters={"lo": _io(rx=0, tx=0)}, if_stats={"lo": _stats(speed=0)}):
        await plugin.update()

    now[0] = 101.0
    with _patch_psutil(io_counters={"lo": _io(rx=0, tx=0)}, if_stats={"lo": _stats(speed=0)}):
        await plugin.update()

    item = store.get("network")["data"][0]
    assert item["hidden"] is False


async def test_hide_zero_reads_threshold_and_unhides_above_it(tmp_path, monkeypatch, store):
    """v4 regression d88f9d98: network must actually read hide_threshold_bytes."""
    config = _config_with(tmp_path, monkeypatch, "[network]\nhide_zero=True\nhide_threshold_bytes=1000\n")
    plugin = PluginModel(store, config)
    now = _fake_now(monkeypatch)

    with _patch_psutil(io_counters={"eth0": _io(rx=0, tx=0)}, if_stats={"eth0": _stats(speed=1000)}):
        await plugin.update()  # cycle 1 — rate None, hidden

    assert store.get("network")["data"][0]["hidden"] is True

    now[0] = 101.0
    with _patch_psutil(io_counters={"eth0": _io(rx=1000, tx=0)}, if_stats={"eth0": _stats(speed=1000)}):
        await plugin.update()  # rx rate == 1000 == threshold -> strict '>' -> still hidden

    assert store.get("network")["data"][0]["hidden"] is True

    now[0] = 102.0
    with _patch_psutil(io_counters={"eth0": _io(rx=3000, tx=0)}, if_stats={"eth0": _stats(speed=1000)}):
        await plugin.update()  # delta 2000/1s = 2000 > 1000 -> unhide

    assert store.get("network")["data"][0]["hidden"] is False

    now[0] = 103.0
    with _patch_psutil(io_counters={"eth0": _io(rx=3000, tx=0)}, if_stats={"eth0": _stats(speed=1000)}):
        await plugin.update()  # rate back to 0 -> sticky: stays visible

    assert store.get("network")["data"][0]["hidden"] is False


async def test_hide_zero_row_visible_when_only_one_direction_moves(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[network]\nhide_zero=True\n")
    plugin = PluginModel(store, config)
    now = _fake_now(monkeypatch)

    with _patch_psutil(io_counters={"eth0": _io(rx=0, tx=0)}, if_stats={"eth0": _stats(speed=1000)}):
        await plugin.update()

    now[0] = 101.0
    with _patch_psutil(io_counters={"eth0": _io(rx=500, tx=0)}, if_stats={"eth0": _stats(speed=1000)}):
        await plugin.update()  # rx moves, tx stays at 0

    assert store.get("network")["data"][0]["hidden"] is False


# ---------------------------------------------------------- `U` cumulative counters


async def test_cumulative_counters_ride_beside_the_rates(store, config, monkeypatch):
    """`bytes_recv` becomes a rate; the raw counter the `U` key renders
    (v4 `network_cumul`) stays in `*_cumul`, from cycle 1 on."""
    plugin = PluginModel(store, config)
    now = _fake_now(monkeypatch)
    with _patch_psutil(io_counters={"eth0": _io(rx=1_000, tx=500)}, if_stats={"eth0": _stats()}):
        await plugin.update()
    first = store.get("network")["data"][0]
    assert (first["bytes_recv_cumul"], first["bytes_sent_cumul"]) == (1_000, 500)

    now[0] = 102.0
    with _patch_psutil(io_counters={"eth0": _io(rx=3_000, tx=1_500)}, if_stats={"eth0": _stats()}):
        await plugin.update()
    second = store.get("network")["data"][0]
    assert second["bytes_recv"] == 1000.0
    assert (second["bytes_recv_cumul"], second["bytes_sent_cumul"]) == (3_000, 1_500)


def test_cumulative_fields_are_internal_and_exported(store, config):
    fields = PluginModel(store, config)._fields
    for name, label in (("bytes_recv_cumul", "Rx"), ("bytes_sent_cumul", "Tx")):
        assert fields[name]["internal"] is True
        assert fields[name].get("exportable", True) is True
        assert fields[name]["short_name"] == label
        assert not fields[name].get("rate")
