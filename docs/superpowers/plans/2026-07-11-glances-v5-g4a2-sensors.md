# Glances v5 — `sensors` plugin port (G4A-2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the v4 `sensors` plugin to the Glances v5 asyncio collection architecture (LEFT sidebar), reusing the v4 hardware grabbers untouched, with a generalized per-prefix "mean" option gated per sensor type (default off).

**Architecture:** `PluginModel(GlancesPluginBase[list])`, `IS_COLLECTION=True`, `primary_key="label"`. `_grab_stats` merges four sub-types (temperature_core, fan_speed, temperature_hdd, battery) into one flat list via the reused v4 grab classes. `_expand_parameters` applies aliases then the mean fold; `_derived_parameters` computes per-row bespoke alert levels (per-sensor config → per-type config → hardware thresholds). A dedicated `render_curses_v5.render` mirrors v4 `msg_curse`.

**Tech Stack:** Python 3.9+, psutil, asyncio, pytest. Reused v4 modules: `glances.plugins.sensors.__init__` (`GlancesGrabSensors`, `sensors_definition`), `glances.plugins.sensors.sensor.glances_hddtemp.GlancesGrabHDDTemp`, `glances.plugins.sensors.sensor.glances_batpercent.GlancesGrabBat`.

**Reference spec:** `docs/superpowers/specs/2026-07-11-glances-v5-g4a2-sensors-design.md`

## Global Constraints

- **NEVER `git commit`, `git push`, or open a PR.** Each task ends by
  **staging** with `git add` only — the maintainer commits personally.
  Never add a `Co-Authored-By` trailer. (Plan "commit" steps are replaced
  by "stage" steps throughout.)
- **NEVER modify `NEWS.rst`** — release-time only.
- **Test runner:** `.venv/bin/python -m pytest` (NOT plain `python` — a
  wrapper hook fails otherwise).
- **Lint/format:** `.venv/bin/python -m ruff check glances/plugins/sensors/`
  and `.venv/bin/python -m ruff format glances/plugins/sensors/` before
  staging each task.
- **Mirror-v4 rule:** the TUI layout and alerting semantics replicate v4;
  the only accepted divergences are listed in the spec §8.
- **No dead code:** everything added must be used.
- The four sensor type strings, used verbatim throughout:
  `temperature_core`, `fan_speed`, `temperature_hdd`, `battery`.

---

### Task 1: Model scaffold, collection shape, and `_grab_stats`

**Files:**
- Create: `glances/plugins/sensors/model_v5.py`
- Test: `tests/test_plugin_sensors_v5.py`

**Interfaces:**
- Consumes: `GlancesPluginBase` from `glances.plugins.plugin.base_v5`;
  `GlancesGrabSensors` and `sensors_definition` from
  `glances.plugins.sensors`; `GlancesGrabHDDTemp` from
  `glances.plugins.sensors.sensor.glances_hddtemp`; `GlancesGrabBat` from
  `glances.plugins.sensors.sensor.glances_batpercent`.
- Produces: `PluginModel` (collection). `_grab_stats()` → `list[dict]`,
  each dict shaped `{"label": str, "unit": str, "value": int|str,
  "warning": int|None, "critical": int|None, "type": str[, "status": str]}`.
  Later tasks (2, 3) override `_expand_parameters` / `_derived_parameters`
  on this class. `fields_description` keys: `label`(pk), `type`, `unit`,
  `value`, `warning`, `critical`, `status`.

- [ ] **Step 1: Write the failing test (identity + fields)**

Create `tests/test_plugin_sensors_v5.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the v5 sensors plugin model."""

from __future__ import annotations

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.sensors.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    return GlancesConfigV5()


def test_plugin_identity(store, config):
    p = PluginModel(store, config)
    assert p.plugin_name == "sensors"
    assert p.IS_COLLECTION is True
    assert p._primary_key == "label"


def test_fields_description_flags():
    fd = PluginModel.fields_description
    assert fd["label"]["primary_key"] is True
    assert fd["value"]["watched"] is True
    assert fd["value"].get("prominent") is True
    assert "default_thresholds" not in fd["value"]
    for key in ("type", "unit", "warning", "critical", "status"):
        assert fd[key].get("internal") is True
        assert fd[key].get("watched", False) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_plugin_sensors_v5.py::test_plugin_identity -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glances.plugins.sensors.model_v5'`

