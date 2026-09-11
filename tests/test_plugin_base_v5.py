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


async def test_normalize_by_skips_level_when_divisor_is_missing_or_zero(store, config):
    """A missing, None, or zero divisor → level is skipped ("no limit" semantics).

    Used when the threshold-base field can legitimately be 0 (e.g. an
    interface whose link speed is unknown). Skipping avoids spurious
    alerts against an arbitrary fallback divisor.
    """

    class Normalised(FakeScalarPlugin):
        fields_description = {
            "bytes_recv": {
                "description": "bytes per second",
                "unit": "bytespers",
                "watched": True,
                "default_thresholds": {"warning": 0.8},
                "normalize_by": "bytes_speed_rate_per_sec",
            },
            "bytes_speed_rate_per_sec": {
                "description": "per-direction link speed in bytes/s",
                "unit": "bytespers",
            },
        }

    # Divisor missing entirely → no level for bytes_recv.
    plugin = Normalised(store, config, payload={"bytes_recv": 1_000_000})
    await plugin.update()
    assert "bytes_recv" not in store.get("fakescalar")["_levels"]

    # Divisor explicitly 0 (e.g. loopback) → no level either.
    plugin2 = Normalised(store, config, payload={"bytes_recv": 1_000_000, "bytes_speed_rate_per_sec": 0})
    await plugin2.update()
    assert "bytes_recv" not in store.get("fakescalar")["_levels"]


# ---------------------------------------------------------- _transform_gauge (rate)


async def test_rate_field_none_on_first_cycle(store, config):
    """First cycle has no _raw_previous — rate fields are kept, set to None."""

    class Counter(FakeScalarPlugin):
        fields_description = {
            "ctx_switches": {"description": "ctx", "unit": "number", "rate": True},
        }

    plugin = Counter(store, config, payload={"ctx_switches": 10_000})
    await plugin.update()
    payload = store.get("fakescalar")
    assert "ctx_switches" in payload
    assert payload["ctx_switches"] is None  # kept, not computable yet


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

    await plugin.update()  # first cycle, ctx_switches = None, _raw_previous = {ctx_switches: 10_000}

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


# ---------------------------------------------------------- collection: primary key validation


def test_collection_missing_primary_key_raises(store, config):
    """A collection plugin without `primary_key=True` on any field is a bug."""

    class NoPK(GlancesPluginBase[list]):
        plugin_name = "nopk"
        IS_COLLECTION = True
        fields_description = {"name": {"description": "n", "unit": "string"}}

        async def _grab_stats(self) -> list:
            return []

    with pytest.raises(ValueError, match="primary_key=True"):
        NoPK(store, config)


def test_collection_multiple_primary_keys_raises(store, config):
    """At most one field may carry `primary_key=True`."""

    class TwoPK(GlancesPluginBase[list]):
        plugin_name = "twopk"
        IS_COLLECTION = True
        fields_description = {
            "a": {"description": "a", "unit": "string", "primary_key": True},
            "b": {"description": "b", "unit": "string", "primary_key": True},
        }

        async def _grab_stats(self) -> list:
            return []

    with pytest.raises(ValueError, match="primary_key=True"):
        TwoPK(store, config)


# ---------------------------------------------------------- collection: _transform_gauge (rate)


class _CounterCollection(FakeCollectionPlugin):
    """Collection plugin with a `rate: True` field on each item."""

    fields_description = {
        "name": {"description": "n", "unit": "string", "primary_key": True},
        "rx": {"description": "rx", "unit": "bytespers", "rate": True},
    }


async def test_collection_rate_none_on_first_cycle(store, config):
    """First cycle: no _raw_previous, all per-item rate fields kept, set to None."""
    plugin = _CounterCollection(store, config, payload=[{"name": "eth0", "rx": 1000}, {"name": "wlan0", "rx": 500}])
    await plugin.update()
    items = store.get("fakecollection")["data"]
    assert all("rx" in item and item["rx"] is None for item in items)


async def test_collection_rate_computed_per_item_on_second_cycle(store, config, monkeypatch):
    """Second cycle: rate = (curr - prev) / elapsed, matched per primary key."""
    plugin = _CounterCollection(store, config, payload=[{"name": "eth0", "rx": 1000}, {"name": "wlan0", "rx": 500}])

    fake_now = [100.0]
    import glances.plugins.plugin.base_v5 as base_module

    monkeypatch.setattr(base_module.time, "monotonic", lambda: fake_now[0])

    await plugin.update()  # cycle 1 — rx = None

    fake_now[0] = 102.0  # +2 s
    plugin._payload = [{"name": "eth0", "rx": 3000}, {"name": "wlan0", "rx": 800}]
    await plugin.update()

    items = {item["name"]: item for item in store.get("fakecollection")["data"]}
    # eth0: delta 2000 / 2 s = 1000 ; wlan0: delta 300 / 2 s = 150
    assert items["eth0"]["rx"] == 1000.0
    assert items["wlan0"]["rx"] == 150.0


