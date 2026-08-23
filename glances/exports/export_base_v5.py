#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — base class for export modules (architecture §7).

The v5 counterpart of v4's ``glances/exports/export.py``. Three
responsibilities:

1. **Config access** — ``load_conf()`` reads an exporter's section from
   ``GlancesConfigV5``, mirroring the v4 helper of the same name.
2. **Wire format** — ``build_export()`` and ``normalize_for_influxdb()``
   are ported verbatim from v4 so that field names reaching a backend are
   unchanged. Users' dashboards are keyed on those names.
3. **Payload preparation** — two v5-specific steps the v4 code did not
   need: injecting the ``key`` field (v5 store payloads do not carry one)
   and merging the plugin's config section as flat limits.

``update()`` and ``export()`` are SYNCHRONOUS on purpose. Every backend
client is blocking (file IO, influxdb-client, prometheus-client), so the
coroutine boundary lives one level up: ``AsyncScheduler._export_loop()``
calls ``await asyncio.to_thread(exporter.update, plugins)`` once per
exporter per tick. Architecture §7.3 promises an async ``update()``; that
promise is superseded by design §4.2 — an ``async def`` whose body is
entirely blocking would still need a finer-grained ``to_thread`` for no
gain.
"""

from __future__ import annotations

import re
import threading
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

from glances.globals import json_dumps
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5
    from glances.plugins.plugin.base_v5 import GlancesPluginBase

# Hard-coded fallback, matching the scheduler's own. Used only when neither
# [export] refresh nor [global] refresh is set. Not imported from
# glances.scheduler_v5 — a copy lives there too, kept separate on purpose so
# the scheduler does not need a module-top `import glances.exports`, which
# would add fastapi/uvicorn-adjacent import cost to TUI startup.
_DEFAULT_REFRESH_TIME = 2.0


def resolve_export_refresh(config: GlancesConfigV5, global_refresh: float | None = None) -> float:
    """Resolve `[export] refresh`, floored at the global refresh.

    Exporting faster than the plugins are polled duplicates points in the
    backend without adding information, so a lower value is clamped up
    rather than honoured. Absent key → the global cadence, which is v4's
    effective behaviour (v4 exports once per collection cycle).

    `global_refresh` lets the scheduler pass the value it already resolved
    through its own `refresh` / `refresh_time` precedence chain. Callers
    outside the scheduler omit it and get the same chain applied here.
    """
    if global_refresh is None:
        global_refresh = _DEFAULT_REFRESH_TIME
        for key in ("refresh", "refresh_time"):
            try:
                candidate = float(config.get("global", key, -1.0))
            except (TypeError, ValueError):
                continue
            if candidate > 0:
                global_refresh = candidate
                break

    try:
        value = float(config.get("export", "refresh", -1.0))
    except (TypeError, ValueError):
        return global_refresh
    if value <= 0:
        return global_refresh
    if value < global_refresh:
        logger.warning(
            "[export] refresh=%s is faster than the global refresh (%s) — clamped to %s",
            value,
            global_refresh,
            global_refresh,
        )
        return global_refresh
    return value


class GlancesExportBase(ABC):
    """Base class every v5 export module derives from."""

    export_name: ClassVar[str] = ""
    """Short identifier — "csv", "influxdb2". Matches the directory suffix
    (``glances/exports/glances_<export_name>/``) and the CLI token accepted
    by ``--export``."""

    # Set by InfluxDB-family subclasses via load_conf(); read by normalize_for_influxdb().
    tags: str | None = None
    hostname: str | None = None

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        self.config = config
        self.args = args

        # Mandatory for most export modules; subclasses overwrite via load_conf().
        self.host: Any = None
        self.port: Any = None

        # Common [export] section (v4: load_common_conf).
        # GlancesConfigV5 has no get_list_value(); passing a list default
        # routes the raw string through _coerce_list, which splits on commas.
        self.exclude_fields: list[str] = config.get("export", "exclude_fields", []) if config else []

        # Per-plugin flat limits, built once per plugin name (see _limits_for).
        self._limits_cache: dict[str, dict[str, Any]] = {}

        # Serialises update() against exit(). The scheduler cancels the
        # export task while it may be suspended at
        # `await asyncio.to_thread(exporter.update, plugins)` — cancellation
        # raises CancelledError at the await point but does not stop the
        # worker thread already running update(). stop() then calls exit()
        # concurrently. Held in the base, not per-subclass, so every future
        # exporter inherits the protection (see update()/exit() docstrings).
        self._lifecycle_lock = threading.Lock()

        logger.debug("Init v5 export module %s", self.export_name or type(self).__name__)

    # ------------------------------------------------------------- config

    def load_conf(
        self,
        section: str,
        mandatories: tuple[str, ...] = ("host", "port"),
        options: tuple[str, ...] = (),
    ) -> bool:
        """Load ``[section]`` into instance attributes.

        Returns False when the section is missing or a mandatory key is
        absent — a deliberate strengthening over v4, which silently continued
        with missing mandatories as None. The caller treats False as fatal
        (design §8).

        An optional key that is absent leaves the subclass's own default in
        place; it is NOT set to None.
        """
        if self.config is None or not self.config.has_section(section):
            logger.error("No %s configuration found", section)
            return False

        for opt in mandatories:
            value = self.config.get_value(section, opt)
            if value is None:
                logger.error("Error in the %s configuration (missing option %r)", section, opt)
                return False
            setattr(self, opt, value)

        for opt in options:
            value = self.config.get_value(section, opt)
            if value is not None:
                setattr(self, opt, value)

        logger.debug("Load %s section from the Glances configuration file", section)
        return True

    def is_excluded(self, field: str) -> bool:
        """True when `field` matches one of ``[export] exclude_fields``."""
        return any(re.fullmatch(pattern, field, re.I) for pattern in self.exclude_fields)

    @staticmethod
    def parse_tags(tags: str | None) -> dict[str, str]:
        """Parse ``foo:bar,spam:eggs`` into a dict. Returns {} on malformed input."""
        if not tags:
            return {}
        try:
            return dict(x.split(":", 1) for x in tags.split(","))
        except ValueError:
            logger.info("Invalid tags passed: %s", tags)
            return {}

    # --------------------------------------------------------- wire format

    def build_export(self, stats: dict | list) -> tuple[list[str], list[Any]]:
        """Flatten a payload into parallel (names, values) lists.

        Ported verbatim from v4 ``GlancesExport.build_export``. Behaviour
        that looks like an oversight but is not:

        - the dict is NOT sorted — sorting broke several exporters (#3449);
        - booleans become the JSON strings "true"/"false", not 0/1;
        - a list value is joined with spaces rather than expanded.

        For a collection item, ``stats["key"]`` names the field holding the
        item's identity, and its VALUE becomes the ``<value>.`` prefix.
        ``GlancesExportBase._inject_key()`` puts that field there — v5 store
        payloads do not carry one.
        """
        export_names: list[str] = []
        export_values: list[Any] = []

        if isinstance(stats, dict):
            if "key" in stats and stats["key"] in stats:
                pre_key = "{}.".format(stats[stats["key"]])
            else:
                pre_key = ""
            for key, value in stats.items():
                key = str(key).lower()
                if isinstance(value, bool):
                    value = json_dumps(value).decode()
                if isinstance(value, list):
                    value = " ".join([str(v) for v in value])
                if isinstance(value, dict):
                    item_names, item_values = self.build_export(value)
                    item_names = [pre_key + key + str(i) for i in item_names]
                    export_names += item_names
                    export_values += item_values
                else:
                    if self.is_excluded(pre_key + key):
                        continue
                    export_names.append(pre_key + key)
                    export_values.append(value)
        elif isinstance(stats, list):
            for item in stats:
                item_names, item_values = self.build_export(item)
                export_names += item_names
                export_values += item_values

        return export_names, export_values

    def normalize_for_influxdb(self, name: str, columns: list[str], points: list[Any]) -> list[dict[str, Any]]:
        """Convert flattened stats into InfluxDB measurements.

        Ported verbatim from v4 ``GlancesExport.normalize_for_influxdb``.
        Requires the subclass to define ``self.tags`` and ``self.hostname``.
        """
        ret: list[dict[str, Any]] = []

        # Converted to tags to avoid InfluxDB type mismatches and to allow filtering.
        FIELD_TO_TAG = ["name", "cmdline", "type"]
        # The AMP 'result' field is a string or a number depending on the AMP (#3419).
        FIELD_TO_STRING = ["result"]

        data_dict = dict(zip(columns, points))

        # issue1871 — a '<x>.key' column marks '<x>' as a measurement identity.
        keys_list = [k.split(".")[0] for k in columns if k.endswith(".key")]
        if not keys_list:
            keys_list = [None]

        for measurement in keys_list:
            if measurement is not None:
                fields = {
                    k.replace(f"{measurement}.", ""): data_dict[k] for k in data_dict if k.startswith(f"{measurement}.")
                }
            else:
                fields = data_dict
            for k in fields:
                if fields[k] is None:
                    continue
                try:
                    fields[k] = float(fields[k])
                except (TypeError, ValueError):
                    try:
                        fields[k] = str(fields[k])
                    except (TypeError, ValueError):
                        pass
                if k in FIELD_TO_STRING:
                    fields[k] = str(fields[k])
            tags = self.parse_tags(self.tags)
            tags["hostname"] = self.hostname
            if "hostname" in fields:
                fields.pop("hostname")
            if "key" in fields and fields["key"] in fields:
                tags[fields["key"]] = str(fields[fields["key"]])
                fields.pop(fields["key"])
            for k in FIELD_TO_TAG:
                if k in fields:
                    tags[k] = str(fields[k])
                    fields.pop(k)
            ret.append({"measurement": name, "tags": tags, "fields": fields})
        return ret

    # ---- payload preparation (v5-specific)

    # Config keys that are command templates, never metrics. Excluded from
    # the exported payload — see design §5.4. v4 exported them in clear text.
    _ACTION_KEY_MARKER = "_action"

    # v4 default: 3 points per second for one day.
    _DEFAULT_HISTORY_SIZE = 28800.0

    def _inject_key(self, plugin: GlancesPluginBase, payload: dict | list) -> dict | list:
        """Add the ``key`` field v4 payloads carried and v5 payloads do not.

        v4's ``build_export`` reads ``stats["key"]`` to learn which field
        holds an item's identity: it builds the ``<value>.`` prefix from it
        (``eth0.rx``) and emits a ``<value>.key`` column that
        ``normalize_for_influxdb`` uses to decide which fields become tags.

        v5 store payloads have no such field — the primary key is declared
        in ``fields_description`` (``primary_key: True``) and resolved into
        ``plugin._primary_key``. Without this injection, every interface's
        ``rx`` collapses onto a single unprefixed series and InfluxDB
        tagging degrades to hostname-only.

        Scalar plugins have no primary key and are returned unchanged.
        """
        primary_key = getattr(plugin, "_primary_key", None)
        if not primary_key or not isinstance(payload, list):
            return payload
        return [{**item, "key": primary_key} for item in payload]

    def _limits_for(self, plugin: GlancesPluginBase) -> dict[str, Any]:
        """Return the plugin's config section flattened v4-style.

        Shape: ``{"<plugin>_<option>": float | list[str]}`` plus
        ``history_size`` from ``[global]`` — the exact shape v4 builds in
        ``GlancesPluginModel.load_limits`` and merges into the exported
        payload, so field names reaching a backend are unchanged.

        Two departures from v4:

        - keys containing ``_action`` are skipped (design §5.4): they hold
          shell commands and Mustache templates, never measurements;
        - the result is cached per plugin name — the config does not change
          between ticks.

        This lives in the export layer, not on the plugin: the flat
        ``<plugin>_<key>`` form is an output-format convention. The plugin's
        own ``get_limits()`` answers a different question (effective
        thresholds, structured) for the REST API and MCP; the two must not
        be unified.

        The cache lives for the process's lifetime — nothing currently
        invalidates it. v5 has no config hot-reload story yet; if one ever
        lands, it must clear ``self._limits_cache``, or a changed threshold
        would keep exporting its stale value.
        """
        cached = self._limits_cache.get(plugin.plugin_name)
        if cached is not None:
            return cached

        limits: dict[str, Any] = {
            "history_size": self.config.get_float_value("global", "history_size", self._DEFAULT_HISTORY_SIZE)
        }

        for option, _ in self.config.items(plugin.plugin_name):
            if self._ACTION_KEY_MARKER in option:
                continue
            name = f"{plugin.plugin_name}_{option}"
            try:
                limits[name] = self.config.get_float_value(plugin.plugin_name, option)
            except ValueError:
                raw = self.config.get_value(plugin.plugin_name, option)
                limits[name] = str(raw).split(",")

        self._limits_cache[plugin.plugin_name] = limits
        return limits

    def _merge_limits(self, plugin: GlancesPluginBase, payload: dict | list) -> dict | list:
        """Merge the flat limits into the payload, v4-style.

        ``<plugin>_disable`` is dropped, as v4 does — it describes the
        plugin's activation, not its measurements.
        """
        limits = dict(self._limits_for(plugin))
        limits.pop(f"{plugin.plugin_name}_disable", None)

        if isinstance(payload, list):
            return [{**item, **limits} for item in payload]
        return {**payload, **limits}

    # ---------------------------------------------------------- lifecycle

    def update(self, plugins: list[GlancesPluginBase]) -> None:
        """Export every exportable plugin's current stats. One tick's work.

        Called from ``AsyncScheduler._export_loop()`` inside a worker thread
        — this method and everything it calls may block.

        The registry arrives unfiltered: filtering on ``EXPORTABLE`` happens
        here, once, so the scheduler needs no knowledge of what an exporter
        cares about. Disabled plugins are already absent — ``discover_plugins()``
        never instantiates them.

        One plugin failing must not cost the others their tick, so each is
        guarded individually — the same isolation rule the plugin loop and
        the alerts ingest already follow.

        Holds ``self._lifecycle_lock`` for the whole call so a concurrent
        ``exit()`` (``AsyncScheduler.stop()`` after cancelling the export
        task) blocks until this tick finishes rather than tearing down
        backend resources — e.g. closing a file handle — while this thread
        is still writing to them.
        """
        with self._lifecycle_lock:
            for plugin in plugins:
                if not getattr(plugin, "EXPORTABLE", True):
                    continue
                try:
                    payload = plugin.get_export()
                    if not payload:
                        # Plugin registered but has not published yet (cycle 0),
                        # or genuinely empty (no container running). Nothing to send.
                        continue
                    payload = self._inject_key(plugin, payload)
                    payload = self._merge_limits(plugin, payload)
                    names, values = self.build_export(payload)
                    self.export(plugin.plugin_name, names, values)
                except Exception as e:
                    logger.warning(
                        "Export %s: plugin %s failed (%s)",
                        self.export_name,
                        plugin.plugin_name,
                        e,
                    )

    @abstractmethod
    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        """Write one plugin's flattened stats to the backend."""

    def exit(self) -> None:
        """Release backend resources. Called from ``AsyncScheduler.stop()``.

        Takes ``self._lifecycle_lock`` before doing anything, so a call
        arriving while ``update()`` is still running in its worker thread
        blocks until that tick completes — see ``update()``'s docstring for
        why this matters. A subclass overriding ``exit()`` to close its own
        backend resources gets this protection only by calling
        ``super().exit()`` FIRST, before its own teardown: acquiring and
        releasing the lock there is a barrier that waits for any in-flight
        ``update()`` to finish. Since the scheduler cancels the export task
        before ``stop()`` invokes ``exit()``, no new ``update()`` call can
        start once that barrier has passed, so the subclass's own teardown
        is then safe to run unprotected. A subclass that forgets to call
        ``super().exit()`` gets no protection at all.
        """
        with self._lifecycle_lock:
            logger.debug("Finalise v5 export interface %s", self.export_name)