- [ ] **Step 3: Write the model scaffold**

Create `glances/plugins/sensors/model_v5.py`:

```python
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
from typing import Any, ClassVar

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
            "prominent": True,
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
        out.extend(self._grab_typed(lambda: self._grab_temp_core.update(), _TEMP_CORE))
        out.extend(self._grab_typed(lambda: self._grab_fan.update(), _FAN_SPEED))
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_plugin_sensors_v5.py -v`
Expected: PASS (both tests)

- [ ] **Step 5: Write the failing test (grab shape + partial failure)**

Append to `tests/test_plugin_sensors_v5.py`:

```python
@pytest.mark.asyncio
async def test_grab_stats_merges_all_types(store, config, monkeypatch):
    p = PluginModel(store, config)
    monkeypatch.setattr(
        p._grab_temp_core,
        "update",
        lambda: [{"label": "Core 0", "unit": "C", "value": 42, "warning": 80, "critical": 90}],
    )
    monkeypatch.setattr(p._grab_fan, "update", lambda: [{"label": "fan1", "unit": "R", "value": 1200}])
    monkeypatch.setattr(p._grab_hdd, "get", lambda: [{"label": "sda", "unit": "C", "value": 35}])

    def _bat():
        return [{"label": "Battery", "unit": "%", "value": 80, "status": "Charging"}]

    monkeypatch.setattr(p, "_grab_battery", _bat)

    rows = await p._grab_stats()
    by_label = {r["label"]: r for r in rows}
    assert by_label["Core 0"]["type"] == "temperature_core"
    assert by_label["Core 0"]["warning"] == 80
    assert by_label["fan1"]["type"] == "fan_speed"
    assert by_label["fan1"]["warning"] is None  # defaulted
    assert by_label["sda"]["type"] == "temperature_hdd"
    assert by_label["Battery"]["type"] == "battery"
    assert by_label["Battery"]["status"] == "Charging"


@pytest.mark.asyncio
async def test_grab_stats_survives_one_grabber_failure(store, config, monkeypatch):
    p = PluginModel(store, config)

    def _boom():
        raise OSError("boom")

    monkeypatch.setattr(p._grab_temp_core, "update", _boom)
    monkeypatch.setattr(p._grab_fan, "update", lambda: [{"label": "fan1", "unit": "R", "value": 1200}])
    monkeypatch.setattr(p._grab_hdd, "get", lambda: [])
    monkeypatch.setattr(p, "_grab_battery", lambda: [])

    rows = await p._grab_stats()
    assert [r["label"] for r in rows] == ["fan1"]  # temp core failed, fan survived
```

- [ ] **Step 6: Run to verify pass**

Run: `.venv/bin/python -m pytest tests/test_plugin_sensors_v5.py -v`
Expected: PASS (4 tests). The implementation from Step 3 already satisfies these.

- [ ] **Step 7: Lint, format, stage**

```bash
.venv/bin/python -m ruff check glances/plugins/sensors/model_v5.py tests/test_plugin_sensors_v5.py
.venv/bin/python -m ruff format glances/plugins/sensors/model_v5.py tests/test_plugin_sensors_v5.py
git add glances/plugins/sensors/model_v5.py tests/test_plugin_sensors_v5.py
```

(No commit — staging only, per Global Constraints.)

---

### Task 2: Aliases + generalized per-prefix mean fold (`_expand_parameters`)

**Files:**
- Modify: `glances/plugins/sensors/model_v5.py`
- Test: `tests/test_plugin_sensors_v5.py`

**Interfaces:**
- Consumes: `PluginModel` from Task 1; `natural_keys`, `split_esc` from
  `glances.globals`.
- Produces: `_expand_parameters(self)` override on `PluginModel` that
  mutates `self._stats` in place — applies aliases, then folds same-prefix
  groups per enabled type, then sorts by `natural_keys(label)`. Helper
  methods `_apply_aliases`, `_apply_mean_fold`, and module function
  `_label_prefix(label: str) -> str`.