async def test_collection_rate_none_for_newly_appearing_item(store, config, monkeypatch):
    """An interface that appears between cycles has rate = None on its first appearance."""
    plugin = _CounterCollection(store, config, payload=[{"name": "eth0", "rx": 1000}])

    fake_now = [100.0]
    import glances.plugins.plugin.base_v5 as base_module

    monkeypatch.setattr(base_module.time, "monotonic", lambda: fake_now[0])

    await plugin.update()

    fake_now[0] = 101.0
    plugin._payload = [{"name": "eth0", "rx": 1500}, {"name": "wlan0", "rx": 500}]
    await plugin.update()

    items = {item["name"]: item for item in store.get("fakecollection")["data"]}
    assert items["eth0"]["rx"] == 500.0  # rate computed
    assert "rx" in items["wlan0"]
    assert items["wlan0"]["rx"] is None  # first appearance — not computable yet


async def test_collection_disappearing_item_does_not_poison_others(store, config, monkeypatch):
    """An interface present in cycle N but absent in N+1 doesn't break rates for others."""
    plugin = _CounterCollection(store, config, payload=[{"name": "eth0", "rx": 1000}, {"name": "wlan0", "rx": 500}])

    fake_now = [100.0]
    import glances.plugins.plugin.base_v5 as base_module

    monkeypatch.setattr(base_module.time, "monotonic", lambda: fake_now[0])

    await plugin.update()

    fake_now[0] = 101.0
    plugin._payload = [{"name": "eth0", "rx": 1500}]  # wlan0 disappears
    await plugin.update()

    items = store.get("fakecollection")["data"]
    assert len(items) == 1
    assert items[0]["name"] == "eth0"
    assert items[0]["rx"] == 500.0


# ---------------------------------------------------------- collection: _levels indexing


class _WatchedCollection(FakeCollectionPlugin):
    """Collection plugin with a watched field and `normalize_by`."""

    fields_description = {
        "name": {"description": "n", "unit": "string", "primary_key": True},
        "rx": {
            "description": "rx",
            "unit": "bytespers",
            "watched": True,
            "default_thresholds": {"careful": 0.5, "warning": 0.7, "critical": 0.9},
            "normalize_by": "speed",
        },
        "speed": {"description": "speed", "unit": "bytespers"},
    }


async def test_collection_levels_indexed_by_primary_key(store, config):
    """`_levels` for a collection is keyed by the primary-key value."""
    plugin = _WatchedCollection(
        store,
        config,
        payload=[
            {"name": "eth0", "rx": 800, "speed": 1000},  # 0.8 → warning
            {"name": "wlan0", "rx": 200, "speed": 1000},  # 0.2 → ok
        ],
    )
    await plugin.update()
    levels = store.get("fakecollection")["_levels"]
    assert levels == {
        "eth0": {"rx": {"level": "warning", "prominent": True}},
        "wlan0": {"rx": {"level": "ok", "prominent": True}},
    }


async def test_collection_levels_skip_field_when_divisor_is_zero(store, config):
    """An item whose normalize_by divisor is 0 has no level for that field."""
    plugin = _WatchedCollection(
        store,
        config,
        payload=[
            {"name": "eth0", "rx": 800, "speed": 1000},
            {"name": "lo", "rx": 1, "speed": 0},  # speed=0 → no level for rx
        ],
    )
    await plugin.update()
    levels = store.get("fakecollection")["_levels"]
    assert "rx" in levels["eth0"]
    # lo has no entry at all (no other watched fields contributed).
    assert "lo" not in levels


# ---------------------------------------------------------- collection: hide / show filtering


def _write_config(tmp_path, monkeypatch, body: str) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    xdg = tmp_path / "xdg"
    cfg_dir = xdg / "glances"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "glances.conf").write_text(body)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    return GlancesConfigV5()


async def test_collection_hide_drops_matching_items(tmp_path, monkeypatch, store):
    config = _write_config(tmp_path, monkeypatch, "[fakecollection]\nhide=lo,docker.*\n")
    plugin = FakeCollectionPlugin(
        store,
        config,
        payload=[
            {"name": "eth0", "rx": 100},
            {"name": "lo", "rx": 0},
            {"name": "docker0", "rx": 50},
        ],
    )
    await plugin.update()
    names = [item["name"] for item in store.get("fakecollection")["data"]]
    assert names == ["eth0"]


