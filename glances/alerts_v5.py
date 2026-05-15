#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 alert state machine.

Reads `_levels` from each plugin (via `plugin.get_stats()`), tracks
level transitions with hysteresis, fires configured actions, and
maintains an in-memory alert history exposed via the REST API
(Phase 1.6).

Architecture references:
- §3.3   `_levels` payload (the input to this module)
- §3.4   GlancesAlerts (this module) + action system

Lifecycle:

```
alerts = GlancesAlerts(config, actions=registry)
# scheduler calls this once per plugin update cycle:
await alerts.ingest_plugin(plugin)
# REST handler reads:
alerts.get_history()
```

The scheduler integration is optional — the scheduler accepts an
``alerts`` argument and only ingests when it is non-None. Phase 1.4 is
otherwise self-contained: no plugin code changes are required.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import time
from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from glances.actions_v5.action_base import GlancesActionBase
from glances.config_v5 import GlancesConfigV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)

# Defaults — chosen to match v4 behaviour (5 s of persistence before firing
# a transition, 200-event ring buffer, 3-cycle warmup at startup).
_DEFAULT_MIN_DURATION_SECONDS = 5.0
_DEFAULT_HISTORY_SIZE = 200
# Skip alert ingestion for the first N refresh cycles per plugin. Mirrors
# v4: rates are not yet computed on cycle 0, thresholds can fire spuriously
# on cycle 1-2 while the system warms up. The cell colouring in the TUI is
# unaffected (it reads `_levels` directly from the payload).
_DEFAULT_WARMUP_CYCLES = 3


@dataclass
class _AlertState:
    """Per-(plugin, key, field) hysteresis state."""

    committed_level: str = "ok"
    pending_level: str | None = None
    pending_since: float | None = None
    # ``False`` until the very first observation has been processed for this
    # (plugin, key, field). The transition produced by that first observation
    # — if any — carries ``is_initial=True`` so the renderer can show a
    # steady-state level instead of a misleading "ok → <level>" arrow when
    # Glances starts while the system is already in a non-ok state.
    has_committed: bool = False


@dataclass
class _Transition:
    previous: str
    new: str
    # See ``_AlertState.has_committed`` — set on the FIRST commit out of the
    # default ``committed_level="ok"`` initial state. Subsequent transitions
    # are real changes and stay ``is_initial=False``.
    is_initial: bool = False


