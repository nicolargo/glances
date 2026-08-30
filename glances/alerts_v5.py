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
from collections import Counter, deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from glances.actions_v5.action_base import GlancesActionBase
from glances.config_v5 import GlancesConfigV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.processes import sort_stats

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

# Only these levels raise an alert (history event + action dispatch). A
# ``careful`` (or any other sub-warning) level still colours the TUI cell
# from ``_levels`` but is treated as ``ok`` by the alert state machine, so
# it never enters the alert history or the footer list. Mirrors v4, whose
# logs record WARNING/CRITICAL only.
_ALERTABLE_LEVELS = frozenset({"warning", "critical"})

# Top-process capture depth: sample the N highest processes each cycle, keep
# the M most frequently sampled names. v4 values, deliberately hard-coded —
# see spec §5.3, no config key.
_TOP_PROCESSES_SAMPLE = 6
_TOP_PROCESSES_KEEP = 3

# `top_counter` accumulates for the incident's whole lifetime (spec §3
# decision 2 - never reset, not even on critical -> warning), so a
# long-running incident with a churning process name (e.g. `kworker/u16:3`
# spawned fresh each cycle) grows the dict by one key per cycle forever.
# Cap the number of DISTINCT KEYS, not a sliding window over time: 6 names
# are sampled per cycle (`_TOP_PROCESSES_SAMPLE`), so reaching 128 distinct
# names takes 20+ cycles of *complete* churn (zero name overlap between
# cycles). A genuinely persistent process is by construction always among
# the most-common entries, so trimming down to the 32 most common - more
# than 10x the 3 that are ever read via `most_common(_TOP_PROCESSES_KEEP)`
# - discards only long-tail one-shot names and cannot disturb the reported
# top 3.
_TOP_COUNTER_MAX_KEYS = 128
_TOP_COUNTER_TRIM_TO = 32


def _alert_level(level: str) -> str:
    """Collapse any non-alertable level (e.g. ``careful``) to ``ok``."""
    return level if level in _ALERTABLE_LEVELS else "ok"


