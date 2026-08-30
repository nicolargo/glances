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
from collections import Counter
from typing import Any

import pytest

from glances.actions_v5.action_base import GlancesActionBase
from glances.alerts_v5 import _TOP_COUNTER_MAX_KEYS, GlancesAlerts, _AlertState
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
    """Default test config — disables the alert warmup so each test can
    observe a single ingestion. The warmup itself is tested separately
    via `_config_with(... warmup_cycles=N ...)`."""
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    xdg = tmp_path / "xdg"
    cfg_dir = xdg / "glances"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "glances.conf").write_text("[alerts]\nwarmup_cycles=0\n")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    return GlancesConfigV5()


def _config_with(tmp_path, monkeypatch, body: str) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    xdg = tmp_path / "xdg"
    cfg_dir = xdg / "glances"
    cfg_dir.mkdir(parents=True)
    # Default to no warmup so individual alert tests can ingest once and
    # observe the outcome. Tests that need the warmup pass an explicit
    # `warmup_cycles=N` in their body.
    if "warmup_cycles" not in body:
        if "[alerts]" in body:
            body = body.replace("[alerts]", "[alerts]\nwarmup_cycles=0", 1)
        else:
            body = "[alerts]\nwarmup_cycles=0\n" + body
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


async def test_is_initializing_true_before_any_ingest(config):
    """At construction time no plugin has been ingested → initializing."""
    alerts = GlancesAlerts(config)
    assert alerts.is_initializing() is True


async def test_is_initializing_true_during_warmup(tmp_path, monkeypatch, store):
    """While at least one plugin is still inside the warmup window → initializing."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nwarmup_cycles=3\n")
    alerts = GlancesAlerts(config)
    plugin = _FakeScalarPlugin(store, config)
    # Cycles 1..3 are warmup — no events can fire yet.
    for _ in range(3):
        await _run_with_levels(plugin, alerts, {"percent": {"level": "ok", "prominent": True}})
    assert alerts.is_initializing() is True


async def test_is_initializing_false_after_warmup_completes(tmp_path, monkeypatch, store):
    """Once every ingested plugin is past its warmup → no longer initializing."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nwarmup_cycles=3\n")
    alerts = GlancesAlerts(config)
    plugin = _FakeScalarPlugin(store, config)
    # 4 cycles: 3 warmup + 1 real ingest.
    for _ in range(4):
        await _run_with_levels(plugin, alerts, {"percent": {"level": "ok", "prominent": True}})
    assert alerts.is_initializing() is False


async def test_is_initializing_false_after_warmup_even_with_pending(tmp_path, monkeypatch, store):
    """Once warmup is done the engine is no longer "initializing" — even while
    a non-ok observation is still inside its min_duration window (a pending,
    not-yet-committed transition). Settling is NOT initializing: with an empty
    history the UI shows "no alert detected", which is accurate (no alert has
    committed yet). Dropping the old pending-based clause prevents
    is_initializing() from latching True forever when a field flaps across a
    threshold and its transition never commits."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nwarmup_cycles=1\nmin_duration_seconds=5\n")
    clock = _clock()
    alerts = GlancesAlerts(config, now=clock)
    plugin = _FakeScalarPlugin(store, config)

    # First cycle is warmup → still initializing.
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    assert alerts.is_initializing() is True

    # Second cycle: post-warmup. observed=warning, committed=ok → pending.
    # History still empty (min_duration not elapsed), but warmup is complete
    # → no longer initializing.
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    assert alerts.get_history() == []
    assert alerts.is_initializing() is False


async def test_is_initializing_false_once_any_plugin_past_warmup(tmp_path, monkeypatch, store):
    """Mixed state — as soon as ONE plugin has finished its warmup and produced
    a real (post-warmup) ingest, the engine can have fired events, so it is no
    longer "initializing", even while another plugin is still warming up.

    Requiring EVERY plugin to finish warmup was a latch bug: each plugin has its
    own refresh loop, so a single slow-refresh plugin (polling every few
    minutes) would hold ``is_initializing()`` at ``True`` for minutes — and a
    plugin that only ever ingests once would hold it forever."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nwarmup_cycles=3\n")
    alerts = GlancesAlerts(config)
    p_fast = _FakeScalarPlugin(store, config)
    p_fast.plugin_name = "fast"
    p_slow = _FakeScalarPlugin(store, config)
    p_slow.plugin_name = "slow"
    # `fast` gets 4 cycles (past warmup); `slow` only 2 (still warming).
    for _ in range(4):
        await _run_with_levels(p_fast, alerts, {"percent": {"level": "ok", "prominent": True}})
    for _ in range(2):
        await _run_with_levels(p_slow, alerts, {"percent": {"level": "ok", "prominent": True}})
    assert alerts.is_initializing() is False


async def test_first_event_after_warmup_is_flagged_initial(tmp_path, monkeypatch, store):
    """When the first post-warmup observation is already non-ok, the emitted
    event is flagged ``is_initial=True`` — Glances was started while the
    system was already in that state, so the renderer must show the level
    as a steady state instead of a misleading "ok → <level>" transition."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    alerts = GlancesAlerts(config)
    plugin = _FakeScalarPlugin(store, config, payload={"percent": 60.0})
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})

    history = alerts.get_history()
    assert len(history) == 1
    event = history[0]
    assert event["level"] == "warning"
    assert event["previous_level"] == "ok"  # default committed_level
    assert event["is_initial"] is True


async def test_careful_level_raises_no_alert(tmp_path, monkeypatch, store):
    """A ``careful`` level colours the TUI but must NOT enter the alert
    history (alerts are warning+ only). ``warning`` on the same field does."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    alerts = GlancesAlerts(config)
    plugin = _FakeScalarPlugin(store, config, payload={"percent": 50.0})
    await _run_with_levels(plugin, alerts, {"percent": {"level": "careful", "prominent": True}})
    assert alerts.get_history() == []  # careful -> no alert

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    assert len(alerts.get_history()) == 1
    assert alerts.get_history()[0]["level"] == "warning"


