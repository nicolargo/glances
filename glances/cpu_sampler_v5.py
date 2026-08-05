#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Coalesced psutil CPU sampler shared between `cpu` and `percpu` plugins.

This is the v5 analogue of v4's `glances/cpu_percent.py` singleton. Two
plugins consume CPU stats — `cpu` (scalar, system-wide aggregate) and
`percpu` (collection, one entry per logical core) — and the asyncio
scheduler updates them independently. Without coalescing each plugin
would call psutil on every cycle, paying the cost twice when the two
plugins refresh at the same time.

The sampler caches each sub-sample (aggregate, per-core, counters) under
a TTL window. Within the TTL, repeated callers receive the cached value
without an additional psutil call. The default TTL is `1.0 s` — short
enough to be transparent at the default `refresh_time = 2 s`, long
enough to absorb cycles fired in the same scheduler tick.

Each sub-sample has its own `asyncio.Lock` so two parallel plugin
updates can't trigger two psutil calls for the same sub-sample.

Percentages are derived from our own `psutil.cpu_times()` snapshots rather
than from `psutil.cpu_times_percent()`. psutil scales a sample with
``100.0 / max(1, all_delta)``, where ``all_delta`` is the summed CPU time of
the window — expressed in *seconds* on Linux, not in ticks as that ``max(1,
…)`` assumes. With ``percpu=True`` the sum covers a single core, so any
window shorter than one second is under-scaled linearly (a 0.5 s window
reports half the real values) and psutil only becomes trustworthy after a
full second. That is what forced the old blocking one-second sample on the
first `quicklook` / `percpu` update, and it also silently under-reported the
system-wide value at startup on 1–2 vCPU hosts (there ``all_delta`` is
``ncpu × window``). Computing the deltas here removes both problems: the
result is exact from a ~0.2 s window and nothing ever blocks.

Public API (consumed by `cpu/model_v5.py` and `percpu/model_v5.py`):

- ``await sampler.get_aggregate()``  -> CPU time percentages (system-wide)
- ``await sampler.get_per_core()``   -> list of CPU time percentages (per core)
- ``await sampler.get_stats()``      -> psutil cpu_stats (counters)
- ``sampler.cpu_count``               -> int (logical core count, cached forever)

Module-level singleton ``sampler`` exposed for shared access; tests
instantiate `CpuSamplerV5` directly with their own TTL.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import psutil

logger = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 1.0

# Fields Linux already accounts for inside `user` / `nice`. psutil subtracts
# them from the window total (`psutil._cpu_tot_time`); so do we, or every
# other field comes out under-scaled on a host running VMs.
_GUEST_FIELDS = ("guest", "guest_nice")


