#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for GlancesExportBase.

Test stack: pytest + pytest-asyncio (auto mode). See architecture decisions §9.
"""

from __future__ import annotations

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.exports.export_base_v5 import GlancesExportBase
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5


class FakeScalarPlugin(GlancesPluginBase[dict]):
    plugin_name = "fakescalar"
    IS_COLLECTION = False
    fields_description = {
        "percent": {"description": "p", "unit": "percent"},
        "total": {"description": "t", "unit": "bytes"},
        "secret": {"description": "s", "unit": "string", "exportable": False},
    }

    def __init__(self, store, config, payload=None):
        super().__init__(store, config)
        self._payload = payload if payload is not None else {"percent": 50.0, "total": 1024, "secret": "x"}

    async def _grab_stats(self) -> dict:
        return dict(self._payload)


class FakeCollectionPlugin(GlancesPluginBase[list]):
    plugin_name = "fakecollection"
    IS_COLLECTION = True
    fields_description = {
        "name": {"description": "n", "unit": "string", "primary_key": True},
        "rx": {"description": "r", "unit": "bytespers"},
    }

    def __init__(self, store, config, payload=None):
        super().__init__(store, config)
        self._payload = (
            payload
            if payload is not None
            else [
                {"name": "eth0", "rx": 10},
                {"name": "eth1", "rx": 20},
            ]
        )

    async def _grab_stats(self) -> list:
        return [dict(item) for item in self._payload]


def test_v4_export_module_is_not_shadowed_by_the_v5_exports_package():
    """Regression test for a real breakage, not a hypothetical one.

    An earlier draft of the G8 design put the v5 base class in a
    ``glances/exports/export/`` sub-package. Python cannot resolve both
    ``glances/exports/export.py`` (the v4 base, read-only per this repo's
    rules) and a same-named ``glances/exports/export/`` package under one
    parent — the package wins, and
    ``from glances.exports.export import GlancesExport`` raises
    ImportError, breaking all 24 v4 exporters. This is currently guarded
    only transitively via test_export_timescaledb_list.py; assert it
    directly so nobody reintroduces the shadowing package and nobody
    deletes this test as "redundant".
    """
    from glances.exports.export import GlancesExport

    assert hasattr(GlancesExport, "non_exportable_plugins")


def test_exportable_defaults_to_true():
    assert GlancesPluginBase.EXPORTABLE is True
    assert FakeScalarPlugin.EXPORTABLE is True


def test_non_exportable_plugins_declare_the_flag():
    from glances.plugins.psutilversion.model_v5 import PluginModel as PsutilVersion
    from glances.plugins.quicklook.model_v5 import PluginModel as Quicklook
    from glances.plugins.version.model_v5 import PluginModel as Version

    assert Quicklook.EXPORTABLE is False
    assert Version.EXPORTABLE is False
    assert PsutilVersion.EXPORTABLE is False


class FakeExport(GlancesExportBase):
    export_name = "fake"

    def __init__(self, config, args):
        super().__init__(config, args)
        self.exported: list[tuple[str, list, list]] = []

    def export(self, name, columns, points):
        self.exported.append((name, list(columns), list(points)))


def make_config(sections: dict) -> GlancesConfigV5:
    config = GlancesConfigV5()
    config._merged = {s: dict(opts) for s, opts in sections.items()}
    return config


def test_load_conf_reads_mandatories_and_options():
    config = make_config({"backend": {"host": "localhost", "port": "8086", "prefix": "gl"}})
    exporter = FakeExport(config, args=None)
    ok = exporter.load_conf("backend", mandatories=("host", "port"), options=("prefix", "tags"))
    assert ok is True
    assert exporter.host == "localhost"
    assert exporter.port == "8086"
    assert exporter.prefix == "gl"
    assert getattr(exporter, "tags", None) is None


def test_load_conf_returns_false_on_missing_section():
    exporter = FakeExport(make_config({}), args=None)
    assert exporter.load_conf("backend") is False


def test_load_conf_returns_false_on_missing_mandatory():
    config = make_config({"backend": {"host": "localhost"}})
    exporter = FakeExport(config, args=None)
    assert exporter.load_conf("backend", mandatories=("host", "port")) is False


def test_is_excluded_uses_full_match_case_insensitive():
    config = make_config({"export": {"exclude_fields": r".*_critical,.*\.key$"}})
    exporter = FakeExport(config, args=None)
    assert exporter.is_excluded("cpu_critical") is True
    assert exporter.is_excluded("CPU_CRITICAL") is True
    assert exporter.is_excluded("eth0.key") is True
    assert exporter.is_excluded("percent") is False


def test_is_excluded_is_false_when_key_absent():
    exporter = FakeExport(make_config({}), args=None)
    assert exporter.is_excluded("anything") is False


def test_parse_tags():
    exporter = FakeExport(make_config({}), args=None)
    assert exporter.parse_tags("foo:bar,spam:eggs") == {"foo": "bar", "spam": "eggs"}
    assert exporter.parse_tags(None) == {}
    assert exporter.parse_tags("broken") == {}


def test_build_export_flattens_a_scalar_payload():
    exporter = FakeExport(make_config({}), args=None)
    names, values = exporter.build_export({"percent": 50.0, "total": 1024})
    assert names == ["percent", "total"]
    assert values == [50.0, 1024]


def test_build_export_prefixes_items_with_the_key_value():
    exporter = FakeExport(make_config({}), args=None)
    names, values = exporter.build_export(
        [
            {"key": "name", "name": "eth0", "rx": 10},
            {"key": "name", "name": "eth1", "rx": 20},
        ]
    )
    assert names == ["eth0.key", "eth0.name", "eth0.rx", "eth1.key", "eth1.name", "eth1.rx"]
    assert values == ["name", "eth0", 10, "name", "eth1", 20]


def test_build_export_serialises_bool_and_joins_list():
    exporter = FakeExport(make_config({}), args=None)
    names, values = exporter.build_export({"flag": True, "cpus": [1, 2, 3]})
    assert dict(zip(names, values)) == {"flag": "true", "cpus": "1 2 3"}


def test_build_export_drops_excluded_fields():
    config = make_config({"export": {"exclude_fields": ".*_critical"}})
    exporter = FakeExport(config, args=None)
    names, _ = exporter.build_export({"percent": 1.0, "cpu_critical": 90.0})
    assert names == ["percent"]


def test_normalize_for_influxdb_turns_the_key_into_a_tag():
    exporter = FakeExport(make_config({}), args=None)
    exporter.tags = None
    exporter.hostname = "testhost"
    names, values = exporter.build_export([{"key": "name", "name": "eth0", "rx": 10}])
    measurements = exporter.normalize_for_influxdb("network", names, values)
    assert len(measurements) == 1
    measurement = measurements[0]
    assert measurement["measurement"] == "network"
    assert measurement["tags"]["hostname"] == "testhost"
    assert measurement["tags"]["name"] == "eth0"
    assert measurement["fields"]["rx"] == 10.0


@pytest.mark.asyncio
async def test_inject_key_adds_the_primary_key_field_to_each_item():
    store = StatsStoreV5()
    plugin = FakeCollectionPlugin(store, make_config({}))
    await plugin.update()
    exporter = FakeExport(make_config({}), args=None)

    payload = exporter._inject_key(plugin, plugin.get_export())

    assert [item["key"] for item in payload] == ["name", "name"]
    names, _ = exporter.build_export(payload)
    assert "eth0.rx" in names
    assert "eth0.key" in names


@pytest.mark.asyncio
async def test_inject_key_leaves_a_scalar_payload_untouched():
    store = StatsStoreV5()
    plugin = FakeScalarPlugin(store, make_config({}))
    await plugin.update()
    exporter = FakeExport(make_config({}), args=None)

    payload = exporter._inject_key(plugin, plugin.get_export())

    assert "key" not in payload


def test_limits_for_flattens_the_plugin_section():
    config = make_config(
        {
            "fakescalar": {"careful": "50", "warning": "70", "critical": "90"},
            "global": {"history_size": "1200"},
        }
    )
    store = StatsStoreV5()
    plugin = FakeScalarPlugin(store, config)
    exporter = FakeExport(config, args=None)

    limits = exporter._limits_for(plugin)

    assert limits["fakescalar_careful"] == 50.0
    assert limits["fakescalar_warning"] == 70.0
    assert limits["fakescalar_critical"] == 90.0
    assert limits["history_size"] == 1200.0


def test_limits_for_splits_non_numeric_values_on_commas():
    config = make_config({"fakescalar": {"status_ok": "R,S,D"}})
    store = StatsStoreV5()
    plugin = FakeScalarPlugin(store, config)
    exporter = FakeExport(config, args=None)

    assert exporter._limits_for(plugin)["fakescalar_status_ok"] == ["R", "S", "D"]


def test_limits_for_never_exports_action_templates():
    """Security divergence from v4 — design §5.4.

    v4 merges the whole plugin section into the exported payload, so a
    shell command configured as an action leaves the machine in clear text.
    """
    config = make_config(
        {
            "fakescalar": {
                "careful": "50",
                "critical_action": "/usr/bin/mail -s alert ops@example.com",
                "warning_action_repeat": "/usr/bin/logger boom",
            }
        }
    )
    store = StatsStoreV5()
    plugin = FakeScalarPlugin(store, config)
    exporter = FakeExport(config, args=None)

    limits = exporter._limits_for(plugin)

    assert limits["fakescalar_careful"] == 50.0
    assert not [k for k in limits if "_action" in k]
    assert "/usr/bin/mail -s alert ops@example.com" not in str(limits.values())


def test_limits_for_is_cached_per_plugin():
    config = make_config({"fakescalar": {"careful": "50"}})
    store = StatsStoreV5()
    plugin = FakeScalarPlugin(store, config)
    exporter = FakeExport(config, args=None)

    first = exporter._limits_for(plugin)
    second = exporter._limits_for(plugin)

    assert first is second


@pytest.mark.asyncio
async def test_merge_limits_drops_the_disable_key():
    config = make_config({"fakescalar": {"careful": "50", "disable": "False"}})
    store = StatsStoreV5()
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()
    exporter = FakeExport(config, args=None)

    payload = exporter._merge_limits(plugin, plugin.get_export())

    assert payload["fakescalar_careful"] == 50.0
    assert "fakescalar_disable" not in payload
    # Guards against _merge_limits() aliasing the cached dict instead of
    # copying it before popping — a bare `self._limits_for(plugin)` would
    # delete "fakescalar_disable" from the cache itself, so this key would
    # then silently vanish from every subsequent call too.
    assert "fakescalar_disable" in exporter._limits_for(plugin)


@pytest.mark.asyncio
async def test_merge_limits_applies_to_every_item_of_a_collection():
    config = make_config({"fakecollection": {"rx_careful": "60"}})
    store = StatsStoreV5()
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()
    exporter = FakeExport(config, args=None)

    payload = exporter._merge_limits(plugin, plugin.get_export())

    assert all(item["fakecollection_rx_careful"] == 60.0 for item in payload)


@pytest.mark.asyncio
async def test_update_exports_one_call_per_plugin():
    store = StatsStoreV5()
    config = make_config({})
    scalar = FakeScalarPlugin(store, config)
    collection = FakeCollectionPlugin(store, config)
    await scalar.update()
    await collection.update()
    exporter = FakeExport(config, args=None)

    exporter.update([scalar, collection])

    assert [name for name, _, _ in exporter.exported] == ["fakescalar", "fakecollection"]


@pytest.mark.asyncio
async def test_update_skips_non_exportable_plugins():
    class NotExportable(FakeScalarPlugin):
        plugin_name = "hidden"
        EXPORTABLE = False

    store = StatsStoreV5()
    config = make_config({})
    plugin = NotExportable(store, config)
    await plugin.update()
    exporter = FakeExport(config, args=None)

    exporter.update([plugin])

    assert exporter.exported == []


@pytest.mark.asyncio
async def test_update_skips_a_plugin_with_no_payload_yet():
    store = StatsStoreV5()
    config = make_config({})
    plugin = FakeScalarPlugin(store, config)  # never updated → store empty
    exporter = FakeExport(config, args=None)

    exporter.update([plugin])

    assert exporter.exported == []


@pytest.mark.asyncio
async def test_update_isolates_a_failing_plugin(caplog):
    class Boom(FakeExport):
        def export(self, name, columns, points):
            if name == "fakescalar":
                raise RuntimeError("backend down")
            super().export(name, columns, points)

    store = StatsStoreV5()
    config = make_config({})
    scalar = FakeScalarPlugin(store, config)
    collection = FakeCollectionPlugin(store, config)
    await scalar.update()
    await collection.update()
    exporter = Boom(config, args=None)

    with caplog.at_level("WARNING"):
        exporter.update([scalar, collection])

    assert [name for name, _, _ in exporter.exported] == ["fakecollection"]
    assert "backend down" in caplog.text


@pytest.mark.asyncio
async def test_update_output_carries_stats_limits_and_key():
    store = StatsStoreV5()
    config = make_config({"fakecollection": {"rx_careful": "60"}})
    collection = FakeCollectionPlugin(store, config)
    await collection.update()
    exporter = FakeExport(config, args=None)

    exporter.update([collection])

    _, names, values = exporter.exported[0]
    row = dict(zip(names, values))
    assert row["eth0.rx"] == 10
    assert row["eth0.key"] == "name"
    assert row["eth0.fakecollection_rx_careful"] == 60.0