async def test_subsequent_transitions_are_not_initial(tmp_path, monkeypatch, store):
    """After the first observed level has been committed, every following
    transition is a real change — ``is_initial`` must be ``False``."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    alerts = GlancesAlerts(config)
    plugin = _FakeScalarPlugin(store, config, payload={"percent": 80.0})

    # First post-warmup observation: warning. Flagged initial.
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    # Then back to ok — real transition.
    await _run_with_levels(plugin, alerts, {"percent": {"level": "ok", "prominent": True}})
    # Then up again to warning — real transition.
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})

    history = alerts.get_history()
    assert len(history) == 3
    assert history[0]["is_initial"] is True
    assert history[1]["is_initial"] is False
    assert history[2]["is_initial"] is False


async def test_initial_flag_set_when_first_observed_is_ok_then_non_ok(tmp_path, monkeypatch, store):
    """If the first post-warmup observation IS ok, no event is emitted (no
    transition). A later transition out of ok is then a real change, not an
    initial state."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    alerts = GlancesAlerts(config)
    plugin = _FakeScalarPlugin(store, config, payload={"percent": 30.0})

    # First observation: ok → no event but state is now confirmed at ok.
    await _run_with_levels(plugin, alerts, {"percent": {"level": "ok", "prominent": True}})
    assert alerts.get_history() == []

    # Later, system enters warning — real transition, NOT initial.
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    history = alerts.get_history()
    assert len(history) == 1
    assert history[0]["is_initial"] is False


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


# ----------------------- min_duration precedence (Phase 1.2 fix) -----------


async def test_field_min_duration_overrides_plugin(tmp_path, monkeypatch, store):
    """`<field>_min_duration_seconds` beats the plugin-section default."""
    config = _config_with(
        tmp_path,
        monkeypatch,
        # Plugin says 10 s for everything; the field-specific key says 0 → commits now.
        "[alerts]\nmin_duration_seconds=10\n[fakescalar]\nmin_duration_seconds=10\npercent_min_duration_seconds=0\n",
    )
    alerts = GlancesAlerts(config)
    plugin = _FakeScalarPlugin(store, config)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    assert len(alerts.get_history()) == 1


async def test_field_level_min_duration_overrides_field(tmp_path, monkeypatch, store):
    """`<field>_<level>_min_duration_seconds` beats `<field>_min_duration_seconds`.

    This is the contract the user asked for:
    ``ctx_switches_critical_min_duration_seconds=300`` raises critical
    only after 300 s sustained, while other levels of the same field stay
    fast. Here we encode the same shape with `warning_min_duration_seconds=10`
    overridden to `0` only for the critical level — entering critical must
    commit instantly while entering warning would still hold.
    """
    config = _config_with(
        tmp_path,
        monkeypatch,
        "[alerts]\nmin_duration_seconds=10\n"
        "[fakescalar]\npercent_min_duration_seconds=10\n"
        "percent_critical_min_duration_seconds=0\n",
    )
    alerts = GlancesAlerts(config)
    plugin = _FakeScalarPlugin(store, config)
    # Observing `critical` directly → uses the 0 s override → immediate commit.
    await _run_with_levels(plugin, alerts, {"percent": {"level": "critical", "prominent": True}})
    assert len(alerts.get_history()) == 1
    assert alerts.get_history()[0]["level"] == "critical"


async def test_warning_level_uses_field_default_when_only_critical_overridden(tmp_path, monkeypatch, store):
    """Per-level override on `critical` must NOT bleed into `warning`."""
    config = _config_with(
        tmp_path,
        monkeypatch,
        "[alerts]\nmin_duration_seconds=10\n"
        "[fakescalar]\npercent_min_duration_seconds=10\n"
        "percent_critical_min_duration_seconds=0\n",
    )
    alerts = GlancesAlerts(config)
    plugin = _FakeScalarPlugin(store, config)
    # warning observation → field default (10 s) applies → no immediate commit.
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    assert alerts.get_history() == []


async def test_collection_pk_field_level_min_duration_overrides_field_level(tmp_path, monkeypatch, store):
    """`<pk>_<field>_<level>_min_duration_seconds` beats `<field>_<level>_min_duration_seconds`."""
    config = _config_with(
        tmp_path,
        monkeypatch,
        "[alerts]\nmin_duration_seconds=10\n"
        "[fakecollection]\nrx_warning_min_duration_seconds=10\n"
        "eth0_rx_warning_min_duration_seconds=0\n",
    )
    alerts = GlancesAlerts(config)
    plugin = _FakeCollectionPlugin(store, config)
    # eth0 hits the pk-specific 0 s → immediate commit. lo stays under the 10 s field default.
    await _run_with_levels(
        plugin,
        alerts,
        {
            "eth0": {"rx": {"level": "warning", "prominent": True}},
            "lo": {"rx": {"level": "warning", "prominent": True}},
        },
    )
    history = alerts.get_history()
    keys = {(e["key"], e["level"]) for e in history}
    assert ("eth0", "warning") in keys
    assert ("lo", "warning") not in keys  # held back by 10 s field default


