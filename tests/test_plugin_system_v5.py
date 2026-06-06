#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `system` plugin."""

from __future__ import annotations

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.system.model_v5 import PluginModel
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
    assert plugin.plugin_name == "system"
    assert plugin.IS_COLLECTION is False
    assert plugin.DISPLAY_IN_TUI is True


async def test_update_collects_linux_system_info(store, config, monkeypatch):
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.system", lambda: "Linux")
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.node", lambda: "myhost")
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.architecture", lambda: ("64bit", ""))
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.release", lambda: "6.8.0-generic")
    monkeypatch.setattr("glances.plugins.system.model_v5._linux_distro", lambda: "Ubuntu 24.04")
    plugin = PluginModel(store, config)
    await plugin.update()
    payload = store.get("system")
    assert payload["os_name"] == "Linux"
    assert payload["hostname"] == "myhost"
    assert payload["platform"] == "64bit"
    assert payload["linux_distro"] == "Ubuntu 24.04"
    assert payload["os_version"] == "6.8.0-generic"
    assert "Ubuntu 24.04" in payload["hr_name"]
    assert "64bit" in payload["hr_name"]


async def test_system_info_msg_overrides_hr_name(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[system]\nsystem_info_msg={hostname} rocks\n")
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.system", lambda: "Linux")
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.node", lambda: "myhost")
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.architecture", lambda: ("64bit", ""))
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.release", lambda: "6.8.0")
    monkeypatch.setattr("glances.plugins.system.model_v5._linux_distro", lambda: "Ubuntu 24.04")
    plugin = PluginModel(store, config)
    await plugin.update()
    assert store.get("system")["hr_name"] == "myhost rocks"


async def test_no_watched_field_means_empty_levels(store, config, monkeypatch):
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.system", lambda: "Linux")
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.node", lambda: "h")
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.architecture", lambda: ("64bit", ""))
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.release", lambda: "6")
    monkeypatch.setattr("glances.plugins.system.model_v5._linux_distro", lambda: "Ubuntu")
    plugin = PluginModel(store, config)
    await plugin.update()
    assert store.get("system")["_levels"] == {}