@dataclass
class _AlertState:
    """Per-(plugin, key, field) hysteresis state."""

    committed_level: str = "ok"
    pending_level: str | None = None
    pending_since: float | None = None
    # ISO-8601 UTC instant of the transition that took this tuple OUT of
    # ``ok``; ``None`` while it is ``ok``. Not moved by an escalation — a
    # ``warning -> critical`` is the same incident. ``_history`` is a bounded
    # ring buffer, so the opening event of a long-running alert is eventually
    # evicted by later, unrelated transitions; this field is then the only
    # surviving record of when that alert actually started.
    committed_since: str | None = None
    # ``False`` until the very first observation has been processed for this
    # (plugin, key, field). The transition produced by that first observation
    # — if any — carries ``is_initial=True`` so the renderer can show a
    # steady-state level instead of a misleading "ok → <level>" arrow when
    # Glances starts while the system is already in a non-ok state.
    has_committed: bool = False
    # Top-process accumulation, live only while the incident is open.
    # `top_event` is a REFERENCE to the dict this incident's opening event
    # put in `_history`; rewriting it in place is how v4's GlancesEvent
    # behaves, and it is what keeps `GET /api/5/alert` current on an
    # incident that is still running. All three are None while `ok`.
    top_counter: Counter[str] | None = None
    top_sort: str | None = None
    top_event: dict[str, Any] | None = None


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
        process_engine: Any | None = None,
    ) -> None:
        self.config = config
        self.actions = actions or {}
        self._hostname = hostname or socket.gethostname()
        self._now = now
        # Optional process engine (``glances.processes.glances_processes``)
        # for dynamic auto-sort (v4 ``events_list.set_process_sort`` parity).
        # Duck-typed: needs ``.auto_sort`` (bool) and ``.set_sort_key``. When
        # ``None`` (default — tests, headless rigs without the process
        # plugins) auto-sort is a no-op and no global state is touched.
        self._process_engine = process_engine

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

    def get_ongoing(self) -> dict[tuple[str, str | None, str], str]:
        """Return the currently non-``ok`` committed levels, keyed by tuple.

        A read-only view over ``_state``. Unlike ``get_history()`` — a bounded
        ring buffer — ``_state`` keeps one entry per watched
        ``(plugin, key, field)`` for the lifetime of the process, so an alert
        that has been active long enough for its transitions to age out of the
        history is still reported here.

        The TUI uses this as the authority on what is active; the history only
        supplies the chronology (when an incident opened, which levels it went
        through). Returns a fresh dict — callers may mutate it freely.

        Never called from the ingest path, and it writes nothing: the alert
        engine's observable behaviour is unchanged by its existence.
        """
        return {
            state_key: state.committed_level
            for state_key, state in self._state.items()
            if state.committed_level != "ok"
        }

    def get_ongoing_since(self) -> dict[tuple[str, str | None, str], str]:
        """Return when each currently non-``ok`` tuple entered its alert state.

        Companion to :meth:`get_ongoing`, keyed identically and read from the
        same unbounded ``_state``. Values are ISO-8601 UTC strings, the exact
        ``ts`` of the opening event.

        Exists because ``get_history()`` is a bounded ring buffer: an alert
        that stays active long enough sees its own opening event evicted by
        later transitions, after which the history can no longer say when it
        began. The TUI would then render its start as ``--:--:--``.

        Read-only, allocates a fresh dict, never called from the ingest path.
        """
        return {
            state_key: state.committed_since
            for state_key, state in self._state.items()
            if state.committed_level != "ok" and state.committed_since is not None
        }

    def get_ongoing_top(self) -> dict[tuple[str, str | None, str], dict[str, Any]]:
        """Return the accumulated top processes of each active incident.

        Companion to :meth:`get_ongoing_since`, keyed identically and read
        from the same unbounded ``_state``. Values are
        ``{"top": [names], "top_sort": <sort key>}``.

        Reads ``top_event["top"]`` — the list `_accumulate_top` already
        computed and wrote this cycle — rather than recomputing
        ``top_counter.most_common(...)``. This is deliberate, not an
        optimisation to undo: the TUI runs as its own OS
        ``threading.Thread`` (see ``glances_curses_v5.py``) and calls this
        method from its repaint path while the asyncio loop may
        concurrently be running ``_accumulate_top``, which mutates
        ``top_counter`` in place. ``Counter.most_common()`` delegates to
        ``heapq.nlargest``, pure Python and therefore preemptible by the
        GIL mid-iteration; a process name never seen before changes the
        dict's SIZE while the other thread iterates it, raising
        ``RuntimeError: dictionary changed size during iteration`` — and
        the TUI's repaint loop has no per-iteration guard, so that
        exception kills the TUI thread for the rest of the process's
        life. ``top_event["top"]`` is instead a single atomic dict lookup:
        each cycle assigns a brand-new list object (never mutated in
        place), so there is nothing for a second thread to race with.

        For the same reason, ``state.top_event`` is read into a local ONCE
        and re-tested from that local — never re-read from ``state`` — so a
        concurrent ``_release_top`` (the incident resolving between the
        guard and the ``.get("top")`` call) cannot flip it to ``None``
        in between and raise ``AttributeError``.

        Exists for the same reason as ``get_ongoing_since``: ``get_history()``
        is a bounded ring buffer, so a long-running incident eventually loses
        the opening event that carries its ``top``. Tuples with nothing
        accumulated (no process engine, process plugins disabled, field not
        annotated, or the opening event's sample was empty this cycle) are
        omitted rather than reported with an empty list.

        Read-only, never called from the ingest path. Allocates a fresh
        result dict, but the ``top`` list inside each value is the SAME
        list object stored on the history event (not a copy) — the current
        consumer (``_derive_incidents``) copies it before use, so this is
        safe today, but a future caller must not mutate it in place.
        """
        result: dict[tuple[str, str | None, str], dict[str, Any]] = {}
        for state_key, state in self._state.items():
            event = state.top_event
            if state.committed_level == "ok" or event is None or state.top_sort is None:
                continue
            names = event.get("top")
            if not names:
                continue
            result[state_key] = {"top": names, "top_sort": state.top_sort}
        return result

    def is_initializing(self) -> bool:
        """Return ``True`` only while the alert engine *cannot have produced any
        event yet* — i.e. no plugin has finished its warmup window. Concretely,
        ``True`` iff either:

        - **No ingestion has happened.** Scheduler has not yet completed
          a first tick (``_plugin_cycles`` empty).
        - **Every ingested plugin is still inside its warmup window.**
          Warmup skips ingestion entirely for the first N cycles per plugin
          (default 3) — alerts cannot fire during that window.

        The test is "no plugin past warmup", NOT "some plugin still warming".
        Each plugin runs its own refresh loop, so requiring *every* plugin to
        clear warmup let a single slow-refresh plugin (polling every few
        minutes) hold the flag ``True`` for minutes — and a plugin that only
        ever ingests once would latch it ``True`` forever. As soon as one
        plugin is past warmup the engine is live: an empty history then means
        "no alert detected".

        We also deliberately do NOT treat a still-pending (hysteresis)
        transition as "initializing": a field that flaps across a threshold
        keeps resetting its debounce window and never commits, which would
        latch the flag ``True`` forever too. A pending-but-uncommitted
        transition is genuinely "no alert yet"; if it commits, the event
        appears within ``min_duration`` seconds.
        """
        if not self._plugin_cycles:
            return True
        return not any(seen > self._warmup_cycles for seen in self._plugin_cycles.values())

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
        # Plugin-level opt-out: when ``EMITS_ALERTS=False`` the plugin still
        # produces ``_levels`` for the renderer's colouring, but the alerts
        # pipeline ignores it (no history, no action dispatch). Used by
        # plugins whose watched-field semantic is decorative — see
        # ``GlancesPluginBase.EMITS_ALERTS``.
        if not getattr(plugin, "EMITS_ALERTS", True):
            return

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

        # Sorted process lists for this cycle, keyed by sort key. Built
        # lazily: no active alert on an annotated field means no sort at all.
        top_cache: dict[str, list[dict[str, Any]]] = {}

        for key, field_name, observed_level, value, prominent in self._observations(plugin, payload, levels):
            state_key = (plugin.plugin_name, key, field_name)
            state = self._state.setdefault(state_key, _AlertState())
            # Hot-path short-circuit: when the observation matches the
            # currently committed level AND no candidate transition is
            # pending, no min_duration is needed and ``_reconcile`` would
            # take its fast-path no-op anyway. Skipping the call here
            # saves a ``_min_duration_for`` lookup (up to 5 config reads).
            # processlist with 580 procs × 2 stable ok-levels = 1160 obs
            # per cycle, almost all stable — short-circuit savings:
            # ~5800 config reads/cycle. We still need ``has_committed``
            # book-keeping and the steady-state repeat-action dispatch
            # below, so we set the flag and fall through.
            if observed_level == state.committed_level and state.pending_level is None:
                state.has_committed = True
                transition = None
            else:
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
                # Same timestamp as the event, by construction — the two can
                # never drift.
                if transition.new == "ok":
                    state.committed_since = None
                    # The incident is over: freeze whatever was accumulated.
                    self._release_top(state)
                elif state.committed_since is None:
                    # This transition OPENS the incident (an escalation leaves
                    # `committed_since` set and must not restart the capture).
                    state.committed_since = event["ts"]
                    self._open_top(state, self._top_sort_key(plugin, field_name), event)
                if transition.new != "ok":
                    # Entry into a non-ok level: fire non-repeat actions.
                    self._fire_actions(plugin, key, field_name, transition.new, value, repeat=False)

            # Steady-state repeat dispatch — fires on every ingest cycle
            # while the committed level is non-ok, including the cycle of
            # the entry transition (v4-aligned behaviour).
            if state.committed_level != "ok":
                self._accumulate_top(state, top_cache)
                self._fire_actions(plugin, key, field_name, state.committed_level, value, repeat=True)

        # Dynamic process auto-sort (v4 parity) — recomputed from the full
        # committed state after every ingest so recovery resets the key too.
        self._update_auto_sort()

    # ------------------------------------------------------- process auto-sort

    def _auto_sort_key(self) -> str:
        """Map the current worst active alert to a process sort key.

        Mirrors v4 ``EventsList.get_event_sort_key``:
        - an active ``mem`` alert        → ``memory_percent``
        - an active ``cpu`` iowait alert → ``io_counters``
        - otherwise                      → ``cpu_percent`` (the default)

        "Active" = the (plugin, field) has a committed non-ok level. MEM
        takes precedence over IOWAIT, matching v4's intent of surfacing the
        memory hogs first when memory pressure is the dominant signal.
        """
        mem_active = False
        iowait_active = False
        for (plugin_name, _key, field_name), state in self._state.items():
            if state.committed_level == "ok":
                continue
            if plugin_name == "mem":
                mem_active = True
            elif plugin_name == "cpu" and field_name == "iowait":
                iowait_active = True
        if mem_active:
            return "memory_percent"
        if iowait_active:
            return "io_counters"
        return "cpu_percent"

    def _update_auto_sort(self) -> None:
        """Push the alert-derived sort key to the engine when auto-sort is on.

        No-op when no engine is wired or the user has selected a manual sort
        key (``auto_sort`` False). ``set_sort_key(key, auto=True)`` keeps
        auto-sort enabled — only the manual hotkeys turn it off."""
        engine = self._process_engine
        if engine is None or not getattr(engine, "auto_sort", False):
            return
        try:
            engine.set_sort_key(self._auto_sort_key(), auto=True)
        except Exception as e:  # pragma: no cover — defensive
            logger.debug("auto-sort update failed: %s", e)

    # ---------------------------------------------------- top processes

    @staticmethod
    def _top_sort_key(plugin: GlancesPluginBase, field_name: str) -> str | None:
        """The field's declared process sort key, or None if it has none.

        Read from `fields_description` rather than from a table here, so a
        plugin opts in without `alerts_v5` knowing it exists (spec §4).
        """
        schema = type(plugin).fields_description.get(field_name, {})
        key = schema.get("top_processes_sort")
        return key if isinstance(key, str) and key else None

    def _open_top(self, state: _AlertState, sort_key: str | None, event: dict[str, Any]) -> None:
        """Start accumulating for an incident that just opened."""
        if sort_key is None:
            return
        state.top_counter = Counter()
        state.top_sort = sort_key
        state.top_event = event

    @staticmethod
    def _release_top(state: _AlertState) -> None:
        """Stop accumulating; the last value stays frozen in the opening event."""
        state.top_counter = None
        state.top_sort = None
        state.top_event = None

    def _sample_processes(self, sort_key: str) -> list[dict[str, Any]]:
        """The `_TOP_PROCESSES_SAMPLE` highest processes for `sort_key`.

        Empty when no engine is wired or the process plugins are disabled —
        the caller then writes nothing at all, so the payload key stays
        absent rather than becoming an empty list.
        """
        engine = self._process_engine
        if engine is None:
            return []
        try:
            procs = engine.get_list()
        except Exception as e:  # pragma: no cover - defensive
            logger.debug("top-process sampling failed: %s", e)
            return []
        if not procs:
            return []
        # `list(procs)`: `GlancesProcesses.get_list()` returns `processlist`
        # BY REFERENCE, and one branch of `sort_stats` sorts its argument IN
        # PLACE. The engine's own in-place caller invalidates a cache right
        # after sorting; we have no such hook, so we must not mutate its list.
        return sort_stats(list(procs), sort_key)[:_TOP_PROCESSES_SAMPLE]

    def _accumulate_top(self, state: _AlertState, cache: dict[str, list[dict[str, Any]]]) -> None:
        """One cycle of accumulation, then rewrite the opening event in place.

        `cache` is per-`ingest_plugin`-call, so the process list is sorted at
        most once per distinct sort key per cycle — and not at all while no
        annotated field is in alert.
        """
        if state.top_event is None or state.top_sort is None or state.top_counter is None:
            return
        sampled = cache.get(state.top_sort)
        if sampled is None:
            sampled = self._sample_processes(state.top_sort)
            cache[state.top_sort] = sampled
        if not sampled:
            return
        for proc in sampled:
            name = proc.get("name")
            if name:
                state.top_counter[str(name)] += 1
        # Bound the distinct-key count (see `_TOP_COUNTER_MAX_KEYS` above).
        # Single `len()` check so the common case (well under the cap) pays
        # almost nothing; only exceeding it pays for the rebuild. Rebinding
        # `state.top_counter` to a NEW `Counter` (rather than mutating the
        # existing one in place, e.g. via repeated `del`) is safe under the
        # threading model documented on `get_ongoing_top()`: that method
        # deliberately never reads `top_counter` — only the frozen
        # `top_event["top"]` list written below — specifically so the TUI
        # thread never iterates this dict concurrently with this coroutine
        # mutating it. If a future change makes `get_ongoing_top` read
        # `top_counter` directly, this rebind (or any mutation here) would
        # reintroduce that same "dictionary changed size during iteration"
        # race.
        if len(state.top_counter) > _TOP_COUNTER_MAX_KEYS:
            state.top_counter = Counter(dict(state.top_counter.most_common(_TOP_COUNTER_TRIM_TO)))
        # `most_common` is v4's `sorted(..., reverse=True)[0:3]`: Counter
        # keeps insertion order and the sort is stable, so ties break
        # identically — in O(n) instead of O(n log n).
        state.top_event["top"] = [name for name, _ in state.top_counter.most_common(_TOP_PROCESSES_KEEP)]
        state.top_event["top_sort"] = state.top_sort

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
                yield (None, field_name, _alert_level(level), payload.get(field_name), prominent)
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
                yield (str(pk_value), field_name, _alert_level(level), item.get(field_name), prominent)

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
