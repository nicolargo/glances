#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 plugin base class.

Generic asynchronous base class for all Glances v5 plugins. Two flavours:

- `GlancesPluginBase[dict]`  — scalar plugins (cpu, mem, load, …)
- `GlancesPluginBase[list]`  — collection plugins (network, fs, containers, …)

The distinction is also carried at runtime by the `IS_COLLECTION` class
attribute (Python erases the `T` type parameter at runtime).

Architecture references:
- §1.3   StatsStore (lockless reads, async-locked writes)
- §3.1   GlancesPluginBase pipeline
- §3.2   fields_description schema
- §3.3   _levels (placeholder until Phase 1 / GlancesAlerts)
- §7.2   get_export() — only access path for exporters

Maximum logic lives in this base class. A concrete plugin only implements
`_grab_stats()` and declares its `plugin_name`, `IS_COLLECTION` and
`fields_description` — every other behaviour has a working default here.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Generic, TypeVar

from glances.config_v5 import GlancesConfigV5
from glances.plugins.plugin.thresholds_v5 import compute_level, read_thresholds
from glances.stats_store_v5 import StatsStoreV5

logger = logging.getLogger(__name__)

T = TypeVar("T", dict, list)

# Metadata fields injected by the base class into every plugin's
# fields_description. Plugins must not redeclare them.
_BASE_METADATA_FIELDS: dict[str, dict[str, Any]] = {
    "time_since_update": {
        "description": "Seconds elapsed since the previous successful update cycle.",
        "unit": "seconds",
        "exportable": False,
    },
}


