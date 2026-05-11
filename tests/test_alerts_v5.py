#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for `GlancesAlerts`.

Covers: state machine (hysteresis), event shape, history bounded buffer,
3-level action precedence, fire-and-forget dispatch, scalar vs collection
plugins, min_duration_seconds per-plugin override.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest

from glances.actions_v5.action_base import GlancesActionBase
from glances.alerts_v5 import GlancesAlerts
from glances.config_v5 import GlancesConfigV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5

# ---------------------------------------------------------- fakes


class _RecordingAction(GlancesActionBase):
    """Test double that records every execute() call."""

    action_name = "action"
    requires = []

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[dict[str, Any]] = []

    async def execute(self, plugin_name, level, context, action_value, repeat=False):
        self.calls.append(
            {
                "plugin_name": plugin_name,
                "level": level,
                "context": dict(context),
                "action_value": action_value,
                "repeat": repeat,
            }
        )


class _BoomAction(GlancesActionBase):
    """Test double that always raises."""

    action_name = "boom"
    requires = []

    async def execute(self, plugin_name, level, context, action_value, repeat=False):
        raise RuntimeError("boom")


class _FakeScalarPlugin(GlancesPluginBase[dict]):
    """Scalar plugin whose `_levels` is set externally for the test."""

    plugin_name = "fakescalar"
    IS_COLLECTION = False
    fields_description = {
        "percent": {"description": "p", "unit": "percent"},
        "total": {"description": "t", "unit": "bytes"},
    }

    def __init__(self, store, config, *, payload=None, levels=None):
        super().__init__(store, config)
        self._payload = payload if payload is not None else {"percent": 50.0, "total": 1024}
        self._fixed_levels = levels if levels is not None else {}

    async def _grab_stats(self) -> dict:
        return dict(self._payload)

    def _derived_parameters(self) -> None:
        self._levels = dict(self._fixed_levels)


class _FakeCollectionPlugin(GlancesPluginBase[list]):
    """Collection plugin whose `_levels` is set externally for the test."""

    plugin_name = "fakecollection"
    IS_COLLECTION = True
    fields_description = {
        "name": {"description": "n", "unit": "string", "primary_key": True},
        "rx": {"description": "rx", "unit": "bytespers"},
    }

    def __init__(self, store, config, *, payload=None, levels=None):
        super().__init__(store, config)
        self._payload = payload if payload is not None else [{"name": "eth0", "rx": 1000}, {"name": "lo", "rx": 0}]
        self._fixed_levels = levels if levels is not None else {}

    async def _grab_stats(self) -> list:
        return [dict(item) for item in self._payload]

    def _derived_parameters(self) -> None:
        self._levels = {pk: dict(entries) for pk, entries in self._fixed_levels.items()}


# ---------------------------------------------------------- fixtures


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


def _clock():
    """A mutable monotonic clock substitute. Use `clock.tick(seconds)` to advance."""
    slot = [0.0]

    class _Clock:
        def __call__(self) -> float:
            return slot[0]

        def tick(self, seconds: float) -> None:
            slot[0] += seconds

    return _Clock()


async def _run_with_levels(plugin, alerts, levels):
    """Force a plugin's `_levels` to `levels`, refresh the store, then ingest."""
    plugin._fixed_levels = levels
    await plugin.update()
    await alerts.ingest_plugin(plugin)
    await alerts.drain()


# ---------------------------------------------------------- state machine


async def test_no_transition_when_level_stays_ok(store, config):
    alerts = GlancesAlerts(config)
    plugin = _FakeScalarPlugin(store, config)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "ok", "prominent": True}})
    assert alerts.get_history() == []