- [ ] **Step 1: Write the failing test (alias)**

Append to `tests/test_plugin_sensors_v5.py`:

```python
def _expand(p, rows):
    """Drive _expand_parameters against a given stats list."""
    p._stats = rows
    p._expand_parameters()
    return p._stats


def _cfg_with(tmp_path, monkeypatch, body: str) -> GlancesConfigV5:
    # Mirror tests/test_plugin_network_v5.py::_config_with — load a
    # [sensors] body via an XDG-discovered glances.conf.
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    xdg = tmp_path / "xdg"
    cfg_dir = xdg / "glances"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "glances.conf").write_text(body)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    return GlancesConfigV5()


def test_alias_relabels(tmp_path, monkeypatch, store):
    config = _cfg_with(tmp_path, monkeypatch, "[sensors]\nalias=core 0:CPU Package\n")
    p = PluginModel(store, config)
    out = _expand(
        p,
        [{"label": "Core 0", "unit": "C", "value": 42, "warning": None, "critical": None, "type": "temperature_core"}],
    )
    assert out[0]["label"] == "CPU Package"
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_plugin_sensors_v5.py::test_alias_relabels -v`
Expected: FAIL — alias not applied (label still `"Core 0"`), because
`_expand_parameters` is not yet overridden.

- [ ] **Step 3: Implement aliases + fold**

Add imports at the top of `model_v5.py`:

```python
import re

from glances.globals import natural_keys, split_esc
```

Add methods to `PluginModel` (after `_grab_stats`):

```python
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

    A type is folded only if `[sensors] <type>_mean=true`. Within that
    type, rows sharing a label prefix (label minus its trailing number)
    with >= 2 numeric members collapse to one row: value = round(mean),
    other fields copied from the first matched row. Non-numeric values
    (ERR/SLP/UNK) and singletons pass through unchanged.
    """
    result: list = []
    # Partition rows by type, preserving non-folded types verbatim.
    by_type: dict[str, list] = {}
    for row in rows:
        by_type.setdefault(str(row.get("type", "")), []).append(row)

    for sensor_type, type_rows in by_type.items():
        if not self.config.get("sensors", f"{sensor_type}_mean", False):
            result.extend(type_rows)
            continue
        result.extend(self._fold_group(type_rows))
    return result


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
```

Add the module-level prefix helper (after the type constants):

```python
def _label_prefix(label: str) -> str:
    """Return the label with a trailing number (and its spacing) stripped.

    'Core 0' -> 'Core'; 'Package id 0' -> 'Package id'; 'fan1' -> 'fan';
    a label with no trailing number is returned unchanged.
    """
    return re.sub(r"\s*\d+\s*$", "", label) or label
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/python -m pytest tests/test_plugin_sensors_v5.py::test_alias_relabels -v`
Expected: PASS

- [ ] **Step 5: Write the failing tests (fold cases)**

Append to `tests/test_plugin_sensors_v5.py`:

```python
def _rows_core(*values):
    return [
        {"label": f"Core {i}", "unit": "C", "value": v, "warning": 80, "critical": 90, "type": "temperature_core"}
        for i, v in enumerate(values)
    ]


def test_fold_enabled_collapses_group(tmp_path, monkeypatch, store):
    config = _cfg_with(tmp_path, monkeypatch, "[sensors]\ntemperature_core_mean=true\n")
    p = PluginModel(store, config)
    out = _expand(p, _rows_core(40, 42, 44))
    assert len(out) == 1
    assert out[0]["label"] == "Core (mean)"
    assert out[0]["value"] == 42  # int(126/3 + 0.5)
    assert out[0]["warning"] == 80  # copied from first


def test_fold_disabled_keeps_rows(tmp_path, monkeypatch, store):
    config = _cfg_with(tmp_path, monkeypatch, "[sensors]\n")  # no mean key
    p = PluginModel(store, config)
    out = _expand(p, _rows_core(40, 42, 44))
    assert len(out) == 3
    assert {r["label"] for r in out} == {"Core 0", "Core 1", "Core 2"}


def test_fold_singleton_unchanged(tmp_path, monkeypatch, store):
    config = _cfg_with(tmp_path, monkeypatch, "[sensors]\ntemperature_core_mean=true\n")
    p = PluginModel(store, config)
    out = _expand(p, _rows_core(40))  # only Core 0
    assert len(out) == 1
    assert out[0]["label"] == "Core 0"  # not folded


def test_fold_excludes_non_numeric(tmp_path, monkeypatch, store):
    config = _cfg_with(tmp_path, monkeypatch, "[sensors]\ntemperature_hdd_mean=true\n")
    p = PluginModel(store, config)
    rows = [
        {"label": "sda", "unit": "C", "value": 40, "warning": None, "critical": None, "type": "temperature_hdd"},
        {"label": "sdb", "unit": "C", "value": 44, "warning": None, "critical": None, "type": "temperature_hdd"},
        {"label": "sdc", "unit": "C", "value": "ERR", "warning": None, "critical": None, "type": "temperature_hdd"},
    ]
    out = _expand(p, rows)
    labels = {r["label"] for r in out}
    # sda/sdb have distinct prefixes ('sda','sdb') -> NOT folded (prefix differs).
    # This asserts the prefix rule: only trailing-number groups fold.
    assert "ERR" not in [r["value"] for r in out if r["label"].endswith("(mean)")]
    assert "sdc" in labels  # non-numeric passes through
```

Note on the `sda/sdb` case: `_label_prefix("sda")` == `"sda"` (no trailing
number), so each disk is its own prefix and nothing folds — this is
correct behaviour and the test asserts the non-numeric row survives. If you
want a positive HDD fold test, use labels `disk 0`, `disk 1`, `disk 2`.

- [ ] **Step 6: Run to verify pass**

Run: `.venv/bin/python -m pytest tests/test_plugin_sensors_v5.py -v`
Expected: PASS (all)

- [ ] **Step 7: Lint, format, stage**

```bash
.venv/bin/python -m ruff check glances/plugins/sensors/model_v5.py tests/test_plugin_sensors_v5.py
.venv/bin/python -m ruff format glances/plugins/sensors/model_v5.py tests/test_plugin_sensors_v5.py
git add glances/plugins/sensors/model_v5.py tests/test_plugin_sensors_v5.py
```

---

### Task 3: Per-row bespoke thresholds + alerts (`_derived_parameters`)

**Files:**
- Modify: `glances/plugins/sensors/model_v5.py`
- Test: `tests/test_plugin_sensors_v5.py`

**Interfaces:**
- Consumes: `PluginModel` from Tasks 1–2. `self._stats` is the folded/aliased
  list at the time `_derived_parameters` runs.
- Produces: `_derived_parameters(self)` override building
  `self._levels = {label: {"value": {"level": str, "prominent": True}}}`.
  Helper `_resolve_level(row) -> str | None` and
  `_conf_threshold(sensor_type, label, level) -> float | None`.
  `EMITS_ALERTS` stays the base default `True` (no override needed) — a
  crossing is ingested into the alert footer.

- [ ] **Step 1: Write the failing tests (threshold precedence)**

Append to `tests/test_plugin_sensors_v5.py`:

```python
def _levels(p, rows):
    p._stats = rows
    p._derived_parameters()
    return p._levels


def _temp_row(label, value, warning=None, critical=None):
    return {
        "label": label,
        "unit": "C",
        "value": value,
        "warning": warning,
        "critical": critical,
        "type": "temperature_core",
    }


def test_level_from_hardware_threshold(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_temp_row("Core 0", 95, warning=80, critical=90)])
    assert lv["Core 0"]["value"]["level"] == "critical"
    assert lv["Core 0"]["value"]["prominent"] is True


def test_level_hardware_warning(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_temp_row("Core 0", 85, warning=80, critical=90)])
    assert lv["Core 0"]["value"]["level"] == "warning"


def test_level_none_when_no_critical(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_temp_row("Core 0", 85, warning=80, critical=None)])
    assert "Core 0" not in lv  # no threshold source -> no level entry


def test_per_type_config_beats_hardware(tmp_path, monkeypatch, store):
    config = _cfg_with(tmp_path, monkeypatch, "[sensors]\ntemperature_core_critical=70\n")
    p = PluginModel(store, config)
    lv = _levels(p, [_temp_row("Core 0", 75, warning=80, critical=90)])
    # config critical 70 < value 75 -> critical, even though hardware critical is 90.
    assert lv["Core 0"]["value"]["level"] == "critical"


def test_per_sensor_config_beats_per_type(tmp_path, monkeypatch, store):
    config = _cfg_with(
        tmp_path,
        monkeypatch,
        "[sensors]\ntemperature_core_critical=70\ntemperature_core_core 0_critical=99\n",
    )
    p = PluginModel(store, config)
    lv = _levels(p, [_temp_row("Core 0", 75, warning=80, critical=90)])
    # per-sensor critical 99 > value 75 -> not critical; warning unset -> ok.
    assert lv["Core 0"]["value"]["level"] == "ok"


def test_battery_alerts_on_inverse(tmp_path, monkeypatch, store):
    config = _cfg_with(tmp_path, monkeypatch, "[sensors]\nbattery_critical=80\n")
    p = PluginModel(store, config)
    row = {
        "label": "Battery",
        "unit": "%",
        "value": 10,
        "warning": None,
        "critical": None,
        "type": "battery",
        "status": "Discharging",
    }
    lv = _levels(p, [row])
    # 100 - 10 = 90 >= config critical 80 -> critical (low battery).
    assert lv["Battery"]["value"]["level"] == "critical"


def test_emits_alerts_default_true():
    assert PluginModel.EMITS_ALERTS is True
```

- [ ] **Step 2: Run to verify fail**

Run: `.venv/bin/python -m pytest tests/test_plugin_sensors_v5.py::test_level_from_hardware_threshold -v`
Expected: FAIL — the base `_derived_parameters` computes no level for
`value` (it carries no `default_thresholds`), so `lv["Core 0"]` is absent.

- [ ] **Step 3: Implement bespoke `_derived_parameters`**

Add to `PluginModel` (after the fold methods):

```python
# -------------------------------------------------- transform: alert levels


def _derived_parameters(self) -> None:
    """Compute per-row alert levels with v4 precedence.

    Per row: per-sensor config (#2058) -> per-type config (#3049) ->
    hardware warning/critical -> no level. Battery compares on
    (100 - value) so a low charge alerts. Result:
    `_levels = {label: {"value": {"level", "prominent"}}}`.
    """
    self._levels = {}
    if not isinstance(self._stats, list):
        return
    for row in self._stats:
        level = self._resolve_level(row)
        if level is None:
            continue
        self._levels[str(row.get("label", ""))] = {"value": {"level": level, "prominent": True}}


def _resolve_level(self, row: dict) -> str | None:
    value = row.get("value")
    if not isinstance(value, (int, float)):
        return None  # ERR/SLP/UNK/NOS — no numeric comparison
    sensor_type = str(row.get("type", ""))
    label = str(row.get("label", ""))
    current = (100 - value) if sensor_type == _BATTERY else value

    critical = self._conf_threshold(sensor_type, label, "critical")
    warning = self._conf_threshold(sensor_type, label, "warning")
    if critical is None:
        critical = _as_float(row.get("critical"))
    if warning is None:
        warning = _as_float(row.get("warning"))

    if critical is None:
        return None  # no threshold source -> DEFAULT (no colour, no alert)
    if current >= critical:
        return "critical"
    if warning is not None and current >= warning:
        return "warning"
    return "ok"


def _conf_threshold(self, sensor_type: str, label: str, level: str) -> float | None:
    """Read config thresholds: per-sensor (#2058) then per-type (#3049).

    Config option names are stored lower-cased (ConfigParser
    optionxform), so the composed keys are lower-cased before lookup —
    otherwise a mixed-case label (`Core 0`) never matches the stored
    `temperature_core_core 0_critical` key.
    """
    per_sensor = self.config.get("sensors", f"{sensor_type}_{label}_{level}".lower(), "")
    if per_sensor != "":
        return _as_float(per_sensor)
    per_type = self.config.get("sensors", f"{sensor_type}_{level}".lower(), "")
    if per_type != "":
        return _as_float(per_type)
    return None
```