async def test_collection_pk_field_min_duration_overrides_field(tmp_path, monkeypatch, store):
    """`<pk>_<field>_min_duration_seconds` beats `<field>_min_duration_seconds`."""
    config = _config_with(
        tmp_path,
        monkeypatch,
        "[alerts]\nmin_duration_seconds=10\n"
        "[fakecollection]\nrx_min_duration_seconds=10\n"
        "eth0_rx_min_duration_seconds=0\n",
    )
    alerts = GlancesAlerts(config)
    plugin = _FakeCollectionPlugin(store, config)
    await _run_with_levels(
        plugin,
        alerts,
        {
            "eth0": {"rx": {"level": "warning", "prominent": True}},
            "lo": {"rx": {"level": "warning", "prominent": True}},
        },
    )
    keys = {(e["key"], e["level"]) for e in alerts.get_history()}
    assert ("eth0", "warning") in keys
    assert ("lo", "warning") not in keys


async def test_ctx_switches_critical_300s_end_to_end(tmp_path, monkeypatch, store):
    """End-to-end scenario validating the user-requested contract:

    ``ctx_switches_critical_min_duration_seconds=300`` raises CRITICAL only
    after the value has been at critical for at least 300 s. Earlier cycles
    stay pending; warning observations during the window reset the timer.
    """
    config = _config_with(
        tmp_path,
        monkeypatch,
        "[alerts]\nmin_duration_seconds=5\n[fakescalar]\npercent_critical_min_duration_seconds=300\n",
    )
    clock = _clock()
    alerts = GlancesAlerts(config, now=clock)
    plugin = _FakeScalarPlugin(store, config)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "critical", "prominent": True}})
    assert alerts.get_history() == []  # 0 s — pending

    clock.tick(150.0)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "critical", "prominent": True}})
    assert alerts.get_history() == []  # 150 s — still pending

    clock.tick(149.0)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "critical", "prominent": True}})
    assert alerts.get_history() == []  # 299 s — still pending

    clock.tick(2.0)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "critical", "prominent": True}})
    # 301 s ≥ 300 → commit.
    history = alerts.get_history()
    assert len(history) == 1
    assert history[0]["level"] == "critical"


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


# ---------------------------------------------------------- warmup


async def test_warmup_skips_first_n_cycles(tmp_path, monkeypatch, store):
    """For the first `warmup_cycles` ingestions per plugin, no event is emitted."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\nwarmup_cycles=3\n")
    alerts = GlancesAlerts(config)
    plugin = _FakeScalarPlugin(store, config)
    # First 3 ingestions: warming up, ignored even with a warning level.
    for _ in range(3):
        await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    assert alerts.get_history() == []
    # Cycle 4: warmup elapsed, first real ingestion fires the transition.
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    history = alerts.get_history()
    assert len(history) == 1
    assert history[0]["level"] == "warning"
    assert history[0]["previous_level"] == "ok"


async def test_warmup_is_per_plugin(tmp_path, monkeypatch, store):
    """Two plugins ingesting interleaved each have their own warmup window."""

    class _PluginP1(_FakeScalarPlugin):
        plugin_name = "p1"

    class _PluginP2(_FakeScalarPlugin):
        plugin_name = "p2"

    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\nwarmup_cycles=2\n")
    alerts = GlancesAlerts(config)
    p1 = _PluginP1(store, config)
    p2 = _PluginP2(store, config)

    await _run_with_levels(p1, alerts, {"percent": {"level": "warning", "prominent": True}})
    await _run_with_levels(p2, alerts, {"percent": {"level": "warning", "prominent": True}})
    # Each plugin: 1 warmup tick consumed, still in warmup.
    assert alerts.get_history() == []

    await _run_with_levels(p1, alerts, {"percent": {"level": "warning", "prominent": True}})
    await _run_with_levels(p2, alerts, {"percent": {"level": "warning", "prominent": True}})
    # Each plugin: 2 warmup ticks consumed (== warmup_cycles), still no event.
    assert alerts.get_history() == []

    await _run_with_levels(p1, alerts, {"percent": {"level": "warning", "prominent": True}})
    # p1 cycle 3 — warmup over → emits event.
    assert len(alerts.get_history()) == 1
    assert alerts.get_history()[0]["plugin"] == "p1"


async def test_warmup_zero_means_immediate_ingestion(tmp_path, monkeypatch, store):
    """`warmup_cycles=0` disables the warmup (used by most existing tests)."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\nwarmup_cycles=0\n")
    alerts = GlancesAlerts(config)
    plugin = _FakeScalarPlugin(store, config)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    assert len(alerts.get_history()) == 1


# ---------------------------------------------------------- EMITS_ALERTS opt-out


