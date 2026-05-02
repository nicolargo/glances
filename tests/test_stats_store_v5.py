#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for StatsStoreV5.

Test stack: pytest + pytest-asyncio (auto mode). See architecture decisions §9.

Coverage:
- Round-trip: set/get for dict and list payloads
- Defaults: missing key returns the supplied default (or None)
- Overwrite: a second set replaces the first
- Introspection: keys() and as_dict() reflect the store; as_dict() is a copy
- Concurrency: writes are serialised by the lock
- Lockless reads: get() does not acquire the lock
- Atomicity: a reader that captured a reference is unaffected by a later set
- Type guard: set() rejects anything other than dict or list
"""

from __future__ import annotations

import asyncio

import pytest

from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


# ---------------------------------------------------------------- round-trip


async def test_set_get_dict(store: StatsStoreV5) -> None:
    payload = {"total": 42.0, "user": 30.0}
    await store.set("cpu", payload)
    assert store.get("cpu") == payload


async def test_set_get_list(store: StatsStoreV5) -> None:
    payload = [{"name": "eth0", "rx": 1024}, {"name": "lo", "rx": 0}]
    await store.set("network", payload)
    assert store.get("network") == payload


# --------------------------------------------------------------- defaults


def test_get_missing_returns_default(store: StatsStoreV5) -> None:
    assert store.get("absent", {"fallback": True}) == {"fallback": True}


def test_get_missing_without_default_returns_none(store: StatsStoreV5) -> None:
    assert store.get("absent") is None


# --------------------------------------------------------------- overwrite


async def test_set_overwrites_previous_value(store: StatsStoreV5) -> None:
    await store.set("cpu", {"total": 10.0})
    await store.set("cpu", {"total": 20.0})
    assert store.get("cpu") == {"total": 20.0}


# --------------------------------------------------------------- introspect


async def test_keys_reflects_inserted_plugins(store: StatsStoreV5) -> None:
    await store.set("cpu", {})
    await store.set("mem", {})
    assert set(store.keys()) == {"cpu", "mem"}


async def test_keys_empty_at_init(store: StatsStoreV5) -> None:
    assert store.keys() == []


async def test_as_dict_is_shallow_copy(store: StatsStoreV5) -> None:
    await store.set("cpu", {"total": 1.0})
    snapshot = store.as_dict()
    snapshot["cpu"] = {"total": 999.0}  # mutate snapshot
    snapshot["new"] = {}  # add a key
    # Internal store is unaffected by snapshot mutation.
    assert store.get("cpu") == {"total": 1.0}
    assert "new" not in store.keys()


def test_as_dict_empty_at_init(store: StatsStoreV5) -> None:
    assert store.as_dict() == {}


# --------------------------------------------------------------- concurrency


async def test_concurrent_writes_serialised(store: StatsStoreV5) -> None:
    """100 concurrent writers must leave the store consistent (last-writer-wins)."""

    async def writer(value: int) -> None:
        await store.set("counter", {"value": value})

    await asyncio.gather(*(writer(i) for i in range(100)))
    final = store.get("counter")
    assert isinstance(final, dict)
    assert 0 <= final["value"] < 100  # one of the writers' values landed


async def test_get_does_not_acquire_lock(store: StatsStoreV5) -> None:
    """While set() is awaiting on the lock, get() must still return immediately."""
    await store.set("cpu", {"total": 1.0})

    # Acquire the lock manually to simulate a long write in progress.
    await store._lock.acquire()
    try:
        # If get() tried to acquire the lock, it would block forever.
        # Use wait_for to enforce the lockless contract with a 1s ceiling.
        result = await asyncio.wait_for(asyncio.to_thread(store.get, "cpu"), timeout=1.0)
        assert result == {"total": 1.0}
    finally:
        store._lock.release()


# --------------------------------------------------------------- atomicity


async def test_set_does_not_mutate_previous_reference(store: StatsStoreV5) -> None:
    """A reader that captured the old value must not see it mutated by a later set."""
    await store.set("cpu", {"total": 1.0})
    captured = store.get("cpu")  # reader holds a reference to the old dict

    await store.set("cpu", {"total": 2.0})  # writer replaces top-level value

    # The captured reference is unchanged; the store reflects the new value.
    assert captured == {"total": 1.0}
    assert store.get("cpu") == {"total": 2.0}


# --------------------------------------------------------------- type guard


@pytest.mark.parametrize("bad_value", [42, "string", 3.14, None, ("tuple",), {1, 2}])
async def test_set_rejects_non_dict_non_list(store: StatsStoreV5, bad_value: object) -> None:
    with pytest.raises(TypeError):
        await store.set("plugin", bad_value)  # type: ignore[arg-type]
