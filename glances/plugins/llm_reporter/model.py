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
(``prompt.py``), and publishes it with the status it states.

- The plugin ticks on the global cadence and paces the LLM calls itself;
  ``_ReportCache`` reuses the last report while the system state is unchanged.
- The first report waits ``_WARMUP_CYCLES`` ticks, for trends, top processes
  and alerts to be available.
- The LLM call runs in a worker thread.
- A configuration error is logged at startup and leaves the fields empty; a
  failed call is logged and the previous report is kept.

The report is served by ``/api/5/llm_reporter`` and the MCP
``glances://stats/llm_reporter`` resource.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar

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
)
from glances.plugins.plugin.base import GlancesPluginBase
from glances.stats_store import StatsStore

if TYPE_CHECKING:
    from glances.alerts import GlancesAlerts

logger = logging.getLogger(__name__)

_DEFAULT_TREND_SAMPLES = 3
# Ticks before the first report, as the alerts engine's warm-up.
_WARMUP_CYCLES = 3


class PluginModel(GlancesPluginBase[dict]):
    plugin_name: ClassVar[str] = "llm_reporter"
    IS_COLLECTION: ClassVar[bool] = False
    # The plugins the prompt reads (built along with it by the Python API).
    DEPENDS_ON: ClassVar[tuple[str, ...]] = ("cpu", "mem", "memswap", "load", "processlist")
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
        self._interval = self._resolve_interval()
        self._cache = _ReportCache(config.get(self.plugin_name, "cache_ttl", _DEFAULT_CACHE_TTL))
        self._trend_samples = config.get(self.plugin_name, "trend_samples", _DEFAULT_TREND_SAMPLES)
        self._model: str | None = None
        self._llm: Callable[[str], str] | None = None
        try:
            llm_config = LLMConfig.from_glances_config(config)
            self._model = llm_config.model
            self._llm = _build_reporter(llm_config)
        except Exception as e:
            # The plugin stays registered and publishes empty fields.
            logger.error("Plugin %s: %s — no report will be generated", self.plugin_name, e)
        self._report: str | None = None
        self._status: str | None = None
        self._generated_at: str | None = None
        self._last_call_ts: float | None = None
        self._warmup_left = _WARMUP_CYCLES
        # Clock the tests can set.
        self._monotonic = time.monotonic

    def _resolve_interval(self) -> float:
        """Seconds between two reports: ``[llm_reporter] refresh`` (or ``refresh_time``), else 300."""
        for key in ("refresh", "refresh_time"):
            value = self.config.get(self.plugin_name, key, -1.0)
            if value > 0:
                return value
        return self.DEFAULT_REFRESH_TIME

    def set_alerts(self, alerts: GlancesAlerts) -> None:
        """Hook called by ``main.attach_alerts()``: the active alerts enrich the prompt."""
        self._alerts = alerts

    async def _grab_stats(self) -> dict:
        if self._warmup_left:
            self._warmup_left -= 1
        elif self._llm is not None and self._report_due():
            await self._update_report()
        return {
            "report": self._report,
            "status": self._status,
            "model": self._model,
            "generated_at": self._generated_at,
        }

    def _report_due(self) -> bool:
        return self._last_call_ts is None or self._monotonic() - self._last_call_ts >= self._interval

    async def _update_report(self) -> None:
        """Ask the LLM for a new report, unless the inputs are not ready or the state is unchanged."""
        current = read_current_state(self.store, datetime.now().astimezone().isoformat(timespec="seconds"))
        if current is None:
            return  # waits for cpu and mem
        active_alerts = read_active_alerts(self._alerts)
        now = self._monotonic()
        key = state_key(current.cpu, current.mem_percent, current.swap_percent, len(active_alerts or []))
        if not self._cache.is_stale(key, now):
            return
        prompt = construct_prompt(
            ReportContext(
                current=current,
                trends=read_trends(self.history, self._interval, self._trend_samples),
                active_alerts=active_alerts,
                top_processes=read_top_processes(self.store),
            )
        )
        # Each attempt starts the interval, so a failing provider is retried once per interval.
        self._last_call_ts = now
        try:
            report = await asyncio.to_thread(self._llm, prompt)
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
        self._report = report.strip()
        self._status = parse_status(self._report)
        self._generated_at = current.timestamp
        self._cache.store(key, now)
