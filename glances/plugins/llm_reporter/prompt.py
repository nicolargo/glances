#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — llm_reporter: build the prompt from the stats Glances collects.

Read-only sources: the current values in the stats store, their trend over
the whole history store, the alert incidents (ongoing first, then the last
resolved ones) and the top processes. A section whose source is unavailable
(disabled plugin, short or disabled history, no alerts engine) is left out.

Processes are sent by name, as command lines can hold secrets, with control
characters replaced so that each one stays on its own line.
"""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from glances.alerts_incidents import incidents_payload
from glances.globals import CONTROL_CHARS_TO_QUESTION_MARK, auto_unit

if TYPE_CHECKING:
    from glances.alerts import GlancesAlerts
    from glances.history import HistoryStore
    from glances.stats_store import StatsStore

_TOP_PROCESSES = 5
# Alert incidents in the prompt: the ongoing ones first, then the last resolved.
_ALERT_INCIDENTS = 20
# (plugin, historised field, value format) of each trend line.
_TREND_SERIES: dict[str, tuple[str, str, str]] = {
    "cpu": ("cpu", "total", "{:.0f}%"),
    "memory": ("mem", "percent", "{:.0f}%"),
    "swap": ("memswap", "percent", "{:.0f}%"),
    "load_avg": ("load", "min1", "{:.2f}"),
}
# Historised percent fields of the gpu plugin, a collection: one trend line per GPU.
_GPU_TREND_FIELDS = ("proc", "mem")
_STATUS_RE = re.compile(r"\b(ok|degraded|critical)\b", re.IGNORECASE)

# The report describes; it never prescribes: an action the model suggests, such
# as killing a process, can degrade the system it only saw through these numbers.
_INSTRUCTIONS = """\
You are a system monitoring expert. Analyze the following metrics and produce
a concise health report in 4-6 sentences maximum. Describe the state of the
system only: never recommend an action, such as killing or restarting a
process or changing a setting."""

_ANSWER_FORMAT = """\
Start with one line: "Summary: " followed by one sentence of at most 15 words.
If there are ongoing alerts, the sentence must mention the most severe one.
Then provide in order:
1. Overall health status: OK | Degraded | Critical
2. Root cause if any issue detected"""


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
    # gpu_id -> "proc ..., mem ...", empty without a GPU.
    gpus: dict[str, str]


@dataclass(frozen=True)
class ReportContext:
    current: CurrentState
    trends: Trends | None
    alerts: list[str] | None
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


def _recent_points(
    history: HistoryStore, plugin_name: str, field: str, since: float, item: str | None = None
) -> list[tuple[float, float]]:
    """``(timestamp, value)`` of one series from ``since`` on, gaps (None) dropped.

    ``item`` selects one item of a collection plugin (a GPU's ``gpu_id``).
    """
    hist = history.get(plugin_name)
    values = hist["series"].get(field)
    if item is not None:
        values = values.get(item) if isinstance(values, dict) else None
    if not isinstance(values, list):
        return []
    return [(ts, v) for ts, v in zip(hist["timestamps"], values) if ts >= since and v is not None]


def read_trends(history: HistoryStore | None, samples: int, not_before: float | None = None) -> Trends | None:
    """Each metric's trend over the whole history, ``samples`` points each.

    None — the section is left out — when history is disabled, or when no
    metric has 2 points yet (cold start). A metric short of points alone
    reads ``n/a``. Samples older than ``not_before`` are left out.
    """
    if history is None or samples < 2:
        return None
    since = -math.inf if not_before is None else not_before
    lines: dict[str, str] = {}
    spans: list[float] = []
    for name, (plugin_name, field, value_format) in _TREND_SERIES.items():
        points = sample_evenly(_recent_points(history, plugin_name, field, since), samples)
        if len(points) < 2:
            lines[name] = "n/a"
            continue
        spans.append(points[-1][0] - points[0][0])
        lines[name] = format_series([v for _, v in points], value_format)
    gpus: dict[str, str] = {}
    gpu_series = history.get("gpu")["series"]
    for gpu_id in sorted({gpu_id for field in _GPU_TREND_FIELDS for gpu_id in gpu_series.get(field, {})}):
        parts = []
        for field in _GPU_TREND_FIELDS:
            points = sample_evenly(_recent_points(history, "gpu", field, since, item=gpu_id), samples)
            if len(points) < 2:
                parts.append(f"{field} n/a")
                continue
            spans.append(points[-1][0] - points[0][0])
            parts.append(f"{field} {format_series([v for _, v in points], '{:.0f}%')}")
        gpus[gpu_id] = ", ".join(parts)
    if not spans:
        return None
    return Trends(window_seconds=round(max(spans)), **lines, gpus=gpus)


def _local_time(iso: str) -> str:
    """An alert's start in local time, as the prompt's timestamp: ``HH:MM:SS``, with the date if not today.

    The alerts engine dates in UTC, to the microsecond; a model copied that into its summary.
    """
    try:
        start = datetime.fromisoformat(iso).astimezone()
    except ValueError:
        return iso
    today = datetime.now().astimezone().date()
    return start.strftime("%H:%M:%S" if start.date() == today else "%Y-%m-%d %H:%M:%S")


def _incident_line(incident: dict[str, Any]) -> str:
    """``cpu.iowait: warning, ongoing since 10:02:01 (5m29s), top processes: dd, cp``.

    The incident as the alerts block shows it: its highest level, its start,
    its end once resolved, its duration, and the processes on top while it lasted.
    """
    target = ".".join(str(incident[part]) for part in ("plugin", "key", "field") if incident.get(part))
    begin, end = incident.get("begin"), incident.get("end")
    if incident.get("ongoing"):
        when = "ongoing" + (f" since {_local_time(begin)}" if begin else "")
    else:
        when = (
            "resolved" + (f", from {_local_time(begin)}" if begin else "") + (f" to {_local_time(end)}" if end else "")
        )
    line = f"{target}: {incident.get('level')}, {when}"
    if incident.get("duration"):
        line += f" ({incident['duration']})"
    top = [str(name).translate(CONTROL_CHARS_TO_QUESTION_MARK) for name in incident.get("top") or []]
    if top:
        line += f", top processes: {', '.join(top)}"
    return line


def read_alerts(alerts: GlancesAlerts | None, n: int = _ALERT_INCIDENTS) -> list[str] | None:
    """One line per alert incident, ongoing first, at most ``n``; None without an alerts engine.

    The incidents of the alerts block (``incidents_payload``), so the report
    and the block speak of the same alerts.
    """
    if alerts is None:
        return None
    return [_incident_line(incident) for incident in incidents_payload(alerts)["incidents"][:n]]


def read_top_processes(store: StatsStore, n: int = _TOP_PROCESSES) -> list[str] | None:
    """The ``n`` most CPU-hungry processes, by name; None when processlist publishes nothing.

    Glances itself is left out: busy at startup, it would be reported as the
    process using the CPU.
    """
    items = _scalar(store, "processlist").get("data")
    if not items:
        return None
    others = [p for p in items if p.get("pid") != os.getpid()]
    top = sorted(others, key=lambda p: p.get("cpu_percent") or 0.0, reverse=True)[:n]
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
            f"Load   : {t.load_avg}" + "".join(f"\nGPU {gpu_id} : {line}" for gpu_id, line in t.gpus.items())
        )
    if ctx.alerts is not None:
        sections.append(
            "=== ALERTS (ongoing first, then the last resolved) ===\n"
            + ("\n".join(f"- {a}" for a in ctx.alerts) or "None")
        )
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