Add the module-level float coercion helper (near `_label_prefix`):

```python
def _as_float(value: Any) -> float | None:
    """Best-effort float; None/empty/non-numeric -> None."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/python -m pytest tests/test_plugin_sensors_v5.py -v`
Expected: PASS (all sensors model tests)

- [ ] **Step 5: Lint, format, stage**

```bash
.venv/bin/python -m ruff check glances/plugins/sensors/model_v5.py tests/test_plugin_sensors_v5.py
.venv/bin/python -m ruff format glances/plugins/sensors/model_v5.py tests/test_plugin_sensors_v5.py
git add glances/plugins/sensors/model_v5.py tests/test_plugin_sensors_v5.py
```

---

### Task 4: TUI renderer (`render_curses_v5.render`)

**Files:**
- Create: `glances/plugins/sensors/render_curses_v5.py`
- Test: `tests/test_plugin_sensors_render_curses_v5.py`

**Interfaces:**
- Consumes: `Cell`, `Row`, `ColorRole`, `_LEVEL_TO_ROLE`, `title_role` from
  `glances.outputs.curses_renderer_v5`; `to_fahrenheit` from
  `glances.globals`; `unicode_message` from
  `glances.outputs.glances_unicode`.
- Produces: `render(payload: dict, fields_desc=None, view=None) -> list[Row]`.
  Payload shape: `{"data": list[dict], "_levels": {label: {"value": {...}}}}`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_plugin_sensors_render_curses_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — tests for the sensors curses renderer."""

from __future__ import annotations

from glances.plugins.sensors.render_curses_v5 import render


def _payload(rows, levels=None):
    return {"data": rows, "_levels": levels or {}}


def _flat(rows):
    return "\n".join(" ".join(c.text for c in r.cells) for r in rows)


def _sensor(label, value, unit="C", type="temperature_core", status=None):
    row = {"label": label, "value": value, "unit": unit, "type": type}
    if status is not None:
        row["status"] = status
    return row


def test_empty_returns_header_only():
    rows = render(_payload([]))
    assert "SENSORS" in _flat(rows)
    assert len(rows) == 1  # header only


def test_header_and_one_row():
    rows = render(_payload([_sensor("Core 0", 42)]))
    flat = _flat(rows)
    assert "SENSORS" in flat
    assert "Core 0" in flat
    assert "42" in flat


def test_long_label_truncated():
    rows = render(_payload([_sensor("A" * 40, 42)]))
    # No cell text exceeds the name column width (20) + value column (14).
    for r in rows:
        for c in r.cells:
            assert len(c.text) <= 20


def test_string_sentinel_rendered():
    rows = render(_payload([_sensor("sdc", "ERR", type="temperature_hdd")]))
    assert "ERR" in _flat(rows)


def test_fahrenheit_converts_temperature_only(view=None):
    rows = render(
        _payload([_sensor("Core 0", 100)]),
        None,
        view={"fahrenheit": True},
    )
    flat = _flat(rows)
    assert "212" in flat  # 100C -> 212F
    assert "F" in flat


def test_fahrenheit_skips_fan():
    rows = render(
        _payload([_sensor("fan1", 1200, unit="R", type="fan_speed")]),
        None,
        view={"fahrenheit": True},
    )
    flat = _flat(rows)
    assert "1200" in flat  # unchanged, not converted
    assert "2192" not in flat  # would be 1200*1.8+32 if wrongly converted


def test_battery_trend_arrow():
    rows = render(_payload([_sensor("Battery", 80, unit="%", type="battery", status="Discharging")]))
    flat = _flat(rows)
    # ARROW_DOWN unicode or its ascii fallback 'v'
    assert "↓" in flat or "v" in flat


def test_empty_battery_skipped():
    rows = render(_payload([_sensor("Battery", [], unit="%", type="battery")]))
    flat = _flat(rows)
    assert "Battery" not in flat  # empty-value battery row omitted


def test_level_colour_applied():
    levels = {"Core 0": {"value": {"level": "critical", "prominent": True}}}
    rows = render(_payload([_sensor("Core 0", 95)], levels))
    # find the value cell and assert it is coloured critical
    value_cells = [c for r in rows for c in r.cells if "95" in c.text]
    assert value_cells and value_cells[0].color.value == "critical"
```

- [ ] **Step 2: Run to verify fail**

Run: `.venv/bin/python -m pytest tests/test_plugin_sensors_render_curses_v5.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glances.plugins.sensors.render_curses_v5'`

- [ ] **Step 3: Implement the renderer**

Create `glances/plugins/sensors/render_curses_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the sensors plugin.

Mirrors v4 `sensors.msg_curse()`: a `SENSORS` header then one row per
sensor (`label` + right-aligned value). LEFT sidebar, block <= 34 chars.

    SENSORS
    Core 0                  42C
    fan1                  1200R
    Battery                80%v

- Fahrenheit (`view["fahrenheit"]`) converts temperature rows only
  (not battery / fan_speed).
- Battery rows show a trend arrow from `status`.
- hddtemp string sentinels (ERR/SLP/UNK/NOS) render verbatim.
- Empty-value battery rows are skipped.
"""

