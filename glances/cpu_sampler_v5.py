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

    async def get_aggregate(self) -> Any:
        """System-wide ``cpu_times_percent`` (cached over ``ttl``)."""
        async with self._lock:
            if self._is_fresh(self._aggregate_ts) and self._aggregate is not None:
                return self._aggregate
            self._aggregate = await asyncio.to_thread(psutil.cpu_times_percent, interval=0.0)
            self._aggregate_ts = time.monotonic()
            return self._aggregate

    # ----------------------------------------------------------- per-core

    async def get_per_core(self) -> list[Any]:
        """Per-core ``cpu_times_percent`` (cached over ``ttl``)."""
        async with self._lock:
            if self._is_fresh(self._per_core_ts) and self._per_core:
                return self._per_core
            self._per_core = await asyncio.to_thread(psutil.cpu_times_percent, interval=0.0, percpu=True)
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
