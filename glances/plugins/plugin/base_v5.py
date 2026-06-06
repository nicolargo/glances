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
import re
import time
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Generic, TypeVar

from glances.config_v5 import GlancesConfigV5
from glances.plugins.plugin.thresholds_v5 import (
    compute_level,
    compute_level_categorical,
    read_thresholds,
    read_thresholds_categorical,
)
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
        "internal": True,
    },
}


class GlancesPluginBase(Generic[T], ABC):
    """Generic async base class for Glances v5 plugins."""

    # --- Plugin identity ----------------------------------------------------

    plugin_name: ClassVar[str] = ""
    """Unique plugin identifier (used as StatsStore key and API path)."""

    IS_COLLECTION: ClassVar[bool] = False
    """False for scalar plugins (cpu, mem), True for collection plugins (fs, network)."""

    EMITS_ALERTS: ClassVar[bool] = True
    """Whether ``_levels`` produced by this plugin should drive the alerts pipeline.

    When False, `_levels` is still computed (so the TUI keeps colouring cells)
    but `GlancesAlerts.ingest_plugin` skips this plugin entirely — no history
    events, no action dispatch. Used by plugins where the watched-field
    semantic is decorative only (e.g. processlist: per-process CPU/MEM
    colouring informs the operator visually but does not warrant an
    actionable alert per-pid, since v4 does not page on individual procs)."""

    DISPLAY_IN_TUI: ClassVar[bool] = True
    """Whether this plugin is rendered in the curses TUI.

    Mirrors v4's ``display_curse``. Default True. Set False for plugins
    that exist only for the REST API / exporters and were never shown in
    the v4 TUI (``core``, ``version``, ``psutilversion``). The flag is
    read by ``main_v5.assemble`` when it builds the TUI registry; it does
    not affect REST registration (every discovered plugin is served)."""

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

        # Hot-loop precomputation. Walking ``_fields.items()`` per item to
        # filter on schema flags burns measurable CPU on large collections
        # (processlist with 580 procs × 17 fields = 9860 iterations per
        # cycle inside ``_compute_rates_in_dict`` ALONE). These subsets
        # never change at runtime, so we cache them at construction.
        self._rate_fields: list[tuple[str, dict[str, Any]]] = [(n, s) for n, s in self._fields.items() if s.get("rate")]
        self._watched_fields: list[tuple[str, dict[str, Any]]] = [
            (n, s) for n, s in self._fields.items() if s.get("watched")
        ]
        self._allowed_field_names: set[str] = set(self._fields.keys())

        # Collection plugins must declare exactly one field as the primary
        # key — used to index `_levels`, snapshot raw counters across cycles
        # for per-item rates, and match items between cycles.
        self._primary_key: str | None = self._resolve_primary_key()

        # Compile optional show/hide filters once at construction. Both keys
        # are read from the plugin's config section (`[<plugin_name>]`). The
        # filter applies to collection plugins only; on scalar plugins these
        # lists stay empty.
        self._show_patterns: list[re.Pattern[str]] = self._compile_filter("show")
        self._hide_patterns: list[re.Pattern[str]] = self._compile_filter("hide")

        self._stats: T = self._empty_stats()
        self._stats_previous: T | None = None
        # Snapshot of the raw psutil values from the previous successful
        # cycle, kept across `_transform()` runs so `_transform_gauge` can
        # diff cumulative counters. None until the second cycle.
        # Shape: {field: value} for scalars, {primary_key_value: {field: value}}
        # for collections.
        self._raw_previous: dict[str, Any] | None = None
        self._metadata: dict[str, Any] = {}
        self._levels: dict[str, Any] = {}
        self._last_update_ts: float | None = None

    def _resolve_primary_key(self) -> str | None:
        if not self.IS_COLLECTION:
            return None
        pks = [name for name, schema in self.fields_description.items() if schema.get("primary_key")]
        if len(pks) != 1:
            raise ValueError(
                f"{type(self).__name__} (collection): exactly one field must declare primary_key=True (found {pks})"
            )
        return pks[0]

    def _compile_filter(self, key: str) -> list[re.Pattern[str]]:
        """Read `[<plugin_name>] <key>=pat1,pat2` and compile each entry as a regex.

        Used by collection plugins to filter items by their primary-key value
        before any transformation. Empty list = no filtering.
        """
        raw = self.config.get(self.plugin_name, key, [])
        if isinstance(raw, str):
            raw = [item.strip() for item in raw.split(",") if item.strip()]
        compiled: list[re.Pattern[str]] = []
        for pattern in raw or []:
            try:
                compiled.append(re.compile(pattern))
            except re.error as e:
                logger.warning("Plugin %s: invalid %s regex %r (%s) — ignored", self.plugin_name, key, pattern, e)
        return compiled

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
            # Apply collection-wide show/hide regex filters before anything
            # else — filtered items never reach _raw_previous, so they don't
            # influence rate computation when re-shown.
            if self.IS_COLLECTION and (self._show_patterns or self._hide_patterns):
                self._stats = self._filter_collection(self._stats)  # type: ignore[assignment]
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

    def _filter_collection(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Drop items whose primary-key value does not pass show/hide filters.

        Pattern matching uses `re.search` (substring-friendly). When `show`
        is set, only matching items pass. `hide` is then applied to drop
        matches. Both are optional and independent.
        """
        pk = self._primary_key
        if pk is None:
            return items
        kept: list[dict[str, Any]] = []
        for item in items:
            pk_value = str(item.get(pk, ""))
            if self._show_patterns and not any(p.search(pk_value) for p in self._show_patterns):
                continue
            if self._hide_patterns and any(p.search(pk_value) for p in self._hide_patterns):
                continue
            kept.append(item)
        return kept

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
        """Snapshot the raw payload before `_transform` mutates it.

        Scalar plugins: `{field: value}` (flat).
        Collection plugins: `{primary_key_value: {field: value}}` (per-item).
        Items without a resolvable primary-key value are skipped — they
        cannot be matched across cycles for rate computation.

        Plugins with no ``rate: True`` field never consult the snapshot
        (``_transform_gauge`` is a no-op for them), so we skip the dict
        copies entirely — ``processlist`` with 580+ procs saves ~580
        per-cycle dict allocations alone.
        """
        if not self._rate_fields:
            return None

        if not self.IS_COLLECTION:
            if not isinstance(self._stats, dict):
                return None
            return dict(self._stats)

        if not isinstance(self._stats, list) or self._primary_key is None:
            return None
        indexed: dict[str, Any] = {}
        for item in self._stats:
            if not isinstance(item, dict):
                continue
            pk_value = item.get(self._primary_key)
            if pk_value is None:
                continue
            indexed[pk_value] = dict(item)
        return indexed

    # Override hooks ---------------------------------------------------------

    def _transform_gauge(self) -> None:
        """Convert cumulative counter fields to per-second rates.

        Walks every field declared with `rate: True` and replaces the
        cumulative counter with `(current - previous) / elapsed`.

        Behaviour (identical for scalars and collections):
        - First cycle (no `_raw_previous`) or `time_since_update == 0`: the
          rate field is **removed** from the payload — consumers see it as
          absent rather than a misleading 0.0 or a raw counter value.
        - Counter wrap or reboot (delta < 0): clamped to 0.0.
        - Collections: items are matched between cycles by their primary-key
          value. An item that did not exist last cycle has its rate fields
          stripped on its first appearance.

        Override only for non-standard rate computation.
        """
        elapsed = self._metadata.get("time_since_update", 0.0)
        prev_raw = self._raw_previous if isinstance(self._raw_previous, dict) else {}

        if not self.IS_COLLECTION:
            if isinstance(self._stats, dict):
                self._compute_rates_in_dict(self._stats, prev_raw, elapsed)
            return

        if not isinstance(self._stats, list) or self._primary_key is None:
            return
        for item in self._stats:
            if not isinstance(item, dict):
                continue
            pk_value = item.get(self._primary_key)
            prev_item = prev_raw.get(pk_value) if pk_value is not None else None
            if not isinstance(prev_item, dict):
                prev_item = {}
            self._compute_rates_in_dict(item, prev_item, elapsed)

    def _compute_rates_in_dict(self, stats: dict[str, Any], prev_raw: dict[str, Any], elapsed: float) -> None:
        """Replace counter fields with per-second rates inside one dict."""
        if not self._rate_fields:
            return
        for field_name, _schema in self._rate_fields:
            if field_name not in stats:
                continue
            if elapsed <= 0 or field_name not in prev_raw:
                # First cycle (or no previous sample for this field) — strip
                # the field; consumers must accept its absence.
                del stats[field_name]
                continue
            try:
                delta = float(stats[field_name]) - float(prev_raw[field_name])
            except (TypeError, ValueError):
                del stats[field_name]
                continue
            stats[field_name] = max(0.0, delta / float(elapsed))

    def _expand_parameters(self) -> None:
        """Expand compound psutil fields (e.g. cpu_times → user/system/iowait)."""

    def _derived_parameters(self) -> None:
        """Compute derived fields and `_levels`.

        Walks `fields_description`, computing a level for every field
        flagged with `watched: True` against the thresholds resolved
        from config (with `default_thresholds` from the field schema as
        fallback). See architecture §3.3.

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
        (e.g. ``ctx_switches`` and ``load`` averaged across CPU cores)
        and for percent-of-capacity comparisons (e.g.
        ``network.bytes_recv`` against ``bytes_speed_rate_per_sec``).
        If the divisor is missing, ``None`` or zero, the level is
        **skipped** for this field — meaning "no meaningful threshold
        computable" (e.g. an interface whose link speed is unknown).

        Scalar plugins: `_levels = {field: {level, prominent}}`.
        Collection plugins: `_levels = {pk_value: {field: {level, prominent}}}`
        — indexed by the primary-key value of each item.
        """
        self._levels = {}

        if not self.IS_COLLECTION:
            if not isinstance(self._stats, dict):
                return
            self._compute_levels_for_item(self._stats, self._levels)
            return

        if not isinstance(self._stats, list) or self._primary_key is None:
            return

        # Hot path. ``read_thresholds*`` is invariant in ``pk_value`` for
        # the vast majority of deployments — only network plugins
        # historically expose per-interface overrides like
        # ``wlan0_bytes_recv_warning=0.7``. processlist with 500+ items
        # used to incur 500× redundant config reads + CSV parses per
        # cycle. We precompute the plugin-level thresholds once here,
        # detect whether **any** per-pk override exists in the section,
        # and only fall back to the per-item config read when it does.
        plugin_thresholds = self._precompute_plugin_thresholds()
        fields_with_pk_overrides = self._scan_pk_override_fields()

        for item in self._stats:
            if not isinstance(item, dict):
                continue
            pk_value = item.get(self._primary_key)
            if pk_value is None:
                continue
            entry: dict[str, Any] = {}
            self._compute_levels_for_item(
                item,
                entry,
                pk_value=str(pk_value),
                plugin_thresholds=plugin_thresholds,
                fields_with_pk_overrides=fields_with_pk_overrides,
            )
            if entry:
                self._levels[pk_value] = entry

    # --------------------------------------------------- threshold precompute

    def _precompute_plugin_thresholds(self) -> dict[str, dict[str, Any]]:
        """Build plugin-level (pk-agnostic) thresholds for each watched field.

        Called once per cycle by ``_derived_parameters``; the result is
        reused for every item of a collection. ``_compute_levels_for_item``
        layers per-item ``<pk>_<field>_<level>`` overrides on top only
        when the section actually carries such keys.

        Returns ``{field_name: {"thresholds": {...}}}`` for numeric fields
        and ``{field_name: {"mapping": {...}}}`` for categorical ones.
        Empty / unconfigured fields are omitted from the result.
        """
        out: dict[str, dict[str, Any]] = {}
        for field_name, schema in self._watched_fields:
            if schema.get("threshold_type") == "categorical":
                mapping = read_thresholds_categorical(self.config, self.plugin_name, field=field_name)
                if mapping:
                    out[field_name] = {"mapping": mapping}
            else:
                thresholds = read_thresholds(
                    self.config,
                    self.plugin_name,
                    field=field_name,
                    defaults=schema.get("default_thresholds"),
                    strict=bool(schema.get("strict_thresholds", False)),
                )
                if thresholds:
                    out[field_name] = {"thresholds": thresholds}
        return out

    def _scan_pk_override_fields(self) -> set[str]:
        """Return the set of watched field names that have **at least one**
        ``<pk>_<field>_<level>`` key configured in the plugin's section.

        Used to short-circuit the per-item ``read_thresholds*`` re-read
        when no operator has configured per-pk overrides — the common
        case for processlist (500 procs × per-pid override = nonsensical)
        and the explicit feature for network (per-interface overrides).
        """
        out: set[str] = set()
        if not self._watched_fields:
            return out
        # ``ok`` is added so the categorical path is covered too (numeric
        # only uses careful/warning/critical, but the extra check is cheap).
        levels = ("ok", "careful", "warning", "critical")
        try:
            section_keys = self.config.section_keys(self.plugin_name)
        except AttributeError:
            return out  # config object without introspection API → skip optim
        for key in section_keys:
            for field_name, _schema in self._watched_fields:
                # Pattern: `<pk>_<field>_<level>` — `<pk>` must be non-empty
                # and must NOT be ``<field>_`` (that's the plain
                # `<field>_<level>` key, already handled by precompute).
                for level in levels:
                    suffix = f"_{field_name}_{level}"
                    if key.endswith(suffix) and not key.startswith(f"{field_name}_"):
                        # `<pk>` is whatever precedes `_<field>_<level>` —
                        # must be non-empty.
                        prefix_len = len(key) - len(suffix)
                        if prefix_len > 0:
                            out.add(field_name)
                            break
        return out

    def _compute_levels_for_item(
        self,
        item: dict[str, Any],
        target: dict[str, Any],
        pk_value: str | None = None,
        plugin_thresholds: dict[str, dict[str, Any]] | None = None,
        fields_with_pk_overrides: set[str] | None = None,
    ) -> None:
        """Walk `fields_description`, populate `target[field] = {level, prominent}`.

        Same logic for scalar plugins (target is `self._levels`, no
        ``pk_value``) and for each item of a collection plugin (target
        is the per-item entry, ``pk_value`` carries the primary-key value
        used to honour per-item config overrides — e.g.
        ``[network] wlan0_bytes_recv_warning=0.7``).

        ``plugin_thresholds`` / ``fields_with_pk_overrides`` are populated
        by ``_derived_parameters`` for collection plugins and skip
        per-item config reads when no override exists. Scalars pass
        ``None`` — the function falls back to the original eager-read
        behaviour.
        """
        for field_name, schema in self._watched_fields:
            value = item.get(field_name)
            if value is None:
                continue

            # Categorical fields (status, nice, etc.) take a separate
            # path — value sets, no normalisation, no numeric comparison.
            if schema.get("threshold_type") == "categorical":
                mapping = self._resolve_categorical_mapping(
                    field_name,
                    pk_value,
                    plugin_thresholds=plugin_thresholds,
                    fields_with_pk_overrides=fields_with_pk_overrides,
                )
                if not mapping:
                    continue
                level = compute_level_categorical(value, mapping)
                if level is None:
                    # Value not in any configured bucket → no level entry.
                    # Renderer falls back to DEFAULT (no colour), alert
                    # pipeline sees no event. Mirrors v4 ``get_alert``
                    # returning ``'DEFAULT'`` for unmatched values.
                    continue
                target[field_name] = {
                    "level": level,
                    "prominent": bool(schema.get("prominent", True)),
                }
                continue

            normalize_field = schema.get("normalize_by")
            if normalize_field:
                divisor = item.get(normalize_field)
                if divisor in (None, 0):
                    # No meaningful threshold — e.g. interface link speed
                    # unknown. Treat as "no limit" and skip the level entry
                    # rather than alerting against a fallback divisor.
                    continue
                try:
                    value = float(value) / float(divisor)
                except (TypeError, ValueError, ZeroDivisionError):
                    continue
            thresholds = self._resolve_numeric_thresholds(
                field_name,
                schema,
                pk_value,
                plugin_thresholds=plugin_thresholds,
                fields_with_pk_overrides=fields_with_pk_overrides,
            )
            if not thresholds:
                continue
            direction = schema.get("watch_direction", "high")
            target[field_name] = {
                "level": compute_level(value, thresholds, direction),
                "prominent": bool(schema.get("prominent", True)),
            }

    def _resolve_categorical_mapping(
        self,
        field_name: str,
        pk_value: str | None,
        plugin_thresholds: dict[str, dict[str, Any]] | None,
        fields_with_pk_overrides: set[str] | None,
    ) -> dict[str, set[str]]:
        """Resolve the per-item categorical mapping.

        Fast path: when the cycle-level scan reports no pk-specific keys
        for this field, reuse the precomputed plugin-level mapping
        verbatim. Slow path (rare): re-read with pk_value to apply the
        per-pk override.
        """
        if plugin_thresholds is not None and (
            fields_with_pk_overrides is None or field_name not in fields_with_pk_overrides
        ):
            entry = plugin_thresholds.get(field_name)
            return entry.get("mapping", {}) if entry else {}
        return read_thresholds_categorical(self.config, self.plugin_name, field=field_name, pk_value=pk_value)

    def _resolve_numeric_thresholds(
        self,
        field_name: str,
        schema: dict[str, Any],
        pk_value: str | None,
        plugin_thresholds: dict[str, dict[str, Any]] | None,
        fields_with_pk_overrides: set[str] | None,
    ) -> dict[str, float]:
        """Resolve the per-item numeric thresholds. Same fast/slow split."""
        if plugin_thresholds is not None and (
            fields_with_pk_overrides is None or field_name not in fields_with_pk_overrides
        ):
            entry = plugin_thresholds.get(field_name)
            return entry.get("thresholds", {}) if entry else {}
        return read_thresholds(
            self.config,
            self.plugin_name,
            field=field_name,
            pk_value=pk_value,
            defaults=schema.get("default_thresholds"),
            strict=bool(schema.get("strict_thresholds", False)),
        )

    def _remove_parameters(self) -> None:
        """Filter out fields not declared in `fields_description` and strip
        internal keys (`_*`). Implemented in the base class — never override.
        """
        allowed = self._allowed_field_names

        if self.IS_COLLECTION:
            # self._stats is list[dict]
            self._stats = [self._filter_dict(item, allowed) for item in self._stats]  # type: ignore[assignment]
        else:
            self._stats = self._filter_dict(self._stats, allowed)  # type: ignore[assignment]

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
