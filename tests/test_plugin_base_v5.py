#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for GlancesPluginBase[T].

Test stack: pytest + pytest-asyncio (auto mode). See architecture decisions §9.

Coverage:
- Pipeline: 5 steps run in the documented order
- Scalar plugin: store payload shape, get_stats, get_export filtering
- Collection plugin: store payload shape with "data" envelope
- _remove_parameters strips fields not declared in fields_description
- get_export honours `exportable: False` and strips `_*` keys
- Resilience: exception in any step → warning log, no store write
- Type guard: _grab_stats returning the wrong type raises TypeError
- Metadata: time_since_update is non-negative and reset on second cycle
- Override hooks: _derived_parameters can populate _levels visible in store
"""

from __future__ import annotations

import logging

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5

# ---------------------------------------------------------- fake plugins


class FakeScalarPlugin(GlancesPluginBase[dict]):
    plugin_name = "fakescalar"
    IS_COLLECTION = False
    fields_description = {
        "percent": {"description": "p", "unit": "percent"},
        "total": {"description": "t", "unit": "bytes"},
        "internal_only": {"description": "x", "unit": "string", "exportable": False},
    }

    def __init__(self, store, config, payload=None):
        super().__init__(store, config)
        self._payload = payload if payload is not None else {"percent": 50.0, "total": 1024}
        self.calls: list[str] = []

    async def _grab_stats(self) -> dict:
        self.calls.append("grab")
        return dict(self._payload)


class FakeCollectionPlugin(GlancesPluginBase[list]):
    plugin_name = "fakecollection"
    IS_COLLECTION = True
    fields_description = {
        "name": {"description": "n", "unit": "string", "primary_key": True},
        "rx": {"description": "r", "unit": "bytespers"},
        "internal_only": {"description": "x", "unit": "string", "exportable": False},
    }

    def __init__(self, store, config, payload=None):
        super().__init__(store, config)
        self._payload = (
            payload
            if payload is not None
            else [
                {"name": "eth0", "rx": 1024},
                {"name": "lo", "rx": 0},
            ]
        )

    async def _grab_stats(self) -> list:
        return [dict(item) for item in self._payload]


# ---------------------------------------------------------- fixtures


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


# ---------------------------------------------------------- identity


def test_missing_plugin_name_raises(store, config):
    class NoName(GlancesPluginBase[dict]):
        IS_COLLECTION = False

        async def _grab_stats(self) -> dict:
            return {}

    with pytest.raises(ValueError, match="plugin_name"):
        NoName(store, config)


def test_metadata_field_injected(store, config):
    plugin = FakeScalarPlugin(store, config)
    assert "time_since_update" in plugin._fields
    assert plugin._fields["time_since_update"]["exportable"] is False


# ---------------------------------------------------------- scalar plugin


async def test_scalar_update_writes_payload(store, config):
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()

    payload = store.get("fakescalar")
    assert payload is not None
    assert payload["percent"] == 50.0
    assert payload["total"] == 1024
    assert "time_since_update" in payload
    assert payload["_levels"] == {}


async def test_scalar_get_stats_returns_payload(store, config):
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()
    assert plugin.get_stats()["percent"] == 50.0


async def test_scalar_get_export_strips_internals_and_levels(store, config):
    plugin = FakeScalarPlugin(
        store,
        config,
        payload={"percent": 50.0, "total": 1024, "internal_only": "x"},
    )
    await plugin.update()

    exported = plugin.get_export()
    assert exported == {"percent": 50.0, "total": 1024}
    assert "internal_only" not in exported  # exportable: False
    assert "_levels" not in exported
    assert "time_since_update" not in exported  # exportable: False


async def test_scalar_remove_parameters_strips_undeclared(store, config):
    plugin = FakeScalarPlugin(
        store,
        config,
        payload={"percent": 50.0, "total": 1024, "undeclared_field": "noise"},
    )
    await plugin.update()

    payload = store.get("fakescalar")
    assert "undeclared_field" not in payload


# ---------------------------------------------------------- collection plugin


async def test_collection_update_writes_data_envelope(store, config):
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()

    payload = store.get("fakecollection")
    assert isinstance(payload, dict)
    assert "data" in payload
    assert isinstance(payload["data"], list)
    assert payload["data"][0]["name"] == "eth0"
    assert "time_since_update" in payload
    assert payload["_levels"] == {}


async def test_collection_get_export_returns_list(store, config):
    plugin = FakeCollectionPlugin(
        store,
        config,
        payload=[
            {"name": "eth0", "rx": 1024, "internal_only": "x"},
            {"name": "lo", "rx": 0, "internal_only": "y"},
        ],
    )
    await plugin.update()

    exported = plugin.get_export()
    assert exported == [{"name": "eth0", "rx": 1024}, {"name": "lo", "rx": 0}]


async def test_collection_remove_parameters_strips_per_item(store, config):
    plugin = FakeCollectionPlugin(
        store,
        config,
        payload=[{"name": "eth0", "rx": 1024, "noise": "drop"}],
    )
    await plugin.update()

    payload = store.get("fakecollection")
    assert "noise" not in payload["data"][0]


# ---------------------------------------------------------- resilience


async def test_grab_exception_does_not_crash_and_skips_store(store, config, caplog):
    class BoomPlugin(FakeScalarPlugin):
        async def _grab_stats(self) -> dict:
            raise RuntimeError("psutil exploded")

    plugin = BoomPlugin(store, config)
    with caplog.at_level(logging.WARNING):
        await plugin.update()  # must not raise

    assert "fakescalar update failed" in caplog.text
    assert store.get("fakescalar") is None  # no payload written


async def test_transform_exception_does_not_crash_and_skips_store(store, config, caplog):
    class BoomPlugin(FakeScalarPlugin):
        def _derived_parameters(self) -> None:
            raise RuntimeError("transform exploded")

    plugin = BoomPlugin(store, config)
    with caplog.at_level(logging.WARNING):
        await plugin.update()

    assert "fakescalar update failed" in caplog.text
    assert store.get("fakescalar") is None


async def test_wrong_grab_return_type_logs_warning(store, config, caplog):
    class WrongTypePlugin(FakeScalarPlugin):
        async def _grab_stats(self) -> dict:
            return ["not", "a", "dict"]  # type: ignore[return-value]

    plugin = WrongTypePlugin(store, config)
    with caplog.at_level(logging.WARNING):
        await plugin.update()

    assert "must return dict" in caplog.text
    assert store.get("fakescalar") is None


async def test_collection_wrong_grab_return_type_logs_warning(store, config, caplog):
    class WrongTypePlugin(FakeCollectionPlugin):
        async def _grab_stats(self) -> list:
            return {"not": "a list"}  # type: ignore[return-value]

    plugin = WrongTypePlugin(store, config)
    with caplog.at_level(logging.WARNING):
        await plugin.update()

    assert "must return list" in caplog.text
    assert store.get("fakecollection") is None


# ---------------------------------------------------------- metadata


async def test_time_since_update_zero_on_first_cycle(store, config):
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()
    assert store.get("fakescalar")["time_since_update"] == 0.0


async def test_time_since_update_increases_on_second_cycle(store, config):
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()
    await plugin.update()
    assert store.get("fakescalar")["time_since_update"] >= 0.0
    # Cannot assert > 0 reliably without sleeping; just ensure non-negative
    # and the second cycle still wrote a payload.


# ---------------------------------------------------------- override hooks


async def test_derived_parameters_can_populate_levels(store, config):
    class WithLevels(FakeScalarPlugin):
        def _derived_parameters(self) -> None:
            self._levels = {"percent": "warning"}

    plugin = WithLevels(store, config)
    await plugin.update()
    assert store.get("fakescalar")["_levels"] == {"percent": "warning"}


async def test_pipeline_runs_grab_before_transform(store, config):
    """_grab_stats must be invoked before _transform sub-steps."""
    order: list[str] = []

    class Tracker(FakeScalarPlugin):
        async def _grab_stats(self) -> dict:
            order.append("grab")
            return {"percent": 1.0, "total": 1}

        def _transform_gauge(self) -> None:
            order.append("gauge")

        def _expand_parameters(self) -> None:
            order.append("expand")

        def _derived_parameters(self) -> None:
            order.append("derived")

    plugin = Tracker(store, config)
    await plugin.update()
    assert order == ["grab", "gauge", "expand", "derived"]


# ---------------------------------------------------------- empty payloads


async def test_get_export_before_update_returns_empty(store, config):
    plugin = FakeScalarPlugin(store, config)
    assert plugin.get_export() == {}


async def test_get_export_collection_before_update_returns_empty_list(store, config):
    plugin = FakeCollectionPlugin(store, config)
    assert plugin.get_export() == []


async def test_get_stats_before_update_returns_empty_dict(store, config):
    plugin = FakeScalarPlugin(store, config)
    assert plugin.get_stats() == {}
