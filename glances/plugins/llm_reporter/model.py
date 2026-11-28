#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — llm_reporter plugin: an opt-in health report written by an LLM, on request (issue #3448).

A report is written only when someone asks for one: the ``H`` key (TUI and
WebUI), the "AI report" button, or ``POST /api/5/llm_reporter/request``, which a
client TUI calls on its server. The plugin then asks the configured LLM for a
short health report built from the stats Glances collects (``prompt.py``) and
publishes it with the date of the stats it describes, its age and the status
it states. The report windows show it with its age, and not at all while a
new one is being written: Glances never presents an old report as current.

- One call at a time, and at most one every ``min_interval`` seconds (default
  60), counted from the start of the last call: Glances is unauthenticated by
  default, and each call can be billed. A request inside that interval is
  answered with the previous report, its age and ``available_in``.
- A request during Glances' startup waits for its end: ``_STARTUP_DELAY``
  seconds and ``_STARTUP_CYCLES`` refresh cycles, past Glances' own startup
  load, and the end of the alerts engine's warm-up (until then, the prompt
  would claim no alert). The trends leave out the samples of the first
  ``_STARTUP_SAMPLES_SKIPPED`` seconds.
- The prompt is built on the scheduler's loop, at the first tick after the
  request; the LLM call runs in a daemon thread, which quitting Glances does
  not wait for.
- ``revision`` grows at each change of the state, so a UI holding both a
  request's answer and a later copy of the payload shows the newer one.
- A configuration error is logged at startup and published as ``error``; a
  failed call is logged, published as ``error``, and keeps the previous report.

The state is served by ``/api/5/llm_reporter`` and the MCP
``glances://stats/llm_reporter`` resource.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

from glances.config import GlancesConfig
from glances.plugins.llm_reporter.llm_reporter import LLMConfig, _build_reporter
from glances.plugins.llm_reporter.prompt import (
    ReportContext,
    construct_prompt,
    parse_status,
    read_alerts,
    read_current_state,
    read_top_processes,
    read_trends,
)
from glances.plugins.plugin.base import GlancesPluginBase
from glances.stats_store import StatsStore

if TYPE_CHECKING:
    from glances.alerts import GlancesAlerts

logger = logging.getLogger(__name__)

# Points of each metric's trend, spread over the whole history.
_DEFAULT_TREND_SAMPLES = 12
# Seconds from the start of a call before the next one can start.
_DEFAULT_MIN_INTERVAL = 60.0
# Seconds from the first tick to the first report: Glances' own startup load is over
# by then (it would be reported as a process using the CPU).
_STARTUP_DELAY = 30.0
# Refresh cycles the first report waits too, as the alerts engine's warm-up: with a
# slow global refresh, the seconds alone pass while the engine still skips its first
# cycles. The engine itself is also asked (`_startup_over`).
_STARTUP_CYCLES = 3
# Seconds of samples the trends leave out at startup: a process's first CPU reading is
# always 0, then comes Glances' own startup load.
_STARTUP_SAMPLES_SKIPPED = 10.0

# `state`: no report under way; a request waiting for the end of Glances' startup;
# a report being written (from the request to the LLM's answer).
_IDLE, _STARTING, _GENERATING = "idle", "starting", "generating"
# `error`: fixed sentences, as the exception of a call can quote its endpoint. The
# log has the details.
_NOT_CONFIGURED = "The LLM reporter is not configured correctly: see the Glances log."
_CALL_FAILED = "The LLM call failed: see the Glances log."
_EMPTY_REPORT = "The LLM returned an empty report: see the Glances log."
_Number = TypeVar("_Number", int, float)