async def test_plugin_with_emits_alerts_false_is_skipped(tmp_path, monkeypatch, store):
    """Plugins flagged ``EMITS_ALERTS=False`` produce ``_levels`` for the
    renderer but contribute nothing to the alerts history.

    Mirrors the processlist case: per-process CPU/MEM thresholds drive cell
    colouring without paging the operator on individual pids."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\nwarmup_cycles=0\n")
    alerts = GlancesAlerts(config)
    plugin = _FakeScalarPlugin(store, config)
    plugin.EMITS_ALERTS = False  # opt-out (subclass-level in real plugins)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "critical", "prominent": True}})
    assert alerts.get_history() == []


async def test_plugin_with_emits_alerts_false_does_not_fire_actions(tmp_path, monkeypatch, store):
    """Opt-out also prevents action dispatch (entry + repeat)."""
    config = _config_with(
        tmp_path,
        monkeypatch,
        "[alerts]\nmin_duration_seconds=0\nwarmup_cycles=0\n[fakescalar]\npercent_critical_action=run_recording\n",
    )
    recording = _RecordingAction()
    registry = {"run_recording": recording}
    alerts = GlancesAlerts(config, actions=registry)
    plugin = _FakeScalarPlugin(store, config)
    plugin.EMITS_ALERTS = False
    await _run_with_levels(plugin, alerts, {"percent": {"level": "critical", "prominent": True}})
    assert recording.calls == []


# ---------------------------------------------------------- dynamic process auto-sort


class _MemPlugin(_FakeScalarPlugin):
    """Scalar plugin named ``mem`` — drives auto-sort to memory_percent."""

    plugin_name = "mem"


class _CpuPlugin(_FakeScalarPlugin):
    """Scalar plugin named ``cpu`` — its ``iowait`` field drives io_counters."""

    plugin_name = "cpu"


class _FakeProcessEngine:
    """Duck-typed ``glances_processes`` stand-in for auto-sort tests."""

    def __init__(self, auto_sort: bool = True) -> None:
        self.auto_sort = auto_sort
        self.sort_key = "cpu_percent"
        self.calls: list[tuple[str, bool]] = []

    def set_sort_key(self, key, auto=True) -> None:
        self.calls.append((key, auto))
        self.sort_key = "cpu_percent" if key == "auto" else key
        self.auto_sort = True if key == "auto" else auto


async def test_auto_sort_defaults_to_cpu_percent(tmp_path, monkeypatch, store):
    """No active alert → auto-sort keeps cpu_percent (and stays enabled)."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeProcessEngine()
    alerts = GlancesAlerts(config, process_engine=engine)
    plugin = _CpuPlugin(store, config)
    await _run_with_levels(plugin, alerts, {"total": {"level": "ok", "prominent": True}})
    assert engine.sort_key == "cpu_percent"
    assert engine.calls[-1] == ("cpu_percent", True)


async def test_auto_sort_switches_to_memory_on_mem_alert(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeProcessEngine()
    alerts = GlancesAlerts(config, process_engine=engine)
    plugin = _MemPlugin(store, config)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "critical", "prominent": True}})
    assert engine.sort_key == "memory_percent"