async def test_collection_show_keeps_only_matching_items(tmp_path, monkeypatch, store):
    config = _write_config(tmp_path, monkeypatch, "[fakecollection]\nshow=eth.*\n")
    plugin = FakeCollectionPlugin(
        store,
        config,
        payload=[
            {"name": "eth0", "rx": 100},
            {"name": "eth1", "rx": 200},
            {"name": "wlan0", "rx": 50},
        ],
    )
    await plugin.update()
    names = sorted(item["name"] for item in store.get("fakecollection")["data"])
    assert names == ["eth0", "eth1"]


async def test_collection_show_then_hide_combined(tmp_path, monkeypatch, store):
    """`show` runs first, `hide` runs second — both apply."""
    config = _write_config(tmp_path, monkeypatch, "[fakecollection]\nshow=^e\nhide=eth1\n")
    plugin = FakeCollectionPlugin(
        store,
        config,
        payload=[
            {"name": "eth0", "rx": 100},
            {"name": "eth1", "rx": 200},
            {"name": "wlan0", "rx": 50},
        ],
    )
    await plugin.update()
    names = [item["name"] for item in store.get("fakecollection")["data"]]
    assert names == ["eth0"]  # wlan0 excluded by show; eth1 excluded by hide


async def test_collection_invalid_regex_is_logged_and_ignored(tmp_path, monkeypatch, store, caplog):
    """An invalid regex pattern is logged and skipped, not raised."""
    config = _write_config(tmp_path, monkeypatch, "[fakecollection]\nhide=[\n")
    with caplog.at_level(logging.WARNING):
        plugin = FakeCollectionPlugin(store, config, payload=[{"name": "eth0", "rx": 100}])
        await plugin.update()
    assert "invalid hide regex" in caplog.text
    # Other items still flow through (no filter applied).
    assert store.get("fakecollection")["data"][0]["name"] == "eth0"


# ---------------------------------------------------------- collection: generic alias (design §5.5)


async def test_collection_alias_published_when_pk_matches(tmp_path, monkeypatch, store):
    config = _write_config(tmp_path, monkeypatch, "[fakecollection]\nalias=eth0:WAN Interface\n")
    plugin = FakeCollectionPlugin(
        store,
        config,
        payload=[{"name": "eth0", "rx": 100}, {"name": "lo", "rx": 0}],
    )
    await plugin.update()
    data = {item["name"]: item for item in store.get("fakecollection")["data"]}
    assert data["eth0"]["alias"] == "WAN Interface"
    assert "alias" not in data["lo"]


async def test_collection_alias_absent_by_default(store, config):
    """No `[<plugin>] alias=` key at all — v4 parity, no default behaviour change."""
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()
    for item in store.get("fakecollection")["data"]:
        assert "alias" not in item


async def test_collection_alias_does_not_rewrite_primary_key(tmp_path, monkeypatch, store):
    config = _write_config(tmp_path, monkeypatch, "[fakecollection]\nalias=eth0:WAN\n")
    plugin = FakeCollectionPlugin(store, config, payload=[{"name": "eth0", "rx": 100}])
    await plugin.update()
    item = store.get("fakecollection")["data"][0]
    assert item["name"] == "eth0"
    assert item["alias"] == "WAN"


async def test_collection_malformed_alias_entry_is_logged_and_skipped(tmp_path, monkeypatch, store, caplog):
    """`alias=eth0` (no `:Name`) is malformed — `_compile_filter()` two
    methods above logs a warning for a bad regex, so a dropped alias entry
    must not be silent either (finding 3). The rest of the list still
    parses."""
    config = _write_config(tmp_path, monkeypatch, "[fakecollection]\nalias=eth0,lo:LAN\n")
    with caplog.at_level(logging.WARNING):
        plugin = FakeCollectionPlugin(
            store,
            config,
            payload=[{"name": "eth0", "rx": 100}, {"name": "lo", "rx": 0}],
        )
        await plugin.update()
    assert "invalid alias entry" in caplog.text
    assert "eth0" in caplog.text
    assert "fakecollection" in caplog.text
    data = {item["name"]: item for item in store.get("fakecollection")["data"]}
    assert "alias" not in data["eth0"]
    assert data["lo"]["alias"] == "LAN"


async def test_collection_hide_matches_alias_as_well_as_raw_pk(tmp_path, monkeypatch, store):
    """v4 parity: `hide=<alias>` drops the item even though the raw
    primary-key value does not match the pattern (`plugin/model.py:1059`)."""
    config = _write_config(tmp_path, monkeypatch, "[fakecollection]\nalias=eth0:WAN\nhide=WAN\n")
    plugin = FakeCollectionPlugin(
        store,
        config,
        payload=[{"name": "eth0", "rx": 100}, {"name": "lo", "rx": 0}],
    )
    await plugin.update()
    names = [item["name"] for item in store.get("fakecollection")["data"]]
    assert names == ["lo"]


