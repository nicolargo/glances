#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — llm_reporter: build the prompt from the stats Glances collects.

Three read-only sources: the current values in the stats store, their trend
in the history store, and the active alerts. A section whose source is
unavailable (disabled plugin, short or disabled history, no alerts engine)
is left out.

Processes are sent by name, as command lines can hold secrets, with control
characters replaced so that each one stays on its own line.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from glances.globals import CONTROL_CHARS_TO_QUESTION_MARK, auto_unit

if TYPE_CHECKING:
    from glances.alerts import GlancesAlerts
    from glances.history import HistoryStore
    from glances.stats_store import StatsStore

_TOP_PROCESSES = 5
# (plugin, historised field, value format) of each trend line.
_TREND_SERIES: dict[str, tuple[str, str, str]] = {
    "cpu": ("cpu", "total", "{:.0f}%"),
    "memory": ("mem", "percent", "{:.0f}%"),
    "swap": ("memswap", "percent", "{:.0f}%"),
    "load_avg": ("load", "min1", "{:.2f}"),
}
_STATUS_RE = re.compile(r"\b(ok|degraded|critical)\b", re.IGNORECASE)

_INSTRUCTIONS = """\
You are a system monitoring expert. Analyze the following metrics and produce
a concise health report in 4-6 sentences maximum."""

_ANSWER_FORMAT = """\
Provide in order:
1. Overall health status: OK | Degraded | Critical
2. Root cause if any issue detected
3. Recommended action (or "None required" if healthy)"""


@dataclass(frozen=True)
class CurrentState:
    timestamp: str
    cpu: float
    mem_percent: float
    mem_used: float | None
    mem_total: float | None
    swap_percent: float | None
    swap_used: float | None
    swap_total: float | None
    load: tuple[float, float, float] | None
    cpu_cores: int | None


@dataclass(frozen=True)
class Trends:
    window_seconds: int
    cpu: str
    memory: str
    swap: str
    load_avg: str


@dataclass(frozen=True)
class ReportContext:
    current: CurrentState
    trends: Trends | None
    active_alerts: list[str] | None
    top_processes: list[str] | None


def _scalar(store: StatsStore, plugin_name: str) -> dict[str, Any]:
    payload = store.get(plugin_name)
    return payload if isinstance(payload, dict) else {}


def read_current_state(store: StatsStore, timestamp: str) -> CurrentState | None:
    """The current values, or None until both cpu and mem have published (first cycle)."""
    cpu, mem = _scalar(store, "cpu"), _scalar(store, "mem")
    if cpu.get("total") is None or mem.get("percent") is None:
        return None
    swap, load = _scalar(store, "memswap"), _scalar(store, "load")
    load_avg = (load.get("min1"), load.get("min5"), load.get("min15"))
    return CurrentState(
        timestamp=timestamp,
        cpu=cpu["total"],
        mem_percent=mem["percent"],
        mem_used=mem.get("used"),
        mem_total=mem.get("total"),
        swap_percent=swap.get("percent"),
        swap_used=swap.get("used"),
        swap_total=swap.get("total"),
        load=None if None in load_avg else load_avg,
        cpu_cores=load.get("cpucore"),
    )


def compute_delta(values: list[float]) -> float:
    """Change over the trend window: last value minus first."""
    return values[-1] - values[0]


def sample_evenly(points: list[Any], n: int) -> list[Any]:
    """``n`` points spread evenly over ``points``, the first and the last included."""
    if len(points) <= n:
        return points
    return [points[round(i * (len(points) - 1) / (n - 1))] for i in range(n)]


def format_series(values: list[float], value_format: str) -> str:
    """``45% → 71% → 92%  (+47%)``."""
    series = " → ".join(value_format.format(v) for v in values)
    delta = value_format.replace("{:", "{:+").format(compute_delta(values))
    return f"{series}  ({delta})"


def _recent_points(history: HistoryStore, plugin_name: str, field: str, since: float) -> list[tuple[float, float]]:
    """``(timestamp, value)`` of one scalar series from ``since`` on, gaps (None) dropped."""
    hist = history.get(plugin_name)
    values = hist["series"].get(field)
    if not isinstance(values, list):
        return []
    return [(ts, v) for ts, v in zip(hist["timestamps"], values) if ts >= since and v is not None]


