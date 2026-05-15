#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `memswap` plugin (scalar)."""

from __future__ import annotations

from collections import namedtuple
from unittest.mock import patch

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.memswap.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5

# psutil result stub ------------------------------------------------------

SwapMemory = namedtuple("sswap", ["total", "used", "free", "percent", "sin", "sout"])


def _swap(percent: float = 25.0, sin: int = 0, sout: int = 0) -> SwapMemory:
    total = 16 * 1024**3  # 16 GiB
    used = int(total * percent / 100.0)
    return SwapMemory(total=total, used=used, free=total - used, percent=percent, sin=sin, sout=sout)


# ----------------------------------------------------------- fixtures


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


# ---------------------------------------------------------- contract


def test_plugin_identity(store, config):
    plugin = PluginModel(store, config)
    assert plugin.plugin_name == "memswap"
    assert plugin.IS_COLLECTION is False


def test_percent_is_watched_prominent(store, config):
    schema = PluginModel(store, config)._fields["percent"]
    assert schema["watched"] is True
    assert schema["prominent"] is True
    assert schema["unit"] == "percent"


def test_total_used_free_are_bytes_not_watched(store, config):
    fields = PluginModel(store, config)._fields
    for name in ("total", "used", "free"):
        assert fields[name]["unit"] == "bytes", name
        assert fields[name].get("watched", False) is False, name


def test_sin_sout_are_rate_counters(store, config):
    """sin/sout are cumulative on psutil — v5 converts them to bytes/s."""
    fields = PluginModel(store, config)._fields
    for name in ("sin", "sout"):
        assert fields[name].get("rate") is True, name


# ---------------------------------------------------------- update pipeline


async def test_update_writes_swap_fields(store, config):
    plugin = PluginModel(store, config)
    with patch("glances.plugins.memswap.model_v5.psutil.swap_memory", return_value=_swap(percent=30.0)):
        await plugin.update()
    payload = store.get("memswap")
    assert payload["percent"] == 30.0
    assert payload["total"] == 16 * 1024**3
    assert payload["used"] > 0
    assert payload["free"] > 0


async def test_update_handles_no_swap_configured(store, config):
    """Illumos / OpenBSD without a swap file: psutil raises — store must not crash."""
    plugin = PluginModel(store, config)
    with patch("glances.plugins.memswap.model_v5.psutil.swap_memory", side_effect=OSError("no swap")):
        await plugin.update()
    # An empty payload is acceptable — the store key may be absent or empty.
    payload = store.get("memswap")
    assert payload is None or payload == {} or payload.get("total") is None


async def test_first_cycle_strips_rate_fields(store, config):
    """sin/sout absent on cycle 1 — no previous sample to diff against."""
    plugin = PluginModel(store, config)
    with patch("glances.plugins.memswap.model_v5.psutil.swap_memory", return_value=_swap()):
        await plugin.update()
    payload = store.get("memswap")
    assert "sin" not in payload
    assert "sout" not in payload


async def test_second_cycle_computes_swap_rates(store, config, monkeypatch):
    """Second cycle: sin/sout become per-second rates."""
    plugin = PluginModel(store, config)

    fake_now = [100.0]
    import glances.plugins.plugin.base_v5 as base_module

    monkeypatch.setattr(base_module.time, "monotonic", lambda: fake_now[0])

    with patch("glances.plugins.memswap.model_v5.psutil.swap_memory", return_value=_swap(sin=1_000_000, sout=500_000)):
        await plugin.update()

    fake_now[0] = 101.0  # +1 s elapsed
    with patch("glances.plugins.memswap.model_v5.psutil.swap_memory", return_value=_swap(sin=2_000_000, sout=600_000)):
        await plugin.update()

    payload = store.get("memswap")
    # delta = 1_000_000 / 1s = 1_000_000 bytes/s
    assert payload["sin"] == 1_000_000.0
    # delta = 100_000 / 1s = 100_000 bytes/s
    assert payload["sout"] == 100_000.0


# ---------------------------------------------------------- _levels


async def test_percent_level_uses_default_thresholds(store, config):
    plugin = PluginModel(store, config)
    with patch("glances.plugins.memswap.model_v5.psutil.swap_memory", return_value=_swap(percent=85.0)):
        await plugin.update()
    # 85 between warning (80) and critical (95) → warning, prominent.
    # Default ladder for swap is 60/80/95 (looser than mem's 50/70/90).
    assert store.get("memswap")["_levels"]["percent"] == {"level": "warning", "prominent": True}


async def test_percent_level_ok_when_low(store, config):
    plugin = PluginModel(store, config)
    with patch("glances.plugins.memswap.model_v5.psutil.swap_memory", return_value=_swap(percent=5.0)):
        await plugin.update()
    assert store.get("memswap")["_levels"]["percent"]["level"] == "ok"


# ---------------------------------------------------------- export


async def test_get_export_strips_internals_and_levels(store, config):
    plugin = PluginModel(store, config)
    with patch("glances.plugins.memswap.model_v5.psutil.swap_memory", return_value=_swap()):
        await plugin.update()
    exported = plugin.get_export()
    assert "_levels" not in exported
    assert "time_since_update" not in exported
    assert exported["percent"] == 25.0