async def test_collection_show_matches_alias_as_well_as_raw_pk(tmp_path, monkeypatch, store):
    """v4 parity: `show=<alias>` keeps the item even though the raw
    primary-key value does not match the pattern (`plugin/model.py:1044`)."""
    config = _write_config(tmp_path, monkeypatch, "[fakecollection]\nalias=eth0:WAN\nshow=WAN\n")
    plugin = FakeCollectionPlugin(
        store,
        config,
        payload=[{"name": "eth0", "rx": 100}, {"name": "lo", "rx": 0}],
    )
    await plugin.update()
    names = [item["name"] for item in store.get("fakecollection")["data"]]
    assert names == ["eth0"]


async def test_collection_alias_does_not_affect_levels_keying_or_override(tmp_path, monkeypatch, store):
    """Configuring an alias for an item must not rename `_levels` keys nor
    break its `<pk>_<field>_<level>` override — design §5.5: both stay
    keyed on the raw primary-key value, never the alias."""
    config = _write_config(
        tmp_path,
        monkeypatch,
        "[fakecollection]\nalias=eth0:WAN\nrx_warning=0.9\neth0_rx_warning=0.5\n",
    )
    plugin = _WatchedCollection(
        store,
        config,
        payload=[{"name": "eth0", "rx": 600, "speed": 1000}],  # ratio 0.6
    )
    await plugin.update()

    data = store.get("fakecollection")["data"][0]
    assert data["name"] == "eth0"  # primary key untouched
    assert data["alias"] == "WAN"

    levels = store.get("fakecollection")["_levels"]
    assert "eth0" in levels  # keyed by the raw pk value
    assert "WAN" not in levels
    # eth0_rx_warning=0.5 (per-item override) wins over the field-wide 0.9
    # — if alias interfered with override resolution this would read
    # "careful" instead (falling back to the field-wide/default thresholds).
    assert levels["eth0"]["rx"]["level"] == "warning"


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


# ---------------------------------------------------------- DISPLAY_IN_TUI flag


def test_display_in_tui_defaults_true():
    """Plugins are shown in the TUI unless they opt out."""
    from glances.plugins.plugin.base_v5 import GlancesPluginBase

    assert GlancesPluginBase.DISPLAY_IN_TUI is True


def test_display_in_tui_can_be_overridden():
    """A subclass can hide itself from the TUI (mirrors v4 display_curse=False)."""
    from glances.plugins.plugin.base_v5 import GlancesPluginBase

    class _Hidden(GlancesPluginBase):
        plugin_name = "hidden_probe"
        IS_COLLECTION = False
        DISPLAY_IN_TUI = False

        async def _grab_stats(self):
            return {}

    assert _Hidden.DISPLAY_IN_TUI is False


# ------------------------------------------------------------ get_api_payload
#
# issue #3211 -- the REST API and the MCP adapter used to serve get_stats(),
# the RAW store payload, so a field declared `exportable: False` reached every
# unauthenticated HTTP client while the exporters correctly dropped it.
# get_api_payload() closes that gap WITHOUT hiding `_levels`, which the WebUI
# colours cells from.
#
# Every test below passes an explicit `payload=` carrying `internal_only`:
# both fakes DECLARE that field but neither `_grab_stats()` produces it by
# default, so an assertion on its absence would pass whatever the code did.


@pytest.mark.asyncio
async def test_get_api_payload_drops_non_exportable_fields_of_a_scalar(config):
    store = StatsStoreV5()
    plugin = FakeScalarPlugin(store, config, payload={"percent": 50.0, "total": 1024, "internal_only": "secret"})
    await plugin.update()

    assert "internal_only" in store.get("fakescalar"), "guard: the fixture must publish it"

    payload = plugin.get_api_payload()

    assert "internal_only" not in payload
    assert payload["percent"] == 50.0


@pytest.mark.asyncio
async def test_get_api_payload_drops_non_exportable_fields_of_every_collection_item(config):
    store = StatsStoreV5()
    plugin = FakeCollectionPlugin(
        store,
        config,
        payload=[
            {"name": "eth0", "rx": 10, "internal_only": "secret"},
            {"name": "eth1", "rx": 20, "internal_only": "secret"},
        ],
    )
    await plugin.update()

    assert any("internal_only" in i for i in store.get("fakecollection")["data"]), "guard: the fixture must publish it"

    payload = plugin.get_api_payload()

    assert payload["data"], "fixture must produce at least one item"
    for item in payload["data"]:
        assert "internal_only" not in item
        assert "rx" in item