async def test_auto_sort_switches_to_io_on_cpu_iowait_alert(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeProcessEngine()
    alerts = GlancesAlerts(config, process_engine=engine)
    plugin = _CpuPlugin(store, config)
    await _run_with_levels(plugin, alerts, {"iowait": {"level": "warning", "prominent": True}})
    assert engine.sort_key == "io_counters"


async def test_auto_sort_mem_takes_precedence_over_iowait(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeProcessEngine()
    alerts = GlancesAlerts(config, process_engine=engine)
    cpu = _CpuPlugin(store, config)
    mem = _MemPlugin(store, config)
    await _run_with_levels(cpu, alerts, {"iowait": {"level": "warning", "prominent": True}})
    assert engine.sort_key == "io_counters"
    await _run_with_levels(mem, alerts, {"percent": {"level": "critical", "prominent": True}})
    # MEM now active alongside IOWAIT → memory_percent wins.
    assert engine.sort_key == "memory_percent"


async def test_auto_sort_resets_after_recovery(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeProcessEngine()
    alerts = GlancesAlerts(config, process_engine=engine)
    mem = _MemPlugin(store, config)
    await _run_with_levels(mem, alerts, {"percent": {"level": "critical", "prominent": True}})
    assert engine.sort_key == "memory_percent"
    # Memory pressure clears → back to the cpu_percent default.
    await _run_with_levels(mem, alerts, {"percent": {"level": "ok", "prominent": True}})
    assert engine.sort_key == "cpu_percent"


async def test_auto_sort_noop_when_manual_sort_selected(tmp_path, monkeypatch, store):
    """`auto_sort=False` (user picked a manual key) → engine untouched."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeProcessEngine(auto_sort=False)
    alerts = GlancesAlerts(config, process_engine=engine)
    mem = _MemPlugin(store, config)
    await _run_with_levels(mem, alerts, {"percent": {"level": "critical", "prominent": True}})
    assert engine.calls == []


async def test_auto_sort_noop_without_engine(tmp_path, monkeypatch, store):
    """No engine wired (default) → ingest still works, no crash."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    alerts = GlancesAlerts(config)  # process_engine=None
    mem = _MemPlugin(store, config)
    await _run_with_levels(mem, alerts, {"percent": {"level": "critical", "prominent": True}})
    assert len(alerts.get_history()) == 1


# ---------------------------------------------------------- get_ongoing


def test_get_ongoing_is_empty_before_any_alert(config):
    """No committed non-ok level → no ongoing entry."""
    alerts = GlancesAlerts(config)
    assert alerts.get_ongoing() == {}


def test_get_ongoing_reports_committed_non_ok_levels(config):
    """A committed warning shows up keyed by (plugin, key, field)."""
    alerts = GlancesAlerts(config)
    alerts._state[("mem", None, "percent")] = _AlertState(committed_level="warning", has_committed=True)
    assert alerts.get_ongoing() == {("mem", None, "percent"): "warning"}


def test_get_ongoing_omits_ok_tuples(config):
    """Recovered tuples are dropped, not reported with level 'ok'."""
    alerts = GlancesAlerts(config)
    alerts._state[("mem", None, "percent")] = _AlertState(committed_level="ok", has_committed=True)
    alerts._state[("fs", "/", "percent")] = _AlertState(committed_level="critical", has_committed=True)
    assert alerts.get_ongoing() == {("fs", "/", "percent"): "critical"}


def test_get_ongoing_survives_history_eviction(config):
    """The whole point: an active alert whose events aged out is still reported.

    `_state` is unbounded while `_history` is a bounded deque, so clearing the
    history must not change what `get_ongoing()` reports.
    """
    alerts = GlancesAlerts(config)
    alerts._state[("cpu", None, "total")] = _AlertState(committed_level="critical", has_committed=True)
    alerts._history.clear()
    assert alerts.get_ongoing() == {("cpu", None, "total"): "critical"}


def test_get_ongoing_does_not_mutate_state(config):
    """Read-only: calling it twice yields equal results and leaves _state alone."""
    alerts = GlancesAlerts(config)
    alerts._state[("mem", None, "percent")] = _AlertState(committed_level="warning", has_committed=True)
    before = dict(alerts._state)
    first = alerts.get_ongoing()
    second = alerts.get_ongoing()
    assert first == second
    assert alerts._state == before


def test_get_ongoing_returns_a_copy(config):
    """Mutating the returned dict must not corrupt the engine."""
    alerts = GlancesAlerts(config)
    alerts._state[("mem", None, "percent")] = _AlertState(committed_level="warning", has_committed=True)
    alerts.get_ongoing()[("bogus", None, "x")] = "critical"
    assert ("bogus", None, "x") not in alerts._state


# ---------------------------------------------------- get_ongoing_since


async def test_get_ongoing_since_records_the_opening_transition(tmp_path, monkeypatch, store):
    """The instant an incident opened is kept in `_state`, not only in `_history`."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    alerts = GlancesAlerts(config)
    plugin = _FakeScalarPlugin(store, config)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    opening = alerts.get_history()[0]
    assert alerts.get_ongoing_since() == {("fakescalar", None, "percent"): opening["ts"]}


async def test_get_ongoing_since_is_not_moved_by_an_escalation(tmp_path, monkeypatch, store):
    """warning → critical is the SAME incident: its start must not jump."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    alerts = GlancesAlerts(config)
    plugin = _FakeScalarPlugin(store, config)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    opening_ts = alerts.get_history()[0]["ts"]
    await _run_with_levels(plugin, alerts, {"percent": {"level": "critical", "prominent": True}})
    assert len(alerts.get_history()) == 2
    assert alerts.get_ongoing_since() == {("fakescalar", None, "percent"): opening_ts}


async def test_get_ongoing_since_is_cleared_on_recovery(tmp_path, monkeypatch, store):
    """Back to `ok` closes the incident — nothing is reported as ongoing."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    alerts = GlancesAlerts(config)
    plugin = _FakeScalarPlugin(store, config)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    await _run_with_levels(plugin, alerts, {"percent": {"level": "ok", "prominent": True}})
    assert alerts.get_ongoing_since() == {}


async def test_get_ongoing_since_survives_history_eviction(tmp_path, monkeypatch, store):
    """The bug this exists for: `_history` is a bounded ring buffer, so the
    opening event of a long-running alert is evicted by later, unrelated
    transitions. `_state` must still know when it started."""
    config = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\nhistory_size=4\n")
    alerts = GlancesAlerts(config)
    plugin = _FakeScalarPlugin(store, config)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    opening_ts = alerts.get_history()[0]["ts"]

    # Flap an unrelated field until the opening event has aged out.
    for _ in range(4):
        await _run_with_levels(
            plugin,
            alerts,
            {"percent": {"level": "warning", "prominent": True}, "total": {"level": "critical", "prominent": False}},
        )
        await _run_with_levels(
            plugin,
            alerts,
            {"percent": {"level": "warning", "prominent": True}, "total": {"level": "ok", "prominent": False}},
        )

    state_key = ("fakescalar", None, "percent")
    assert all(evt["field"] != "percent" for evt in alerts.get_history())
    assert alerts.get_ongoing() == {state_key: "warning"}
    assert alerts.get_ongoing_since() == {state_key: opening_ts}


# ---------------------------------------------------------- top processes: allowlist


def test_top_processes_sort_allowlist_is_exactly_five_fields():
    """Spec §4 — only the aggregate signals a user reacts to are annotated.

    Annotating cpu.system/user/steal alongside cpu.total would produce three
    near-identical rows for one episode of CPU pressure; load.min5 alongside
    load.min15 would double every load incident.
    """
    from glances.plugins.cpu.model_v5 import PluginModel as CpuModel
    from glances.plugins.load.model_v5 import PluginModel as LoadModel
    from glances.plugins.mem.model_v5 import PluginModel as MemModel
    from glances.plugins.memswap.model_v5 import PluginModel as SwapModel

    declared = {
        (model.plugin_name, field): schema["top_processes_sort"]
        for model in (CpuModel, LoadModel, MemModel, SwapModel)
        for field, schema in model.fields_description.items()
        if "top_processes_sort" in schema
    }
    assert declared == {
        ("cpu", "total"): "cpu_percent",
        ("cpu", "iowait"): "io_counters",
        ("mem", "percent"): "memory_percent",
        ("memswap", "percent"): "memory_percent",
        ("load", "min15"): "cpu_percent",
    }


class _FakeTopProcessEngine:
    """Duck-typed stand-in for `glances.processes.glances_processes`."""

    auto_sort = False

    def __init__(self, procs=None):
        self.procs = list(procs or [])
        self.get_list_calls = 0

    def get_list(self):
        self.get_list_calls += 1
        return list(self.procs)

    def set_sort_key(self, key, auto=False):  # pragma: no cover - auto_sort is False
        pass


class _FakeTopPlugin(_FakeScalarPlugin):
    """Scalar plugin whose `percent` field opts into top-process capture."""

    plugin_name = "faketop"
    fields_description = {
        "percent": {"description": "p", "unit": "percent", "top_processes_sort": "cpu_percent"},
        "total": {"description": "t", "unit": "bytes"},
    }


def _proc(name, cpu):
    return {"name": name, "cpu_percent": cpu, "memory_percent": 0.0}


def _procs(*names):
    """Processes in descending cpu_percent order, highest first."""
    return [_proc(name, 100.0 - index) for index, name in enumerate(names)]


@pytest.mark.asyncio
async def test_top_processes_favour_persistence_over_the_current_cycle(tmp_path, monkeypatch, store):
    """Spec §5.3 — the top 3 are the most FREQUENT names across the incident,
    not the current cycle's highest consumers."""
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeTopProcessEngine(_procs("p1", "p2", "p3", "p4", "p5", "p6", "p7"))
    alerts = GlancesAlerts(cfg, process_engine=engine)
    plugin = _FakeTopPlugin(store, cfg)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    # p7 becomes the cycle's #1, but p1/p2 have now been seen twice.
    engine.procs = _procs("p7", "p1", "p2", "p8", "p9", "p10")
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})

    opening = alerts.get_history()[0]
    assert opening["top"] == ["p1", "p2", "p3"]
    assert opening["top_sort"] == "cpu_percent"


@pytest.mark.asyncio
async def test_top_processes_survive_de_escalation(tmp_path, monkeypatch, store):
    """Spec §3 decision 2 — critical -> warning must NOT wipe the accumulator."""
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeTopProcessEngine(_procs("a", "b", "c", "d", "e", "f"))
    alerts = GlancesAlerts(cfg, process_engine=engine)
    plugin = _FakeTopPlugin(store, cfg)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    await _run_with_levels(plugin, alerts, {"percent": {"level": "critical", "prominent": True}})
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})

    state = alerts._state[("faketop", None, "percent")]
    assert sum(state.top_counter.values()) == 18  # 3 cycles x 6 sampled
    # The accumulator still points at the OPENING event, not the escalation.
    assert alerts.get_history()[0]["top"] == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_only_the_opening_event_carries_the_top(tmp_path, monkeypatch, store):
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeTopProcessEngine(_procs("a", "b", "c"))
    alerts = GlancesAlerts(cfg, process_engine=engine)
    plugin = _FakeTopPlugin(store, cfg)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    await _run_with_levels(plugin, alerts, {"percent": {"level": "critical", "prominent": True}})

    history = alerts.get_history()
    assert "top" in history[0]
    assert "top" not in history[1]


