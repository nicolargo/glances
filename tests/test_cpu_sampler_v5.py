#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for `cpu_sampler_v5`."""

from __future__ import annotations

import asyncio
from collections import namedtuple
from unittest.mock import patch

from glances.cpu_sampler_v5 import CpuSamplerV5

# psutil result stubs ------------------------------------------------------

CpuTimesPercent = namedtuple(
    "scputimes_percent",
    ["user", "system", "idle", "nice", "iowait", "irq", "softirq", "steal", "guest", "guest_nice"],
)

CpuStats = namedtuple("scpustats", ["ctx_switches", "interrupts", "soft_interrupts", "syscalls"])


def _agg(idle: float = 70.0) -> CpuTimesPercent:
    return CpuTimesPercent(
        user=10.0,
        system=15.0,
        idle=idle,
        nice=0.5,
        iowait=2.0,
        irq=0.1,
        softirq=0.1,
        steal=0.0,
        guest=0.0,
        guest_nice=0.0,
    )


def _per_core(n: int = 2) -> list[CpuTimesPercent]:
    return [_agg(idle=70.0 + i) for i in range(n)]


def _stats(ctx: int = 12_345) -> CpuStats:
    return CpuStats(ctx_switches=ctx, interrupts=2_000, soft_interrupts=1_000, syscalls=0)


# ---------------------------------------------------------- aggregate cache


async def test_aggregate_call_is_cached_within_ttl():
    sampler = CpuSamplerV5(ttl=10.0)
    with patch("glances.cpu_sampler_v5.psutil.cpu_times_percent", return_value=_agg()) as m:
        a = await sampler.get_aggregate()
        b = await sampler.get_aggregate()
    assert a is b
    assert m.call_count == 1  # second call hit the cache


async def test_aggregate_call_refreshes_after_ttl():
    sampler = CpuSamplerV5(ttl=0.01)
    with patch("glances.cpu_sampler_v5.psutil.cpu_times_percent", return_value=_agg()) as m:
        await sampler.get_aggregate()
        await asyncio.sleep(0.02)
        await sampler.get_aggregate()
    assert m.call_count == 2  # cache expired


# ---------------------------------------------------------- per-core cache


async def test_per_core_call_is_cached_within_ttl():
    sampler = CpuSamplerV5(ttl=10.0)
    with patch("glances.cpu_sampler_v5.psutil.cpu_times_percent", return_value=_per_core(4)) as m:
        a = await sampler.get_per_core()
        b = await sampler.get_per_core()
    assert a is b
    assert m.call_count == 1


async def test_aggregate_and_per_core_are_independent_calls():
    """Two different psutil calls — both must fire when caches are cold."""
    sampler = CpuSamplerV5(ttl=10.0)

    def stub(*args, **kwargs):
        return _per_core(2) if kwargs.get("percpu") else _agg()

    with patch("glances.cpu_sampler_v5.psutil.cpu_times_percent", side_effect=stub) as m:
        await sampler.get_aggregate()
        await sampler.get_per_core()
    # Two distinct psutil calls — one for aggregate, one for percpu.
    assert m.call_count == 2


# ---------------------------------------------------------- cpu_stats cache


async def test_stats_call_is_cached_within_ttl():
    sampler = CpuSamplerV5(ttl=10.0)
    with patch("glances.cpu_sampler_v5.psutil.cpu_stats", return_value=_stats()) as m:
        await sampler.get_stats()
        await sampler.get_stats()
    assert m.call_count == 1


# ---------------------------------------------------------- cpu_count


def test_cpu_count_is_lazy_and_cached():
    sampler = CpuSamplerV5()
    with patch("glances.cpu_sampler_v5.psutil.cpu_count", return_value=8) as m:
        assert sampler.cpu_count == 8
        assert sampler.cpu_count == 8
    assert m.call_count == 1  # cached forever


def test_cpu_count_falls_back_to_one_when_psutil_returns_none():
    sampler = CpuSamplerV5()
    with patch("glances.cpu_sampler_v5.psutil.cpu_count", return_value=None):
        assert sampler.cpu_count == 1


def test_cpu_count_falls_back_to_one_on_exception():
    sampler = CpuSamplerV5()
    with patch("glances.cpu_sampler_v5.psutil.cpu_count", side_effect=RuntimeError):
        assert sampler.cpu_count == 1


# ---------------------------------------------------------- concurrency


async def test_concurrent_aggregate_calls_only_sample_once():
    """Two parallel callers within TTL must not duplicate the psutil call."""
    sampler = CpuSamplerV5(ttl=10.0)
    call_count = {"n": 0}

    def stub(*args, **kwargs):
        call_count["n"] += 1
        return _agg()

    with patch("glances.cpu_sampler_v5.psutil.cpu_times_percent", side_effect=stub):
        # Fire two concurrent gets — both should land within the TTL window;
        # the lock serialises them so only one psutil sample is performed.
        results = await asyncio.gather(sampler.get_aggregate(), sampler.get_aggregate())
    assert call_count["n"] == 1
    assert results[0] is results[1]


