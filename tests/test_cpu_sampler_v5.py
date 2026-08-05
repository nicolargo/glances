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
import time
from collections import namedtuple
from unittest.mock import patch

import pytest

from glances.cpu_sampler_v5 import CpuSamplerV5

# psutil result stubs ------------------------------------------------------

CpuStats = namedtuple("scpustats", ["ctx_switches", "interrupts", "soft_interrupts", "syscalls"])

CpuTimes = namedtuple(
    "scputimes",
    ["user", "nice", "system", "idle", "iowait", "irq", "softirq", "steal", "guest", "guest_nice"],
)


def _stats(ctx: int = 12_345) -> CpuStats:
    return CpuStats(ctx_switches=ctx, interrupts=2_000, soft_interrupts=1_000, syscalls=0)


def _times(**kw) -> CpuTimes:
    """Cumulative CPU times, in seconds (Linux psutil semantics)."""
    return CpuTimes(**dict.fromkeys(CpuTimes._fields, 0.0) | kw)


def _times_stub(aggregate: list, per_core: list):
    """psutil.cpu_times replacement returning a scripted sequence per mode."""

    def stub(percpu: bool = False):
        return per_core.pop(0) if percpu else aggregate.pop(0)

    return stub


def _sum_pct(sample) -> float:
    """Sum the percentage fields the way psutil defines the total: on Linux
    `guest`/`guest_nice` are already counted inside `user`/`nice`."""
    return sum(getattr(sample, f) for f in sample._fields if f not in ("guest", "guest_nice"))


# ---------------------------------------------------------- aggregate cache


async def test_aggregate_call_is_cached_within_ttl():
    sampler = CpuSamplerV5(ttl=10.0)
    with patch("glances.cpu_sampler_v5.psutil.cpu_times", return_value=_times(user=1.0, idle=3.0)) as m:
        a = await sampler.get_aggregate()
        b = await sampler.get_aggregate()
    assert a is b
    assert m.call_count == 1  # second call hit the cache


async def test_aggregate_call_refreshes_after_ttl():
    sampler = CpuSamplerV5(ttl=0.01)
    with patch("glances.cpu_sampler_v5.psutil.cpu_times", return_value=_times(user=1.0, idle=3.0)) as m:
        await sampler.get_aggregate()
        await asyncio.sleep(0.02)
        await sampler.get_aggregate()
    assert m.call_count == 2  # cache expired


# ---------------------------------------------------------- per-core cache


async def test_per_core_call_is_cached_within_ttl():
    sampler = CpuSamplerV5(ttl=10.0)
    cores = [_times(user=1.0, idle=3.0) for _ in range(4)]
    with patch("glances.cpu_sampler_v5.psutil.cpu_times", return_value=cores) as m:
        a = await sampler.get_per_core()
        b = await sampler.get_per_core()
    assert a is b
    assert m.call_count == 1


async def test_aggregate_and_per_core_are_independent_calls():
    """Two different psutil calls — both must fire when caches are cold."""
    sampler = CpuSamplerV5(ttl=10.0)

    def stub(*args, **kwargs):
        return [_times(user=1.0, idle=3.0)] * 2 if kwargs.get("percpu") else _times(user=1.0, idle=3.0)

    with patch("glances.cpu_sampler_v5.psutil.cpu_times", side_effect=stub) as m:
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
        return _times(user=1.0, idle=3.0)

    with patch("glances.cpu_sampler_v5.psutil.cpu_times", side_effect=stub):
        # Fire two concurrent gets — both should land within the TTL window;
        # the lock serialises them so only one psutil sample is performed.
        results = await asyncio.gather(sampler.get_aggregate(), sampler.get_aggregate())
    assert call_count["n"] == 1
    assert results[0] is results[1]


# ---------------------------------------------------------- delta arithmetic


async def test_aggregate_percentages_are_computed_from_cpu_times_deltas():
    """The sampler must derive percentages from its own cpu_times snapshots.

    The window is deliberately sub-second: psutil's own `cpu_times_percent`
    cannot produce these values over such a window (see the next test), so this
    also pins *who* does the arithmetic."""
    prime, later = _times(), _times(user=0.05, idle=0.15)
    with patch("glances.cpu_sampler_v5.psutil.cpu_times", side_effect=_times_stub([prime, later], [[], []])):
        sampler = CpuSamplerV5(ttl=10.0)
        actual = await sampler.get_aggregate()

    assert actual.user == 25.0
    assert actual.idle == 75.0


async def test_percentages_are_exact_over_a_sub_second_window():
    """Regression: psutil's `scale = 100 / max(1, all_delta)` treats `all_delta`
    as ticks while Linux reports seconds, so a per-core window shorter than 1 s
    is under-scaled *linearly* (0.25 s → values at 25 % of the truth). Computing
    the deltas ourselves has no such floor."""
    prime, later = _times(), _times(user=0.05, idle=0.20)  # a 0.25 s window
    with patch("glances.cpu_sampler_v5.psutil.cpu_times", side_effect=_times_stub([prime, later], [[], []])):
        sampler = CpuSamplerV5(ttl=10.0)
        actual = await sampler.get_aggregate()

    assert actual.user == 20.0
    assert actual.idle == 80.0
    assert _sum_pct(actual) == pytest.approx(100.0)