def read_trends(history: HistoryStore | None, window: float, samples: int, now: float | None = None) -> Trends | None:
    """Each metric's trend over the last ``window`` seconds, ``samples`` points each.

    None — the section is left out — when history is disabled, or when no
    metric has 2 points yet (cold start). A metric short of points alone
    reads ``n/a``.
    """
    if history is None or samples < 2:
        return None
    since = (time.time() if now is None else now) - window
    lines: dict[str, str] = {}
    spans: list[float] = []
    for name, (plugin_name, field, value_format) in _TREND_SERIES.items():
        points = sample_evenly(_recent_points(history, plugin_name, field, since), samples)
        if len(points) < 2:
            lines[name] = "n/a"
            continue
        spans.append(points[-1][0] - points[0][0])
        lines[name] = format_series([v for _, v in points], value_format)
    if not spans:
        return None
    return Trends(window_seconds=round(max(spans)), **lines)


def read_active_alerts(alerts: GlancesAlerts | None) -> list[str] | None:
    """One line per active alert, or None without an alerts engine."""
    if alerts is None:
        return None
    since = alerts.get_ongoing_since()
    top = alerts.get_ongoing_top()
    lines = []
    for key, level in sorted(alerts.get_ongoing().items(), key=lambda item: [str(part) for part in item[0]]):
        line = f"{'.'.join(str(part) for part in key if part)}: {level}"
        if key in since:
            line += f" since {since[key]}"
        if key in top:
            line += f" (top processes: {', '.join(top[key]['top'])})"
        lines.append(line)
    return lines


def read_top_processes(store: StatsStore, n: int = _TOP_PROCESSES) -> list[str] | None:
    """The ``n`` most CPU-hungry processes, by name; None when processlist publishes nothing."""
    items = _scalar(store, "processlist").get("data")
    if not items:
        return None
    top = sorted(items, key=lambda p: p.get("cpu_percent") or 0.0, reverse=True)[:n]
    return [
        f"{str(p.get('name') or '?').translate(CONTROL_CHARS_TO_QUESTION_MARK)}: "
        f"CPU {p.get('cpu_percent') or 0.0:.1f}%, MEM {p.get('memory_percent') or 0.0:.1f}%"
        for p in top
    ]


def _usage(percent: float | None, used: float | None, total: float | None) -> str:
    if percent is None:
        return "n/a"
    if used is None or total is None:
        return f"{percent:.1f}%"
    return f"{auto_unit(used)} / {auto_unit(total)} ({percent:.1f}%)"


def _load(load: tuple[float, float, float] | None, cores: int | None) -> str:
    if load is None:
        return "n/a"
    text = " / ".join(f"{v:.2f}" for v in load)
    return f"{text} ({cores} cores)" if cores else text


def construct_prompt(ctx: ReportContext) -> str:
    c = ctx.current
    sections = [
        _INSTRUCTIONS,
        "=== CURRENT STATE ===\n"
        f"Timestamp : {c.timestamp}\n"
        f"CPU       : {c.cpu:.1f}%\n"
        f"Memory    : {_usage(c.mem_percent, c.mem_used, c.mem_total)}\n"
        f"Swap      : {_usage(c.swap_percent, c.swap_used, c.swap_total)}\n"
        f"Load avg  : {_load(c.load, c.cpu_cores)}",
    ]
    if ctx.trends is not None:
        t = ctx.trends
        sections.append(
            f"=== TRENDS (last {t.window_seconds}s) ===\n"
            f"CPU    : {t.cpu}\n"
            f"Memory : {t.memory}\n"
            f"Swap   : {t.swap}\n"
            f"Load   : {t.load_avg}"
        )
    if ctx.active_alerts is not None:
        sections.append("=== ACTIVE ALERTS ===\n" + ("\n".join(f"- {a}" for a in ctx.active_alerts) or "None"))
    if ctx.top_processes:
        sections.append("=== TOP PROCESSES ===\n" + "\n".join(f"- {p}" for p in ctx.top_processes))
    sections.append(_ANSWER_FORMAT)
    return "\n\n".join(sections)


def parse_status(report: str) -> str:
    """The health status a report states — ``ok``, ``degraded`` or ``critical`` — else ``unknown``.

    Read after the word "status" on the first line that states one, as the
    prompt asks the model to answer.
    """
    for line in report.splitlines():
        _, found, after = line.lower().partition("status")
        match = _STATUS_RE.search(after) if found else None
        if match:
            return match.group(1).lower()
    return "unknown"