@pytest.mark.asyncio
async def test_closing_an_incident_freezes_the_top(tmp_path, monkeypatch, store):
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeTopProcessEngine(_procs("a", "b", "c"))
    alerts = GlancesAlerts(cfg, process_engine=engine)
    plugin = _FakeTopPlugin(store, cfg)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    frozen = list(alerts.get_history()[0]["top"])
    await _run_with_levels(plugin, alerts, {"percent": {"level": "ok", "prominent": True}})
    engine.procs = _procs("z1", "z2", "z3")
    await _run_with_levels(plugin, alerts, {"percent": {"level": "ok", "prominent": True}})

    state = alerts._state[("faketop", None, "percent")]
    assert state.top_counter is None
    assert state.top_event is None
    assert alerts.get_history()[0]["top"] == frozen


@pytest.mark.asyncio
async def test_field_without_sort_key_never_gets_a_top(tmp_path, monkeypatch, store):
    """Spec §4 — an fs/sensors-style alert must not carry a meaningless top."""
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeTopProcessEngine(_procs("a", "b", "c"))
    alerts = GlancesAlerts(cfg, process_engine=engine)
    plugin = _FakeScalarPlugin(store, cfg)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})

    opening = alerts.get_history()[0]
    assert "top" not in opening
    assert "top_sort" not in opening


@pytest.mark.asyncio
async def test_empty_process_list_writes_no_top_key(tmp_path, monkeypatch, store):
    """Process plugins disabled -> the key is ABSENT, not an empty list."""
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    alerts = GlancesAlerts(cfg, process_engine=_FakeTopProcessEngine([]))
    plugin = _FakeTopPlugin(store, cfg)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})

    assert "top" not in alerts.get_history()[0]


@pytest.mark.asyncio
async def test_no_process_engine_is_a_no_op(tmp_path, monkeypatch, store):
    """Default construction (tests, headless rigs) must not raise."""
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    alerts = GlancesAlerts(cfg)
    plugin = _FakeTopPlugin(store, cfg)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})

    assert "top" not in alerts.get_history()[0]


@pytest.mark.asyncio
async def test_get_ongoing_top_reports_active_incidents_only(tmp_path, monkeypatch, store):
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeTopProcessEngine(_procs("a", "b", "c"))
    alerts = GlancesAlerts(cfg, process_engine=engine)
    plugin = _FakeTopPlugin(store, cfg)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    assert alerts.get_ongoing_top() == {
        ("faketop", None, "percent"): {"top": ["a", "b", "c"], "top_sort": "cpu_percent"}
    }

    await _run_with_levels(plugin, alerts, {"percent": {"level": "ok", "prominent": True}})
    assert alerts.get_ongoing_top() == {}