class PluginModel(GlancesPluginBase[dict]):
    plugin_name: ClassVar[str] = "llm_reporter"
    IS_COLLECTION: ClassVar[bool] = False
    # The plugins the prompt reads (built along with it by the Python API).
    DEPENDS_ON: ClassVar[tuple[str, ...]] = ("cpu", "mem", "memswap", "load", "processlist", "gpu")
    # The report reads the alerts; it raises none.
    EMITS_ALERTS: ClassVar[bool] = False
    # Free text, served by the REST API and MCP.
    EXPORTABLE: ClassVar[bool] = False
    DISPLAY_IN_TUI: ClassVar[bool] = False
    DISABLED_BY_DEFAULT: ClassVar[bool] = True
    # Published at the global cadence, whatever `[llm_reporter] refresh` says: the
    # report windows follow `state` from one refresh to the next.
    SCHEDULE_AT_GLOBAL_REFRESH: ClassVar[bool] = True
    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "state": {
            "description": "idle; starting: a request waits for the end of Glances' startup; generating: the LLM "
            "is writing a report.",
            "unit": "string",
        },
        "report": {
            "description": "Last health report the LLM wrote on request, from the current metrics, their trends, "
            "the alert incidents and the top processes. None until the first report.",
            "unit": "string",
        },
        "status": {
            "description": "Health status the report states: ok, degraded, critical, or unknown when "
            "the report states none. None until the first report.",
            "unit": "string",
        },
        "model": {"description": "LLM model the report is requested from.", "unit": "string"},
        "generated_at": {
            "description": "Date of the stats the report describes, in ISO 8601 format. None until the first report.",
            "unit": "string",
        },
        "age": {
            "description": "Seconds since the stats the report describes. None until the first report.",
            "unit": "second",
        },
        "available_in": {
            "description": "Seconds before a new report can be requested (min_interval after the start of the "
            "last call): 0 when one can be requested now.",
            "unit": "second",
        },
        "error": {
            "description": "Why the last request brought no report, or why the plugin can write none. None otherwise.",
            "unit": "string",
        },
        "revision": {
            "description": "Grows at each change of the state: of two copies of this payload, the higher "
            "revision is the newer.",
            "unit": "number",
        },
    }

    def __init__(self, store: StatsStore, config: GlancesConfig) -> None:
        super().__init__(store, config)
        self._alerts: GlancesAlerts | None = None
        self._min_interval = _DEFAULT_MIN_INTERVAL
        self._trend_samples = _DEFAULT_TREND_SAMPLES
        self._model: str | None = None
        self._llm: Callable[[str], str] | None = None
        self._error: str | None = None
        try:
            self._min_interval = self._config_number("min_interval", _DEFAULT_MIN_INTERVAL)
            self._trend_samples = self._config_number("trend_samples", _DEFAULT_TREND_SAMPLES)
            llm_config = LLMConfig.from_glances_config(config)
            self._model = llm_config.model
            self._llm = _build_reporter(llm_config)
        except Exception as e:
            # The plugin stays registered: a request is answered with `error`.
            logger.error("Plugin %s: %s — no report will be generated", self.plugin_name, e)
            self._error = _NOT_CONFIGURED
        # The state below is shared by the scheduler's loop, the callers of
        # `request_report` (REST handlers, the TUI thread) and the LLM call's thread.
        self._lock = threading.Lock()
        self._state = _IDLE
        self._revision = 0
        self._report: str | None = None
        self._status: str | None = None
        self._generated_at: str | None = None
        # Monotonic dates: of the stats the report describes (its age), and of the
        # start of the last call (the cooldown).
        self._generated: float | None = None
        self._call_started: float | None = None
        self._in_flight = False
        # The LLM call's thread, while it runs or once it is done.
        self._thread: threading.Thread | None = None
        # The first tick (monotonic clock), and the oldest sample the trends use (history clock).
        self._started: float | None = None
        self._trends_since: float | None = None
        self._ticks = 0
        # Set once the startup is over (`_startup_over`), for good.
        self._ready = False
        # Clock the tests can set.
        self._monotonic = time.monotonic

    def _config_number(self, key: str, default: _Number) -> _Number:
        """Read a finite, non-negative tuning value; report the key, never the possibly secret malformed value."""
        kind = "integer" if isinstance(default, int) else "number"
        try:
            value = self.config.get(self.plugin_name, key, default)
            if not math.isfinite(value) or value < 0:
                raise ValueError
        except (TypeError, ValueError, OverflowError):
            raise ValueError(f"[llm_reporter] {key} must be a finite non-negative {kind}") from None
        return value

    def set_alerts(self, alerts: GlancesAlerts) -> None:
        """Hook called by ``main.attach_alerts()``: the alert incidents enrich the prompt."""
        self._alerts = alerts

    # ----------------------------------------------------------- requests

    def request_report(self) -> dict[str, Any]:
        """Ask for a new report and return the state that follows. Thread-safe.

        A report starts unless the plugin cannot write any, one is already under
        way, or the last call started less than ``min_interval`` seconds ago: the
        state returned then carries the previous report, its age, and when a new
        one can be requested.
        """
        with self._lock:
            now = self._monotonic()
            if self._llm is not None and self._state == _IDLE and self._cooldown(now) == 0:
                self._error = None
                self._set_state(_GENERATING if self._ready else _STARTING)
            return self._payload(now)

    def report_state(self) -> dict[str, Any]:
        """The state as published, at this instant. Thread-safe."""
        with self._lock:
            return self._payload(self._monotonic())

    def _set_state(self, state: str) -> None:
        self._state = state
        self._revision += 1

    def _cooldown(self, now: float) -> int:
        """Whole seconds before a new call can start."""
        if self._call_started is None:
            return 0
        return max(0, math.ceil(self._min_interval - (now - self._call_started)))

    def _payload(self, now: float) -> dict[str, Any]:
        return {
            "state": self._state,
            "report": self._report,
            "status": self._status,
            "model": self._model,
            "generated_at": self._generated_at,
            # Whole seconds elapsed, as `available_in` counts the seconds to come: the two
            # add up to min_interval after a report.
            "age": None if self._generated is None else max(0, int(now - self._generated)),
            "available_in": self._cooldown(now),
            "error": self._error,
            "revision": self._revision,
        }

    # -------------------------------------------------------------- ticks

    async def _grab_stats(self) -> dict:
        now = self._monotonic()
        if self._started is None:
            self._started = now
            self._trends_since = time.time() + _STARTUP_SAMPLES_SKIPPED
        self._ticks += 1
        if not self._ready:
            self._ready = self._startup_over(now)
        with self._lock:
            if self._state == _STARTING and self._ready:
                self._set_state(_GENERATING)
            due = self._state == _GENERATING and not self._in_flight
        if due:
            self._start_call(now)
        return self.report_state()

    def _startup_over(self, now: float) -> bool:
        """Past ``_STARTUP_DELAY`` seconds and ``_STARTUP_CYCLES`` cycles, and the alerts engine's warm-up."""
        # During its warm-up, the engine has no alert yet: the prompt would claim none.
        if now - self._started < _STARTUP_DELAY or self._ticks <= _STARTUP_CYCLES:
            return False
        return self._alerts is None or not self._alerts.is_initializing()

    def _start_call(self, now: float) -> None:
        """Build the prompt from the current stats, then start the LLM call in its own thread."""
        current = read_current_state(self.store, datetime.now().astimezone().isoformat(timespec="seconds"))
        if current is None:
            return  # cpu and mem have not published yet: the next tick tries again
        prompt = construct_prompt(
            ReportContext(
                current=current,
                trends=read_trends(self.history, self._trend_samples, not_before=self._trends_since),
                alerts=read_alerts(self._alerts),
                top_processes=read_top_processes(self.store),
            )
        )
        with self._lock:
            self._in_flight = True
            self._call_started = now
        # A daemon thread: quitting Glances during a call does not wait for the
        # answer (up to the timeout of every retry).
        self._thread = threading.Thread(
            target=self._call, args=(prompt, current.timestamp, now), name="llm_reporter", daemon=True
        )
        self._thread.start()

    def _call(self, prompt: str, generated_at: str, generated: float) -> None:
        """The LLM call, in its own thread: publish its report, or its error, and go back to idle."""
        report: str | None = None
        error: str | None = None
        try:
            report = (self._llm(prompt) or "").strip()
        except Exception as e:
            logger.warning(
                "Plugin %s: report generation failed (%s: %s) — keeping the previous report",
                self.plugin_name,
                type(e).__name__,
                e,
            )
            error = _CALL_FAILED
        else:
            if not report:
                logger.warning(
                    "Plugin %s: the LLM returned an empty report — keeping the previous one", self.plugin_name
                )
                error = _EMPTY_REPORT
        with self._lock:
            if error is None:
                self._report = report
                self._status = parse_status(report)
                self._generated_at = generated_at
                self._generated = generated
            self._error = error
            self._in_flight = False
            self._set_state(_IDLE)
