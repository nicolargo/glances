#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 stats store.

Single shared key/value container holding the latest stats produced by each
plugin. Architecture decision §1.3:

- Writes are serialised by an `asyncio.Lock` and only happen via `set()`.
- Reads are **lockless** — TUI thread, REST API, and exporters call `get()`
  / `as_dict()` without acquiring anything. This is safe because:
    1. The store always *replaces* a top-level key (never mutates a sub-dict
       in place), so a reader sees either the old value or the new one,
       never a partially-updated structure.
    2. `dict[key] = value` and `dict.get(key)` are single bytecode operations
       in CPython, atomic under the GIL.

  If CPython ever drops the GIL or changes either guarantee, reads will need
  to acquire the lock.

Pub/sub and `subscribe()` are intentionally not provided — they will be
added when a real consumer needs them, not before (no dead code).
"""

from __future__ import annotations

import asyncio
from typing import TypeVar

T = TypeVar("T")

PluginData = dict | list


class StatsStoreV5:
    """Async-write / lockless-read store for plugin stats."""

    def __init__(self) -> None:
        self._data: dict[str, PluginData] = {}
        self._lock = asyncio.Lock()

    async def set(self, plugin_name: str, data: PluginData) -> None:
        """Replace the stored value for `plugin_name`.

        Always a top-level reassignment, never an in-place mutation — this is
        what keeps `get()` lockless under the GIL.
        """
        if not isinstance(data, (dict, list)):
            raise TypeError(f"StatsStoreV5 only accepts dict or list, got {type(data).__name__}")
        async with self._lock:
            self._data[plugin_name] = data

    def get(self, plugin_name: str, default: T = None) -> PluginData | T:
        """Return the stored value for `plugin_name`, or `default` if absent.

        Lockless. Safe to call from any thread or coroutine.
        """
        return self._data.get(plugin_name, default)

    def keys(self) -> list[str]:
        """Return the list of plugin names currently in the store."""
        return list(self._data.keys())

    def as_dict(self) -> dict[str, PluginData]:
        """Return a shallow copy of the full store.

        Shallow copy: mutating the returned dict's structure (adding/removing
        keys) does not affect the store, but mutating a referenced sub-value
        would. Consumers must treat the returned values as read-only.
        """
        return dict(self._data)
