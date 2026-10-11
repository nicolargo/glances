#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `uptime` plugin."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from glances.config import GlancesConfig
from glances.plugins.uptime.model import PluginModel
from glances.stats_store import StatsStore


@pytest.fixture
def store() -> StatsStore:
    return StatsStore()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfig:
    monkeypatch.setattr(GlancesConfig, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfig()


def test_plugin_identity(store, config):
    plugin = PluginModel(store, config)
    assert plugin.plugin_name == "uptime"
    assert plugin.IS_COLLECTION is False
    assert plugin.DISPLAY_IN_TUI is True


async def test_update_writes_seconds_since_boot(store, config):
    plugin = PluginModel(store, config)
    with (
        patch("glances.plugins.uptime.model.time.time", return_value=1_000_000.0),
        patch("glances.plugins.uptime.model.psutil.boot_time", return_value=1_000_000.0 - 3600),
    ):
        await plugin.update()
    payload = store.get("uptime")
    assert payload is not None
    assert payload["seconds"] == 3600


async def test_seconds_is_exportable(store, config):
    plugin = PluginModel(store, config)
    with (
        patch("glances.plugins.uptime.model.time.time", return_value=1_000_000.0),
        patch("glances.plugins.uptime.model.psutil.boot_time", return_value=1_000_000.0 - 120),
    ):
        await plugin.update()
    exported = plugin.get_export()
    assert exported == {"seconds": 120}


async def test_grab_tolerates_psutil_failure(store, config):
    plugin = PluginModel(store, config)
    with patch("glances.plugins.uptime.model.psutil.boot_time", side_effect=OSError("nope")):
        await plugin.update()
    assert store.get("uptime") == {"_levels": {}, "time_since_update": 0.0}
