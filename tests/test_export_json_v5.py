#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the JSON export module."""

from __future__ import annotations

import argparse
import json

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5


class FakeScalarPlugin(GlancesPluginBase[dict]):
    plugin_name = "fakescalar"
    IS_COLLECTION = False
    fields_description = {
        "percent": {"description": "p", "unit": "percent"},
        "total": {"description": "t", "unit": "bytes"},
    }

    async def _grab_stats(self) -> dict:
        return {"percent": 50.0, "total": 1024}


class FakeCollectionPlugin(GlancesPluginBase[list]):
    plugin_name = "fakecollection"
    IS_COLLECTION = True
    fields_description = {
        "name": {"description": "n", "unit": "string", "primary_key": True},
        "rx": {"description": "r", "unit": "bytespers"},
    }

    async def _grab_stats(self) -> list:
        return [{"name": "eth0", "rx": 10}]


def make_config(sections: dict) -> GlancesConfigV5:
    config = GlancesConfigV5()
    config._merged = {s: dict(opts) for s, opts in sections.items()}
    return config


def make_args(path) -> argparse.Namespace:
    return argparse.Namespace(export_json_file=str(path))


@pytest.mark.asyncio
async def test_json_writes_one_object_per_cycle(tmp_path):
    from glances.exports.glances_json.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({})
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()

    path = tmp_path / "glances.json"
    exporter = Export(config, make_args(path))
    exporter.update([plugin])
    exporter.exit()

    payload = json.loads(path.read_text())
    assert payload["fakescalar"]["percent"] == 50.0
    assert payload["fakescalar"]["total"] == 1024


@pytest.mark.asyncio
async def test_json_rewrites_the_file_each_cycle(tmp_path):
    from glances.exports.glances_json.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({})
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()

    path = tmp_path / "glances.json"
    exporter = Export(config, make_args(path))
    exporter.update([plugin])
    exporter.update([plugin])
    exporter.exit()

    assert len(path.read_text().strip().splitlines()) == 1


@pytest.mark.asyncio
async def test_json_carries_the_merged_limits(tmp_path):
    """Unlike CSV, the JSON exporter inherits v4's limits merge."""
    from glances.exports.glances_json.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({"fakescalar": {"careful": "50"}})
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()

    path = tmp_path / "glances.json"
    exporter = Export(config, make_args(path))
    exporter.update([plugin])
    exporter.exit()

    payload = json.loads(path.read_text())
    assert payload["fakescalar"]["fakescalar_careful"] == 50.0


@pytest.mark.asyncio
async def test_json_never_carries_action_templates(tmp_path):
    from glances.exports.glances_json.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({"fakescalar": {"careful": "50", "critical_action": "/usr/bin/mail ops@example.com"}})
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()

    path = tmp_path / "glances.json"
    exporter = Export(config, make_args(path))
    exporter.update([plugin])
    exporter.exit()

    assert "/usr/bin/mail" not in path.read_text()


@pytest.mark.asyncio
async def test_json_prefixes_collection_items(tmp_path):
    from glances.exports.glances_json.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({})
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()

    path = tmp_path / "glances.json"
    exporter = Export(config, make_args(path))
    exporter.update([plugin])
    exporter.exit()

    payload = json.loads(path.read_text())
    assert payload["fakecollection"]["eth0.rx"] == 10


def test_json_exits_when_the_file_cannot_be_created(tmp_path):
    from glances.exports.glances_json.export_v5 import Export

    unreachable = tmp_path / "no-such-dir" / "glances.json"
    with pytest.raises(SystemExit) as excinfo:
        Export(make_config({}), make_args(unreachable))
    assert excinfo.value.code == 2


def test_json_exit_calls_super_first(tmp_path, monkeypatch):
    from glances.exports.export_base_v5 import GlancesExportBase
    from glances.exports.glances_json.export_v5 import Export

    calls = []
    real_exit = GlancesExportBase.exit
    monkeypatch.setattr(GlancesExportBase, "exit", lambda self: (calls.append("base"), real_exit(self))[1])

    exporter = Export(make_config({}), make_args(tmp_path / "g.json"))
    exporter.exit()

    assert calls == ["base"], "Export.exit() must call super().exit()"