async def test_immediate_commit_when_min_duration_is_zero(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    alerts = GlancesAlerts(config)
    plugin = _FakeScalarPlugin(store, config)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    history = alerts.get_history()
    assert len(history) == 1
    assert history[0]["level"] == "warning"
    assert history[0]["previous_level"] == "ok"


async def test_hysteresis_holds_back_first_observation(tmp_path, monkeypatch, store):
    """With min_duration > 0, first cycle of a new level does not fire."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=5\n")
    clock = _clock()
    alerts = GlancesAlerts(config, now=clock)
    plugin = _FakeScalarPlugin(store, config)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    assert alerts.get_history() == []

    # 4 s later — still pending.
    clock.tick(4.0)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    assert alerts.get_history() == []

    # 2 more seconds — total 6 s ≥ 5 → commit.
    clock.tick(2.0)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    history = alerts.get_history()
    assert len(history) == 1
    assert history[0]["level"] == "warning"


async def test_hysteresis_resets_when_observed_level_oscillates(tmp_path, monkeypatch, store):
    """If the observed level changes during pending, the timer restarts."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=5\n")
    clock = _clock()
    alerts = GlancesAlerts(config, now=clock)
    plugin = _FakeScalarPlugin(store, config)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    clock.tick(3.0)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "critical", "prominent": True}})
    clock.tick(3.0)
    # Total 6 s — would have committed warning, but oscillated to critical at t=3.
    # The critical window only started at t=3, so 6-3=3 s < 5 → still no fire.
    assert alerts.get_history() == []


