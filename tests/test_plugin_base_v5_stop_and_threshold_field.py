#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Base-class extension points added for the G6A containers port:
- ``GlancesPluginBase.stop()`` teardown hook (default no-op).
- ``threshold_field`` schema alias in threshold resolution.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5


class _NoopCollection(GlancesPluginBase[list]):
    plugin_name: ClassVar[str] = "noop_collection"
    IS_COLLECTION: ClassVar[bool] = True
    fields_description: ClassVar[dict] = {"name": {"primary_key": True}}

    async def _grab_stats(self) -> list:
        return []


# ---------------------------------------------------------- fixtures


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path: Path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


def _mk(store, config, cls=_NoopCollection):
    return cls(store, config)


def test_stop_default_is_noop(store, config):
    plugin = _mk(store, config)
    # Default stop() must exist and do nothing (no raise, no return value).
    assert plugin.stop() is None


# ---------------------------------------------------- threshold_field alias


@pytest.fixture
def store_with():
    """Factory fixture — returns a callable producing a fresh StatsStoreV5."""

    def _factory() -> StatsStoreV5:
        return StatsStoreV5()

    return _factory


@pytest.fixture
def config_with(tmp_path: Path, monkeypatch):
    """Factory fixture — returns a callable that builds a real GlancesConfigV5
    from a ``{section: {key: value}}`` dict, backed by a temp glances.conf.
    """
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    xdg = tmp_path / "xdg"
    cfg_dir = xdg / "glances"
    cfg_dir.mkdir(parents=True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))

    def _factory(sections: dict[str, dict[str, str]]) -> GlancesConfigV5:
        body = ""
        for section, options in sections.items():
            body += f"[{section}]\n"
            for key, value in options.items():
                body += f"{key}={value}\n"
        (cfg_dir / "glances.conf").write_text(body)
        return GlancesConfigV5()

    return _factory


class _AliasCollection(GlancesPluginBase[list]):
    plugin_name: ClassVar[str] = "alias_collection"
    IS_COLLECTION: ClassVar[bool] = True
    fields_description: ClassVar[dict] = {
        "name": {"primary_key": True},
        # Value under `cpu_percent`, thresholds under the `cpu` prefix.
        "cpu_percent": {
            "watched": True,
            "watch_direction": "high",
            "threshold_field": "cpu",
        },
    }

    async def _grab_stats(self) -> list:
        return []


def test_threshold_field_alias_resolves_prefixed_keys(store_with, config_with):
    # Config uses the v4-style `cpu_*` prefix, NOT `cpu_percent_*`.
    config = config_with({"alias_collection": {"cpu_warning": "70", "cpu_critical": "90"}})
    plugin = _AliasCollection(store_with(), config)
    plugin._stats = [{"name": "web", "cpu_percent": 75.0}]
    plugin._derived_parameters()
    assert plugin._levels["web"]["cpu_percent"]["level"] == "warning"


def test_threshold_field_alias_resolves_per_pk_override(store_with, config_with):
    config = config_with({"alias_collection": {"cpu_warning": "70", "web_cpu_warning": "10"}})
    plugin = _AliasCollection(store_with(), config)
    plugin._stats = [{"name": "web", "cpu_percent": 15.0}]
    plugin._derived_parameters()
    # Per-container override `web_cpu_warning=10` wins → 15 ≥ 10 → warning.
    assert plugin._levels["web"]["cpu_percent"]["level"] == "warning"


def test_absent_threshold_field_preserves_field_name_default(store_with, config_with):
    # A field WITHOUT threshold_field keeps the field-name prefix.
    class _Plain(GlancesPluginBase[list]):
        plugin_name = "plain_collection"
        IS_COLLECTION = True
        fields_description = {
            "name": {"primary_key": True},
            "cpu_percent": {"watched": True, "watch_direction": "high"},
        }

        async def _grab_stats(self):
            return []

    config = config_with({"plain_collection": {"cpu_percent_warning": "70"}})
    plugin = _Plain(store_with(), config)
    plugin._stats = [{"name": "web", "cpu_percent": 75.0}]
    plugin._derived_parameters()
    assert plugin._levels["web"]["cpu_percent"]["level"] == "warning"