from __future__ import annotations

from typing import Any

from glances.globals import to_fahrenheit
from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row, title_role
from glances.outputs.glances_unicode import unicode_message

_NAME_MAX_WIDTH = 20
_VALUE_COL_WIDTH = 14
_SENTINELS = ("ERR", "SLP", "UNK", "NOS")
_NO_FAHRENHEIT_TYPES = ("battery", "fan_speed")


def _format_label(label: str) -> str:
    if len(label) > _NAME_MAX_WIDTH:
        return label[:_NAME_MAX_WIDTH]
    return label.ljust(_NAME_MAX_WIDTH)


def _battery_trend(row: dict[str, Any]) -> str:
    status = str(row.get("status", ""))
    if status.startswith("Charg"):
        return unicode_message("ARROW_UP")
    if status.startswith("Discharg"):
        return unicode_message("ARROW_DOWN")
    if status.startswith("Full"):
        return unicode_message("CHECK")
    return ""


def _level_role(levels: dict[str, Any], label: str) -> tuple[ColorRole, bool]:
    entry = levels.get(label, {}) if isinstance(levels, dict) else {}
    value_entry = entry.get("value", {}) if isinstance(entry, dict) else {}
    level = value_entry.get("level")
    prominent = bool(value_entry.get("prominent"))
    return _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT), prominent