async def test_pending_clears_when_observation_returns_to_committed(tmp_path, monkeypatch, store):
    """An observation matching the committed level cancels any pending transition."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=5\n")
    clock = _clock()
    alerts = GlancesAlerts(config, now=clock)
    plugin = _FakeScalarPlugin(store, config)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    clock.tick(2.0)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "ok", "prominent": True}})
    # Now pending should be cleared. Even after 10 s of warning, the
    # timer starts fresh.
    clock.tick(10.0)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    # First cycle of fresh warning → no fire yet.
    assert alerts.get_history() == []
    clock.tick(6.0)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    history = alerts.get_history()
    assert len(history) == 1


async def test_resolution_event_recorded_but_no_action_fired(tmp_path, monkeypatch, store):
    """Transition non-ok → ok is recorded in history; non-repeat actions do not fire."""
    config = _config_with(
        tmp_path,
        monkeypatch,
        "[alerts]\nmin_duration_seconds=0\n[fakescalar]\nwarning_action=true\n",
    )
    action = _RecordingAction()
    alerts = GlancesAlerts(config, actions={"action": action})
    plugin = _FakeScalarPlugin(store, config)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    assert any(call["repeat"] is False for call in action.calls)
    action.calls.clear()

    # Resolution: warning → ok.
    await _run_with_levels(plugin, alerts, {"percent": {"level": "ok", "prominent": True}})
    history = alerts.get_history()
    assert history[-1]["level"] == "ok"
    assert history[-1]["previous_level"] == "warning"
    # No non-repeat action on resolution.
    assert not any(call["repeat"] is False for call in action.calls)


# ---------------------------------------------------------- event shape


async def test_event_shape_includes_required_fields(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    alerts = GlancesAlerts(config, hostname="myhost")
    plugin = _FakeScalarPlugin(store, config, payload={"percent": 75.0, "total": 1024})
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    event = alerts.get_history()[0]
    assert event["plugin"] == "fakescalar"
    assert event["field"] == "percent"
    assert event["key"] is None  # scalar
    assert event["level"] == "warning"
    assert event["previous_level"] == "ok"
    assert event["value"] == 75.0
    assert event["prominent"] is True
    assert event["hostname"] == "myhost"
    assert "ts" in event


async def test_event_key_field_is_pk_value_for_collection(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    alerts = GlancesAlerts(config)
    plugin = _FakeCollectionPlugin(
        store,
        config,
        payload=[{"name": "eth0", "rx": 1000}, {"name": "wlan0", "rx": 500}],
    )
    await _run_with_levels(
        plugin,
        alerts,
        {
            "eth0": {"rx": {"level": "warning", "prominent": True}},
            "wlan0": {"rx": {"level": "critical", "prominent": True}},
        },
    )
    keys = sorted(event["key"] for event in alerts.get_history())
    assert keys == ["eth0", "wlan0"]


# ---------------------------------------------------------- history bounded


async def test_history_size_capped_by_deque(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\nhistory_size=3\n")
    alerts = GlancesAlerts(config)
    plugin = _FakeScalarPlugin(store, config)
    # Drive 5 alternating transitions — old events should be evicted.
    for level in ["warning", "ok", "critical", "ok", "warning"]:
        await _run_with_levels(plugin, alerts, {"percent": {"level": level, "prominent": True}})
    history = alerts.get_history()
    assert len(history) == 3
    # Last three transitions (critical, ok, warning).
    assert [event["level"] for event in history] == ["critical", "ok", "warning"]


# ---------------------------------------------------------- min_duration per-plugin


async def test_per_plugin_min_duration_overrides_global(tmp_path, monkeypatch, store):
    config = _config_with(
        tmp_path,
        monkeypatch,
        "[alerts]\nmin_duration_seconds=10\n[fakescalar]\nmin_duration_seconds=0\n",
    )
    alerts = GlancesAlerts(config)
    plugin = _FakeScalarPlugin(store, config)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    # Plugin override is 0 → immediate commit.
    assert len(alerts.get_history()) == 1


# ---------------------------------------------------------- action dispatch


async def test_non_repeat_action_fires_on_entry(tmp_path, monkeypatch, store):
    config = _config_with(
        tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n[fakescalar]\nwarning_action=echo hi\n"
    )
    action = _RecordingAction()
    alerts = GlancesAlerts(config, actions={"action": action})
    plugin = _FakeScalarPlugin(store, config)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    # One non-repeat call (entry) — repeat key isn't set so no repeat call.
    assert [c["repeat"] for c in action.calls] == [False]
    assert action.calls[0]["action_value"] == "echo hi"


async def test_repeat_action_fires_every_cycle_while_committed_non_ok(tmp_path, monkeypatch, store):
    config = _config_with(
        tmp_path,
        monkeypatch,
        "[alerts]\nmin_duration_seconds=0\n[fakescalar]\nwarning_action_repeat=repeat-cmd\n",
    )
    action = _RecordingAction()
    alerts = GlancesAlerts(config, actions={"action": action})
    plugin = _FakeScalarPlugin(store, config)

    # First cycle: entry — repeat fires (one call).
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    assert [c["repeat"] for c in action.calls] == [True]
    # Second cycle, same level — repeat fires again.
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    assert [c["repeat"] for c in action.calls] == [True, True]
    # Third cycle, back to ok — no repeat fire.
    await _run_with_levels(plugin, alerts, {"percent": {"level": "ok", "prominent": True}})
    assert [c["repeat"] for c in action.calls] == [True, True]


async def test_both_repeat_and_non_repeat_fire_on_entry(tmp_path, monkeypatch, store):
    config = _config_with(
        tmp_path,
        monkeypatch,
        "[alerts]\nmin_duration_seconds=0\n[fakescalar]\nwarning_action=once\nwarning_action_repeat=every\n",
    )
    action = _RecordingAction()
    alerts = GlancesAlerts(config, actions={"action": action})
    plugin = _FakeScalarPlugin(store, config)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    repeat_flags = sorted(c["repeat"] for c in action.calls)
    assert repeat_flags == [False, True]  # both fire on entry


async def test_action_key_precedence_pk_then_field_then_bare(tmp_path, monkeypatch, store):
    """For collections, `<pk>_<field>_<level>_<action>` beats `<field>_..` beats `<level>_..`."""
    config = _config_with(
        tmp_path,
        monkeypatch,
        "[alerts]\nmin_duration_seconds=0\n"
        "[fakecollection]\n"
        "critical_action=any-field\n"
        "rx_critical_action=any-iface\n"
        "wlan0_rx_critical_action=wlan-specific\n",
    )
    action = _RecordingAction()
    alerts = GlancesAlerts(config, actions={"action": action})
    plugin = _FakeCollectionPlugin(
        store,
        config,
        payload=[{"name": "eth0", "rx": 100}, {"name": "wlan0", "rx": 200}],
    )
    await _run_with_levels(
        plugin,
        alerts,
        {
            "eth0": {"rx": {"level": "critical", "prominent": True}},
            "wlan0": {"rx": {"level": "critical", "prominent": True}},
        },
    )
    # Filter non-repeat calls (entries).
    entries = [c for c in action.calls if not c["repeat"]]
    payloads = {c["context"]["name"]: c["action_value"] for c in entries}
    assert payloads["eth0"] == "any-iface"  # field-specific (no pk override for eth0)
    assert payloads["wlan0"] == "wlan-specific"


async def test_action_template_context_includes_builtins(tmp_path, monkeypatch, store):
    config = _config_with(
        tmp_path,
        monkeypatch,
        "[alerts]\nmin_duration_seconds=0\n[fakescalar]\nwarning_action=t\n",
    )
    action = _RecordingAction()
    alerts = GlancesAlerts(config, actions={"action": action}, hostname="myhost")
    plugin = _FakeScalarPlugin(store, config, payload={"percent": 75.0, "total": 1024})
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    context = action.calls[0]["context"]
    assert context["_glances_hostname"] == "myhost"
    assert context["_glances_plugin"] == "fakescalar"
    assert context["_glances_level"] == "warning"
    assert "_glances_timestamp" in context
    # Plugin export values flow into the context.
    assert context["percent"] == 75.0
    assert context["total"] == 1024


async def test_failing_action_is_logged_and_does_not_raise(tmp_path, monkeypatch, store, caplog):
    config = _config_with(
        tmp_path,
        monkeypatch,
        "[alerts]\nmin_duration_seconds=0\n[fakescalar]\nwarning_boom=t\n",
    )
    alerts = GlancesAlerts(config, actions={"boom": _BoomAction()})
    plugin = _FakeScalarPlugin(store, config)
    with caplog.at_level(logging.WARNING):
        await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    assert "Action 'boom' failed" in caplog.text


# ---------------------------------------------------------- collection plugin


async def test_collection_state_is_per_pk_value(tmp_path, monkeypatch, store):
    """Each interface tracks its own committed level independently."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    alerts = GlancesAlerts(config)
    plugin = _FakeCollectionPlugin(
        store,
        config,
        payload=[{"name": "eth0", "rx": 1000}, {"name": "wlan0", "rx": 500}],
    )
    # First cycle: eth0 warning, wlan0 ok.
    await _run_with_levels(
        plugin,
        alerts,
        {
            "eth0": {"rx": {"level": "warning", "prominent": True}},
            "wlan0": {"rx": {"level": "ok", "prominent": True}},
        },
    )
    assert len(alerts.get_history()) == 1
    assert alerts.get_history()[0]["key"] == "eth0"

    # Second cycle: eth0 stays warning, wlan0 → critical.
    await _run_with_levels(
        plugin,
        alerts,
        {
            "eth0": {"rx": {"level": "warning", "prominent": True}},
            "wlan0": {"rx": {"level": "critical", "prominent": True}},
        },
    )
    # Two transitions total now: eth0 warning entry + wlan0 critical entry.
    assert len(alerts.get_history()) == 2
    last = alerts.get_history()[-1]
    assert last["key"] == "wlan0"
    assert last["level"] == "critical"


# ---------------------------------------------------------- minor


async def test_get_history_returns_a_copy(tmp_path, monkeypatch, store):
    """Mutating the returned list must not corrupt the internal deque."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    alerts = GlancesAlerts(config)
    plugin = _FakeScalarPlugin(store, config)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    snapshot = alerts.get_history()
    snapshot.clear()
    assert len(alerts.get_history()) == 1


async def test_ingest_plugin_with_no_actions_is_safe(tmp_path, monkeypatch, store):
    """A `GlancesAlerts` with no actions registry still ingests transitions cleanly."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    alerts = GlancesAlerts(config)  # actions=None default
    plugin = _FakeScalarPlugin(store, config)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    assert len(alerts.get_history()) == 1