@pytest.mark.asyncio
async def test_get_ongoing_top_is_read_only_and_returns_a_fresh_dict(tmp_path, monkeypatch, store):
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeTopProcessEngine(_procs("a", "b", "c"))
    alerts = GlancesAlerts(cfg, process_engine=engine)
    plugin = _FakeTopPlugin(store, cfg)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})

    first = alerts.get_ongoing_top()
    first.clear()
    assert alerts.get_ongoing_top()  # mutating the copy left the engine alone


@pytest.mark.asyncio
async def test_get_ongoing_top_skips_incidents_with_nothing_accumulated(tmp_path, monkeypatch, store):
    """An annotated field with an empty process list must not appear."""
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    alerts = GlancesAlerts(cfg, process_engine=_FakeTopProcessEngine([]))
    plugin = _FakeTopPlugin(store, cfg)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})

    assert alerts.get_ongoing_top() == {}


@pytest.mark.asyncio
async def test_get_ongoing_top_reads_the_event_not_the_live_counter(tmp_path, monkeypatch, store):
    """Regression test for the cross-thread race.

    The TUI calls `get_ongoing_top()` from its own `threading.Thread` while
    the asyncio loop may concurrently be mutating `top_counter` inside
    `_accumulate_top`. `Counter.most_common()` iterates the live dict and
    is not safe to call from a second thread while it changes size, so
    `get_ongoing_top()` must read the list `_accumulate_top` already wrote
    to `top_event["top"]` instead. Prove it directly: replace
    `top_counter` with a sentinel that raises on any access, and show
    `get_ongoing_top()` neither touches it nor raises, and returns exactly
    the opening event's frozen `top` list.
    """
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeTopProcessEngine(_procs("a", "b", "c"))
    alerts = GlancesAlerts(cfg, process_engine=engine)
    plugin = _FakeTopPlugin(store, cfg)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})

    state_key = ("faketop", None, "percent")
    state = alerts._state[state_key]
    opening_event = alerts.get_history()[0]

    class _BoomCounter:
        """Raises the moment anything reads it — proves it is never touched."""

        def most_common(self, n):
            raise AssertionError("get_ongoing_top() must not call most_common() on the live Counter")

        def __iter__(self):
            raise AssertionError("get_ongoing_top() must not iterate the live Counter")

    state.top_counter = _BoomCounter()

    result = alerts.get_ongoing_top()

    assert result == {state_key: {"top": opening_event["top"], "top_sort": "cpu_percent"}}
    assert result[state_key]["top"] is opening_event["top"]


class _FakeMultiTopPlugin(_FakeScalarPlugin):
    """Scalar plugin with two fields sharing the same `top_processes_sort` key.

    Used to exercise the per-ingest-call memoisation: both fields alerting
    in the same cycle must sample the process list exactly once, not once
    per field.
    """

    plugin_name = "fakemultitop"
    fields_description = {
        "percent": {"description": "p", "unit": "percent", "top_processes_sort": "cpu_percent"},
        "peak": {"description": "pk", "unit": "percent", "top_processes_sort": "cpu_percent"},
    }


@pytest.mark.asyncio
async def test_top_processes_sort_is_memoised_per_ingest_call(tmp_path, monkeypatch, store):
    """Spec §9 invariant 1 — at most one `get_list()` (hence one `sort_stats()`)
    per distinct sort key per `ingest_plugin()` call, even with two annotated
    fields both alerting on the same sort key in the same cycle."""
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeTopProcessEngine(_procs("a", "b", "c"))
    alerts = GlancesAlerts(cfg, process_engine=engine)
    plugin = _FakeMultiTopPlugin(store, cfg)

    await _run_with_levels(
        plugin,
        alerts,
        {
            "percent": {"level": "warning", "prominent": True},
            "peak": {"level": "warning", "prominent": True},
        },
    )

    assert engine.get_list_calls == 1


@pytest.mark.asyncio
async def test_top_processes_no_active_alert_costs_zero_get_list_calls(tmp_path, monkeypatch, store):
    """Spec §9 invariant 2 — the quiet path (no active alert on an annotated
    field) must not touch the process engine at all."""
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeTopProcessEngine(_procs("a", "b", "c"))
    alerts = GlancesAlerts(cfg, process_engine=engine)
    plugin = _FakeTopPlugin(store, cfg)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "ok", "prominent": True}})

    assert engine.get_list_calls == 0


@pytest.mark.asyncio
async def test_reopening_an_incident_starts_a_fresh_top(tmp_path, monkeypatch, store):
    """Spec §5.2 — the same (plugin, key, field) tuple can alert again after
    resolving. The new incident must rebind `top_event` to its OWN opening
    event and start a fresh Counter: the old event's top stays frozen, and
    the new one carries only the new processes."""
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeTopProcessEngine(_procs("a", "b", "c"))
    alerts = GlancesAlerts(cfg, process_engine=engine)
    plugin = _FakeTopPlugin(store, cfg)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    first_opening = alerts.get_history()[0]
    assert first_opening["top"] == ["a", "b", "c"]

    await _run_with_levels(plugin, alerts, {"percent": {"level": "ok", "prominent": True}})

    engine.procs = _procs("x", "y", "z")
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    second_opening = alerts.get_history()[-1]

    assert second_opening is not first_opening
    assert second_opening["top"] == ["x", "y", "z"]
    # The first incident's opening event is untouched by the new incident.
    assert first_opening["top"] == ["a", "b", "c"]


