#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — CPU plugin (scalar, system-wide aggregate).

Migrated from `glances/plugins/cpu/__init__.py`. Companion to the v5
`percpu` plugin (per-core view); both share psutil samples through
``glances.cpu_sampler_v5`` (architecture §3 — equivalent of v4's
``glances/cpu_percent.py`` shared singleton).

V4-aligned watched fields:
- ``total``        prominent True  — sum of CPU% except idle.
- ``system``       prominent False — kernel-space CPU%.
- ``user``         prominent False — user-space CPU%.
- ``iowait``       prominent False — Linux I/O wait CPU%.
- ``dpc``          prominent False — Windows deferred procedure calls.
- ``steal``        prominent True  — virtualised CPU stolen by hypervisor.
                   Stricter thresholds (5/15/30) — any non-trivial steal
                   indicates a noisy-neighbour situation worth surfacing.
- ``ctx_switches`` prominent True  — counter rate, **absolute thresholds**
                   (10k/15k/20k). Not per-core normalised — the metric
                   is a system-wide scheduler-pressure signal. Diverges
                   from v4 (which documents 50000*cpucore but its
                   ``get_limit`` chain never resolves the default, so v4
                   ships effectively no threshold).

SNMP support is **not ported to v5** (architecture §10).
"""

from __future__ import annotations

from typing import Any, ClassVar

from glances.cpu_sampler_v5 import sampler
from glances.plugins.plugin.base_v5 import GlancesPluginBase

_DEFAULT_PERCENT_THRESHOLDS = {"careful": 50.0, "warning": 70.0, "critical": 90.0}
_DEFAULT_STEAL_THRESHOLDS = {"careful": 5.0, "warning": 15.0, "critical": 30.0}
# `ctx_switches` thresholds are absolute (no per-core normalisation). Empirical
# values: typical desktop idle ~3-10k ctx/s; busy parallel build 50k+. Picked
# to flag system-wide scheduler pressure regardless of core count — a single
# thrashing process produces similar absolute rates on any machine. Big SMP
# servers (128+ cores) can override via `[cpu] ctx_switches_*` in glances.conf.
#
# v5 divergence from v4: v4 documents `critical = 50000 * cpucore` in
# `conf/glances.conf` but the `get_limit` fallback chain in v4 silently
# never resolves to a value (double-prefix bug in `_limits` keys), so v4
# ships effectively no default threshold. v5 fixes this by shipping
# real defaults. Documented in NEWS.rst at 5.0.0.
_DEFAULT_CTX_THRESHOLDS = {"careful": 10000.0, "warning": 15000.0, "critical": 20000.0}


class PluginModel(GlancesPluginBase[dict]):
    """System-wide CPU plugin (scalar)."""

    plugin_name: ClassVar[str] = "cpu"
    IS_COLLECTION: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "total": {
            "description": "Sum of all CPU percentages (except idle).",
            "unit": "percent",
            "history": True,
            "watched": True,
            "watch_direction": "high",
            "prominent": True,
            "default_thresholds": _DEFAULT_PERCENT_THRESHOLDS,
        },
        "system": {
            "description": (
                "Percent time spent in kernel space. System CPU time is the time "
                "spent running code in the operating system kernel."
            ),
            "unit": "percent",
            "history": True,
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "default_thresholds": _DEFAULT_PERCENT_THRESHOLDS,
        },
        "user": {
            "description": (
                "Percent time spent in user space. User CPU time is the time spent "
                "on the processor running the program's code (or code in libraries)."
            ),
            "unit": "percent",
            "history": True,
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "default_thresholds": _DEFAULT_PERCENT_THRESHOLDS,
        },
        "iowait": {
            "description": ("(Linux) Percent time spent by the CPU waiting for I/O operations to complete."),
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": True,
            "default_thresholds": _DEFAULT_PERCENT_THRESHOLDS,
        },
        "dpc": {
            "description": "(Windows) Percent time spent servicing deferred procedure calls (DPCs).",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "default_thresholds": _DEFAULT_PERCENT_THRESHOLDS,
        },
        "idle": {
            "description": (
                "Percent of CPU not used by any program. Every program or task that "
                "runs occupies a certain amount of processing time on the CPU; when "
                "the CPU has completed all tasks it is idle."
            ),
            "unit": "percent",
        },
        "irq": {
            "description": ("(Linux and BSD) Percent time spent servicing hardware and software interrupts."),
            "unit": "percent",
        },
        "nice": {
            "description": (
                "(UNIX) Percent time occupied by user-level processes with a positive nice "
                "value (processes that have been niced down)."
            ),
            "unit": "percent",
        },
        "steal": {
            "description": (
                "(Linux) Percentage of time a virtual CPU waits for a real CPU while the "
                "hypervisor is servicing another virtual processor."
            ),
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "default_thresholds": _DEFAULT_STEAL_THRESHOLDS,
        },
        "guest": {
            "description": (
                "(Linux) Time spent running a virtual CPU for guest operating systems "
                "under the control of the Linux kernel."
            ),
            "unit": "percent",
        },
        "ctx_switches": {
            "description": (
                "Number of context switches (voluntary + involuntary) per second. A "
                "context switch is the procedure a CPU follows to change from one task "
                "to another while ensuring the tasks do not conflict."
            ),
            "unit": "number",
            "rate": True,
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "default_thresholds": _DEFAULT_CTX_THRESHOLDS,
            "short_name": "ctx_sw",
        },
        "interrupts": {
            "description": "Number of interrupts per second.",
            "unit": "number",
            "rate": True,
            "short_name": "inter",
        },
        "soft_interrupts": {
            "description": "Number of software interrupts per second. Always 0 on Windows and SunOS.",
            "unit": "number",
            "rate": True,
            "short_name": "sw_int",
        },
        "syscalls": {
            "description": "Number of system calls per second. Always 0 on Linux.",
            "unit": "number",
            "rate": True,
        },
        "cpucore": {
            "description": "Total number of logical CPU cores.",
            "unit": "number",
            "internal": True,
        },
    }

    async def _grab_stats(self) -> dict:
        # Both psutil calls are coalesced through the shared sampler —
        # when the `percpu` plugin is updated in the same scheduler
        # tick, only one psutil sample fires per sub-call. The sampler
        # also guards against psutil's "no baseline yet" first-call
        # behaviour (cf. `_is_unsettled`).
        agg = await sampler.get_aggregate()
        cpu_stats = await sampler.get_stats()

        out: dict[str, Any] = {}
        # cpu_times_percent fields (subset declared in fields_description).
        for name in ("user", "system", "idle", "nice", "iowait", "irq", "steal", "guest", "dpc"):
            if hasattr(agg, name):
                out[name] = getattr(agg, name)

        # `total` = 100 - idle (single source of truth, no double psutil call).
        if "idle" in out:
            out["total"] = round(100.0 - out["idle"], 1)

        # cpu_stats fields — cumulative counters; converted to rates by
        # the base class `_transform_gauge` (rate=True in schema).
        for name in ("ctx_switches", "interrupts", "soft_interrupts", "syscalls"):
            if hasattr(cpu_stats, name):
                out[name] = getattr(cpu_stats, name)

        out["cpucore"] = sampler.cpu_count
        return out