class CpuSamplerV5:
    """TTL-coalesced wrapper around psutil CPU sampling calls."""

    def __init__(self, ttl: float = DEFAULT_TTL_SECONDS) -> None:
        self._ttl = ttl
        # One lock per sub-sample (aggregate / per-core / counters). They guard
        # independent psutil calls and independent cached state, so a slow
        # path must not serialise the others. Each lock still prevents two
        # concurrent callers from duplicating the *same* psutil sub-sample.
        self._aggregate_lock = asyncio.Lock()
        self._per_core_lock = asyncio.Lock()
        self._stats_lock = asyncio.Lock()

        self._aggregate: Any | None = None
        self._aggregate_ts: float = 0.0

        self._per_core: list[Any] = []
        self._per_core_ts: float = 0.0

        self._stats: Any | None = None
        self._stats_ts: float = 0.0

        self._cpu_count: int | None = None

        # Cumulative `cpu_times` snapshots anchoring the next delta window.
        self._prev_aggregate_times: Any | None = None
        self._prev_per_core_times: list[Any] | None = None
        self._prime()

    def _prime(self) -> None:
        """Anchor both delta baselines at construction time.

        v4 does the same at import time (``cpu_percent.CpuPercent.__init__``
        takes a first sample and discards it): by the time the first plugin
        update runs, a real window has already elapsed, so the very first
        frame carries true values instead of a placeholder.

        Guarded: a platform where ``cpu_times`` raises must not break the
        import of this module and take the cpu / percpu / quicklook plugins
        down with it. Without a baseline the first sample falls back to the
        idle placeholder and the one after it is exact.
        """
        try:
            self._prev_aggregate_times = psutil.cpu_times()
            self._prev_per_core_times = psutil.cpu_times(percpu=True)
        except Exception as e:
            logger.debug("CPU sampler: cannot prime the delta baseline (%s)", e)

    # ----------------------------------------------------------- helpers

    def _is_fresh(self, ts: float) -> bool:
        return ts > 0 and (time.monotonic() - ts) < self._ttl

    @staticmethod
    def _percent_from_deltas(previous: Any, current: Any) -> Any | None:
        """Percentages over the ``[previous, current]`` window.

        Same semantics as ``psutil.cpu_times_percent`` — negative deltas
        trimmed to zero (CPU times can go backwards, psutil issues #392 /
        #645 / #1210), guest time excluded from the total on Linux, each
        field clamped to ``[0, 100]`` and rounded to one decimal — minus the
        ``max(1, all_delta)`` clamp that makes psutil wrong below a one-second
        window (see the module docstring).

        Returns ``None`` when the window holds no measurable CPU time, so the
        caller can decide what to serve instead of publishing a bogus sample.
        """
        fields = current._fields
        deltas = [max(0.0, getattr(current, f) - getattr(previous, f)) for f in fields]
        total = sum(deltas)
        if psutil.LINUX:
            total -= sum(deltas[fields.index(f)] for f in _GUEST_FIELDS if f in fields)
        if total <= 0:
            return None
        scale = 100.0 / total
        return current.__class__(*(min(max(0.0, round(d * scale, 1)), 100.0) for d in deltas))

    @staticmethod
    def _idle_sample(template: Any) -> Any:
        """A fully-idle sample shaped like ``template``.

        Only used when no usable window exists yet — no baseline, or two
        snapshots taken inside the same clock tick. Reporting *idle* is the
        safe default here: the all-zeros sample psutil returns in that
        situation has ``idle=0``, which the cpu plugin renders as
        ``total=100 %`` — the spurious startup spike.
        """
        return template.__class__(*(100.0 if f == "idle" else 0.0 for f in template._fields))

    # ----------------------------------------------------------- aggregate

    async def get_aggregate(self) -> Any:
        """System-wide CPU time percentages (cached over ``ttl``)."""
        async with self._aggregate_lock:
            if self._is_fresh(self._aggregate_ts) and self._aggregate is not None:
                return self._aggregate
            current = await asyncio.to_thread(psutil.cpu_times)
            percent = None
            if self._prev_aggregate_times is not None:
                percent = self._percent_from_deltas(self._prev_aggregate_times, current)
            self._prev_aggregate_times = current
            if percent is None:
                percent = self._aggregate if self._aggregate is not None else self._idle_sample(current)
            self._aggregate = percent
            self._aggregate_ts = time.monotonic()
            return self._aggregate

    # ----------------------------------------------------------- per-core

    async def get_per_core(self) -> list[Any]:
        """Per-core CPU time percentages (cached over ``ttl``)."""
        async with self._per_core_lock:
            if self._is_fresh(self._per_core_ts) and self._per_core:
                return self._per_core
            current = await asyncio.to_thread(psutil.cpu_times, percpu=True)
            percent = self._per_core_from_deltas(self._prev_per_core_times, current)
            self._prev_per_core_times = current
            if percent is None:
                percent = self._per_core or [self._idle_sample(core) for core in current]
            self._per_core = percent
            self._per_core_ts = time.monotonic()
            return self._per_core

    @classmethod
    def _per_core_from_deltas(cls, previous: list[Any] | None, current: list[Any]) -> list[Any] | None:
        """Per-core version of ``_percent_from_deltas``.

        A core count change (CPU hotplug, a container cpuset resize) makes the
        two snapshots non-comparable — reprime rather than zip mismatched
        lists onto the wrong cores.
        """
        if previous is None or len(previous) != len(current):
            return None
        out = []
        for prev_core, cur_core in zip(previous, current):
            percent = cls._percent_from_deltas(prev_core, cur_core)
            if percent is None:
                return None
            out.append(percent)
        return out

    # ----------------------------------------------------------- counters

    async def get_stats(self) -> Any:
        """``psutil.cpu_stats()`` — context switches, interrupts, etc."""
        async with self._stats_lock:
            if self._is_fresh(self._stats_ts) and self._stats is not None:
                return self._stats
            self._stats = await asyncio.to_thread(psutil.cpu_stats)
            self._stats_ts = time.monotonic()
            return self._stats

    # ----------------------------------------------------------- core count

    @property
    def cpu_count(self) -> int:
        """Logical core count, cached forever (does not change at runtime)."""
        if self._cpu_count is None:
            try:
                self._cpu_count = psutil.cpu_count(logical=True) or 1
            except Exception:
                self._cpu_count = 1
        return self._cpu_count


# Module-level singleton, consumed by cpu and percpu plugins.
sampler = CpuSamplerV5()