# ---------------------------------------------------------- module singleton


def test_module_level_singleton_exists():
    """The module exposes a shared instance for cpu and percpu plugins."""
    from glances.cpu_sampler_v5 import sampler

    assert isinstance(sampler, CpuSamplerV5)


# ---------------------------------------------------------- unsettled-sample guard


def test_is_unsettled_detects_all_zero_sample():
    """psutil returns 0.0 everywhere on the first call (no baseline)."""
    zeroed = _agg(idle=0.0)._replace(user=0.0, system=0.0, nice=0.0, iowait=0.0)
    assert CpuSamplerV5._is_unsettled(zeroed) is True


def test_is_unsettled_detects_partial_first_call():
    """Real-world bug: first call after init returns e.g. idle=1.0 and
    everything else 0.0 — sum ≪ 100 → unsettled."""
    partial = CpuTimesPercent(
        user=0.0,
        system=0.0,
        idle=1.0,
        nice=0.0,
        iowait=0.0,
        irq=0.0,
        softirq=0.0,
        steal=0.0,
        guest=0.0,
        guest_nice=0.0,
    )
    assert CpuSamplerV5._is_unsettled(partial) is True


def test_is_unsettled_accepts_settled_sample():
    """A real sample sums to ~100% across the time-percent fields."""
    settled = _agg(idle=72.5)  # user=10+system=15+idle=72.5+... ≈ 100
    assert CpuSamplerV5._is_unsettled(settled) is False


def _all_zero() -> CpuTimesPercent:
    """The all-zeros sample psutil returns on the very first call (no
    baseline). idle=0 → the cpu plugin would render total=100 %."""
    return CpuTimesPercent(
        user=0.0,
        system=0.0,
        idle=0.0,
        nice=0.0,
        iowait=0.0,
        irq=0.0,
        softirq=0.0,
        steal=0.0,
        guest=0.0,
        guest_nice=0.0,
    )


async def test_fetch_aggregate_recovers_with_blocking_sample_after_unsettled():
    """Regression (#startup-100%): when the non-blocking aggregate sample is
    unsettled, the sampler recovers with a short *blocking* sample
    (``interval > 0``) that psutil guarantees to be settled — so the cpu
    plugin never renders the spurious ``total=100 %`` spike at startup."""
    sampler = CpuSamplerV5(ttl=10.0)
    settled = _agg(idle=72.0)
    calls: list[dict] = []

    def stub(*args, **kwargs):
        calls.append(kwargs)
        # First (non-blocking) call is the unsettled all-zeros artifact;
        # the blocking recovery call returns a real, settled sample.
        return _all_zero() if kwargs.get("interval") == 0.0 else settled

    with patch("glances.cpu_sampler_v5.psutil.cpu_times_percent", side_effect=stub):
        actual = await sampler.get_aggregate()

    assert actual.idle == 72.0  # the settled blocking sample is what we cached
    assert actual.idle != 0.0  # never the all-zeros artifact → never total=100
    # Exactly two calls: the cold non-blocking probe + one blocking recovery.
    assert [c.get("interval") for c in calls] == [0.0, 0.1]
    assert calls[1].get("percpu") is False


async def test_fetch_aggregate_keeps_settled_first_sample():
    """When the first non-blocking sample is already settled, no blocking
    recovery call is made (steady-state hot path stays cheap)."""
    sampler = CpuSamplerV5(ttl=10.0)
    calls: list[dict] = []

    def stub(*args, **kwargs):
        calls.append(kwargs)
        return _agg(idle=72.0)

    with patch("glances.cpu_sampler_v5.psutil.cpu_times_percent", side_effect=stub):
        actual = await sampler.get_aggregate()

    assert actual.idle == 72.0
    assert [c.get("interval") for c in calls] == [0.0]  # single non-blocking call


async def test_fetch_per_core_retries_non_blocking_after_unsettled():
    """Per-core keeps its legacy best-effort retry (brief sleep + one more
    non-blocking sample) — it settles over a couple of refreshes, not via a
    short blocking window."""
    sampler = CpuSamplerV5(ttl=10.0)
    unsettled = [_all_zero(), _all_zero()]
    settled = _per_core(2)
    results = [unsettled, settled]

    def stub(*args, **kwargs):
        return results.pop(0)

    with patch("glances.cpu_sampler_v5.psutil.cpu_times_percent", side_effect=stub):
        with patch("glances.cpu_sampler_v5.asyncio.sleep") as fake_sleep:
            fake_sleep.return_value = None
            actual = await sampler.get_per_core()

    assert actual[0].idle == 70.0  # the settled second sample
    assert results == []  # both samples consumed
    fake_sleep.assert_awaited_once()  # per-core path still sleeps
