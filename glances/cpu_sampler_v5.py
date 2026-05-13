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

Concurrent samplers are serialised under an `asyncio.Lock` so two
parallel plugin updates can't trigger two psutil calls for the same
sub-sample.

Public API (consumed by `cpu/model_v5.py` and `percpu/model_v5.py`):

- ``await sampler.get_aggregate()``  -> psutil cpu_times_percent (system-wide)
- ``await sampler.get_per_core()``   -> list[psutil cpu_times_percent] (per core)
- ``await sampler.get_stats()``      -> psutil cpu_stats (counters)
- ``sampler.cpu_count``               -> int (logical core count, cached forever)

Module-level singleton ``sampler`` exposed for shared access; tests
instantiate `CpuSamplerV5` directly with their own TTL.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import psutil

DEFAULT_TTL_SECONDS = 1.0


class CpuSamplerV5:
    """TTL-coalesced wrapper around psutil CPU sampling calls."""

    def __init__(self, ttl: float = DEFAULT_TTL_SECONDS) -> None:
        self._ttl = ttl
        self._lock = asyncio.Lock()

        self._aggregate: Any | None = None
        self._aggregate_ts: float = 0.0

        self._per_core: list[Any] = []
        self._per_core_ts: float = 0.0

        self._stats: Any | None = None
        self._stats_ts: float = 0.0

        self._cpu_count: int | None = None

    # ----------------------------------------------------------- helpers

    def _is_fresh(self, ts: float) -> bool:
        return ts > 0 and (time.monotonic() - ts) < self._ttl

    # ----------------------------------------------------------- aggregate

    @staticmethod
    def _is_unsettled(sample: Any) -> bool:
        """Detect a psutil sample taken before its baseline is built.

        ``psutil.cpu_times_percent(interval=0.0)`` returns ``0.0`` for
        every field on the very first call (no anchor). The next few
        calls — until enough wall time has elapsed since the anchor —
        return partial samples that don't sum to ~100% (typical
        signature: ``idle≈1.0, every other field == 0.0``). Cache-ing
        such a sample would propagate the "100% CPU spike" for a full
        TTL window after startup.

        Heuristic: a settled cpu_times_percent sample sums to roughly
        100%. Below 50% means no real baseline yet.
        """
        names = ("user", "system", "idle", "nice", "iowait", "irq", "softirq", "steal", "guest", "dpc")
        total = 0.0
        for n in names:
            v = getattr(sample, n, 0.0)
            if isinstance(v, (int, float)):
                total += float(v)
        return total < 50.0

    async def _fetch_aggregate(self, percpu: bool = False) -> Any:
        """Pull a psutil sample; if it looks unsettled, sleep briefly and
        retry once. Caller is responsible for holding ``self._lock``."""
        result = await asyncio.to_thread(psutil.cpu_times_percent, interval=0.0, percpu=percpu)
        first = result[0] if (percpu and result) else result
        if first is not None and self._is_unsettled(first):
            # Give psutil's anchor enough wall time to register a real
            # delta on the next call. 50 ms is comfortably above the
            # ~1 ms granularity below which psutil reports all zeros and
            # imperceptible to the user at startup.
            await asyncio.sleep(0.05)
            result = await asyncio.to_thread(psutil.cpu_times_percent, interval=0.0, percpu=percpu)
        return result

    async def get_aggregate(self) -> Any:
        """System-wide ``cpu_times_percent`` (cached over ``ttl``)."""
        async with self._lock:
            if self._is_fresh(self._aggregate_ts) and self._aggregate is not None:
                return self._aggregate
            self._aggregate = await self._fetch_aggregate(percpu=False)
            self._aggregate_ts = time.monotonic()
            return self._aggregate

    # ----------------------------------------------------------- per-core

    async def get_per_core(self) -> list[Any]:
        """Per-core ``cpu_times_percent`` (cached over ``ttl``)."""
        async with self._lock:
            if self._is_fresh(self._per_core_ts) and self._per_core:
                return self._per_core
            self._per_core = await self._fetch_aggregate(percpu=True)
            self._per_core_ts = time.monotonic()
            return self._per_core

    # ----------------------------------------------------------- counters

    async def get_stats(self) -> Any:
        """``psutil.cpu_stats()`` — context switches, interrupts, etc."""
        async with self._lock:
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
