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
from glances.globals import split_esc
from glances.history_v5 import HistoryStoreV5
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
    "hidden": {
        "description": (
            "hide_zero display filter (design §5.1). True only when every "
            "HIDE_ZERO_FIELDS entry of this item is still sticky-hidden. "
            "Set per-item by _compute_hide_zero(); absent for plugins that "
            "do not declare HIDE_ZERO_FIELDS."
        ),
        "unit": "bool",
        "exportable": False,
        "internal": True,
    },
    "alias": {
        "description": (
            "Alias for this item's primary-key value, from "
            "`[<plugin_name>] alias=<key>:<Name>,...` (design §5.5, v4 "
            "`plugin/model.py:1075-1081`). Present only when the primary-key "
            "value has a configured match; the primary key itself is never "
            "rewritten. Set per-item by _apply_alias() (default "
            "_expand_parameters() hook), collection plugins only. Not "
            "applicable to `sensors`, which overrides `_expand_parameters()` "
            "with its own richer alias mechanism (`sensors/model_v5.py:194-214`)."
        ),
        "unit": "string",
        "internal": True,
    },
}


class GlancesPluginBase(Generic[T], ABC):
    """Generic async base class for Glances v5 plugins."""

    # --- Plugin identity ----------------------------------------------------

    plugin_name: ClassVar[str] = ""
    """Unique plugin identifier (used as StatsStore key and API path)."""

    IS_COLLECTION: ClassVar[bool] = False
    # Plugins whose update must run first because this one reads what they
    # leave behind (e.g. `processlist` reads the process engine `processcount`
    # drives). The scheduler does not use it; the Python API updates plugins
    # one by one and does (api_v5, design 2026-09-26 §5.2).
    DEPENDS_ON: ClassVar[tuple[str, ...]] = ()
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

    EXPORTABLE: ClassVar[bool] = True
    """Whether this plugin's stats are handed to the export modules.

    Mirrors v4's ``GlancesExport.non_exportable_plugins`` hard-coded list,
    inverted into a per-plugin declaration so that adding a plugin never
    requires editing a central list in the export layer. Read by
    ``GlancesExportBase.update()``.

    Set False for plugins whose payload is a presentation aggregate rather
    than a measurement (``quicklook`` re-states cpu/mem/load) or a constant
    string (``version``, ``psutilversion``)."""

    SCHEDULE_AT_GLOBAL_REFRESH: ClassVar[bool] = False
    """Poll this plugin at the GLOBAL refresh cadence, ignoring ``[<plugin>] refresh``.

    Default False: a plugin is polled at its own ``[<plugin>] refresh`` (the
    ``update()`` call *is* both the source read and the store publication, so
    one cadence is correct).

    Set True only for a plugin whose data source mutates ASYNCHRONOUSLY between
    its own ticks — where ``[<plugin>] refresh`` means "how often to poll the
    source" rather than "how often to publish". Such a plugin must publish its
    current snapshot on the fast display cadence (so the TUI reflects the
    source's progress promptly) while throttling the heavy source poll itself.
    ``ports`` is the sole case: its ``ThreadScanner`` fills the scan list
    incrementally in the background, and republishing that list is trivially
    cheap. Read by ``AsyncScheduler.register()``."""

    DEFAULT_REFRESH_TIME: ClassVar[float | None] = None
    """This plugin's intended polling cadence, in seconds, when no config sets it.

    Default ``None``: the plugin is polled at ``[global] refresh`` (2s). Set a
    value on plugins that are expensive to collect or whose data changes
    slowly, so the cadence travels with the plugin instead of depending on a
    key being present in the user's ``glances.conf``.

    Resolution order (``AsyncScheduler._resolve_refresh_time``)::

        refresh_time= argument
          → [<plugin_name>] refresh | refresh_time
          → DEFAULT_REFRESH_TIME
          → [global] refresh | refresh_time
          → 2.0

    A user's explicit ``[<plugin>] refresh`` therefore always wins — declaring
    a value here can never override a configured deployment.

    Plugins with ``SCHEDULE_AT_GLOBAL_REFRESH`` are polled at the global
    cadence regardless; for them this attribute is the default of the *source*
    poll they throttle themselves (``ports`` reads it in
    ``_resolve_scan_interval``)."""

    DISABLED_BY_DEFAULT: ClassVar[bool] = False
    """Value of ``[<plugin_name>] disable`` assumed when the key is absent.

    Mirrors the per-plugin default shipped in ``conf/glances.conf``: most
    plugins ship ``disable=False``, a few CPU-heavy or opt-in ones ship
    ``disable=True`` (``connections``, ``npu``, ``vms``). Read by
    ``is_disabled()``."""

    FILTER_EXTRA_FIELDS: ClassVar[tuple[str, ...]] = ()
    """Item fields matched by ``show`` / ``hide`` in addition to the primary key
    and its alias (``fs``: ``device_name``, v4 ``is_display_any(mountpoint,
    device)``). See ``_filter_collection()``."""

    HIDE_ZERO_FIELDS: ClassVar[list[str]] = []
    """Rate fields eligible for the sticky ``hide_zero`` display filter (design §5.1).

    Empty by default — the filter is a no-op unless a collection plugin
    opts in (``network``: ``bytes_recv``/``bytes_sent``; ``diskio``:
    ``read_bytes``/``write_bytes``). A field starts hidden and is un-hidden
    for good the first cycle its (already rate-transformed) value is
    strictly greater than ``[<plugin_name>] hide_threshold_bytes`` — never
    on ``None`` (no sample yet, v4 parity). See ``_compute_hide_zero()``.

    v4 (`plugin/model.py:643-657`) publishes one ``hidden`` boolean per
    field and has each renderer independently compute
    ``all(hidden for f in hide_zero_fields)`` (`network/__init__.py:328`,
    `diskio/__init__.py:259`). v5 does that reduction once here and
    publishes a single row-level ``hidden`` field instead — deliberate
    divergence recorded in design §5.1, do not "fix" it back to per-field."""

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {}
    """Per-field schema. See architecture §3.2."""

    @classmethod
    def is_disabled(cls, config: GlancesConfigV5) -> bool:
        """Return True when ``[<plugin_name>] disable`` resolves to true.

        Classmethod on purpose: ``main_v5.discover_plugins()`` calls it
        BEFORE instantiating the plugin, so that a disabled plugin never
        pays its construction cost (``ports`` builds its scan list and
        starts a scanner thread in ``__init__``)."""
        return bool(config.get(cls.plugin_name, "disable", cls.DISABLED_BY_DEFAULT))

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
        # `history: True` (v4 `items_history_list`): the fields recorded into
        # the history store after each published cycle.
        self._history_fields: list[str] = [n for n, s in self._fields.items() if s.get("history")]
        # The history store, attached by `main_v5.assemble` after construction
        # (an attribute rather than a constructor argument: 22 plugins
        # override `__init__(store, config)`). None = history disabled, or a
        # plugin built outside the CLI (tests).
        self.history: HistoryStoreV5 | None = None

        self._warn_unknown_threshold_keys()

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

        # Generic `alias` (design §5.5, v4 `plugin/model.py:1075-1081`):
        # `[<plugin_name>] alias=<key>:<Name>,...`, lower-keyed, matched
        # against a collection item's primary-key value. Used by the
        # show/hide filters above (v4 parity) and by `_apply_alias()`
        # (default `_expand_parameters()` hook) to publish the per-item
        # `alias` field. Never rewrites the primary key itself.
        self._alias_map: dict[str, str] = self._read_alias()

        # `hide_zero` / `hide_threshold_bytes` (design §5.1): sticky, per-field
        # display filter reduced to one row-level `hidden` boolean — see
        # HIDE_ZERO_FIELDS and _compute_hide_zero(). Read once, like show/hide.
        self.hide_zero: bool = self.config.get(self.plugin_name, "hide_zero", False)
        self.hide_threshold_bytes: int = self.config.get(self.plugin_name, "hide_threshold_bytes", 0)
        # Sticky state, keyed by primary-key value then field name. Rebuilt
        # from scratch every cycle in _compute_hide_zero() from only the
        # items currently present — see that method's docstring.
        self._hide_zero_state: dict[Any, dict[str, bool]] = {}

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
        self._cycle_ts: float | None = None

    def _warn_unknown_threshold_keys(self) -> None:
        """Warn once per unrecognised threshold key found in this plugin's config section.

        v5 renamed several v4 threshold keys (design §3 of the parity-wave-1
        decision doc) and deliberately does not accept the old spellings — a
        stale key is otherwise silently ignored and the user's threshold
        simply stops applying, with nothing in the logs. This surfaces that
        silently-dropped state at construction time.

        Only the plugin's own config section is inspected. A key is a
        *threshold key* when it is exactly ``careful``/``warning``/``critical``
        or ends with ``_careful``/``_warning``/``_critical``. A threshold key
        is recognised when, after stripping the level suffix, the remainder is
        empty (the bare ``careful`` form, valid only when the plugin has at
        least one watched field to apply it to) or ends with one of the
        plugin's accepted threshold names — which covers both
        ``<field>_<level>`` and ``<pk>_<field>_<level>`` shapes without having
        to parse the primary-key prefix.
        """
        try:
            section_keys = self.config.section_keys(self.plugin_name)
        except AttributeError:
            return  # config object without introspection API → skip check
        if not section_keys:
            return

        levels = ("careful", "warning", "critical")
        accepted = {self._threshold_key(name, schema).lower() for name, schema in self._watched_fields}

        for key in section_keys:
            key_lower = key.lower()
            remainder: str | None = None
            for level in levels:
                if key_lower == level:
                    remainder = ""
                    break
                suffix = f"_{level}"
                if key_lower.endswith(suffix):
                    remainder = key_lower[: -len(suffix)]
                    break
            if remainder is None:
                continue  # not a threshold key

            recognised = (remainder == "" and accepted) or any(remainder.endswith(name) for name in accepted)
            if not recognised:
                recognised = self._recognises_threshold_key(remainder)
            if not recognised:
                accepted_desc = (
                    ", ".join(sorted(accepted)) if accepted else "none — plugin declares no generic threshold keys"
                )
                logger.warning(
                    "Plugin %s: unrecognised threshold key %r in config section [%s] (accepted threshold names: %s)",
                    self.plugin_name,
                    key,
                    self.plugin_name,
                    accepted_desc,
                )

    def _recognises_threshold_key(self, remainder: str) -> bool:
        """Extension point: does this plugin accept ``remainder`` as a threshold-key body?

        ``_warn_unknown_threshold_keys()`` calls this only as a fallback,
        after its own generic ``<field>``/``<pk>_<field>`` suffix rule
        (built from ``_watched_fields``) has already rejected the key.
        ``remainder`` is the config key lower-cased with its trailing
        ``_careful``/``_warning``/``_critical`` (or the bare level itself)
        already stripped.

        Default ``False``: a plugin driven entirely by the base class's
        watched-field pipeline (the overwhelming majority) has nothing
        extra to recognise.

        Override for a plugin that resolves its own thresholds outside
        that pipeline (a custom ``_derived_parameters()``) and therefore
        owns key shapes the generic ``<field>``-suffix rule cannot
        express — e.g. ``sensors``, whose ``<type>_<level>`` and
        ``<type>_<label>_<level>`` tiers are resolved in
        ``sensors/model_v5.py::_resolve_thresholds`` rather than through
        a declared watched field per threshold name. This is a hook a
        plugin answers for its own key shapes, not a name to add to a
        list maintained here — adding a new self-resolving plugin never
        requires touching this file.

        Called from ``GlancesPluginBase.__init__`` BEFORE the subclass's
        own ``__init__`` body runs (a subclass calls ``super().__init__()``
        first, then does its own setup) — an override must not read any
        ``self.<attribute>`` the subclass sets there; it has not been
        assigned yet. Module-level constants (as ``sensors`` does) are safe.
        """
        return False

    def _resolve_primary_key(self) -> str | None:
        if not self.IS_COLLECTION:
            return None
        pks = [name for name, schema in self.fields_description.items() if schema.get("primary_key")]
        if len(pks) != 1:
            raise ValueError(
                f"{type(self).__name__} (collection): exactly one field must declare primary_key=True (found {pks})"
            )
        return pks[0]

    def _compile_filter(self, key: str, section: str | None = None) -> list[re.Pattern[str]]:
        """Read `[<section>] <key>=pat1,pat2` and compile each entry as a regex.

        Used by collection plugins to filter items by their primary-key value
        before any transformation. Empty list = no filtering. ``section``
        defaults to ``self.plugin_name`` — pass it explicitly for a plugin
        that reads another plugin's config section (e.g. ``programlist``
        reusing ``[processlist] export``, v4 parity for issue #794).
        """
        raw = self.config.get(section or self.plugin_name, key, [])
        if isinstance(raw, str):
            raw = [item.strip() for item in raw.split(",") if item.strip()]
        compiled: list[re.Pattern[str]] = []
        for pattern in raw or []:
            try:
                compiled.append(re.compile(pattern))
            except re.error as e:
                logger.warning("Plugin %s: invalid %s regex %r (%s) — ignored", self.plugin_name, key, pattern, e)
        return compiled

    def _read_alias(self) -> dict[str, str]:
        """Parse `[<plugin_name>] alias=<key>:<Name>,...` into a lower-keyed map.

        v4 parity (`plugin/model.py:1075-1081`). Collection plugins only —
        an alias matches a collection item's primary-key value. Scalar
        plugins never consult this map.
        """
        if not self.IS_COLLECTION:
            return {}
        raw = self.config.get(self.plugin_name, "alias", "")
        if not raw:
            return {}
        aliases: dict[str, str] = {}
        for pair in str(raw).split(","):
            entry = pair.strip()
            parts = split_esc(entry, ":")
            if len(parts) >= 2 and parts[0]:
                aliases[parts[0].strip().lower()] = parts[1].strip()
            elif entry:
                logger.warning(
                    "Plugin %s: invalid alias entry %r in [%s] (expected <key>:<Name>) — ignored",
                    self.plugin_name,
                    entry,
                    self.plugin_name,
                )
        return aliases

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
            # After the publish, inside the same `try`: what is recorded is
            # what REST served, and a failed cycle records nothing.
            if self.history is not None and self._history_fields:
                self.history.record(self.plugin_name, self._stats, self._history_fields, self._primary_key)
            # Promote the snapshot only after a successful cycle so a failed
            # grab can't poison the next rate computation.
            self._raw_previous = new_raw
            self._last_update_ts = self._cycle_ts
        except Exception as e:
            logger.warning("Plugin %s update failed: %s", self.plugin_name, e)

    def stop(self) -> None:
        """Release resources held by the plugin (background threads, sockets…).

        Default no-op. Overridden by plugins that own long-lived resources
        (e.g. ``containers`` engine streaming threads). Called once by the
        scheduler on shutdown, after the plugin's update loop is cancelled.
        Must be safe to call even if the plugin never produced stats.
        """

    def _filter_collection(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Drop items whose primary-key value does not pass show/hide filters.

        Pattern matching uses `re.search` (substring-friendly). When `show`
        is set, only matching items pass. `hide` is then applied to drop
        matches. Both are optional and independent.

        A configured alias (design §5.5) is matched too — v4 parity,
        `plugin/model.py:1044,1059`. `_alias_map` is looked up directly
        rather than through the item's (not yet published) `alias` field.
        The ``FILTER_EXTRA_FIELDS`` values are matched the same way.
        """
        pk = self._primary_key
        if pk is None:
            return items
        kept: list[dict[str, Any]] = []
        for item in items:
            pk_value = str(item.get(pk, ""))
            candidates = [pk_value]
            alias_value = self._alias_map.get(pk_value.lower())
            if alias_value is not None:
                candidates.append(alias_value)
            candidates.extend(str(item[f]) for f in self.FILTER_EXTRA_FIELDS if item.get(f) is not None)
            if self._show_patterns and not any(p.search(c) for p in self._show_patterns for c in candidates):
                continue
            if self._hide_patterns and any(p.search(c) for p in self._hide_patterns for c in candidates):
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
        # Committed by `update()` with `_raw_previous`, only once the cycle has
        # succeeded: the two must describe the same instant, or a failed cycle
        # halves the elapsed time the next rate is divided by.
        self._cycle_ts = now

    def _transform(self) -> None:
        """Run the transformation pipeline (architecture §3.1).

        `_compute_hide_zero` (design §5.1) is inserted right after
        `_transform_gauge`: it needs the just-computed rate value, and must
        run before `_remove_parameters` strips undeclared fields.
        """
        self._transform_gauge()
        self._compute_hide_zero()
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
          rate field is kept in the payload with value `None` — the field
          set must stay stable and match `fields_description`, which is the
          contract consumers (REST, exporters) rely on; `None` is still not
          a misleading 0.0 or a raw counter value.
        - Counter wrap or reboot (delta < 0): clamped to 0.0.
        - Collections: items are matched between cycles by their primary-key
          value. An item appearing for the first time goes through the same
          path — no previous sample means its rate fields are set to `None`,
          same as the first cycle.

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
                # First cycle (or no previous sample for this field) — keep
                # the field, but its rate cannot be computed yet.
                stats[field_name] = None
                continue
            try:
                delta = float(stats[field_name]) - float(prev_raw[field_name])
            except (TypeError, ValueError):
                stats[field_name] = None
                continue
            stats[field_name] = max(0.0, delta / float(elapsed))

    def _compute_hide_zero(self) -> None:
        """Sticky, per-field `hide_zero` display filter, reduced to one boolean per item.

        No-op when `HIDE_ZERO_FIELDS` is empty (the default) or the plugin is
        not a collection — no `hidden` key is added to the payload at all in
        that case. Same for an item whose primary-key value is `None`: it is
        skipped entirely (no `hidden` key either) — sticky state is keyed by
        primary-key value, so an item without one cannot carry any.

        When `hide_zero` is False (the default, always for a plugin that has
        not opted in), every remaining item gets `hidden = False` —
        published, never omitted, so a consumer can rely on the field's
        presence once a plugin declares `HIDE_ZERO_FIELDS`.

        When `hide_zero` is True: for each field in `HIDE_ZERO_FIELDS`, a
        field starts hidden and is un-hidden **for good** the first cycle its
        value is strictly greater than `hide_threshold_bytes` (v4 `cc5e2bab`
        — `>`, never `>=`). `None` (no sample yet, e.g. cycle 1 of a rate
        field) never un-hides. A `HIDE_ZERO_FIELDS` entry absent from the
        item itself counts as hidden (`fields_state.get(f, True)` below).
        The published `hidden` is `True` only while *every* field in
        `HIDE_ZERO_FIELDS` is still hidden (v4 `ff80c903`, structural here —
        see `HIDE_ZERO_FIELDS` docstring for the one-boolean-per-item
        divergence from v4).

        Sticky state (`self._hide_zero_state`) is keyed by primary-key value
        then field name, and is rebuilt from scratch every cycle from only
        the items present in `self._stats` this cycle — mirroring v4's
        `update_views()`, which replaces `self.views` wholesale each cycle
        (`plugin/model.py:672-686`). An item absent for one cycle (interface
        down, disk unplugged) therefore loses its accumulated state: if it
        reappears later, it starts hidden again rather than resuming from
        wherever it left off.
        """
        if not self.HIDE_ZERO_FIELDS or not self.IS_COLLECTION:
            return
        if not isinstance(self._stats, list) or self._primary_key is None:
            return

        new_state: dict[Any, dict[str, bool]] = {}
        for item in self._stats:
            if not isinstance(item, dict):
                continue
            pk_value = item.get(self._primary_key)
            if pk_value is None:
                continue

            if not self.hide_zero:
                item["hidden"] = False
                continue

            prev_fields = self._hide_zero_state.get(pk_value, {})
            fields_state: dict[str, bool] = {}
            for field_name in self.HIDE_ZERO_FIELDS:
                if field_name not in item:
                    continue
                still_hidden = prev_fields.get(field_name, True)
                value = item[field_name]
                if still_hidden and value is not None and value > self.hide_threshold_bytes:
                    still_hidden = False
                fields_state[field_name] = still_hidden
            new_state[pk_value] = fields_state
            item["hidden"] = all(fields_state.get(f, True) for f in self.HIDE_ZERO_FIELDS)

        self._hide_zero_state = new_state

    def _expand_parameters(self) -> None:
        """Expand compound psutil fields (e.g. cpu_times → user/system/iowait).

        Default hook also applies the generic per-item `alias` field
        (design §5.5, see `_apply_alias()`). A plugin that overrides this
        hook WITHOUT calling `super()` opts out of the generic mechanism
        entirely — `sensors` does this, since it rewrites its primary key
        with its own richer alias mechanism (`sensors/model_v5.py:194-214`)
        rather than publishing a separate `alias` field.
        """
        self._apply_alias()

    def _apply_alias(self) -> None:
        """Publish the generic per-item `alias` field (design §5.5).

        Set only when the item's primary-key value matches a configured
        `[<plugin_name>] alias=<key>:<Name>,...` entry (v4 parity: `network`,
        `diskio`, `fs` published `stat['alias']` the same way —
        `network/__init__.py:192`, `diskio/__init__.py:172-173`,
        `fs/__init__.py:199-200`). The primary key itself is **never**
        rewritten — `_levels`, the per-item threshold overrides
        (`<pk>_<field>_<level>`) and the rate matching in
        `_transform_gauge`/`_snapshot_raw` are all keyed on its raw value.
        """
        if not self.IS_COLLECTION or not self._alias_map or self._primary_key is None:
            return
        if not isinstance(self._stats, list):
            return
        pk = self._primary_key
        for item in self._stats:
            if not isinstance(item, dict):
                continue
            pk_value = item.get(pk)
            if pk_value is None:
                continue
            alias = self._alias_map.get(str(pk_value).lower())
            if alias is not None:
                item["alias"] = alias

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

    @staticmethod
    def _threshold_key(field_name: str, schema: dict[str, Any]) -> str:
        """Config-key prefix for a watched field's thresholds.

        Defaults to the field name; a field may declare ``threshold_field``
        to decouple its config-key prefix from its value key (e.g.
        ``containers`` stores CPU under ``cpu_percent`` but reads thresholds
        from ``[containers] cpu_*``). See design §5.2.
        """
        return schema.get("threshold_field", field_name)

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
            key = self._threshold_key(field_name, schema)
            if schema.get("threshold_type") == "categorical":
                mapping = read_thresholds_categorical(self.config, self.plugin_name, field=key)
                if mapping:
                    out[field_name] = {"mapping": mapping}
            else:
                thresholds = read_thresholds(
                    self.config,
                    self.plugin_name,
                    field=key,
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
            for field_name, schema in self._watched_fields:
                tkey = self._threshold_key(field_name, schema)
                # Pattern: `<pk>_<tkey>_<level>` — `<pk>` must be non-empty
                # and must NOT be ``<tkey>_`` (that's the plain
                # `<tkey>_<level>` key, already handled by precompute).
                for level in levels:
                    suffix = f"_{tkey}_{level}"
                    if key.endswith(suffix) and not key.startswith(f"{tkey}_"):
                        # `<pk>` is whatever precedes `_<tkey>_<level>` —
                        # must be non-empty.
                        prefix_len = len(key) - len(suffix)
                        if prefix_len > 0:
                            out.add(field_name)
                            break
        return out

    def get_limits(self) -> dict[str, Any]:
        """Return this plugin's **effective** thresholds, keyed by field name.

        Effective = the plugin's config section layered over each field's
        ``default_thresholds`` — what drives ``_levels`` for plugins that go
        through the base class's watched-field resolution (see Known
        limitation below). Consumed by the REST ``/api/5/<plugin>/limits``
        route and by the MCP ``glances://limits`` resource, which share this
        single source of truth.

        Computed on demand rather than cached: thresholds derive from
        config + schema, not from psutil, so this answers correctly before
        the scheduler's first cycle. A cache filled by ``_derived_parameters``
        would be empty at cycle 0.

        Shape — numeric fields at the top level, categorical fields grouped
        under ``_categorical`` because their form is inverted (level → set
        of values instead of level → number), per-item overrides grouped
        under ``_per_item`` (see ``_per_item_limits()``)::

            {"percent": {"careful": 50.0, "warning": 70.0},
             "_categorical": {"status": {"ok": ["R", "S"]}},
             "_per_item": {"eth0": {"rx": {"warning": 60.0}}}}

        ``_categorical`` and ``_per_item`` are each omitted when empty.
        Underscore-prefixed keys cannot collide with a field name:
        ``_remove_parameters`` strips every ``_*`` key from stats, so no
        declared field starts with one.

        Known limitation: six plugins — ``sensors``, ``wifi``, ``folders``,
        ``raid``, ``ports``, ``amps`` — override ``_derived_parameters()``
        and compute ``_levels`` outside the base class's watched-field path
        that this method walks. For those plugins, ``get_limits()`` returns
        ``{}`` even when the operator's config carries thresholds that are
        genuinely active and driving colours. Fixing this would require a
        per-plugin ``get_limits()`` override hook — a deliberate follow-up,
        not implemented here.

        Security (design §7): the key space read here is closed and
        code-controlled — field names come from ``fields_description``,
        levels from the threshold ladder. No arbitrary config key can reach
        the payload, which is what keeps ``*_action`` templates out of it.
        """
        out: dict[str, Any] = {}
        categorical: dict[str, dict[str, list[str]]] = {}

        for field_name, entry in self._precompute_plugin_thresholds().items():
            # Dispatch on the output key, not on schema["threshold_type"] —
            # _precompute_plugin_thresholds owns that mapping.
            if "thresholds" in entry:
                out[field_name] = dict(entry["thresholds"])
            elif "mapping" in entry:
                # read_thresholds_categorical returns sets, which json cannot
                # serialise. Sorted lists also make the payload deterministic.
                categorical[field_name] = {level: sorted(values) for level, values in entry["mapping"].items()}

        if categorical:
            out["_categorical"] = categorical

        per_item = self._per_item_limits()
        if per_item:
            out["_per_item"] = per_item

        return out

    def _per_item_limits(self) -> dict[str, dict[str, dict[str, float]]]:
        """Resolve per-item threshold overrides for a collection plugin.

        Returns ``{pk_value: {field_name: {level: value}}}``, restricted to
        items currently published in the store and to fields whose resolved
        thresholds actually differ from the plugin-level ones.

        ``_scan_pk_override_fields()`` is empty on any deployment without
        ``<pk>_<field>_<level>`` keys — the overwhelming majority — which
        short-circuits this method entirely. That guard is what keeps
        ``/limits`` cheap on processlist (500+ items).

        Categorical fields are skipped: a per-primary-key categorical
        override (e.g. a per-PID process status set) has no sensible use
        case, and including it would fork the ``_per_item`` payload shape.

        Known limitation (design §4.3): an override configured for an item
        absent from the store at call time — a downed interface, a stopped
        container — is not reported.
        """
        if not self.IS_COLLECTION or self._primary_key is None:
            return {}

        override_fields = self._scan_pk_override_fields()
        if not override_fields:
            return {}

        payload = self.store.get(self.plugin_name)
        if not isinstance(payload, dict):
            return {}
        stats = payload.get("data")
        if not isinstance(stats, list):
            return {}

        plugin_level = self._precompute_plugin_thresholds()
        schema_by_name = dict(self._watched_fields)

        out: dict[str, dict[str, dict[str, float]]] = {}
        for item in stats:
            if not isinstance(item, dict):
                continue
            pk_value = item.get(self._primary_key)
            if pk_value is None:
                continue
            per_field: dict[str, dict[str, float]] = {}
            for field_name in override_fields:
                schema = schema_by_name.get(field_name)
                if schema is None or schema.get("threshold_type") == "categorical":
                    continue
                thresholds = read_thresholds(
                    self.config,
                    self.plugin_name,
                    field=self._threshold_key(field_name, schema),
                    pk_value=str(pk_value),
                    defaults=schema.get("default_thresholds"),
                    strict=bool(schema.get("strict_thresholds", False)),
                )
                baseline = plugin_level.get(field_name, {}).get("thresholds", {})
                if thresholds and thresholds != baseline:
                    per_field[field_name] = thresholds
            if per_field:
                out[str(pk_value)] = per_field
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
        schema = self._fields.get(field_name, {})
        return read_thresholds_categorical(
            self.config, self.plugin_name, field=self._threshold_key(field_name, schema), pk_value=pk_value
        )

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
            field=self._threshold_key(field_name, schema),
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
            return [self._project(item, keep_internal=False) for item in items]
        return self._project(payload, keep_internal=False)

    def get_api_payload(self) -> dict[str, Any]:
        """Filtered view for the REST API and the MCP adapter (issue #3211).

        Drops fields declared `exportable: False`; KEEPS `_levels` and `_key`,
        which is what a UI colours cells from and walks `_levels` with.

        Always returns a dict, unlike `get_export()`, which returns a bare
        list for collection plugins: the API serves the payload shape its
        clients already know, envelope included.
        """
        payload = self.store.get(self.plugin_name, {})
        if not isinstance(payload, dict) or not payload:
            # Empty == the plugin has registered but has not published yet
            # (scheduler cycle 0). Returning {} keeps that distinguishable:
            # projecting it instead would hand a collection plugin back a
            # `{"data": []}` envelope, which reads as "published, nothing to
            # show" and would put it in /api/5/all a cycle too early.
            return {}

        out = self._project(payload, keep_internal=True)
        if self.IS_COLLECTION:
            # `data` is not a declared field, so the envelope projection above
            # passes the list through untouched. Each item must be projected on
            # its own or every non-exportable field survives.
            out["data"] = [self._project(item, keep_internal=True) for item in payload.get("data", [])]
            # The primary key's NAME. `_levels` is keyed by its VALUE, so a
            # consumer that does not know the name cannot walk it without
            # hardcoding the field — which is what 32 WebUI components would
            # otherwise each do. Underscore-prefixed like `_levels`: it is
            # metadata about the payload, not a metric, and `_project()`
            # therefore keeps it out of the export view.
            if self._primary_key:
                out["_key"] = self._primary_key
        return out

    def get_history(self, nb: int = 0, field: str | None = None, item: str | None = None) -> dict[str, Any]:
        """This plugin's history, columnar (history design §5.5). REST and MCP both serve it.

        ``{"timestamps": [...], "series": {field: [...]}}`` for a scalar
        plugin; ``series`` nests ``{field: {item: [...]}}`` for a collection.
        The last ``nb`` points (0 = all). ``field`` / ``item`` narrow
        ``series`` and keep its shape.

        Empty -- not an error -- when history is disabled, when the plugin
        declares no history field, or before its first cycle. Raises
        ``KeyError`` for a ``field`` the plugin does not historise, and for
        an ``item`` no historised series is recorded for.
        """
        if field is not None and field not in self._history_fields:
            raise KeyError(f"{self.plugin_name!r} keeps no history for field {field!r}")
        if self.history is None:
            return {"timestamps": [], "series": {}}
        out = self.history.get(self.plugin_name, nb)
        series = out["series"]
        if field is not None:
            series = {field: series[field]} if field in series else {}
        if item is not None:
            series = {
                name: {item: values[item]}
                for name, values in series.items()
                if isinstance(values, dict) and item in values
            }
            if not series:
                raise KeyError(f"{self.plugin_name!r} has no history for item {item!r}")
        out["series"] = series
        return out

    def _project(self, d: dict[str, Any], *, keep_internal: bool) -> dict[str, Any]:
        """Filter one payload dict for a consumer.

        `keep_internal=False` (exporters): drop every `_*` key and every field
        declared `exportable: False`.
        `keep_internal=True` (REST, MCP): additionally keep `_*` keys and
        fields declared `internal: True`.

        `internal` and `exportable` are independent flags. A field marked
        `internal: True` is not a metric worth shipping to a time-series
        backend, but Glances' own clients need it: `time_since_update` is the
        divisor the WebUI uses to turn counters into rates
        (`plugin-cpu.vue`, `plugin-processlist.vue`). Filtering the API purely
        on `exportable` would strip it from every endpoint and leave those
        views dividing by undefined.

        One helper, two views, so the REST and export projections cannot drift
        apart (issue #3211).
        """
        return {
            k: v
            for k, v in d.items()
            if (keep_internal and (k.startswith("_") or self._fields.get(k, {}).get("internal", False)))
            or (not k.startswith("_") and self._fields.get(k, {}).get("exportable", True))
        }
