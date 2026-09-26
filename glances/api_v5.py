#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the Python API.

    >>> from glances import api_v5 as api
    >>> gl = api.GlancesAPI()
    >>> gl.cpu["total"]
    7.7
    >>> gl.network["eth0"]["bytes_recv"]
    3472.0

Design: ``docs/superpowers/specs/2026-09-26-glances-v5-python-api-design.md``.
The v4 API (``glances/api.py``) is left untouched; this module replaces it at
the ``develop-v5 → develop`` merge.

v5's plugins are coroutines, and the caller may already be inside a running
event loop (a Jupyter notebook is), where ``asyncio.run`` refuses to start.
The API therefore owns a private event loop on a daemon thread, in both modes,
and hands every call over to it (design §5.1):

- **on demand** (default): reading ``gl.<plugin>`` updates that plugin, and its
  ``DEPENDS_ON``, when its last update is older than ``[global] refresh``.
  Nothing runs between two reads.
- **background** (``background=True``): the v5 scheduler runs on that loop and
  reads are served from the store.

An API object never acts on the host: alerts are recorded but their configured
actions never run, and no exporter is started (design §5.3).
"""

from __future__ import annotations

import asyncio
import copy
import os
import pprint
import threading
import time
import weakref
from collections.abc import Iterator, Mapping
from types import SimpleNamespace
from typing import Any

from glances.alerts_v5 import GlancesAlerts
from glances.config_v5 import GlancesConfigV5
from glances.globals import auto_unit
from glances.main_v5 import _VERSION, _global_refresh, attach_history, discover_plugin_classes
from glances.outputs.glances_bars import Bar
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.processes import sort_stats
from glances.scheduler_v5 import AsyncScheduler
from glances.stats_store_v5 import StatsStoreV5

# How long `close()` waits for the loop thread and the scheduler.
_SHUTDOWN_TIMEOUT = 5.0


class PluginView(Mapping):
    """A read-only snapshot of one plugin, as it was when it was read (design §5.4).

    A mapping: ``view[key]``, ``get``, ``keys``, ``items``, ``len``, ``in``.
    For a collection plugin the keys are the primary-key values
    (``gl.network["eth0"]``, ``gl.processlist[1234]``, ``gl.fs["/home"]``);
    for a scalar plugin they are the field names.

    Everything it holds is a copy: changing it changes nothing Glances, or a
    later read, sees. Read ``gl.<plugin>`` again for fresh values.

    Attributes:
        name: the plugin name.
        raw: the payload, as ``/api/5/<plugin>`` serves it without its
            ``_``-prefixed metadata (v4 ``get_raw()``).
        fields: the schema, ``fields_description`` (``/api/5/<plugin>/info``).
        limits: the effective thresholds (v4 ``.limits``).
        levels: the alert level of each watched field, ``_levels``.
    """

    def __init__(self, plugin: GlancesPluginBase) -> None:
        self.name: str = plugin.plugin_name
        # The REST view, not `get_export()`: exporters get only the processes
        # matching `[processlist] export`, which is none by default.
        payload = copy.deepcopy(plugin.get_api_payload())
        self.levels: dict[str, Any] = payload.get("_levels", {})
        if plugin.IS_COLLECTION:
            self.raw: dict[str, Any] | list[dict[str, Any]] = payload.get("data", [])
        else:
            self.raw = {k: v for k, v in payload.items() if not k.startswith("_")}
        self.fields: dict[str, dict[str, Any]] = copy.deepcopy(plugin.fields_description)
        self.limits: dict[str, Any] = copy.deepcopy(plugin.get_limits())
        self._plugin = plugin
        if isinstance(self.raw, list):
            key = plugin._primary_key
            self._data: dict[Any, Any] = {
                item[key]: item for item in self.raw if isinstance(item, dict) and key in item
            }
        else:
            self._data = self.raw

    def __getitem__(self, key: Any) -> Any:
        return self._data[key]

    def __iter__(self) -> Iterator[Any]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def keys(self) -> list[Any]:  # type: ignore[override]
        """The keys, as a list (v4 returns a list, not a view)."""
        return list(self._data)

    def history(self, nb: int = 0, field: str | None = None, item: str | None = None) -> dict[str, Any]:
        """The plugin's history, as ``/api/5/<plugin>/history`` serves it.

        Read when called, not when the view was taken. Raises ``KeyError`` for
        a field the plugin does not historise or an item it has no series for.
        """
        return self._plugin.get_history(nb=nb, field=field, item=item)

    def __repr__(self) -> str:
        return pprint.pformat(self._data)


class GlancesAPI:
    """Glances' stats, from Python.

    Args:
        config_path: an extra ``glances.conf``, layered over the usual search
            path (system file, XDG file, ``GLANCES_<SECTION>__<KEY>``), as
            ``-C`` does. ``sys.argv`` is never read.
        background: run the v5 scheduler in a thread, so stats stay fresh and
            the history and alerts fill up between reads. Off by default: then
            a plugin is updated when it is read.
        plugins: build only these plugins (and what they depend on), e.g.
            ``["cpu", "mem"]``. Default: every plugin ``glances.conf`` enables.

    Use it as a context manager, or call ``close()``: some plugins hold
    background resources until then.
    """

    def __init__(
        self,
        config_path: str | None = None,
        background: bool = False,
        plugins: list[str] | None = None,
    ) -> None:
        self.__version__ = _VERSION.split(".")[0]
        self._config = GlancesConfigV5(cli_config_path=config_path)
        self._store = StatsStoreV5()
        self._ttl = _global_refresh(self._config)
        self._background = background
        self._plugins, self._disabled = self._build(plugins)
        attach_history(list(self._plugins.values()), self._config, SimpleNamespace(disable_history=False))
        # No actions: an API object records alerts, it never runs the
        # `<field>_<level>_action` commands of glances.conf (design §5.3).
        self._alerts = GlancesAlerts(self._config, actions={})
        self._updated: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, name="glances-api-v5", daemon=True)
        self._thread.start()
        self._scheduler: AsyncScheduler | None = None
        # Filled once the scheduler exists; the finaliser reads it then.
        self._scheduler_ref: list[AsyncScheduler] = []
        # Registered before the first call into the loop, so that a failure
        # below still gets the thread and the plugins' resources released.
        self._finalizer = weakref.finalize(
            self, _shutdown, self._loop, self._thread, self._plugins.copy(), self._scheduler_ref
        )

        # One full cycle up front, as v4 does, so the first read has rates.
        self._call(self._prime_all())
        if background:
            self._scheduler = AsyncScheduler(self._store, self._config, alerts=self._alerts)
            for plugin in self._plugins.values():
                self._scheduler.register(plugin)
            self._scheduler_ref.append(self._scheduler)
            asyncio.run_coroutine_threadsafe(self._scheduler.run_forever(), self._loop)

    # ------------------------------------------------------------ building

    def _build(self, wanted: list[str] | None) -> tuple[dict[str, GlancesPluginBase], set[str]]:
        """Instantiate the enabled plugins, `wanted` and their `DEPENDS_ON` only if given."""
        classes = {cls.plugin_name: cls for _name, cls in discover_plugin_classes() if cls.plugin_name}
        if wanted is None:
            names = set(classes)
        else:
            unknown = [name for name in wanted if name not in classes]
            if unknown:
                raise ValueError(f"Unknown plugin(s): {', '.join(unknown)}")
            names, todo = set(), list(wanted)
            while todo:
                name = todo.pop()
                if name not in names:
                    names.add(name)
                    todo.extend(classes[name].DEPENDS_ON)
        built: dict[str, GlancesPluginBase] = {}
        disabled: set[str] = set()
        for name in sorted(names):
            if classes[name].is_disabled(self._config):
                disabled.add(name)
                continue
            built[name] = classes[name](self._store, self._config)
        return built, disabled

    # ------------------------------------------------------------- the loop

    def _call(self, coro: Any) -> Any:
        """Run `coro` on the API's loop and wait for its result."""
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    async def _refresh_all(self) -> None:
        for name in self._plugins:
            await self._refresh(name)

    async def _refresh(self, name: str) -> None:
        """Update `name` (dependencies first) unless it is fresher than the TTL.

        Runs on the API's loop only, so creating a lock here is race-free; the
        lock is what makes two threads reading at once trigger one update.
        """
        plugin = self._plugins[name]
        for dependency in plugin.DEPENDS_ON:
            if dependency in self._plugins:
                await self._refresh(dependency)
        lock = self._locks.setdefault(name, asyncio.Lock())
        async with lock:
            last = self._updated.get(name)
            if last is not None and time.monotonic() - last < self._ttl:
                return
            await plugin.update()
            await self._alerts.ingest_plugin(plugin)
            self._updated[name] = time.monotonic()

    async def _prime_all(self) -> None:
        """One update of every plugin, recorded as no update at all.

        So the first read updates again and has a rate to show, whatever the
        TTL: a rate needs two samples. v4 gets the same effect from its empty
        cache.
        """
        await self._refresh_all()
        self._updated.clear()

    # -------------------------------------------------------------- reading

    def __getattr__(self, name: str) -> PluginView:
        # Private names and anything looked up before __init__ finished must
        # not recurse into `self._plugins`.
        if name.startswith("_"):
            raise AttributeError(name)
        plugins = self.__dict__.get("_plugins", {})
        if name in plugins:
            if not self._background:
                self._call(self._refresh(name))
            return PluginView(plugins[name])
        if name in self.__dict__.get("_disabled", set()):
            raise AttributeError(f"Plugin {name!r} is disabled in glances.conf ([{name}] disable)")
        raise AttributeError(f"'{type(self).__name__}' object has no attribute {name!r}")

    def plugins(self) -> list[str]:
        """The plugins this API built (enabled in glances.conf, and in `plugins=` if given)."""
        return sorted(self._plugins)

    def alerts(self) -> list[dict[str, Any]]:
        """The alert events recorded so far, as ``/api/5/alert`` serves them."""

        async def _history() -> list[dict[str, Any]]:
            return self._alerts.get_history()

        return self._call(_history())

    # -------------------------------------------------------------- helpers

    def auto_unit(self, number: Any, low_precision: bool = False, min_symbol: str = "K", none_symbol: str = "-") -> str:
        """A number as a human-readable string with a unit suffix (``6.07G``). Same as v4."""
        return auto_unit(number, low_precision, min_symbol, none_symbol)

    def bar(
        self,
        value: float,
        size: int = 18,
        bar_char: str = "■",
        empty_char: str = "□",
        pre_char: str = "",
        post_char: str = "",
    ) -> str:
        """A percentage as a text bar (``■■□□□□``). Same as v4."""
        b = Bar(
            size, bar_char=bar_char, empty_char=empty_char, pre_char=pre_char, post_char=post_char, display_value=False
        )
        b.percent = value
        return b.get()

    def top_process(
        self, limit: int = 3, sorted_by: str = "cpu_percent", sorted_by_secondary: str = "memory_percent"
    ) -> list[dict[str, Any]]:
        """The top processes, sorted by `sorted_by` then `sorted_by_secondary`.

        Leaves out kernel threads (no command line), as v4 does, and this
        process itself, which is the one reading its own load. v4 matched
        "glances" as a whole argument instead, which missed `/usr/bin/glances`.
        """
        own = os.getpid()
        processes = [p for p in self.processlist.raw if p.get("cmdline") and p.get("pid") != own]
        return sort_stats(processes, sorted_by=sorted_by, sorted_by_secondary=sorted_by_secondary)[:limit]

    # ------------------------------------------------------------ lifecycle

    def close(self) -> None:
        """Stop the scheduler if it runs, release the plugins' resources, stop the loop."""
        self._finalizer()

    def __enter__(self) -> GlancesAPI:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def _shutdown(
    loop: asyncio.AbstractEventLoop,
    thread: threading.Thread,
    plugins: dict[str, GlancesPluginBase],
    scheduler_ref: list[AsyncScheduler],
) -> None:
    """`close()`, and the finaliser of a GlancesAPI nobody closed.

    Takes the objects, never the GlancesAPI itself: a finaliser that held it
    would keep it alive forever.
    """
    if loop.is_running():
        for scheduler in scheduler_ref:
            try:
                asyncio.run_coroutine_threadsafe(scheduler.stop(), loop).result(_SHUTDOWN_TIMEOUT)
            except Exception:  # noqa: S110 -- best effort on the way out
                pass
    for plugin in plugins.values():
        try:
            plugin.stop()
        except Exception:  # noqa: S110 -- best effort on the way out
            pass
    if loop.is_running():
        loop.call_soon_threadsafe(loop.stop)
    thread.join(_SHUTDOWN_TIMEOUT)
    if not loop.is_running():
        loop.close()
