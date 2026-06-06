#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `core` plugin (REST-only)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.core.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


def test_plugin_identity(store, config):
    plugin = PluginModel(store, config)
    assert plugin.plugin_name == "core"
    assert plugin.IS_COLLECTION is False
    assert plugin.DISPLAY_IN_TUI is False


async def test_update_writes_phys_and_log(store, config):
    plugin = PluginModel(store, config)
    with patch("glances.plugins.core.model_v5.psutil.cpu_count", side_effect=lambda logical=True: 4 if logical else 2):
        await plugin.update()
    payload = store.get("core")
    assert payload["phys"] == 2
    assert payload["log"] == 4


async def test_grab_tolerates_failure(store, config):
    plugin = PluginModel(store, config)
    with patch("glances.plugins.core.model_v5.psutil.cpu_count", side_effect=OSError("nope")):
        await plugin.update()
    assert store.get("core") == {"_levels": {}, "time_since_update": 0.0}