class GlancesPluginBase(Generic[T], ABC):
    """Generic async base class for Glances v5 plugins."""

    # --- Plugin identity ----------------------------------------------------

    plugin_name: ClassVar[str] = ""
    """Unique plugin identifier (used as StatsStore key and API path)."""

    IS_COLLECTION: ClassVar[bool] = False
    """False for scalar plugins (cpu, mem), True for collection plugins (fs, network)."""

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {}
    """Per-field schema. See architecture §3.2."""

    # ----------------------------------------------------------- construction

    def __init__(self, store: StatsStoreV5, config: GlancesConfigV5) -> None:
        if not self.plugin_name:
            raise ValueError(f"{type(self).__name__} must declare a non-empty plugin_name")

        self.store = store
        self.config = config

        # Merge base-injected metadata fields with the plugin's declarations.
        # Plugin-declared fields win on collision (escape hatch — should not
        # happen, plugins are not supposed to redeclare time_since_update).
        self._fields: dict[str, dict[str, Any]] = {**_BASE_METADATA_FIELDS, **self.fields_description}

        self._stats: T = self._empty_stats()
        self._stats_previous: T | None = None
        # Snapshot of the raw psutil values from the previous successful
        # cycle, kept across `_transform()` runs so `_transform_gauge` can
        # diff cumulative counters. None until the second cycle.
        self._raw_previous: dict[str, Any] | None = None
        self._metadata: dict[str, Any] = {}
        self._levels: dict[str, Any] = {}
        self._last_update_ts: float | None = None

    def _empty_stats(self) -> T:
        return [] if self.IS_COLLECTION else {}  # type: ignore[return-value]

    # ----------------------------------------------------- update pipeline

    async def update(self) -> None:
        """Orchestrate one update cycle.

        Five steps (architecture §3.1). Implemented in the base class and
        **never overridden** by individual plugins. Any exception is
        swallowed with a warning log — the asyncio gather loop must never
        crash because of a single misbehaving plugin.
        """
        try:
            self._stats_previous = self._stats
            self._stats = await self._grab_stats()
            self._validate_stats_type()
            # Snapshot the raw cumulative values now, before _transform mutates
            # them. The next cycle's _transform_gauge will read this snapshot
            # via self._raw_previous to compute counter rates.
            new_raw = self._snapshot_raw()
            self._add_metadata()
            self._transform()
            await self.store.set(self.plugin_name, self._build_store_payload())
            # Promote the snapshot only after a successful cycle so a failed
            # grab can't poison the next rate computation.
            self._raw_previous = new_raw
        except Exception as e:
            logger.warning("Plugin %s update failed: %s", self.plugin_name, e)

    @abstractmethod
    async def _grab_stats(self) -> T:
        """Collect raw stats. Must wrap blocking psutil calls in `asyncio.to_thread`.

        The only mandatory hook for concrete plugins.
        """

    def _validate_stats_type(self) -> None:
        expected = list if self.IS_COLLECTION else dict
        if not isinstance(self._stats, expected):
            raise TypeError(
                f"Plugin {self.plugin_name}: _grab_stats() must return "
                f"{expected.__name__}, got {type(self._stats).__name__}"
            )

    def _add_metadata(self) -> None:
        """Compute global metadata (default: time_since_update)."""
        now = time.monotonic()
        if self._last_update_ts is None:
            self._metadata["time_since_update"] = 0.0
        else:
            self._metadata["time_since_update"] = max(0.0, now - self._last_update_ts)
        self._last_update_ts = now

    def _transform(self) -> None:
        """Run the four-step transformation pipeline (architecture §3.1)."""
        self._transform_gauge()
        self._expand_parameters()
        self._derived_parameters()
        self._remove_parameters()

    def _snapshot_raw(self) -> dict[str, Any] | None:
        """Snapshot the raw scalar payload before `_transform` mutates it.

        Returns None for collection plugins — collection rate computation
        (per-item, indexed by primary key) lands in Phase 1.3.
        """
        if self.IS_COLLECTION:
            return None
        if not isinstance(self._stats, dict):
            return None
        return dict(self._stats)

    # Override hooks ---------------------------------------------------------

    def _transform_gauge(self) -> None:
        """Convert cumulative counter fields to per-second rates.

        Walks every scalar field declared with `rate: True` in the schema
        and replaces the cumulative counter with `(current - previous) / elapsed`.

        Behaviour:
        - First cycle (no `_raw_previous`) or `time_since_update == 0`: the
          rate field is **removed** from the payload — consumers see it as
          absent rather than a misleading 0.0 or a raw counter value.
        - Counter wrap or reboot (delta < 0): clamped to 0.0.
        - Collection plugins are no-op here; per-item rate computation
          (indexed by primary key) lands in Phase 1.3 alongside the
          `network` plugin.

        Override only for non-standard rate computation.
        """
        if self.IS_COLLECTION:
            return
        if not isinstance(self._stats, dict):
            return
        elapsed = self._metadata.get("time_since_update", 0.0)
        prev_raw = self._raw_previous if isinstance(self._raw_previous, dict) else {}
        for field_name, schema in self._fields.items():
            if not schema.get("rate"):
                continue
            if field_name not in self._stats:
                continue
            if elapsed <= 0 or field_name not in prev_raw:
                # First cycle (or no previous sample for this field) — strip
                # the field; consumers must accept its absence.
                del self._stats[field_name]
                continue
            try:
                delta = float(self._stats[field_name]) - float(prev_raw[field_name])
            except (TypeError, ValueError):
                del self._stats[field_name]
                continue
            self._stats[field_name] = max(0.0, delta / float(elapsed))

    def _expand_parameters(self) -> None:
        """Expand compound psutil fields (e.g. cpu_times → user/system/iowait)."""

    def _derived_parameters(self) -> None:
        """Compute derived fields and `_levels`.

        Default implementation: walk `fields_description`, compute a level
        for every scalar field flagged with `watched: True` against the
        thresholds resolved from config (with `default_thresholds` from
        the field schema as fallback). See architecture §3.3.

        Each entry in `_levels` is a nested dict carrying both the level
        and the `prominent` flag (architecture §3.3):

            {"percent": {"level": "warning", "prominent": True}}

        `prominent` defaults to `True` when the field is `watched` (a
        watched field is meant to be visible by default) but the plugin
        author can opt out per field by setting `prominent: False` in
        `fields_description`. The flag drives the renderer rendering
        mode (font-only vs. background-highlight) and is copied into
        every alert event for downstream filtering (LLM diagnostic).

        ``normalize_by``: when the schema declares ``"normalize_by":
        "<other_field>"``, the level is computed against
        ``value / stats[<other_field>]``. Used for per-core normalisation
        (e.g. ``ctx_switches`` and ``load`` averaged across CPU cores).
        The divisor falls back to ``1`` if the referenced field is
        missing or zero.

        The collection branch (level computation indexed by primary key)
        lands in Phase 1.3 alongside the first collection plugin
        (`network`). Until then, collection plugins keep `_levels = {}`.
        """
        self._levels = {}

        if self.IS_COLLECTION:
            return  # Phase 1.3

        if not isinstance(self._stats, dict):
            return

        for field_name, schema in self._fields.items():
            if not schema.get("watched"):
                continue
            value = self._stats.get(field_name)
            if value is None:
                continue
            normalize_field = schema.get("normalize_by")
            if normalize_field:
                divisor = self._stats.get(normalize_field, 1) or 1
                try:
                    value = float(value) / float(divisor)
                except (TypeError, ValueError, ZeroDivisionError):
                    continue
            thresholds = read_thresholds(
                self.config,
                self.plugin_name,
                field_name,
                defaults=schema.get("default_thresholds"),
            )
            if not thresholds:
                continue
            direction = schema.get("watch_direction", "high")
            self._levels[field_name] = {
                "level": compute_level(value, thresholds, direction),
                "prominent": bool(schema.get("prominent", True)),
            }

    def _remove_parameters(self) -> None:
        """Filter out fields not declared in `fields_description` and strip
        internal keys (`_*`). Implemented in the base class — never override.
        """
        declared = set(self._fields.keys())

        if self.IS_COLLECTION:
            # self._stats is list[dict]
            self._stats = [self._filter_dict(item, declared) for item in self._stats]  # type: ignore[assignment]
        else:
            self._stats = self._filter_dict(self._stats, declared)  # type: ignore[assignment]

    @staticmethod
    def _filter_dict(d: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
        return {k: v for k, v in d.items() if k in allowed and not k.startswith("_")}

    # ----------------------------------------------------- store payload

    def _build_store_payload(self) -> dict[str, Any]:
        """Assemble the dict written to the StatsStore.

        Layout (architecture §3.3):
        - scalar:     {**stats, **metadata, "_levels": {...}}
        - collection: {"data": [...], **metadata, "_levels": {...}}
        """
        if self.IS_COLLECTION:
            return {"data": self._stats, **self._metadata, "_levels": self._levels}
        return {**self._stats, **self._metadata, "_levels": self._levels}  # type: ignore[dict-item]

    # ----------------------------------------------------------- consumers

    def get_stats(self) -> dict[str, Any]:
        """Return the latest payload as written to the store.

        Used by the REST API. Lockless read (architecture §1.3).
        Returns an empty dict if the plugin has never produced stats yet.
        """
        return self.store.get(self.plugin_name, {})

    def get_export(self) -> dict[str, Any] | list[dict[str, Any]]:
        """Filtered view for export modules (architecture §7.2).

        Strips internal keys (`_*`) and fields with `exportable: False`.
        This is the **only** permitted access path for exporters.
        """
        payload = self.store.get(self.plugin_name, {})
        if not isinstance(payload, dict):
            # Defensive: should never happen — store always holds a dict for plugins.
            return [] if self.IS_COLLECTION else {}

        if self.IS_COLLECTION:
            items = payload.get("data", [])
            return [self._project_exportable(item) for item in items]
        return self._project_exportable(payload)

    def _project_exportable(self, d: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in d.items() if not k.startswith("_") and self._fields.get(k, {}).get("exportable", True)}