class _FakeTopProcessEngineByReference:
    """Like `_FakeTopProcessEngine`, but `get_list()` returns the internal
    list BY REFERENCE — as the real `GlancesProcesses.get_list()` does.

    `_FakeTopProcessEngine.get_list()` already returns `list(self.procs)`
    (a copy), which hides a missing `list(...)` copy in `_sample_processes`:
    with that double, every existing test above passes whether or not
    `_sample_processes` copies before calling `sort_stats`. This double
    exists solely to pin that copy — see
    `test_sample_processes_copies_before_sort_stats_in_place_fallback`.
    """

    auto_sort = False

    def __init__(self, procs):
        self.procs = procs

    def get_list(self):
        return self.procs

    def set_sort_key(self, key, auto=False):  # pragma: no cover - auto_sort is False
        pass


@pytest.mark.asyncio
async def test_sample_processes_copies_before_sort_stats_in_place_fallback(tmp_path, monkeypatch, store):
    """Pin the `list(...)` defensive copy in `_sample_processes`.

    `sort_stats`'s standard-sort branch falls back to an IN-PLACE
    `list.sort()` (by name) when the primary comparison raises `TypeError`
    — here, an incomparable `cpu_percent` across two processes (a `str` vs
    a `float`). `GlancesProcesses.get_list()` returns its internal
    `processlist` BY REFERENCE, so without `_sample_processes`'s
    `list(procs)` copy, that in-place fallback sort would reorder the
    engine's own live process list as a side effect of alert ingestion.

    `_FakeTopProcessEngine` (used by every other test in this file) already
    returns a copy from `get_list()`, which would hide a missing `list(...)`
    in `_sample_processes` — hence `_FakeTopProcessEngineByReference` here.
    """
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    procs = [
        {"name": "b_proc", "cpu_percent": "not-a-number", "memory_percent": 0.0},
        {"name": "a_proc", "cpu_percent": 42.0, "memory_percent": 0.0},
    ]
    original_order = [p["name"] for p in procs]
    engine = _FakeTopProcessEngineByReference(procs)
    alerts = GlancesAlerts(cfg, process_engine=engine)
    plugin = _FakeTopPlugin(store, cfg)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})

    # The engine's OWN list must be untouched by ingestion — proves
    # `_sample_processes` handed `sort_stats` a copy, not its live list.
    assert [p["name"] for p in engine.procs] == original_order


@pytest.mark.asyncio
async def test_top_counter_is_bounded_under_sustained_churn(tmp_path, monkeypatch, store):
    """`top_counter` accumulates for the whole incident and is never reset
    (spec §3 decision 2), so a field with high per-cycle name churn (e.g. a
    kernel worker whose name includes a counter, like `kworker/u16:3`) would
    otherwise grow the dict by one key per cycle forever. Drive an incident
    through 30 cycles of TOTAL churn — 6 brand-new names every cycle, never
    repeated, 180 distinct names overall — comfortably past
    `_TOP_COUNTER_MAX_KEYS` (128), and assert the dict is genuinely bounded."""
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeTopProcessEngine(_procs("seed0", "seed1", "seed2", "seed3", "seed4", "seed5"))
    alerts = GlancesAlerts(cfg, process_engine=engine)
    plugin = _FakeTopPlugin(store, cfg)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    for cycle in range(30):
        engine.procs = _procs(*(f"churn{cycle}-{i}" for i in range(6)))
        await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})

    state = alerts._state[("faketop", None, "percent")]
    assert isinstance(state.top_counter, Counter)
    assert len(state.top_counter) <= _TOP_COUNTER_MAX_KEYS


@pytest.mark.asyncio
async def test_persistent_process_survives_trimming_and_stays_first(tmp_path, monkeypatch, store):
    """The fix must not break the feature it protects: a process sampled in
    EVERY cycle is by construction always the most frequent name, so trimming
    to the most-common keys can never evict it, however much one-shot churn
    surrounds it.

    This is the discriminating case: `persistent` is also the FIRST key ever
    inserted into the Counter (cycle 0's sample puts it first). A naive trim
    that drops by INSERTION ORDER instead of by frequency (e.g. an
    OrderedDict-style "keep the last N inserted, drop the oldest") would
    evict `persistent` at the very first trim, since it is the oldest key —
    the opposite of what "most persistent" is supposed to mean. Only a
    frequency-based trim (`Counter.most_common`) keeps it.
    """
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeTopProcessEngine(_procs("persistent", "c0-0", "c0-1", "c0-2", "c0-3", "c0-4"))
    alerts = GlancesAlerts(cfg, process_engine=engine)
    plugin = _FakeTopPlugin(store, cfg)

    total_cycles = 40
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    for cycle in range(1, total_cycles):
        churn = (f"c{cycle}-{i}" for i in range(5))
        # "persistent" sorts first every cycle (highest cpu_percent) so it is
        # always among the `_TOP_PROCESSES_SAMPLE` names sampled.
        engine.procs = _procs("persistent", *churn)
        await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})

    state = alerts._state[("faketop", None, "percent")]
    # 40 cycles x 5 new churn names/cycle = 200 distinct churn names, well
    # past the cap — trimming must have happened at least once.
    assert len(state.top_counter) <= _TOP_COUNTER_MAX_KEYS
    assert state.top_counter["persistent"] == total_cycles
    assert alerts.get_history()[0]["top"][0] == "persistent"