async def test_linux_guest_time_is_excluded_from_the_total():
    """On Linux guest time is already accounted inside `user`, so psutil
    subtracts it from the total — we must too, or every field is under-scaled."""
    prime, later = _times(), _times(user=1.0, guest=0.4, idle=1.0)
    with (
        patch("glances.cpu_sampler_v5.psutil.LINUX", True),
        patch("glances.cpu_sampler_v5.psutil.cpu_times", side_effect=_times_stub([prime, later], [[], []])),
    ):
        sampler = CpuSamplerV5(ttl=10.0)
        actual = await sampler.get_aggregate()

    # total = (1.0 + 0.4 + 1.0) - 0.4 = 2.0
    assert actual.user == 50.0
    assert actual.idle == 50.0


async def test_non_linux_total_keeps_guest_time():
    prime, later = _times(), _times(user=1.0, guest=0.4, idle=1.0)
    with (
        patch("glances.cpu_sampler_v5.psutil.LINUX", False),
        patch("glances.cpu_sampler_v5.psutil.cpu_times", side_effect=_times_stub([prime, later], [[], []])),
    ):
        sampler = CpuSamplerV5(ttl=10.0)
        actual = await sampler.get_aggregate()

    # total = 2.4 → user = 100 * 1.0 / 2.4
    assert actual.user == 41.7


async def test_decreasing_counter_is_clamped_to_zero():
    """CPU times can go backwards (psutil issues #392/#645/#1210). A negative
    delta must be trimmed, not propagated as a negative percentage."""
    prime = _times(user=5.0, idle=5.0)
    later = _times(user=4.0, idle=6.0)  # user went backwards
    with patch("glances.cpu_sampler_v5.psutil.cpu_times", side_effect=_times_stub([prime, later], [[], []])):
        sampler = CpuSamplerV5(ttl=10.0)
        actual = await sampler.get_aggregate()

    assert actual.user == 0.0
    assert actual.idle == 100.0


async def test_degenerate_window_never_reports_a_busy_cpu():
    """A window too short to contain a single tick yields no usable delta. It
    must not surface as `idle=0` — the cpu plugin maps that to `total=100 %`,
    which is precisely the startup spike this sampler exists to avoid."""
    prime = _times(user=5.0, idle=5.0)
    with patch("glances.cpu_sampler_v5.psutil.cpu_times", side_effect=_times_stub([prime, prime], [[], []])):
        sampler = CpuSamplerV5(ttl=0.0)
        actual = await sampler.get_aggregate()

    assert actual.idle == 100.0
    assert actual.user == 0.0


async def test_degenerate_window_reuses_the_last_good_percentages():
    prime, good = _times(), _times(user=0.5, idle=0.5)
    with patch("glances.cpu_sampler_v5.psutil.cpu_times", side_effect=_times_stub([prime, good, good], [[], [], []])):
        sampler = CpuSamplerV5(ttl=0.0)
        first = await sampler.get_aggregate()
        second = await sampler.get_aggregate()  # identical snapshot → zero delta

    assert first.user == 50.0
    assert second == first


async def test_per_core_percentages_are_computed_per_core():
    prime = [_times(), _times()]
    later = [_times(user=0.05, idle=0.15), _times(user=0.15, idle=0.05)]
    with patch(
        "glances.cpu_sampler_v5.psutil.cpu_times", side_effect=_times_stub([_times(), _times()], [prime, later])
    ):
        sampler = CpuSamplerV5(ttl=10.0)
        actual = await sampler.get_per_core()

    assert [c.user for c in actual] == [25.0, 75.0]
    assert [c.idle for c in actual] == [75.0, 25.0]


async def test_core_count_change_yields_no_bogus_sample():
    """CPU hotplug (or a container cpuset change) makes the two snapshots
    non-comparable — reprime instead of zipping mismatched lists."""
    prime = [_times(), _times()]
    later = [_times(user=1.0, idle=3.0)]  # a core disappeared
    with patch(
        "glances.cpu_sampler_v5.psutil.cpu_times", side_effect=_times_stub([_times(), _times()], [prime, later])
    ):
        sampler = CpuSamplerV5(ttl=10.0)
        actual = await sampler.get_per_core()

    assert len(actual) == 1
    assert actual[0].idle == 100.0  # degenerate fallback, never idle=0


async def test_sampler_never_calls_blocking_cpu_times_percent():
    """The whole point of P2: no `interval > 0` psutil call on any path, so the
    first `quicklook` / `percpu` update cannot block for a second."""
    with patch("glances.cpu_sampler_v5.psutil.cpu_times_percent") as blocking:
        sampler = CpuSamplerV5(ttl=0.0)
        await sampler.get_aggregate()
        await sampler.get_per_core()

    blocking.assert_not_called()


async def test_first_per_core_sample_is_accurate_and_does_not_block():
    """End-to-end against the real psutil: a 0.25 s window must return settled
    per-core percentages without the 1 s blocking recovery."""
    sampler = CpuSamplerV5(ttl=0.0)
    await asyncio.sleep(0.25)

    started = time.monotonic()
    cores = await sampler.get_per_core()
    elapsed = time.monotonic() - started

    assert elapsed < 0.2  # the old blocking recovery took ~1.0 s
    assert cores
    for core in cores:
        assert _sum_pct(core) == pytest.approx(100.0, abs=1.5)


# ---------------------------------------------------------- module singleton


def test_module_level_singleton_exists():
    """The module exposes a shared instance for cpu and percpu plugins."""
    from glances.cpu_sampler_v5 import sampler

    assert isinstance(sampler, CpuSamplerV5)
