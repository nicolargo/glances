#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Shared fakes for the v5 exporter tests (P3-3): plugins, config, client libraries.

Each exporter test installs a stand-in for its client library in
`sys.modules` (`fake_module`), feeds real plugin payloads through
`Export.update()`, and asserts on what reached the fake client. No live
backend is involved.
"""

from __future__ import annotations

import asyncio
import sys
import types
from typing import Any

from glances.config_v5 import GlancesConfigV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5

# Names drawn from monitored data are attacker-controlled: a process name, a
# mount point, an interface name. Wave D (SQL/CQL) must survive these.
HOSTILE_NAME = "x'); DROP TABLE cpu; --\"`\\"


class FakeScalarPlugin(GlancesPluginBase[dict]):
    plugin_name = "fakescalar"
    fields_description = {
        "total": {"description": "t", "unit": "percent"},
        "label": {"description": "l", "unit": "string"},
        "missing": {"description": "m", "unit": "percent"},
    }

    async def _grab_stats(self) -> dict:
        return {"total": 12.5, "label": "busy host", "missing": None}


class FakeCollectionPlugin(GlancesPluginBase[list]):
    plugin_name = "fakecollection"
    IS_COLLECTION = True
    fields_description = {
        "name": {"description": "n", "unit": "string", "primary_key": True},
        "rx": {"description": "r", "unit": "bytespers"},
    }

    async def _grab_stats(self) -> list:
        return [{"name": "eth0", "rx": 10}, {"name": HOSTILE_NAME, "rx": 20}]


def make_config(sections: dict[str, dict[str, Any]]) -> GlancesConfigV5:
    config = GlancesConfigV5()
    config._merged = {s: dict(opts) for s, opts in sections.items()}
    return config


def plugins(config: GlancesConfigV5) -> list[GlancesPluginBase]:
    """One scalar and one collection plugin, updated once."""
    store = StatsStoreV5()
    built = [FakeScalarPlugin(store, config), FakeCollectionPlugin(store, config)]
    for plugin in built:
        asyncio.run(plugin.update())
    return built


def fake_module(monkeypatch, name: str, **attributes: Any) -> types.ModuleType:
    """Install `name` (dotted names too) in `sys.modules` for the test."""
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)
    if "." in name:
        parent, child = name.rsplit(".", 1)
        if parent not in sys.modules:
            fake_module(monkeypatch, parent)
        monkeypatch.setattr(sys.modules[parent], child, module, raising=False)
    return module


def missing_module(monkeypatch, name: str) -> None:
    """Make `import name` fail, as on an install without the library."""
    monkeypatch.setitem(sys.modules, name, None)