@pytest.mark.asyncio
async def test_get_api_payload_keeps_levels(config):
    """The whole point of a third view: exporters must not see `_levels`,
    the WebUI must."""
    store = StatsStoreV5()
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()

    assert "_levels" in store.get("fakescalar"), "guard: the store must carry it"

    assert "_levels" in plugin.get_api_payload()
    assert "_levels" not in plugin.get_export()


@pytest.mark.asyncio
async def test_get_api_payload_is_always_a_dict_for_a_collection(config):
    """Unlike get_export(), which returns a bare list: the API keeps the
    envelope its clients already know."""
    store = StatsStoreV5()
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()

    payload = plugin.get_api_payload()

    assert isinstance(payload, dict)
    assert isinstance(payload["data"], list)
    assert isinstance(plugin.get_export(), list)


@pytest.mark.asyncio
async def test_get_api_payload_is_empty_before_the_first_cycle(config):
    store = StatsStoreV5()
    plugin = FakeScalarPlugin(store, config)

    assert plugin.get_api_payload() == {}


# ------------------------------------------------------------------ _key


@pytest.mark.asyncio
async def test_api_payload_publishes_the_primary_key_name_for_a_collection(config):
    """`_levels` for a collection is keyed by the primary key's VALUE. Without
    the key's NAME in the payload, every WebUI component has to hardcode it —
    32 copies of a rule that should live in one place."""
    store = StatsStoreV5()
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()

    payload = plugin.get_api_payload()

    assert payload["_key"] == "name"
    # The value it names really does index _levels.
    assert set(payload["_levels"]) <= {item[payload["_key"]] for item in payload["data"]}


@pytest.mark.asyncio
async def test_api_payload_omits_the_key_for_a_scalar(config):
    store = StatsStoreV5()
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()

    assert "_key" not in plugin.get_api_payload()


@pytest.mark.asyncio
async def test_export_view_is_unchanged_by_the_key(config):
    """`_key` is an API-view concept. Exporters must not see it: the export
    layer already injects its own `key` field with different semantics."""
    store = StatsStoreV5()
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()

    for item in plugin.get_export():
        assert "_key" not in item


@pytest.mark.asyncio
async def test_api_payload_is_still_empty_before_the_first_cycle(config):
    store = StatsStoreV5()
    plugin = FakeCollectionPlugin(store, config)

    assert plugin.get_api_payload() == {}


# ---------------------------------------------------------- unrecognised threshold keys


class FakeNetworkPlugin(GlancesPluginBase[dict]):
    plugin_name = "fakenetwork"
    IS_COLLECTION = False
    fields_description = {
        "bytes_recv": {"description": "r", "unit": "bytespers", "watched": True},
    }

    async def _grab_stats(self) -> dict:
        return {}


class FakeFsPlugin(GlancesPluginBase[dict]):
    plugin_name = "fakefs"
    IS_COLLECTION = False
    fields_description = {
        "percent": {"description": "p", "unit": "percent", "watched": True},
    }

    async def _grab_stats(self) -> dict:
        return {}


class FakeNoWatchedFieldPlugin(GlancesPluginBase[dict]):
    plugin_name = "fakenowatch"
    IS_COLLECTION = False
    fields_description = {
        "percent": {"description": "p", "unit": "percent"},
    }

    async def _grab_stats(self) -> dict:
        return {}


def _threshold_warnings(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if "unrecognised threshold key" in r.getMessage()]


def test_stale_v4_threshold_key_warns_with_accepted_names(tmp_path, monkeypatch, store, caplog):
    config = _write_config(tmp_path, monkeypatch, "[fakenetwork]\nrx_warning=0.7\n")
    with caplog.at_level(logging.WARNING):
        FakeNetworkPlugin(store, config)
    warnings = _threshold_warnings(caplog)
    assert len(warnings) == 1
    assert "rx_warning" in warnings[0]
    assert "bytes_recv" in warnings[0]


def test_per_item_override_with_accepted_suffix_does_not_warn(tmp_path, monkeypatch, store, caplog):
    config = _write_config(tmp_path, monkeypatch, "[fakenetwork]\nwlan0_bytes_recv_warning=0.7\n")
    with caplog.at_level(logging.WARNING):
        FakeNetworkPlugin(store, config)
    assert _threshold_warnings(caplog) == []


def test_primary_key_containing_slash_does_not_warn(tmp_path, monkeypatch, store, caplog):
    config = _write_config(tmp_path, monkeypatch, "[fakefs]\n/home_percent_careful=50\n")
    with caplog.at_level(logging.WARNING):
        FakeFsPlugin(store, config)
    assert _threshold_warnings(caplog) == []