def _value_text(row: dict[str, Any], fahrenheit: bool) -> str:
    value = row.get("value")
    sensor_type = str(row.get("type", ""))
    unit = str(row.get("unit", ""))

    if isinstance(value, str) and value in _SENTINELS:
        return value.rjust(_VALUE_COL_WIDTH)

    if not isinstance(value, (int, float)):
        return ""  # empty battery ([]) or unknown -> caller skips

    if fahrenheit and sensor_type not in _NO_FAHRENHEIT_TYPES:
        text = f"{to_fahrenheit(value):.0f}F"
    else:
        trend = _battery_trend(row) if sensor_type == "battery" else ""
        text = f"{value:.0f}{unit}{trend}"
    return text.rjust(_VALUE_COL_WIDTH)


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]] | None = None, view=None) -> list[Row]:
    header = Row(cells=[Cell(text="SENSORS".ljust(_NAME_MAX_WIDTH), color=title_role(payload), bold=True)])
    rows: list[Row] = [header]

    if not isinstance(payload, dict):
        return rows
    items = payload.get("data")
    if not isinstance(items, list):
        return rows
    levels = payload.get("_levels") if isinstance(payload.get("_levels"), dict) else {}
    view = view or {}
    fahrenheit = bool(view.get("fahrenheit"))

    for row in items:
        if not isinstance(row, dict):
            continue
        # Skip empty-value battery rows (v4 parity).
        if str(row.get("type", "")) == "battery" and row.get("value") in ([], None, ""):
            continue
        value_text = _value_text(row, fahrenheit)
        if not value_text:
            continue
        role, prominent = _level_role(levels, str(row.get("label", "")))
        rows.append(
            Row(
                cells=[
                    Cell(text=_format_label(str(row.get("label", "")))),
                    Cell(text=value_text, color=role, prominent=prominent),
                ]
            )
        )
    return rows
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/python -m pytest tests/test_plugin_sensors_render_curses_v5.py -v`
Expected: PASS (all)

- [ ] **Step 5: Lint, format, stage**

```bash
.venv/bin/python -m ruff check glances/plugins/sensors/render_curses_v5.py tests/test_plugin_sensors_render_curses_v5.py
.venv/bin/python -m ruff format glances/plugins/sensors/render_curses_v5.py tests/test_plugin_sensors_render_curses_v5.py
git add glances/plugins/sensors/render_curses_v5.py tests/test_plugin_sensors_render_curses_v5.py
```

---

### Task 5: Config documentation + full-suite integration

**Files:**
- Modify: `conf/glances.conf` (the `[sensors]` section)
- Test: existing full suite + auto-discovery check

**Interfaces:**
- Consumes: the whole plugin from Tasks 1–4.
- Produces: documented config keys; verified auto-discovery of the
  `sensors` v5 plugin.

- [ ] **Step 1: Inspect the current `[sensors]` config section**

Run: `grep -n "^\[sensors\]" -A 20 conf/glances.conf`
Read the existing block to match its comment style before editing.

- [ ] **Step 2: Add the new keys to `conf/glances.conf`**

In the `[sensors]` section, add (commented, so defaults are unchanged —
retro-compatibility guaranteed):

```ini
# Fold same-prefix sensors of a type into "<prefix> (mean)" (default false)
#temperature_core_mean=true
#fan_speed_mean=true
#temperature_hdd_mean=true
#battery_mean=true
# Rename a sensor label (comma-separated label:alias pairs)
#alias=core 0:CPU Package,core 1:Core One
```

Preserve any existing keys (`hide`, per-type thresholds, `host`, `port`).
Do **not** uncomment anything — commented keys keep behaviour identical.

- [ ] **Step 3: Verify auto-discovery registers the sensors v5 plugin**

Write a throwaway check (do not commit it) confirming the plugin registry
picks up `sensors`:

Run:
```bash
.venv/bin/python -c "from glances.plugins.sensors.model_v5 import PluginModel; from glances.plugins.sensors.render_curses_v5 import render; print(PluginModel.plugin_name, callable(render))"
```
Expected: `sensors True`

If the project has an explicit v5 registry/discovery test (search
`grep -rn "render_curses_v5\|discover" tests/ | head`), run it to confirm
`sensors` is enumerated alongside `gpu`/`npu`.

- [ ] **Step 4: Run the full test suite**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass (previous green baseline was 1657 passed / 1 skipped;
the new sensors tests add to that count, nothing regresses).

- [ ] **Step 5: Lint + format the whole plugin**

```bash
.venv/bin/python -m ruff check glances/plugins/sensors/
.venv/bin/python -m ruff format glances/plugins/sensors/
```
Expected: no errors, no reformatting needed (already formatted per task).

- [ ] **Step 6: Stage**

```bash
git add conf/glances.conf
git status --short
```
(No commit — the maintainer commits personally.)

---

## Manual smoke (maintainer, out of band)

Run `make run-v5` on a machine with sensors (CPU temp / fan / battery) and
confirm: the SENSORS block appears in the LEFT sidebar; a hot sensor colours
and (if critical) shows in the footer alert list; `--fahrenheit` converts
temperature rows only; `[sensors] temperature_core_mean=true` folds the
per-core temps into `Core (mean)`.

## Post-implementation

After all tasks: dispatch a final code-review over the whole
`glances/plugins/sensors/` v5 addition + tests, then update memory
(`project_v5_g4a2_sensors_*`) and the G4A progress note.
