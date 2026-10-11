#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the version + psutilversion plugins (REST-only)."""

from __future__ import annotations

import pytest

from glances.config import GlancesConfig
from glances.plugins.psutilversion.model import PluginModel as PsutilVersionPlugin
from glances.plugins.version.model import PluginModel as VersionPlugin
from glances.stats_store import StatsStore


@pytest.fixture
def store() -> StatsStore:
    return StatsStore()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfig:
    monkeypatch.setattr(GlancesConfig, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfig()


def test_version_identity(store, config):
    plugin = VersionPlugin(store, config)
    assert plugin.plugin_name == "version"
    assert plugin.DISPLAY_IN_TUI is False


def test_psutilversion_identity(store, config):
    plugin = PsutilVersionPlugin(store, config)
    assert plugin.plugin_name == "psutilversion"
    assert plugin.DISPLAY_IN_TUI is False


async def test_version_reports_glances_version(store, config):
    from glances import __version__

    plugin = VersionPlugin(store, config)
    await plugin.update()
    assert store.get("version")["version"] == __version__


async def test_psutilversion_reports_dotted_psutil_version(store, config):
    from glances import psutil_version_info

    plugin = PsutilVersionPlugin(store, config)
    await plugin.update()
    expected = ".".join(str(i) for i in psutil_version_info)
    assert store.get("psutilversion")["version"] == expected