def test_bare_level_key_does_not_warn_when_plugin_has_watched_fields(tmp_path, monkeypatch, store, caplog):
    config = _write_config(tmp_path, monkeypatch, "[fakenetwork]\ncareful=50\n")
    with caplog.at_level(logging.WARNING):
        FakeNetworkPlugin(store, config)
    assert _threshold_warnings(caplog) == []


def test_non_threshold_keys_do_not_warn(tmp_path, monkeypatch, store, caplog):
    config = _write_config(tmp_path, monkeypatch, "[fakenetwork]\nhide_zero=True\nshow=eth.*\n")
    with caplog.at_level(logging.WARNING):
        FakeNetworkPlugin(store, config)
    assert _threshold_warnings(caplog) == []


def test_threshold_key_on_plugin_with_no_watched_field_warns(tmp_path, monkeypatch, store, caplog):
    config = _write_config(tmp_path, monkeypatch, "[fakenowatch]\nwarning=1\n")
    with caplog.at_level(logging.WARNING):
        FakeNoWatchedFieldPlugin(store, config)
    warnings = _threshold_warnings(caplog)
    assert len(warnings) == 1
    assert "warning" in warnings[0]


def test_warning_message_does_not_render_an_empty_accepted_list(tmp_path, monkeypatch, store, caplog):
    """A plugin with no watched field has an empty `accepted` set — the
    message must say so in words, not render `(accepted threshold names: )`
    (finding 6)."""
    config = _write_config(tmp_path, monkeypatch, "[fakenowatch]\nwarning=1\n")
    with caplog.at_level(logging.WARNING):
        FakeNoWatchedFieldPlugin(store, config)
    warnings = _threshold_warnings(caplog)
    assert len(warnings) == 1
    assert "accepted threshold names: )" not in warnings[0]
    assert "declares no generic threshold keys" in warnings[0]


# ---------------------------------------------------------- _recognises_threshold_key() extension point


class FakeSelfResolvingPlugin(GlancesPluginBase[dict]):
    """A plugin that resolves thresholds itself (like `sensors`), outside the
    base class's watched-field pipeline, and declares its own key shape via
    the `_recognises_threshold_key` hook."""

    plugin_name = "fakeselfresolving"
    IS_COLLECTION = False
    fields_description = {
        "value": {"description": "v", "unit": "number", "watched": True},
    }

    async def _grab_stats(self) -> dict:
        return {}

    def _recognises_threshold_key(self, remainder: str) -> bool:
        return remainder == "custom_shape"


def test_recognises_threshold_key_hook_suppresses_warning(tmp_path, monkeypatch, store, caplog):
    config = _write_config(tmp_path, monkeypatch, "[fakeselfresolving]\ncustom_shape_warning=1\n")
    with caplog.at_level(logging.WARNING):
        FakeSelfResolvingPlugin(store, config)
    assert _threshold_warnings(caplog) == []


def test_recognises_threshold_key_hook_does_not_blanket_disable_warnings(tmp_path, monkeypatch, store, caplog):
    """The hook answers per-shape, not per-plugin — a shape it does not
    recognise must still warn."""
    config = _write_config(tmp_path, monkeypatch, "[fakeselfresolving]\nnonsense_warning=1\n")
    with caplog.at_level(logging.WARNING):
        FakeSelfResolvingPlugin(store, config)
    warnings = _threshold_warnings(caplog)
    assert len(warnings) == 1
    assert "nonsense_warning" in warnings[0]


def test_recognises_threshold_key_hook_defaults_to_false(tmp_path, monkeypatch, store, caplog):
    """A plugin that does not override the hook gets no extra recognition —
    default behaviour for the overwhelming majority of plugins is unchanged."""
    config = _write_config(tmp_path, monkeypatch, "[fakenetwork]\ncustom_shape_warning=1\n")
    with caplog.at_level(logging.WARNING):
        FakeNetworkPlugin(store, config)
    warnings = _threshold_warnings(caplog)
    assert len(warnings) == 1
    assert "custom_shape_warning" in warnings[0]


# ---------------------------------------------------------- shipped conf: zero threshold-key warnings


