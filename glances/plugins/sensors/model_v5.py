#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — sensors plugin (collection, per-label).

Migrated from `glances/plugins/sensors/__init__.py`. Merges four
sub-types (temperature_core, fan_speed, temperature_hdd, battery) into
one flat list, keyed by sensor `label`.

Hardware collection reuses the v4 grab classes verbatim:
- `GlancesGrabSensors` — psutil sensors_temperatures() / sensors_fans()
- `GlancesGrabHDDTemp`  — hddtemp daemon socket client
- `GlancesGrabBat`      — batinfo / psutil battery grabber

The v4 alias, hide/show, per-prefix "mean" fold, and per-sensor system
thresholds are ported (see _expand_parameters / _derived_parameters).
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, ClassVar

from glances.globals import natural_keys, split_esc
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.plugins.sensors import GlancesGrabSensors, sensors_definition
from glances.plugins.sensors.sensor.glances_batpercent import GlancesGrabBat
from glances.plugins.sensors.sensor.glances_hddtemp import GlancesGrabHDDTemp

logger = logging.getLogger(__name__)

# Sensor type strings (mirror v4 sensors_definition values).
_TEMP_CORE = "temperature_core"
_FAN_SPEED = "fan_speed"
_TEMP_HDD = "temperature_hdd"
_BATTERY = "battery"


def _label_prefix(label: str) -> str:
    """Return the label with a trailing number (and its spacing) stripped.

    'Core 0' -> 'Core'; 'Package id 0' -> 'Package id'; 'fan1' -> 'fan';
    a label with no trailing number is returned unchanged.
    """
    return re.sub(r"\s*\d+\s*$", "", label) or label


