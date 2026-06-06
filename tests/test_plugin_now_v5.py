#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `now` plugin."""

from __future__ import annotations

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.now.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


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


def test_plugin_identity(store, config):
    plugin = PluginModel(store, config)
    assert plugin.plugin_name == "now"
    assert plugin.IS_COLLECTION is False
    assert plugin.DISPLAY_IN_TUI is True


async def test_update_writes_iso_and_custom(store, config):
    plugin = PluginModel(store, config)
    await plugin.update()
    payload = store.get("now")
    assert "iso" in payload and "custom" in payload
    assert "T" in payload["iso"]
    assert payload["custom"]


async def test_custom_format_from_config(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[global]\nstrftime_format=%Y\n")
    plugin = PluginModel(store, config)
    await plugin.update()
    custom = store.get("now")["custom"]
    assert len(custom) == 4 and custom.isdigit()