class GlancesAlerts:
    """Stateful alert engine — ingests `_levels`, fires actions, keeps history."""

    def __init__(
        self,
        config: GlancesConfigV5,
        actions: dict[str, GlancesActionBase] | None = None,
        hostname: str | None = None,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config
        self.actions = actions or {}
        self._hostname = hostname or socket.gethostname()
        self._now = now

        self._global_min_duration = float(config.get("alerts", "min_duration_seconds", _DEFAULT_MIN_DURATION_SECONDS))
        self._history_size = int(config.get("alerts", "history_size", _DEFAULT_HISTORY_SIZE))
        self._warmup_cycles = max(0, int(config.get("alerts", "warmup_cycles", _DEFAULT_WARMUP_CYCLES)))
        self._history: deque[dict[str, Any]] = deque(maxlen=self._history_size)

        # Per-plugin ingestion counter. Ingestion is skipped while
        # `_plugin_cycles[name] < warmup_cycles` — see `_DEFAULT_WARMUP_CYCLES`.
        self._plugin_cycles: dict[str, int] = {}

        # State per (plugin_name, key, field) — key is None for scalars,
        # the primary-key value (stringified) for collections.
        self._state: dict[tuple[str, str | None, str], _AlertState] = {}

        # Strong references to in-flight action tasks. Required: asyncio docs
        # warn that tasks scheduled via create_task() may be garbage-collected
        # before completion if no strong reference is held.
        self._action_tasks: set[asyncio.Task[None]] = set()

    # ---------------------------------------------------------------- public

    def get_history(self) -> list[dict[str, Any]]:
        """Return the alert history as a list (most-recent-last)."""
        return list(self._history)

    def is_initializing(self) -> bool:
        """Return ``True`` while at least one ingested plugin is still in
        its warmup window — alerts physically cannot have fired yet, so
        the UI shows "(initializing)" instead of the misleading
        "(no events)".

        Also ``True`` when no plugin has been ingested at all (e.g. the
        scheduler has not yet completed its first tick).
        """
        if not self._plugin_cycles:
            return True
        return any(seen <= self._warmup_cycles for seen in self._plugin_cycles.values())

    async def drain(self) -> None:
        """Wait for every in-flight action task to complete.

        Used by tests; in production the scheduler does not wait, so
        actions run fire-and-forget (the monitoring loop must never
        block on a slow shell command — see architecture §3.4).
        """
        if not self._action_tasks:
            return
        await asyncio.gather(*list(self._action_tasks), return_exceptions=True)

    async def ingest_plugin(self, plugin: GlancesPluginBase) -> None:
        """Reconcile one plugin's transitions and dispatch actions.

        Skips entirely during the warmup window (the first
        ``warmup_cycles`` calls per plugin — default 3). Rates and
        threshold-derived `_levels` may not be stable before then; v4
        ignores logs during the same window.
        """
        # Warmup: increment the per-plugin counter and bail out early until
        # the warmup window has elapsed. The TUI still colours cells from
        # `_levels` — only the alert ingestion (history + actions) waits.
        seen = self._plugin_cycles.get(plugin.plugin_name, 0) + 1
        self._plugin_cycles[plugin.plugin_name] = seen
        if seen <= self._warmup_cycles:
            return

        payload = plugin.get_stats()
        if not isinstance(payload, dict):
            return
        levels = payload.get("_levels", {})
        if not isinstance(levels, dict):
            return

        for key, field_name, observed_level, value, prominent in self._observations(plugin, payload, levels):
            state_key = (plugin.plugin_name, key, field_name)
            state = self._state.setdefault(state_key, _AlertState())
            # Per-(field, level) lookup — the most-specific key depends on
            # the *observed* level, e.g. `ctx_switches_critical_min_duration_seconds=300`
            # slows entry into critical without affecting warning/careful ramps.
            min_duration = self._min_duration_for(plugin.plugin_name, key, field_name, observed_level)
            transition = self._reconcile(state, observed_level, min_duration)

            if transition is not None:
                event = self._build_event(
                    plugin.plugin_name,
                    key,
                    field_name,
                    previous_level=transition.previous,
                    new_level=transition.new,
                    value=value,
                    prominent=prominent,
                    is_initial=transition.is_initial,
                )
                self._history.append(event)
                if transition.new != "ok":
                    # Entry into a non-ok level: fire non-repeat actions.
                    self._fire_actions(plugin, key, field_name, transition.new, value, repeat=False)

            # Steady-state repeat dispatch — fires on every ingest cycle
            # while the committed level is non-ok, including the cycle of
            # the entry transition (v4-aligned behaviour).
            if state.committed_level != "ok":
                self._fire_actions(plugin, key, field_name, state.committed_level, value, repeat=True)

    # ----------------------------------------------------- min duration override

    def _min_duration_for(
        self,
        plugin_name: str,
        key: str | None,
        field_name: str,
        observed_level: str,
    ) -> float:
        """Resolve ``min_duration_seconds`` for a given transition observation.

        Precedence (most specific wins, first non-negative float):

        Scalar plugins (``key is None``):
            1. ``<field>_<level>_min_duration_seconds``
            2. ``<field>_min_duration_seconds``
            3. ``min_duration_seconds``                  (plugin section)
            4. ``[alerts] min_duration_seconds``         (global default)

        Collection plugins (``key`` = primary-key value, e.g. ``wlan0``):
            1. ``<pk>_<field>_<level>_min_duration_seconds``
            2. ``<pk>_<field>_min_duration_seconds``
            3. ``<field>_<level>_min_duration_seconds``
            4. ``<field>_min_duration_seconds``
            5. ``min_duration_seconds``                  (plugin section)
            6. ``[alerts] min_duration_seconds``         (global default)

        Symmetric with the 3-level precedence used for thresholds
        (``read_thresholds``) and action keys (``_lookup_action_value``).

        Same ``min_duration`` is applied to every transition direction
        (any → ok, any → non-ok). Possible improvement: introduce a
        separate ``_recovery_min_duration_seconds`` family of keys to
        split entry vs recovery — e.g. fast entry into critical but
        slow drop back to ok. Not implemented today to keep the config
        surface small; see architecture §3.4.
        """
        candidates: list[str] = []
        if key is not None:
            candidates.append(f"{key}_{field_name}_{observed_level}_min_duration_seconds")
            candidates.append(f"{key}_{field_name}_min_duration_seconds")
        candidates.append(f"{field_name}_{observed_level}_min_duration_seconds")
        candidates.append(f"{field_name}_min_duration_seconds")
        candidates.append("min_duration_seconds")

        for cand in candidates:
            raw = self.config.get(plugin_name, cand, -1.0)
            try:
                fv = float(raw)
            except (TypeError, ValueError):
                continue
            if fv >= 0:
                return fv
        return self._global_min_duration

    # --------------------------------------------------------- observation walk

    def _observations(
        self,
        plugin: GlancesPluginBase,
        payload: dict[str, Any],
        levels: dict[str, Any],
    ) -> Iterable[tuple[str | None, str, str, Any, bool]]:
        """Yield `(key, field, level, value, prominent)` for every level entry."""
        if not plugin.IS_COLLECTION:
            for field_name, entry in levels.items():
                level = entry.get("level") if isinstance(entry, dict) else None
                if not isinstance(level, str):
                    continue
                prominent = bool(entry.get("prominent", True))
                yield (None, field_name, level, payload.get(field_name), prominent)
            return

        # Collection — levels is keyed by pk_value.
        pk = plugin._primary_key
        items_by_pk: dict[Any, dict[str, Any]] = {}
        if pk:
            for item in payload.get("data", []):
                if isinstance(item, dict):
                    pk_value = item.get(pk)
                    if pk_value is not None:
                        items_by_pk[pk_value] = item

        for pk_value, fields_entry in levels.items():
            if not isinstance(fields_entry, dict):
                continue
            item = items_by_pk.get(pk_value, {})
            for field_name, entry in fields_entry.items():
                level = entry.get("level") if isinstance(entry, dict) else None
                if not isinstance(level, str):
                    continue
                prominent = bool(entry.get("prominent", True))
                yield (str(pk_value), field_name, level, item.get(field_name), prominent)

    # ------------------------------------------------------------ hysteresis

    def _reconcile(self, state: _AlertState, observed: str, min_duration: float) -> _Transition | None:
        """Update state and return a `_Transition` iff one fires this cycle."""
        if observed == state.committed_level:
            # Observation matches the committed level — cancel any pending
            # transition AND record that we have now seen at least one
            # observation. Later transitions out of this state will be real
            # changes (``is_initial=False``).
            state.pending_level = None
            state.pending_since = None
            state.has_committed = True
            return None

        # No hysteresis configured — commit immediately. Useful for tests
        # and for users who explicitly disable debouncing.
        if min_duration <= 0:
            previous = state.committed_level
            is_initial = not state.has_committed
            state.committed_level = observed
            state.pending_level = None
            state.pending_since = None
            state.has_committed = True
            return _Transition(previous=previous, new=observed, is_initial=is_initial)

        now = self._now()
        if state.pending_level == observed:
            # Still pending the same candidate — check the elapsed window.
            assert state.pending_since is not None
            if now - state.pending_since >= min_duration:
                previous = state.committed_level
                is_initial = not state.has_committed
                state.committed_level = observed
                state.pending_level = None
                state.pending_since = None
                state.has_committed = True
                return _Transition(previous=previous, new=observed, is_initial=is_initial)
            return None

        # Either no pending candidate, or the candidate just changed — start
        # a fresh debounce window from this cycle.
        state.pending_level = observed
        state.pending_since = now
        return None

    # ------------------------------------------------------------ event build

    def _build_event(
        self,
        plugin_name: str,
        key: str | None,
        field_name: str,
        *,
        previous_level: str,
        new_level: str,
        value: Any,
        prominent: bool,
        is_initial: bool = False,
    ) -> dict[str, Any]:
        return {
            "ts": datetime.now(timezone.utc).isoformat(),
            "plugin": plugin_name,
            "key": key,
            "field": field_name,
            "level": new_level,
            "previous_level": previous_level,
            "value": value,
            "prominent": prominent,
            "is_initial": is_initial,
            "hostname": self._hostname,
        }

    # ----------------------------------------------------------- action fire

    def _fire_actions(
        self,
        plugin: GlancesPluginBase,
        key: str | None,
        field_name: str,
        level: str,
        value: Any,  # noqa: ARG002 — currently unused, kept for future per-action context use
        repeat: bool,
    ) -> None:
        """Lookup config keys, build context, schedule action.execute() coroutines."""
        if not self.actions:
            return
        context = self._build_context(plugin, key, level)
        for action_name, action in self.actions.items():
            action_value = self._lookup_action_value(plugin.plugin_name, key, field_name, level, action_name, repeat)
            if not action_value:
                continue
            self._schedule_action(action, plugin.plugin_name, level, context, action_value, repeat)

    def _build_context(self, plugin: GlancesPluginBase, key: str | None, level: str) -> dict[str, Any]:
        """Mustache rendering context: `plugin.get_export()` + built-in variables."""
        export = plugin.get_export()
        if plugin.IS_COLLECTION and key is not None:
            pk = plugin._primary_key
            base: dict[str, Any] = {}
            if pk:
                for item in export if isinstance(export, list) else []:
                    if isinstance(item, dict) and str(item.get(pk)) == key:
                        base = dict(item)
                        break
        else:
            base = dict(export) if isinstance(export, dict) else {}
        return {
            **base,
            "_glances_hostname": self._hostname,
            "_glances_plugin": plugin.plugin_name,
            "_glances_level": level,
            "_glances_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _lookup_action_value(
        self,
        plugin_name: str,
        key: str | None,
        field_name: str,
        level: str,
        action_name: str,
        repeat: bool,
    ) -> str:
        """Resolve the action template value against the 3-level precedence.

        For ``repeat=True`` the suffix is ``_<level>_<action_name>_repeat``,
        otherwise ``_<level>_<action_name>``. The first non-empty key wins:

        1. ``<key>_<field>_<level>_<action_name>[_repeat]`` (collection items)
        2. ``<field>_<level>_<action_name>[_repeat]``
        3. ``<level>_<action_name>[_repeat]``
        """
        suffix = f"{level}_{action_name}_repeat" if repeat else f"{level}_{action_name}"
        candidates: list[str] = []
        if key is not None:
            candidates.append(f"{key}_{field_name}_{suffix}")
        candidates.append(f"{field_name}_{suffix}")
        candidates.append(suffix)
        for cand in candidates:
            raw = self.config.get(plugin_name, cand, "")
            if isinstance(raw, str) and raw:
                return raw
        return ""

    def _schedule_action(
        self,
        action: GlancesActionBase,
        plugin_name: str,
        level: str,
        context: dict[str, Any],
        action_value: str,
        repeat: bool,
    ) -> None:
        """Fire-and-forget: never blocks the monitoring loop (§3.4).

        Errors are logged with full context in `_execute_action`.
        """
        task = asyncio.create_task(self._execute_action(action, plugin_name, level, context, action_value, repeat))
        self._action_tasks.add(task)
        task.add_done_callback(self._action_tasks.discard)

    async def _execute_action(
        self,
        action: GlancesActionBase,
        plugin_name: str,
        level: str,
        context: dict[str, Any],
        action_value: str,
        repeat: bool,
    ) -> None:
        try:
            await action.execute(plugin_name, level, context, action_value, repeat=repeat)
        except Exception as e:
            logger.warning(
                "Action %r failed for plugin=%s level=%s repeat=%s: %s",
                action.action_name,
                plugin_name,
                level,
                repeat,
                e,
            )