def _as_float(value: Any) -> float | None:
    """Best-effort float; None/empty/non-numeric -> None."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class PluginModel(GlancesPluginBase[list]):
    """Sensors plugin (collection)."""

    plugin_name: ClassVar[str] = "sensors"
    IS_COLLECTION: ClassVar[bool] = True

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "label": {
            "description": "Sensor label.",
            "unit": "string",
            "primary_key": True,
        },
        "type": {
            "description": "Sensor type (temperature_core, fan_speed, temperature_hdd, battery).",
            "unit": "string",
            "internal": True,
            "watched": False,
        },
        "unit": {
            "description": "Sensor unit.",
            "unit": "string",
            "internal": True,
            "watched": False,
        },
        "value": {
            "description": "Sensor value.",
            "unit": "number",
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
        },
        "warning": {
            "description": "Hardware warning threshold.",
            "unit": "number",
            "internal": True,
            "watched": False,
        },
        "critical": {
            "description": "Hardware critical threshold.",
            "unit": "number",
            "internal": True,
            "watched": False,
        },
        "status": {
            "description": "Battery charge status.",
            "unit": "string",
            "internal": True,
            "watched": False,
        },
    }

    def __init__(self, store: Any, config: Any) -> None:
        super().__init__(store, config)
        # Build the grab classes once (v4 parity: constructed at init).
        self._grab_temp_core = GlancesGrabSensors(sensors_definition["cpu_temp"])
        self._grab_fan = GlancesGrabSensors(sensors_definition["fan_speed"])
        host = self.config.get("sensors", "host", "127.0.0.1")
        port = self.config.get("sensors", "port", 7634)
        self._grab_hdd = GlancesGrabHDDTemp(host=host, port=port)
        self._grab_bat = GlancesGrabBat()

    def _collect(self) -> list:
        """Synchronous collection (runs in a worker thread).

        Each sub-grabber is guarded independently — one raising must not
        drop the others (mirrors the v4 ThreadPoolExecutor per-future
        try/except).
        """
        out: list[dict[str, Any]] = []
        out.extend(self._grab_typed(self._grab_temp_core.update, _TEMP_CORE))
        out.extend(self._grab_typed(self._grab_fan.update, _FAN_SPEED))
        out.extend(self._grab_typed(self._grab_hdd.get, _TEMP_HDD))
        out.extend(self._grab_typed(self._grab_battery, _BATTERY))
        return out

    def _grab_battery(self) -> list:
        self._grab_bat.update()
        return self._grab_bat.get()

    @staticmethod
    def _grab_typed(fn, sensor_type: str) -> list:
        """Call a grabber, stamp `type`, ensure warning/critical keys exist."""
        try:
            rows = fn() or []
        except Exception as exc:  # noqa: BLE001 — one bad sub-grabber must not drop others
            logger.debug("sensors: %s grab failed: %s", sensor_type, exc)
            return []
        for row in rows:
            row["type"] = sensor_type
            row.setdefault("warning", None)
            row.setdefault("critical", None)
        return rows

    async def _grab_stats(self) -> list:
        return await asyncio.to_thread(self._collect)

    # ------------------------------------------------- transform: alias + fold

    def _expand_parameters(self) -> None:
        """Apply aliases, then the per-type mean fold, then sort.

        Runs after the base hide/show filter (which matches the raw
        label) and before _derived_parameters (which computes levels on
        the final display labels). Mirrors v4 __transform_sensors ordering.
        """
        if not isinstance(self._stats, list):
            return
        self._apply_aliases(self._stats)
        self._stats = self._apply_mean_fold(self._stats)
        self._stats.sort(key=lambda r: natural_keys(str(r.get("label", ""))))

    def _read_aliases(self) -> dict[str, str]:
        """Parse `[sensors] alias=<label>:<name>,...` into a lower-keyed map."""
        raw = self.config.get("sensors", "alias", "")
        if not raw:
            return {}
        aliases: dict[str, str] = {}
        for pair in str(raw).split(","):
            parts = split_esc(pair.strip(), ":")
            if len(parts) >= 2 and parts[0]:
                aliases[parts[0].strip().lower()] = parts[1].strip()
        return aliases

    def _apply_aliases(self, rows: list) -> None:
        aliases = self._read_aliases()
        if not aliases:
            return
        for row in rows:
            label = str(row.get("label", ""))
            alias = aliases.get(label.lower())
            if alias:
                row["label"] = alias

    def _apply_mean_fold(self, rows: list) -> list:
        """Fold same-prefix sensors of each enabled type into `<prefix> (mean)`.

        A type is folded when the global `[sensors] mean` toggle is true,
        unless an explicit per-type `[sensors] <type>_mean` key overrides it
        (see `_mean_enabled`). Within a folded type, rows sharing a label
        prefix (label minus its trailing number) with >= 2 numeric members
        collapse to one row: value = round(mean), other fields copied from
        the first matched row. Non-numeric values (ERR/SLP/UNK) and
        singletons pass through unchanged.
        """
        result: list = []
        # Partition rows by type, preserving non-folded types verbatim.
        by_type: dict[str, list] = {}
        for row in rows:
            by_type.setdefault(str(row.get("type", "")), []).append(row)

        for sensor_type, type_rows in by_type.items():
            if not self._mean_enabled(sensor_type):
                result.extend(type_rows)
                continue
            result.extend(self._fold_group(type_rows))
        return result

    def _mean_enabled(self, sensor_type: str) -> bool:
        """Whether `sensor_type` should be mean-folded.

        The global `[sensors] mean` toggle sets the default for every type.
        An explicit per-type `[sensors] <type>_mean` key always wins over it
        — so a type can be opted OUT (`<type>_mean=false`) while the global
        is on, or opted IN while the global is off. Both default to false.

        Option names are stored lower-cased (ConfigParser optionxform) and
        the sensor-type constants are already lower-case, so the composed
        key matches the stored key directly.
        """
        per_type_key = f"{sensor_type}_mean"
        if per_type_key in self.config.section_keys("sensors"):
            return self.config.get("sensors", per_type_key, False)
        return self.config.get("sensors", "mean", False)

    @staticmethod
    def _fold_group(type_rows: list) -> list:
        """Group one type's rows by prefix; fold groups of >= 2 numeric members."""
        groups: dict[str, list] = {}
        order: list[str] = []
        for row in type_rows:
            prefix = _label_prefix(str(row.get("label", "")))
            if prefix not in groups:
                groups[prefix] = []
                order.append(prefix)
            groups[prefix].append(row)

        out: list = []
        for prefix in order:
            members = groups[prefix]
            numeric = [r for r in members if isinstance(r.get("value"), (int, float))]
            if len(numeric) >= 2:
                mean_value = int(sum(r["value"] for r in numeric) / len(numeric) + 0.5)
                base = dict(numeric[0])
                base["label"] = f"{prefix} (mean)"
                base["value"] = mean_value
                out.append(base)
                # Non-numeric members of the same prefix pass through.
                out.extend(r for r in members if not isinstance(r.get("value"), (int, float)))
            else:
                out.extend(members)
        return out

    # -------------------------------------------------- transform: alert levels

    def _derived_parameters(self) -> None:
        """Compute per-row alert levels with v4 precedence.

        Per row: per-sensor config (#2058) -> per-type config (#3049) ->
        hardware warning/critical -> no level. Battery compares on
        (100 - value) so a low charge alerts. Result:
        `_levels = {label: {"value": {"level", "prominent"}}}`.

        `prominent` is taken from the `value` field schema (not hardcoded)
        so it stays a single source of truth: `prominent: False` there ->
        coloured text with NO background highlight in the TUI.
        """
        self._levels = {}
        if not isinstance(self._stats, list):
            return
        prominent = bool(self.fields_description["value"].get("prominent", False))
        for row in self._stats:
            level = self._resolve_level(row)
            if level is None:
                continue
            self._levels[str(row.get("label", ""))] = {"value": {"level": level, "prominent": prominent}}

    def _resolve_level(self, row: dict) -> str | None:
        value = row.get("value")
        if not isinstance(value, (int, float)):
            return None  # ERR/SLP/UNK/NOS — no numeric comparison
        sensor_type = str(row.get("type", ""))
        label = str(row.get("label", ""))
        current = (100 - value) if sensor_type == _BATTERY else value

        careful, warning, critical = self._resolve_thresholds(sensor_type, label, row)
        if critical is None and warning is None and careful is None:
            return None  # no threshold source -> DEFAULT (no colour, no alert)
        if critical is not None and current >= critical:
            return "critical"
        if warning is not None and current >= warning:
            return "warning"
        if careful is not None and current >= careful:
            return "careful"
        return "ok"

    def _resolve_thresholds(
        self, sensor_type: str, label: str, row: dict
    ) -> tuple[float | None, float | None, float | None]:
        """Resolve (careful, warning, critical) from one coherent tier (v4 parity).

        v4 `update_views`/`get_alert` selects ONE tier — per-sensor (#2058),
        else per-type (#3049), else the hardware row — and reads ALL levels
        (careful/warning/critical) from that same tier. It never mixes (e.g.
        config critical + hardware warning). Mirror that: the first tier with
        at least one level set wins for every level. A config tier is selected
        on ANY of its three levels (#3627): the user is free to define only a
        warning, or only a careful. The hardware tier stays gated on `critical`
        alone — v4 `__get_system_thresholds` returns DEFAULT without it.

        The hardware tier has no `careful` (psutil exposes only
        high/critical), so careful is only ever supplied by a config tier —
        this preserves the shipped default `[sensors] temperature_core_careful`.

        Config option names are stored lower-cased (ConfigParser
        optionxform), so composed keys are lower-cased before lookup —
        otherwise a mixed-case label (`Core 0`) never matches the stored
        `temperature_core_core 0_critical` key.
        """
        # Tier 1: per-sensor config (#2058).
        per_sensor = self._conf_tier(f"{sensor_type}_{label}")
        if any(level is not None for level in per_sensor):
            return per_sensor
        # Tier 2: per-type config (#3049).
        per_type = self._conf_tier(sensor_type)
        if any(level is not None for level in per_type):
            return per_type
        # Tier 3: hardware system thresholds carried on the row (no careful).
        # v4 `__get_system_thresholds` returns DEFAULT when the row has no
        # critical, so the hardware tier is all-or-nothing on `critical`.
        hw_critical = _as_float(row.get("critical"))
        if hw_critical is None:
            return None, None, None
        return None, _as_float(row.get("warning")), hw_critical

    def _conf_tier(self, prefix: str) -> tuple[float | None, float | None, float | None]:
        """Read the (careful, warning, critical) triplet of one config tier."""
        return (
            self._conf_value(f"{prefix}_careful"),
            self._conf_value(f"{prefix}_warning"),
            self._conf_value(f"{prefix}_critical"),
        )

    def _conf_value(self, key: str) -> float | None:
        """Read a `[sensors]` threshold key (lower-cased) as float, else None."""
        raw = self.config.get("sensors", key.lower(), "")
        return _as_float(raw) if raw != "" else None
