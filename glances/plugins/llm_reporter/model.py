#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — llm_reporter plugin: an opt-in health report written by an LLM (issue #3448).

Every ``refresh`` seconds (default 300), the plugin asks the configured LLM
for a short health report built from the stats Glances collects
(``prompt.py``), and publishes it with the status it states and its
one-sentence summary (``short_report``, displayed by the TUI and the WebUI).

- The plugin ticks on the global cadence and paces the LLM calls itself;
  ``_ReportCache`` reuses the last report while the system state is unchanged.
- A change of the active alerts brings the next report early, at most every
  ``min_interval`` seconds (default 60), so the summary follows the alerts.
- The first report waits ``_STARTUP_DELAY`` seconds and ``_STARTUP_CYCLES``
  refresh cycles, past Glances' own startup load, and the end of the alerts
  engine's warm-up; its trends leave out the samples of the first
  ``_STARTUP_SAMPLES_SKIPPED`` seconds.
- The LLM call runs in a daemon thread, which quitting Glances does not wait for.
- A configuration error is logged at startup and leaves the fields empty; a
  failed call is logged and the previous report is kept.

The report is served by ``/api/5/llm_reporter`` and the MCP
``glances://stats/llm_reporter`` resource.
"""

from __future__ import annotations

import asyncio
import logging
import math
import threading
import time
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

from glances.config import GlancesConfig
from glances.plugins.llm_reporter.llm_reporter import (
    _DEFAULT_CACHE_TTL,
    LLMConfig,
    _build_reporter,
    _ReportCache,
    state_key,
)
from glances.plugins.llm_reporter.prompt import (
    ReportContext,
    construct_prompt,
    parse_status,
    read_active_alerts,
    read_current_state,
    read_top_processes,
    read_trends,
    split_summary,
)
from glances.plugins.plugin.base import GlancesPluginBase
from glances.stats_store import StatsStore

if TYPE_CHECKING:
    from glances.alerts import GlancesAlerts

logger = logging.getLogger(__name__)

_DEFAULT_TREND_SAMPLES = 3
# Seconds: when the active alerts change, the next report comes early, at most this often.
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
_Number = TypeVar("_Number", int, float)


async def _run_in_daemon_thread(func: Callable[[str], str], arg: str) -> str:
    """``await asyncio.to_thread(func, arg)``, in a thread that quitting Glances does not wait for."""
    # Python waits for asyncio.to_thread's threads before exiting: quitting during
    # an LLM call would wait for the answer, up to the timeout of every retry.
    # A daemon thread is abandoned instead.
    loop = asyncio.get_running_loop()
    future = loop.create_future()

    def settle(set_outcome: Callable[[Any], None], value: Any) -> None:
        if not future.done():  # done: the await was cancelled
            set_outcome(value)

    def work() -> None:
        try:
            outcome = (future.set_result, func(arg))
        except BaseException as e:
            outcome = (future.set_exception, e)
        try:
            loop.call_soon_threadsafe(settle, *outcome)
        except RuntimeError:
            pass  # the loop is closed: Glances quit during the call

    threading.Thread(target=work, name="llm_reporter", daemon=True).start()
    return await future


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
    # `refresh` paces the LLM calls (`_report_due`); the scheduler ticks the
    # plugin on the global cadence.
    DEFAULT_REFRESH_TIME: ClassVar[float | None] = 300.0
    SCHEDULE_AT_GLOBAL_REFRESH: ClassVar[bool] = True
    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "report": {
            "description": "Health report written by the LLM from the current metrics, their trends, "
            "the active alerts and the top processes. None until the first report.",
            "unit": "string",
        },
        "short_report": {
            "description": "One-sentence summary of the report, shown in the ALERTS title of the TUI and the "
            "WebUI. None until the first report, or when the report states none.",
            "unit": "string",
        },
        "status": {
            "description": "Health status the report states: ok, degraded, critical, or unknown when "
            "the report states none. None until the first report.",
            "unit": "string",
        },
        "model": {"description": "LLM model the report is requested from.", "unit": "string"},
        "generated_at": {
            "description": "Date of the stats the report was generated from, in ISO 8601 format. "
            "None until the first report.",
            "unit": "string",
        },
    }

    def __init__(self, store: StatsStore, config: GlancesConfig) -> None:
        super().__init__(store, config)
        self._alerts: GlancesAlerts | None = None
        self._interval = self.DEFAULT_REFRESH_TIME
        self._min_interval = _DEFAULT_MIN_INTERVAL
        self._cache = _ReportCache(_DEFAULT_CACHE_TTL)
        self._trend_samples = _DEFAULT_TREND_SAMPLES
        self._model: str | None = None
        self._llm: Callable[[str], str] | None = None
        try:
            self._interval = self._resolve_interval()
            self._min_interval = self._config_number("min_interval", _DEFAULT_MIN_INTERVAL)
            self._cache = _ReportCache(self._config_number("cache_ttl", _DEFAULT_CACHE_TTL))
            self._trend_samples = self._config_number("trend_samples", _DEFAULT_TREND_SAMPLES)
            llm_config = LLMConfig.from_glances_config(config)
            self._model = llm_config.model
            self._llm = _build_reporter(llm_config)
        except Exception as e:
            # The plugin stays registered and publishes empty fields.
            logger.error("Plugin %s: %s — no report will be generated", self.plugin_name, e)
        self._report: str | None = None
        self._short_report: str | None = None
        self._status: str | None = None
        self._generated_at: str | None = None
        self._last_call_ts: float | None = None
        # Active alerts (and their levels) when the LLM was last called.
        self._called_alerts: frozenset | None = None
        # The first tick (monotonic clock), and the oldest sample the trends use (history clock).
        self._started: float | None = None
        self._trends_since: float | None = None
        self._ticks = 0
        # Set once the startup is over (`_startup_over`), for good.
        self._ready = False
        # Clock the tests can set.
        self._monotonic = time.monotonic

    def _resolve_interval(self) -> float:
        """Seconds between two reports: ``[llm_reporter] refresh`` (or ``refresh_time``), else 300."""
        for key in ("refresh", "refresh_time"):
            # Non-positive values still fall through to the alias or default, as in the scheduler.
            value = self._config_number(key, -1.0, allow_negative=True)
            if value > 0:
                return value
        return self.DEFAULT_REFRESH_TIME

    def _config_number(self, key: str, default: _Number, *, allow_negative: bool = False) -> _Number:
        """Read a finite tuning value; report the key, never the possibly secret malformed value."""
        kind = "integer" if isinstance(default, int) else "number"
        expected = f"finite {'non-negative ' if not allow_negative else ''}{kind}"
        try:
            value = self.config.get(self.plugin_name, key, default)
            if not math.isfinite(value) or (not allow_negative and value < 0):
                raise ValueError
        except (TypeError, ValueError, OverflowError):
            raise ValueError(f"[llm_reporter] {key} must be a {expected}") from None
        return value

    def set_alerts(self, alerts: GlancesAlerts) -> None:
        """Hook called by ``main.attach_alerts()``: the active alerts enrich the prompt."""
        self._alerts = alerts

    async def _grab_stats(self) -> dict:
        now = self._monotonic()
        if self._started is None:
            self._started = now
            self._trends_since = time.time() + _STARTUP_SAMPLES_SKIPPED
        self._ticks += 1
        if not self._ready:
            self._ready = self._startup_over(now)
        if self._llm is not None and self._ready and self._report_due():
            await self._update_report()
        return {
            "report": self._report,
            "short_report": self._short_report,
            "status": self._status,
            "model": self._model,
            "generated_at": self._generated_at,
        }

    def _startup_over(self, now: float) -> bool:
        """Past ``_STARTUP_DELAY`` seconds and ``_STARTUP_CYCLES`` cycles, and the alerts engine's warm-up."""
        # During its warm-up, the engine has no alert yet: the prompt would claim none.
        if now - self._started < _STARTUP_DELAY or self._ticks <= _STARTUP_CYCLES:
            return False
        return self._alerts is None or not self._alerts.is_initializing()

    def _active_alerts(self) -> frozenset:
        """The ongoing alerts with their levels: an alert opening, closing or changing level changes it."""
        return frozenset(self._alerts.get_ongoing().items()) if self._alerts is not None else frozenset()

    def _report_due(self) -> bool:
        """Every ``refresh`` seconds, and early when the active alerts change, at most every ``min_interval``."""
        # The report describes the alerts it was given: a change makes it, and its
        # summary shown next to the live alert counts, out of date.
        if self._last_call_ts is None:
            return True
        elapsed = self._monotonic() - self._last_call_ts
        if elapsed >= self._interval:
            return True
        return elapsed >= self._min_interval and self._active_alerts() != self._called_alerts

    async def _update_report(self) -> None:
        """Ask the LLM for a new report, unless the inputs are not ready or the state is unchanged."""
        current = read_current_state(self.store, datetime.now().astimezone().isoformat(timespec="seconds"))
        if current is None:
            return  # waits for cpu and mem
        active_alerts = read_active_alerts(self._alerts)
        alerts = self._active_alerts()
        now = self._monotonic()
        key = state_key(current.cpu, current.mem_percent, current.swap_percent, alerts)
        if not self._cache.is_stale(key, now):
            return
        prompt = construct_prompt(
            ReportContext(
                current=current,
                trends=read_trends(self.history, self._interval, self._trend_samples, not_before=self._trends_since),
                active_alerts=active_alerts,
                top_processes=read_top_processes(self.store),
            )
        )
        # Each attempt starts the interval, so a failing provider is retried once per interval
        # (or on the next change of the alerts).
        self._last_call_ts = now
        self._called_alerts = alerts
        try:
            report = await _run_in_daemon_thread(self._llm, prompt)
        except Exception as e:
            logger.warning(
                "Plugin %s: report generation failed (%s: %s) — keeping the previous report",
                self.plugin_name,
                type(e).__name__,
                e,
            )
            return
        if not report or not report.strip():
            logger.warning("Plugin %s: the LLM returned an empty report — keeping the previous one", self.plugin_name)
            return
        self._short_report, body = split_summary(report.strip())
        # A reply that is only the summary stays the report too.
        self._report = body or report.strip()
        self._status = parse_status(self._report)
        self._generated_at = current.timestamp
        self._cache.store(key, now)