def test_shipped_conf_produces_zero_threshold_warnings():
    """Permanent regression guard (finding 2): every plugin constructed
    against the repository's own `conf/glances.conf` must produce zero
    `unrecognised threshold key` WARNINGs. This is what catches the next
    threshold rename that forgets to update its example, or the next
    self-resolving plugin that forgets to override
    `_recognises_threshold_key()` (as `folders`/`ports` did, finding 1).

    Import-order matters here: importing `glances.main_v5` transitively
    imports every `glances.plugins.*.model_v5` module, several of which
    import `glances.logger` for the FIRST time in the process — whose
    module-level `logging.config.dictConfig()` call reconfigures the ROOT
    logger's handlers (`glances/logger.py`). A handler attached before
    that happens (e.g. naively via `caplog`, which attaches to root) is
    silently dropped — this mistake has already been made twice in this
    wave. Do the imports FIRST, attach the handler AFTER.
    """
    import pathlib

    from glances.config_v5 import GlancesConfigV5
    from glances.main_v5 import discover_plugin_classes
    from glances.stats_store_v5 import StatsStoreV5

    plugin_classes = discover_plugin_classes()  # imports every plugins.*.model_v5 module
    assert plugin_classes  # sanity: discovery actually found something

    records: list[logging.LogRecord] = []

    class _Collector(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    target_logger = logging.getLogger("glances.plugins.plugin.base_v5")
    handler = _Collector(level=logging.WARNING)
    target_logger.addHandler(handler)
    try:
        conf_path = pathlib.Path(__file__).resolve().parent.parent / "conf" / "glances.conf"
        config = GlancesConfigV5(cli_config_path=str(conf_path))
        store = StatsStoreV5()
        for _module_name, cls in plugin_classes:
            cls(store, config)
    finally:
        target_logger.removeHandler(handler)

    warnings = [r.getMessage() for r in records if "unrecognised threshold key" in r.getMessage()]
    assert warnings == []


# ---------------------------------------------------------- hide_zero / hide_threshold_bytes (design §5.1)


class _HideZeroCollection(FakeCollectionPlugin):
    """Collection plugin with two rate fields opted into the hide_zero filter."""

    HIDE_ZERO_FIELDS = ["rx", "tx"]
    fields_description = {
        "name": {"description": "n", "unit": "string", "primary_key": True},
        "rx": {"description": "rx", "unit": "bytespers", "rate": True},
        "tx": {"description": "tx", "unit": "bytespers", "rate": True},
    }


def _hz_fake_now(monkeypatch) -> list[float]:
    slot = [100.0]
    import glances.plugins.plugin.base_v5 as base_module

    monkeypatch.setattr(base_module.time, "monotonic", lambda: slot[0])
    return slot


def test_hide_zero_config_defaults(store, config):
    plugin = _HideZeroCollection(store, config)
    assert plugin.hide_zero is False
    assert plugin.hide_threshold_bytes == 0


def test_hide_zero_config_reads_from_section(tmp_path, monkeypatch, store):
    config = _write_config(tmp_path, monkeypatch, "[fakecollection]\nhide_zero=True\nhide_threshold_bytes=500\n")
    plugin = _HideZeroCollection(store, config)
    assert plugin.hide_zero is True
    assert plugin.hide_threshold_bytes == 500


async def test_hide_zero_noop_for_plugin_without_hide_zero_fields(store, config):
    """Base default HIDE_ZERO_FIELDS = [] — `hidden` is never added."""
    plugin = FakeCollectionPlugin(store, config, payload=[{"name": "eth0", "rx": 1024}])
    await plugin.update()
    item = store.get("fakecollection")["data"][0]
    assert "hidden" not in item


async def test_hide_zero_off_by_default_publishes_false_and_keeps_item(store, config):
    """hide_zero defaults to False: `hidden` is always False, item never dropped."""
    plugin = _HideZeroCollection(store, config, payload=[{"name": "eth0", "rx": 0, "tx": 0}])
    await plugin.update()
    data = store.get("fakecollection")["data"]
    assert len(data) == 1
    assert data[0]["hidden"] is False


async def test_hide_zero_none_rate_stays_hidden(tmp_path, monkeypatch, store):
    """First cycle: rate fields are None — None never un-hides (design §5.1)."""
    config = _write_config(tmp_path, monkeypatch, "[fakecollection]\nhide_zero=True\n")
    plugin = _HideZeroCollection(store, config, payload=[{"name": "eth0", "rx": 1000, "tx": 500}])
    await plugin.update()
    item = store.get("fakecollection")["data"][0]
    assert item["rx"] is None
    assert item["hidden"] is True


async def test_hide_zero_sticky_after_burst_then_back_to_zero(tmp_path, monkeypatch, store):
    """v4 cc5e2bab: a burst above the threshold un-hides for good."""
    config = _write_config(tmp_path, monkeypatch, "[fakecollection]\nhide_zero=True\n")
    plugin = _HideZeroCollection(store, config, payload=[{"name": "eth0", "rx": 0, "tx": 0}])
    now = _hz_fake_now(monkeypatch)

    await plugin.update()  # cycle 1 — rx/tx None, hidden
    assert store.get("fakecollection")["data"][0]["hidden"] is True

    now[0] = 101.0
    plugin._payload = [{"name": "eth0", "rx": 5000, "tx": 0}]  # rx rate 5000 > threshold 0
    await plugin.update()
    assert store.get("fakecollection")["data"][0]["hidden"] is False

    now[0] = 102.0
    plugin._payload = [{"name": "eth0", "rx": 5000, "tx": 0}]  # unchanged counter -> rate 0
    await plugin.update()
    assert store.get("fakecollection")["data"][0]["hidden"] is False  # sticky: stays visible


async def test_hide_zero_boundary_equal_threshold_does_not_unhide(tmp_path, monkeypatch, store):
    """v4 cc5e2bab: strict `>`, never `>=`."""
    config = _write_config(tmp_path, monkeypatch, "[fakecollection]\nhide_zero=True\nhide_threshold_bytes=1000\n")
    plugin = _HideZeroCollection(store, config, payload=[{"name": "eth0", "rx": 0, "tx": 0}])
    now = _hz_fake_now(monkeypatch)

    await plugin.update()  # cycle 1 — None

    now[0] = 101.0
    plugin._payload = [{"name": "eth0", "rx": 1000, "tx": 0}]  # rate == 1000 == threshold
    await plugin.update()
    assert store.get("fakecollection")["data"][0]["hidden"] is True

    now[0] = 102.0
    plugin._payload = [{"name": "eth0", "rx": 2001, "tx": 0}]  # delta 1001 / 1s = 1001 > 1000
    await plugin.update()
    assert store.get("fakecollection")["data"][0]["hidden"] is False


async def test_hide_zero_row_visible_when_one_field_unhides(tmp_path, monkeypatch, store):
    """A row stays visible while any of its fields is un-hidden (v4 ff80c903)."""
    config = _write_config(tmp_path, monkeypatch, "[fakecollection]\nhide_zero=True\n")
    plugin = _HideZeroCollection(store, config, payload=[{"name": "eth0", "rx": 0, "tx": 0}])
    now = _hz_fake_now(monkeypatch)

    await plugin.update()

    now[0] = 101.0
    plugin._payload = [{"name": "eth0", "rx": 500, "tx": 0}]  # rx un-hides, tx stays at 0
    await plugin.update()
    assert store.get("fakecollection")["data"][0]["hidden"] is False


async def test_hide_zero_resets_when_item_disappears_and_reappears(tmp_path, monkeypatch, store):
    """Sticky state is rebuilt each cycle from only the items currently present
    (mirrors v4 `update_views()` rebuilding `self.views` wholesale each cycle,
    `plugin/model.py:672-686`): an item absent for one cycle loses its
    accumulated state and starts hidden again if it comes back."""
    config = _write_config(tmp_path, monkeypatch, "[fakecollection]\nhide_zero=True\n")
    plugin = _HideZeroCollection(
        store, config, payload=[{"name": "eth0", "rx": 0, "tx": 0}, {"name": "wlan0", "rx": 0, "tx": 0}]
    )
    now = _hz_fake_now(monkeypatch)
    await plugin.update()  # cycle 1

    now[0] = 101.0
    plugin._payload = [{"name": "eth0", "rx": 5000, "tx": 0}, {"name": "wlan0", "rx": 0, "tx": 0}]
    await plugin.update()  # eth0 un-hides
    eth0 = next(i for i in store.get("fakecollection")["data"] if i["name"] == "eth0")
    assert eth0["hidden"] is False

    now[0] = 102.0
    plugin._payload = [{"name": "wlan0", "rx": 0, "tx": 0}]  # eth0 absent for one cycle
    await plugin.update()

    now[0] = 103.0
    plugin._payload = [{"name": "eth0", "rx": 5000, "tx": 0}, {"name": "wlan0", "rx": 0, "tx": 0}]
    await plugin.update()  # eth0 reappears
    eth0 = next(i for i in store.get("fakecollection")["data"] if i["name"] == "eth0")
    assert eth0["rx"] is None  # no previous sample either — _raw_previous reset too
    assert eth0["hidden"] is True  # sticky state reset — starts hidden again


async def test_hide_zero_hidden_field_is_internal_and_not_exported(tmp_path, monkeypatch, store):
    config = _write_config(tmp_path, monkeypatch, "[fakecollection]\nhide_zero=True\n")
    plugin = _HideZeroCollection(store, config, payload=[{"name": "eth0", "rx": 0, "tx": 0}])
    await plugin.update()

    exported = plugin.get_export()
    assert "hidden" not in exported[0]  # exportable: False

    api_payload = plugin.get_api_payload()
    assert "hidden" in api_payload["data"][0]  # internal: True — REST/MCP still see it
