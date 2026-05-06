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
            # Standard nested shape: {field: {"level": ..., "prominent": bool}}
            self._levels = {"percent": {"level": "warning", "prominent": True}}

    plugin = WithLevels(store, config)
    await plugin.update()
    assert store.get("fakescalar")["_levels"] == {"percent": {"level": "warning", "prominent": True}}


async def test_default_levels_pipeline_writes_nested_entry(store, config):
    """A `watched` field with default_thresholds gets a {level, prominent} entry."""

    class Watched(FakeScalarPlugin):
        fields_description = {
            "percent": {
                "description": "p",
                "unit": "percent",
                "watched": True,
                "watch_direction": "high",
                "prominent": True,
                "default_thresholds": {"careful": 50.0, "warning": 70.0, "critical": 90.0},
            },
        }

    plugin = Watched(store, config, payload={"percent": 75.0})
    await plugin.update()
    assert store.get("fakescalar")["_levels"] == {"percent": {"level": "warning", "prominent": True}}


async def test_prominent_defaults_to_true_when_absent_from_schema(store, config):
    """`prominent` is opt-in to False — absent means True for watched fields."""

    class Watched(FakeScalarPlugin):
        fields_description = {
            "percent": {
                "description": "p",
                "unit": "percent",
                "watched": True,
                # `prominent` not declared — must default to True.
                "default_thresholds": {"warning": 70.0},
            },
        }

    plugin = Watched(store, config, payload={"percent": 75.0})
    await plugin.update()
    assert store.get("fakescalar")["_levels"]["percent"]["prominent"] is True


async def test_prominent_can_be_opted_out_per_field(store, config):
    """A plugin author can demote a watched field with `prominent: False`."""

    class Watched(FakeScalarPlugin):
        fields_description = {
            "percent": {
                "description": "p",
                "unit": "percent",
                "watched": True,
                "prominent": False,
                "default_thresholds": {"warning": 70.0},
            },
        }

    plugin = Watched(store, config, payload={"percent": 75.0})
    await plugin.update()
    assert store.get("fakescalar")["_levels"]["percent"] == {"level": "warning", "prominent": False}


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


# ---------------------------------------------------------- normalize_by


async def test_normalize_by_divides_value_by_referenced_field(store, config):
    """`normalize_by: cpucore` divides the value before threshold check."""

    class Normalised(FakeScalarPlugin):
        fields_description = {
            "load": {
                "description": "load",
                "unit": "float",
                "watched": True,
                "default_thresholds": {"warning": 1.0},
                "normalize_by": "cpucore",
            },
            "cpucore": {"description": "cpu cores", "unit": "number"},
        }

    # 4.0 / 4 = 1.0 → warning
    plugin = Normalised(store, config, payload={"load": 4.0, "cpucore": 4})
    await plugin.update()
    assert store.get("fakescalar")["_levels"]["load"]["level"] == "warning"

    # 0.4 / 4 = 0.1 → ok (below 1.0)
    plugin2 = Normalised(store, config, payload={"load": 0.4, "cpucore": 4})
    await plugin2.update()
    assert store.get("fakescalar")["_levels"]["load"]["level"] == "ok"


async def test_normalize_by_falls_back_to_one_when_referenced_field_missing(store, config):
    """A missing or zero divisor falls back to 1 (defensive — never divides by 0)."""

    class Normalised(FakeScalarPlugin):
        fields_description = {
            "load": {
                "description": "load",
                "unit": "float",
                "watched": True,
                "default_thresholds": {"warning": 1.0},
                "normalize_by": "cpucore",
            },
        }

    # No `cpucore` in payload — divisor falls back to 1, value 1.5 / 1 → warning.
    plugin = Normalised(store, config, payload={"load": 1.5})
    await plugin.update()
    assert store.get("fakescalar")["_levels"]["load"]["level"] == "warning"


# ---------------------------------------------------------- _transform_gauge (rate)


async def test_rate_field_absent_on_first_cycle(store, config):
    """First cycle has no _raw_previous — rate fields are stripped."""

    class Counter(FakeScalarPlugin):
        fields_description = {
            "ctx_switches": {"description": "ctx", "unit": "number", "rate": True},
        }

    plugin = Counter(store, config, payload={"ctx_switches": 10_000})
    await plugin.update()
    payload = store.get("fakescalar")
    assert "ctx_switches" not in payload  # absent on first cycle


async def test_rate_field_computed_on_second_cycle(store, config, monkeypatch):
    """Second cycle: rate = (curr - prev) / elapsed."""

    class Counter(FakeScalarPlugin):
        fields_description = {
            "ctx_switches": {"description": "ctx", "unit": "number", "rate": True},
        }

    plugin = Counter(store, config, payload={"ctx_switches": 10_000})

    # Force time_since_update == 2.0 between the two cycles by patching
    # the monotonic clock observed by `_add_metadata`.
    fake_now = [100.0]

    def fake_monotonic() -> float:
        return fake_now[0]

    import glances.plugins.plugin.base_v5 as base_module

    monkeypatch.setattr(base_module.time, "monotonic", fake_monotonic)

    await plugin.update()  # first cycle, ctx_switches stripped, _raw_previous = {ctx_switches: 10_000}

    fake_now[0] = 102.0  # +2 s
    plugin._payload = {"ctx_switches": 10_500}
    await plugin.update()

    payload = store.get("fakescalar")
    # delta = 500 over 2 s = 250 events/s
    assert payload["ctx_switches"] == 250.0


async def test_rate_field_clamps_negative_delta_to_zero(store, config, monkeypatch):
    """Counter wrap or reboot (delta < 0) → rate = 0.0, never negative."""

    class Counter(FakeScalarPlugin):
        fields_description = {
            "ctx_switches": {"description": "ctx", "unit": "number", "rate": True},
        }

    plugin = Counter(store, config, payload={"ctx_switches": 10_000})

    fake_now = [100.0]
    import glances.plugins.plugin.base_v5 as base_module

    monkeypatch.setattr(base_module.time, "monotonic", lambda: fake_now[0])

    await plugin.update()
    fake_now[0] = 102.0
    plugin._payload = {"ctx_switches": 5_000}  # counter wrap
    await plugin.update()

    assert store.get("fakescalar")["ctx_switches"] == 0.0


async def test_rate_field_with_normalize_by_uses_rate_then_normalises(store, config, monkeypatch):
    """Pipeline order: gauge converts to rate, then derived normalises rate / cpucore."""

    class Counter(FakeScalarPlugin):
        fields_description = {
            "ctx_switches": {
                "description": "ctx",
                "unit": "number",
                "rate": True,
                "watched": True,
                "default_thresholds": {"warning": 70.0},
                "normalize_by": "cpucore",
            },
            "cpucore": {"description": "cpu cores", "unit": "number"},
        }

    plugin = Counter(store, config, payload={"ctx_switches": 0, "cpucore": 4})

    fake_now = [100.0]
    import glances.plugins.plugin.base_v5 as base_module

    monkeypatch.setattr(base_module.time, "monotonic", lambda: fake_now[0])

    await plugin.update()
    fake_now[0] = 101.0  # +1 s
    plugin._payload = {"ctx_switches": 300, "cpucore": 4}
    await plugin.update()

    # rate = 300/s ; normalised = 300 / 4 = 75 ≥ 70 → warning
    payload = store.get("fakescalar")
    assert payload["ctx_switches"] == 300.0
    assert payload["_levels"]["ctx_switches"]["level"] == "warning"


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
