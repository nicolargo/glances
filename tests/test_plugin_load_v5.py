#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `load` plugin.

V4-aligned alert semantics:
- `min1`  is **not watched** (too volatile).
- `min5`  is watched, `prominent: False` (early-warning, font-only render).
- `min15` is watched, `prominent: True`  (sustained-load, background highlight).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.load.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5

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
    assert plugin.plugin_name == "load"
    assert plugin.IS_COLLECTION is False


def test_min1_is_not_watched(store, config):
    plugin = PluginModel(store, config)
    assert plugin._fields["min1"].get("watched", False) is False


def test_min5_is_watched_non_prominent(store, config):
    schema = PluginModel(store, config)._fields["min5"]
    assert schema["watched"] is True
    assert schema["watch_direction"] == "high"
    assert schema["prominent"] is False
    assert "default_thresholds" in schema


def test_min15_is_watched_prominent(store, config):
    schema = PluginModel(store, config)._fields["min15"]
    assert schema["watched"] is True
    assert schema["watch_direction"] == "high"
    assert schema["prominent"] is True
    assert "default_thresholds" in schema


# ---------------------------------------------------------- update pipeline


async def test_update_writes_loadavg_to_store(store, config):
    plugin = PluginModel(store, config)
    with (
        patch("glances.plugins.load.model_v5.psutil.getloadavg", return_value=(0.5, 0.7, 1.2)),
        patch("glances.plugins.load.model_v5.psutil.cpu_count", return_value=4),
    ):
        await plugin.update()

    payload = store.get("load")
    assert payload is not None
    assert payload["min1"] == 0.5
    assert payload["min5"] == 0.7
    assert payload["min15"] == 1.2
    assert payload["cpucore"] == 4


async def test_update_swallows_loadavg_oserror(store, config):
    """OSError on getloadavg() must not crash the update loop."""
    plugin = PluginModel(store, config)
    with patch("glances.plugins.load.model_v5.psutil.getloadavg", side_effect=OSError):
        await plugin.update()
    # Empty stats accepted; payload reflects the metadata layer only.
    payload = store.get("load")
    assert payload is not None
    assert "min1" not in payload


# ---------------------------------------------------------- _levels (per-core normalization)


async def test_min1_never_in_levels(store, config):
    """min1 is too volatile — must never produce a level entry."""
    plugin = PluginModel(store, config)
    with (
        patch("glances.plugins.load.model_v5.psutil.getloadavg", return_value=(99.0, 0.0, 0.0)),
        patch("glances.plugins.load.model_v5.psutil.cpu_count", return_value=4),
    ):
        await plugin.update()
    assert "min1" not in store.get("load")["_levels"]


async def test_min5_level_normalized_by_cpucore_non_prominent(store, config):
    """Default warning=1.0 per core. With 4 cores and min5=4.0 → warning, prominent False."""
    plugin = PluginModel(store, config)
    with (
        patch("glances.plugins.load.model_v5.psutil.getloadavg", return_value=(0.0, 4.0, 0.0)),
        patch("glances.plugins.load.model_v5.psutil.cpu_count", return_value=4),
    ):
        await plugin.update()
    assert store.get("load")["_levels"]["min5"] == {"level": "warning", "prominent": False}


async def test_min15_level_normalized_by_cpucore_prominent(store, config):
    """Default critical=5.0 per core. With 2 cores and min15=11.0 → critical, prominent True."""
    plugin = PluginModel(store, config)
    with (
        patch("glances.plugins.load.model_v5.psutil.getloadavg", return_value=(0.0, 0.0, 11.0)),
        patch("glances.plugins.load.model_v5.psutil.cpu_count", return_value=2),
    ):
        await plugin.update()
    assert store.get("load")["_levels"]["min15"] == {"level": "critical", "prominent": True}


async def test_levels_ok_when_below_careful_per_core(store, config):
    """Default careful=0.7 per core. With 4 cores and min5=2.0 → 0.5/core → ok."""
    plugin = PluginModel(store, config)
    with (
        patch("glances.plugins.load.model_v5.psutil.getloadavg", return_value=(0.0, 2.0, 2.0)),
        patch("glances.plugins.load.model_v5.psutil.cpu_count", return_value=4),
    ):
        await plugin.update()
    levels = store.get("load")["_levels"]
    assert levels["min5"]["level"] == "ok"
    assert levels["min15"]["level"] == "ok"


async def test_levels_fall_back_to_one_core_when_cpucount_unknown(store, config):
    """psutil.cpu_count returning None → divide by 1 (defensive)."""
    plugin = PluginModel(store, config)
    with (
        patch("glances.plugins.load.model_v5.psutil.getloadavg", return_value=(0.0, 0.8, 0.8)),
        patch("glances.plugins.load.model_v5.psutil.cpu_count", return_value=None),
    ):
        await plugin.update()
    # 0.8 / 1 = 0.8 → between 0.7 (careful) and 1.0 (warning) → careful
    assert store.get("load")["_levels"]["min5"]["level"] == "careful"
    assert store.get("load")["_levels"]["min15"]["level"] == "careful"


async def test_user_config_overrides_default_threshold(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[load]\nwarning=2.0\n")
    plugin = PluginModel(store, config)
    with (
        patch("glances.plugins.load.model_v5.psutil.getloadavg", return_value=(0.0, 4.0, 4.0)),
        patch("glances.plugins.load.model_v5.psutil.cpu_count", return_value=4),
    ):
        await plugin.update()
    # 4.0 / 4 = 1.0 — was `warning` at default 1.0; with warning=2.0 the value
    # is below warning → careful (default careful=0.7). Override applies to
    # both watched fields since the bare key is shared.
    assert store.get("load")["_levels"]["min5"]["level"] == "careful"
    assert store.get("load")["_levels"]["min15"]["level"] == "careful"


async def test_field_prefixed_config_targets_one_field_only(tmp_path, monkeypatch, store):
    """`min15_warning=2.0` overrides only min15, leaving min5 at default warning=1.0."""
    config = _config_with(tmp_path, monkeypatch, "[load]\nmin15_warning=2.0\n")
    plugin = PluginModel(store, config)
    with (
        patch("glances.plugins.load.model_v5.psutil.getloadavg", return_value=(0.0, 4.0, 4.0)),
        patch("glances.plugins.load.model_v5.psutil.cpu_count", return_value=4),
    ):
        await plugin.update()
    # min5 (warning=1.0/core × 4 = 4.0) → value 4.0 → warning
    # min15 (warning=2.0/core × 4 = 8.0) → value 4.0 → careful
    assert store.get("load")["_levels"]["min5"]["level"] == "warning"
    assert store.get("load")["_levels"]["min15"]["level"] == "careful"


async def test_no_loadavg_keeps_levels_empty(store, config):
    """If getloadavg fails and _grab_stats returns {}, _levels stays empty."""
    plugin = PluginModel(store, config)
    with patch("glances.plugins.load.model_v5.psutil.getloadavg", side_effect=AttributeError):
        await plugin.update()
    assert store.get("load")["_levels"] == {}
