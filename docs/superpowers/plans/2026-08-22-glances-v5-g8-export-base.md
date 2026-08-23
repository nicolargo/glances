# G8-1 — v5 export base and loop: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the v5 export contract (`GlancesExportBase`), the scheduler loop that drives it, and the discovery + CLI wiring — with no concrete exporter yet.

**Architecture:** `GlancesExportBase` is a synchronous class living in `glances/exports/export_base_v5.py`. It owns the v4 wire format (`build_export`, `normalize_for_influxdb`, `parse_tags`, `is_excluded`), plus two v5-specific payload-preparation steps: injecting the `key` field that v5 payloads lack, and merging the plugin's config section as flat `<plugin>_<key>` limits. `AsyncScheduler` gains a sibling task, `_export_loop()`, that calls `await asyncio.to_thread(exporter.update, plugins)` once per exporter per tick.

**Tech Stack:** Python 3.9+, asyncio, pytest + pytest-asyncio (auto mode), `glances.config_v5.GlancesConfigV5`, `glances.globals.json_dumps`.

**Spec:** `docs/superpowers/specs/2026-08-22-glances-v5-g8-exporters-design.md`

## Global Constraints

- **Never commit.** Every task ends with `git add`, never `git commit`. The maintainer commits personally. Never add a `Co-Authored-By` trailer.
- **Never touch `NEWS.rst`.** Changelog entries are written at release time only.
- **No v4 import leaks.** No file created or modified here may import `glances.exports.export`, `glances.stats`, `glances.config` or any `glances/exports/glances_*/__init__.py`. `glances.globals` and `glances.logger` are shared infrastructure and are allowed.
- **v4 code is read-only.** `glances/exports/export.py` and every `glances/exports/glances_*/__init__.py` must be byte-identical at the end of this plan. They are the reference to port *from*.
- **Wire format is iso-v4** except one rule: any limits key whose name contains `_action` is never exported (spec §5.4).
- **Perf budget:** one `asyncio.to_thread` handoff per exporter per tick, never per plugin. A handoff costs ~307 µs.
- Run the full suite with `uv run pytest -q`. Baseline at the start of this plan: **2513 passed, 1 skipped**.
- Style: the repo runs `ruff` via `make pre-commit`. Double quotes, `from __future__ import annotations`, SPDX header on every new file (copy the 8-line header from `glances/plugins/plugin/base_v5.py`).

---

## File Structure

| File | Responsibility |
|---|---|
| `glances/exports/export_base_v5.py` | `GlancesExportBase`: config helpers, wire format, payload preparation, `update()` orchestration, lifecycle. |
| `glances/plugins/plugin/base_v5.py` | Add the `EXPORTABLE` class flag. |
| `glances/plugins/quicklook/model_v5.py`, `version/model_v5.py`, `psutilversion/model_v5.py` | Set `EXPORTABLE = False`. |
| `glances/scheduler_v5.py` | `register_exporter()`, `_export_loop()`, `_export_refresh_time()`, exporter teardown in `stop()`. |
| `glances/main_v5.py` | `discover_exporters()`, CLI flags, wiring in `assemble()`. |
| `conf/glances.conf` | Document `[export] refresh`. |
| `tests/test_export_base_v5.py` | Contract tests for the base class. |
| `tests/test_export_loop_v5.py` | Scheduler-integration tests for the export loop. |

---

### Task 1: `EXPORTABLE` class flag

**Files:**
- Modify: `glances/plugins/plugin/base_v5.py` (add the ClassVar next to `DISPLAY_IN_TUI`, around line 92)
- Modify: `glances/plugins/quicklook/model_v5.py`, `glances/plugins/version/model_v5.py`, `glances/plugins/psutilversion/model_v5.py`
- Test: `tests/test_export_base_v5.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `GlancesPluginBase.EXPORTABLE: ClassVar[bool] = True`. Task 5 reads it to filter the registry.

- [ ] **Step 1: Write the failing test**

Create `tests/test_export_base_v5.py` with the standard 8-line SPDX header copied from `tests/test_plugin_base_v5.py`, then:

```python
"""Glances v5 — unit tests for GlancesExportBase.

Test stack: pytest + pytest-asyncio (auto mode). See architecture decisions §9.
"""

from __future__ import annotations

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5


class FakeScalarPlugin(GlancesPluginBase[dict]):
    plugin_name = "fakescalar"
    IS_COLLECTION = False
    fields_description = {
        "percent": {"description": "p", "unit": "percent"},
        "total": {"description": "t", "unit": "bytes"},
        "secret": {"description": "s", "unit": "string", "exportable": False},
    }

    def __init__(self, store, config, payload=None):
        super().__init__(store, config)
        self._payload = payload if payload is not None else {"percent": 50.0, "total": 1024, "secret": "x"}

    async def _grab_stats(self) -> dict:
        return dict(self._payload)


class FakeCollectionPlugin(GlancesPluginBase[list]):
    plugin_name = "fakecollection"
    IS_COLLECTION = True
    fields_description = {
        "name": {"description": "n", "unit": "string", "primary_key": True},
        "rx": {"description": "r", "unit": "bytespers"},
    }

    def __init__(self, store, config, payload=None):
        super().__init__(store, config)
        self._payload = payload if payload is not None else [
            {"name": "eth0", "rx": 10},
            {"name": "eth1", "rx": 20},
        ]

    async def _grab_stats(self) -> list:
        return [dict(item) for item in self._payload]


def test_exportable_defaults_to_true():
    assert GlancesPluginBase.EXPORTABLE is True
    assert FakeScalarPlugin.EXPORTABLE is True


def test_non_exportable_plugins_declare_the_flag():
    from glances.plugins.psutilversion.model_v5 import PluginModel as PsutilVersion
    from glances.plugins.quicklook.model_v5 import PluginModel as Quicklook
    from glances.plugins.version.model_v5 import PluginModel as Version

    assert Quicklook.EXPORTABLE is False
    assert Version.EXPORTABLE is False
    assert PsutilVersion.EXPORTABLE is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_export_base_v5.py -v`
Expected: FAIL — `AttributeError: type object 'GlancesPluginBase' has no attribute 'EXPORTABLE'`

- [ ] **Step 3: Add the flag to the base class**

In `glances/plugins/plugin/base_v5.py`, immediately after the `DISPLAY_IN_TUI` ClassVar and its docstring, add:

```python
    EXPORTABLE: ClassVar[bool] = True
    """Whether this plugin's stats are handed to the export modules.

    Mirrors v4's ``GlancesExport.non_exportable_plugins`` hard-coded list,
    inverted into a per-plugin declaration so that adding a plugin never
    requires editing a central list in the export layer. Read by
    ``GlancesExportBase.update()``.

    Set False for plugins whose payload is a presentation aggregate rather
    than a measurement (``quicklook`` re-states cpu/mem/load) or a constant
    string (``version``, ``psutilversion``)."""
```

- [ ] **Step 4: Set the flag on the three plugins**

In each of `glances/plugins/quicklook/model_v5.py`, `glances/plugins/version/model_v5.py`, `glances/plugins/psutilversion/model_v5.py`, add inside the `PluginModel` class body, next to the other ClassVar declarations (`plugin_name`, `IS_COLLECTION`, …):

```python
    EXPORTABLE = False
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_export_base_v5.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Verify no plugin regressed**

Run: `uv run pytest tests/ -k "v5" -q`
Expected: no new failures vs the 2513-passed baseline.

- [ ] **Step 7: Stage**

```bash
git add glances/plugins/plugin/base_v5.py \
        glances/plugins/quicklook/model_v5.py \
        glances/plugins/version/model_v5.py \
        glances/plugins/psutilversion/model_v5.py \
        tests/test_export_base_v5.py
```

Do NOT commit.

---

### Task 2: `GlancesExportBase` skeleton and config helpers

**Files:**
- Create: `glances/exports/export_base_v5.py`
- Test: `tests/test_export_base_v5.py` (append)

**Interfaces:**
- Consumes: `GlancesConfigV5.get`, `.get_value`, `.has_section` (all exist — see `glances/config_v5.py:237-305`).
- Produces:
  - `GlancesExportBase.__init__(self, config: GlancesConfigV5, args: argparse.Namespace)`
  - `GlancesExportBase.export_name: ClassVar[str]`
  - `.load_conf(section: str, mandatories=("host", "port"), options=()) -> bool`
  - `.is_excluded(field: str) -> bool`
  - `.parse_tags(tags: str | None) -> dict[str, str]`
  - `.exit() -> None`
  - abstract `.export(name: str, columns: list[str], points: list[Any]) -> None`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_export_base_v5.py`:

```python
from glances.exports.export_base_v5 import GlancesExportBase


class FakeExport(GlancesExportBase):
    export_name = "fake"

    def __init__(self, config, args):
        super().__init__(config, args)
        self.exported: list[tuple[str, list, list]] = []

    def export(self, name, columns, points):
        self.exported.append((name, list(columns), list(points)))


def make_config(sections: dict) -> GlancesConfigV5:
    config = GlancesConfigV5()
    config._merged = {s: dict(opts) for s, opts in sections.items()}
    return config


def test_load_conf_reads_mandatories_and_options():
    config = make_config({"backend": {"host": "localhost", "port": "8086", "prefix": "gl"}})
    exporter = FakeExport(config, args=None)
    ok = exporter.load_conf("backend", mandatories=("host", "port"), options=("prefix", "tags"))
    assert ok is True
    assert exporter.host == "localhost"
    assert exporter.port == "8086"
    assert exporter.prefix == "gl"
    assert getattr(exporter, "tags", None) is None


def test_load_conf_returns_false_on_missing_section():
    exporter = FakeExport(make_config({}), args=None)
    assert exporter.load_conf("backend") is False


def test_load_conf_returns_false_on_missing_mandatory():
    config = make_config({"backend": {"host": "localhost"}})
    exporter = FakeExport(config, args=None)
    assert exporter.load_conf("backend", mandatories=("host", "port")) is False


def test_is_excluded_uses_full_match_case_insensitive():
    config = make_config({"export": {"exclude_fields": r".*_critical,.*\.key$"}})
    exporter = FakeExport(config, args=None)
    assert exporter.is_excluded("cpu_critical") is True
    assert exporter.is_excluded("CPU_CRITICAL") is True
    assert exporter.is_excluded("eth0.key") is True
    assert exporter.is_excluded("percent") is False


def test_is_excluded_is_false_when_key_absent():
    exporter = FakeExport(make_config({}), args=None)
    assert exporter.is_excluded("anything") is False


def test_parse_tags():
    exporter = FakeExport(make_config({}), args=None)
    assert exporter.parse_tags("foo:bar,spam:eggs") == {"foo": "bar", "spam": "eggs"}
    assert exporter.parse_tags(None) == {}
    assert exporter.parse_tags("broken") == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_export_base_v5.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glances.exports.export_base_v5'`

- [ ] **Step 3: Create the package marker**

SUPERSEDED — no package marker is created. See the ruling below.

```python
"""v5 export base package."""
```

- [ ] **Step 4: Write the implementation**

Create `glances/exports/export_base_v5.py` with the SPDX header, then:

```python
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
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5
    from glances.plugins.plugin.base_v5 import GlancesPluginBase


class GlancesExportBase(ABC):
    """Base class every v5 export module derives from."""

    export_name: ClassVar[str] = ""
    """Short identifier — "csv", "influxdb2". Matches the directory suffix
    (``glances/exports/glances_<export_name>/``) and the CLI token accepted
    by ``--export``."""

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

        logger.debug("Init v5 export module %s", self.export_name or type(self).__name__)

    # ------------------------------------------------------------- config

    def load_conf(
        self,
        section: str,
        mandatories: tuple[str, ...] = ("host", "port"),
        options: tuple[str, ...] = (),
    ) -> bool:
        """Load ``[section]`` into instance attributes. v4 parity.

        Returns False when the section is missing or a mandatory key is
        absent — the caller decides whether that is fatal (it is, for every
        exporter shipped in G8: design §8).

        An optional key that is absent leaves the subclass's own default in
        place; it is NOT set to None, exactly like v4.
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

    # ---------------------------------------------------------- lifecycle

    @abstractmethod
    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        """Write one plugin's flattened stats to the backend."""

    def exit(self) -> None:
        """Release backend resources. Called from ``AsyncScheduler.stop()``."""
        logger.debug("Finalise v5 export interface %s", self.export_name)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_export_base_v5.py -v`
Expected: PASS (8 tests)

- [ ] **Step 6: Stage**

```bash
git add glances/exports/export_base_v5.py tests/test_export_base_v5.py
```

---

### Task 3: `build_export()` and `normalize_for_influxdb()` — verbatim v4 port

**Files:**
- Modify: `glances/exports/export_base_v5.py`
- Test: `tests/test_export_base_v5.py` (append)

**Interfaces:**
- Consumes: Task 2's `is_excluded`, `parse_tags`.
- Produces:
  - `.build_export(stats: dict | list) -> tuple[list[str], list[Any]]`
  - `.normalize_for_influxdb(name: str, columns: list[str], points: list[Any]) -> list[dict]`

Reference implementation to port: `glances/exports/export.py:288-345` (`build_export`) and `:163-232` (`normalize_for_influxdb`). Port them **verbatim** — same branches, same order, same comments. Do not "improve" them: their quirks (not sorting the dict, per issue #3449; `result` coerced to string, per issue #3419) are load-bearing.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_export_base_v5.py`:

```python
def test_build_export_flattens_a_scalar_payload():
    exporter = FakeExport(make_config({}), args=None)
    names, values = exporter.build_export({"percent": 50.0, "total": 1024})
    assert names == ["percent", "total"]
    assert values == [50.0, 1024]


def test_build_export_prefixes_items_with_the_key_value():
    exporter = FakeExport(make_config({}), args=None)
    names, values = exporter.build_export(
        [
            {"key": "name", "name": "eth0", "rx": 10},
            {"key": "name", "name": "eth1", "rx": 20},
        ]
    )
    assert names == ["eth0.key", "eth0.name", "eth0.rx", "eth1.key", "eth1.name", "eth1.rx"]
    assert values == ["name", "eth0", 10, "name", "eth1", 20]


def test_build_export_serialises_bool_and_joins_list():
    exporter = FakeExport(make_config({}), args=None)
    names, values = exporter.build_export({"flag": True, "cpus": [1, 2, 3]})
    assert dict(zip(names, values)) == {"flag": "true", "cpus": "1 2 3"}


def test_build_export_drops_excluded_fields():
    config = make_config({"export": {"exclude_fields": ".*_critical"}})
    exporter = FakeExport(config, args=None)
    names, _ = exporter.build_export({"percent": 1.0, "cpu_critical": 90.0})
    assert names == ["percent"]


def test_normalize_for_influxdb_turns_the_key_into_a_tag():
    exporter = FakeExport(make_config({}), args=None)
    exporter.tags = None
    exporter.hostname = "testhost"
    names, values = exporter.build_export([{"key": "name", "name": "eth0", "rx": 10}])
    measurements = exporter.normalize_for_influxdb("network", names, values)
    assert len(measurements) == 1
    measurement = measurements[0]
    assert measurement["measurement"] == "network"
    assert measurement["tags"]["hostname"] == "testhost"
    assert measurement["tags"]["name"] == "eth0"
    assert measurement["fields"]["rx"] == 10.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_export_base_v5.py -k "build_export or normalize" -v`
Expected: FAIL — `AttributeError: 'FakeExport' object has no attribute 'build_export'`

- [ ] **Step 3: Port the two methods**

First add the import `build_export()` needs, next to `from glances.logger import logger`:

```python
from glances.globals import json_dumps
```

Then add to `GlancesExportBase`, in a `# ---- wire format` section placed between the config helpers and the lifecycle hooks:

```python
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
```

Declare the two attributes `normalize_for_influxdb` reads on the class so type checkers and readers see them:

```python
    # Set by InfluxDB-family subclasses via load_conf(); read by normalize_for_influxdb().
    tags: str | None = None
    hostname: str | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_export_base_v5.py -v`
Expected: PASS (13 tests)

- [ ] **Step 5: Diff against v4 to prove the port is verbatim**

Run:

```bash
diff <(sed -n '288,345p' glances/exports/export.py) \
     <(sed -n '/def build_export/,/return export_names, export_values/p' glances/exports/export_base_v5.py)
```

Expected: differences limited to the docstring, type annotations and indentation. Any difference in a `if`/`for` branch is a porting bug — fix it before moving on.

- [ ] **Step 6: Stage**

```bash
git add glances/exports/export_base_v5.py tests/test_export_base_v5.py
```

---

### Task 4: Payload preparation — `_inject_key()` and `_merge_limits()`

**Files:**
- Modify: `glances/exports/export_base_v5.py`
- Test: `tests/test_export_base_v5.py` (append)

**Interfaces:**
- Consumes: `GlancesPluginBase._primary_key` (set in `__init__`, `glances/plugins/plugin/base_v5.py:184`), `GlancesConfigV5.items(section)`, `.get_float_value(section, option, default)`, `.get_value(section, option)`.
- Produces:
  - `._inject_key(plugin, payload: dict | list) -> dict | list`
  - `._limits_for(plugin) -> dict[str, Any]`
  - `._merge_limits(plugin, payload: dict | list) -> dict | list`

This is the task that carries the two v5-specific behaviours. Read spec §5.2, §5.3 and §5.4 before writing code.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_export_base_v5.py`:

```python
@pytest.mark.asyncio
async def test_inject_key_adds_the_primary_key_field_to_each_item():
    store = StatsStoreV5()
    plugin = FakeCollectionPlugin(store, make_config({}))
    await plugin.update()
    exporter = FakeExport(make_config({}), args=None)

    payload = exporter._inject_key(plugin, plugin.get_export())

    assert [item["key"] for item in payload] == ["name", "name"]
    names, _ = exporter.build_export(payload)
    assert "eth0.rx" in names
    assert "eth0.key" in names


@pytest.mark.asyncio
async def test_inject_key_leaves_a_scalar_payload_untouched():
    store = StatsStoreV5()
    plugin = FakeScalarPlugin(store, make_config({}))
    await plugin.update()
    exporter = FakeExport(make_config({}), args=None)

    payload = exporter._inject_key(plugin, plugin.get_export())

    assert "key" not in payload


def test_limits_for_flattens_the_plugin_section():
    config = make_config({
        "fakescalar": {"careful": "50", "warning": "70", "critical": "90"},
        "global": {"history_size": "1200"},
    })
    store = StatsStoreV5()
    plugin = FakeScalarPlugin(store, config)
    exporter = FakeExport(config, args=None)

    limits = exporter._limits_for(plugin)

    assert limits["fakescalar_careful"] == 50.0
    assert limits["fakescalar_warning"] == 70.0
    assert limits["fakescalar_critical"] == 90.0
    assert limits["history_size"] == 1200.0


def test_limits_for_splits_non_numeric_values_on_commas():
    config = make_config({"fakescalar": {"status_ok": "R,S,D"}})
    store = StatsStoreV5()
    plugin = FakeScalarPlugin(store, config)
    exporter = FakeExport(config, args=None)

    assert exporter._limits_for(plugin)["fakescalar_status_ok"] == ["R", "S", "D"]


def test_limits_for_never_exports_action_templates():
    """Security divergence from v4 — design §5.4.

    v4 merges the whole plugin section into the exported payload, so a
    shell command configured as an action leaves the machine in clear text.
    """
    config = make_config({
        "fakescalar": {
            "careful": "50",
            "critical_action": "/usr/bin/mail -s alert ops@example.com",
            "warning_action_repeat": "/usr/bin/logger boom",
        }
    })
    store = StatsStoreV5()
    plugin = FakeScalarPlugin(store, config)
    exporter = FakeExport(config, args=None)

    limits = exporter._limits_for(plugin)

    assert limits["fakescalar_careful"] == 50.0
    assert not [k for k in limits if "_action" in k]
    assert "/usr/bin/mail -s alert ops@example.com" not in str(limits.values())


def test_limits_for_is_cached_per_plugin():
    config = make_config({"fakescalar": {"careful": "50"}})
    store = StatsStoreV5()
    plugin = FakeScalarPlugin(store, config)
    exporter = FakeExport(config, args=None)

    first = exporter._limits_for(plugin)
    second = exporter._limits_for(plugin)

    assert first is second


@pytest.mark.asyncio
async def test_merge_limits_drops_the_disable_key():
    config = make_config({"fakescalar": {"careful": "50", "disable": "False"}})
    store = StatsStoreV5()
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()
    exporter = FakeExport(config, args=None)

    payload = exporter._merge_limits(plugin, plugin.get_export())

    assert payload["fakescalar_careful"] == 50.0
    assert "fakescalar_disable" not in payload


@pytest.mark.asyncio
async def test_merge_limits_applies_to_every_item_of_a_collection():
    config = make_config({"fakecollection": {"rx_careful": "60"}})
    store = StatsStoreV5()
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()
    exporter = FakeExport(config, args=None)

    payload = exporter._merge_limits(plugin, plugin.get_export())

    assert all(item["fakecollection_rx_careful"] == 60.0 for item in payload)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_export_base_v5.py -k "inject_key or limits" -v`
Expected: FAIL — `AttributeError: 'FakeExport' object has no attribute '_inject_key'`

- [ ] **Step 3: Write the implementation**

Add a `# ---- payload preparation (v5-specific)` section to `GlancesExportBase`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_export_base_v5.py -v`
Expected: PASS (21 tests)

- [ ] **Step 5: Stage**

```bash
git add glances/exports/export_base_v5.py tests/test_export_base_v5.py
```

---

### Task 5: `update()` orchestration

**Files:**
- Modify: `glances/exports/export_base_v5.py`
- Test: `tests/test_export_base_v5.py` (append)

**Interfaces:**
- Consumes: Tasks 1-4.
- Produces: `.update(plugins: list[GlancesPluginBase]) -> None` — synchronous, iterates the registry, calls `self.export()` once per exportable plugin.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_export_base_v5.py`:

```python
@pytest.mark.asyncio
async def test_update_exports_one_call_per_plugin():
    store = StatsStoreV5()
    config = make_config({})
    scalar = FakeScalarPlugin(store, config)
    collection = FakeCollectionPlugin(store, config)
    await scalar.update()
    await collection.update()
    exporter = FakeExport(config, args=None)

    exporter.update([scalar, collection])

    assert [name for name, _, _ in exporter.exported] == ["fakescalar", "fakecollection"]


@pytest.mark.asyncio
async def test_update_skips_non_exportable_plugins():
    class NotExportable(FakeScalarPlugin):
        plugin_name = "hidden"
        EXPORTABLE = False

    store = StatsStoreV5()
    config = make_config({})
    plugin = NotExportable(store, config)
    await plugin.update()
    exporter = FakeExport(config, args=None)

    exporter.update([plugin])

    assert exporter.exported == []


@pytest.mark.asyncio
async def test_update_skips_a_plugin_with_no_payload_yet():
    store = StatsStoreV5()
    config = make_config({})
    plugin = FakeScalarPlugin(store, config)  # never updated → store empty
    exporter = FakeExport(config, args=None)

    exporter.update([plugin])

    assert exporter.exported == []


@pytest.mark.asyncio
async def test_update_isolates_a_failing_plugin(caplog):
    class Boom(FakeExport):
        def export(self, name, columns, points):
            if name == "fakescalar":
                raise RuntimeError("backend down")
            super().export(name, columns, points)

    store = StatsStoreV5()
    config = make_config({})
    scalar = FakeScalarPlugin(store, config)
    collection = FakeCollectionPlugin(store, config)
    await scalar.update()
    await collection.update()
    exporter = Boom(config, args=None)

    with caplog.at_level("WARNING"):
        exporter.update([scalar, collection])

    assert [name for name, _, _ in exporter.exported] == ["fakecollection"]
    assert "backend down" in caplog.text


@pytest.mark.asyncio
async def test_update_output_carries_stats_limits_and_key():
    store = StatsStoreV5()
    config = make_config({"fakecollection": {"rx_careful": "60"}})
    collection = FakeCollectionPlugin(store, config)
    await collection.update()
    exporter = FakeExport(config, args=None)

    exporter.update([collection])

    _, names, values = exporter.exported[0]
    row = dict(zip(names, values))
    assert row["eth0.rx"] == 10
    assert row["eth0.key"] == "name"
    assert row["eth0.fakecollection_rx_careful"] == 60.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_export_base_v5.py -k "update" -v`
Expected: FAIL — `AttributeError: 'FakeExport' object has no attribute 'update'` (the inherited abstract class has none)

- [ ] **Step 3: Write the implementation**

Add to `GlancesExportBase`, above `export()`:

```python
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
        """
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_export_base_v5.py -v`
Expected: PASS (26 tests)

- [ ] **Step 5: Stage**

```bash
git add glances/exports/export_base_v5.py tests/test_export_base_v5.py
```

---

### Task 6: Scheduler export loop

**Files:**
- Modify: `glances/scheduler_v5.py`
- Test: `tests/test_export_loop_v5.py` (create)

**Interfaces:**
- Consumes: `GlancesExportBase.update(plugins)`, `.exit()`, `.export_name`.
- Produces:
  - `glances.exports.export_base_v5.resolve_export_refresh(config, global_refresh=None) -> float` — the single reader of `[export] refresh`. The G8-4 plan's `influxdb2` exporter calls it too.
  - `AsyncScheduler.register_exporter(exporter: GlancesExportBase) -> None`
  - `AsyncScheduler._export_refresh_time() -> float` (delegates to `resolve_export_refresh`)
  - `AsyncScheduler._export_loop() -> None` (internal, started by `run_forever()`)
  - `AsyncScheduler.stop()` now also calls `exporter.exit()` for each registered exporter.

- [ ] **Step 1: Write the failing test**

Create `tests/test_export_loop_v5.py` with the SPDX header, then:

```python
"""Glances v5 — unit tests for the scheduler's export loop (design §7)."""

from __future__ import annotations

import asyncio

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.exports.export_base_v5 import GlancesExportBase
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.scheduler_v5 import AsyncScheduler
from glances.stats_store_v5 import StatsStoreV5


class TinyPlugin(GlancesPluginBase[dict]):
    plugin_name = "tiny"
    IS_COLLECTION = False
    fields_description = {"percent": {"description": "p", "unit": "percent"}}

    async def _grab_stats(self) -> dict:
        return {"percent": 1.0}


class RecordingExport(GlancesExportBase):
    export_name = "recording"

    def __init__(self, config, args=None):
        super().__init__(config, args)
        self.ticks = 0
        self.exited = False

    def update(self, plugins):
        self.ticks += 1

    def export(self, name, columns, points):
        pass

    def exit(self):
        self.exited = True


def make_config(sections: dict) -> GlancesConfigV5:
    config = GlancesConfigV5()
    config._merged = {s: dict(opts) for s, opts in sections.items()}
    return config


@pytest.mark.asyncio
async def test_export_loop_ticks_while_the_scheduler_runs():
    config = make_config({"global": {"refresh": "0.05"}, "export": {"refresh": "0.05"}})
    store = StatsStoreV5()
    scheduler = AsyncScheduler(store, config)
    scheduler.register(TinyPlugin(store, config))
    exporter = RecordingExport(config)
    scheduler.register_exporter(exporter)

    task = asyncio.create_task(scheduler.run_forever())
    await asyncio.sleep(0.2)
    await scheduler.stop()
    task.cancel()

    assert exporter.ticks >= 2


@pytest.mark.asyncio
async def test_no_export_loop_when_no_exporter_registered():
    config = make_config({"global": {"refresh": "0.05"}})
    store = StatsStoreV5()
    scheduler = AsyncScheduler(store, config)
    scheduler.register(TinyPlugin(store, config))

    task = asyncio.create_task(scheduler.run_forever())
    await asyncio.sleep(0.1)
    running = len(scheduler._tasks)
    await scheduler.stop()
    task.cancel()

    assert running == 1  # the plugin loop only


def test_export_refresh_defaults_to_the_global_refresh():
    config = make_config({"global": {"refresh": "3"}})
    scheduler = AsyncScheduler(StatsStoreV5(), config)
    assert scheduler._export_refresh_time() == 3.0


def test_export_refresh_is_clamped_up_to_the_global_refresh(caplog):
    config = make_config({"global": {"refresh": "5"}, "export": {"refresh": "1"}})
    scheduler = AsyncScheduler(StatsStoreV5(), config)
    with caplog.at_level("WARNING"):
        value = scheduler._export_refresh_time()
    assert value == 5.0
    assert "clamped" in caplog.text.lower()


def test_export_refresh_honours_a_slower_setting():
    config = make_config({"global": {"refresh": "2"}, "export": {"refresh": "30"}})
    scheduler = AsyncScheduler(StatsStoreV5(), config)
    assert scheduler._export_refresh_time() == 30.0


@pytest.mark.asyncio
async def test_stop_calls_exit_on_every_exporter():
    config = make_config({"global": {"refresh": "0.05"}})
    store = StatsStoreV5()
    scheduler = AsyncScheduler(store, config)
    scheduler.register(TinyPlugin(store, config))
    exporter = RecordingExport(config)
    scheduler.register_exporter(exporter)

    await scheduler.stop()

    assert exporter.exited is True


@pytest.mark.asyncio
async def test_a_failing_exporter_does_not_stop_the_loop(caplog):
    class Boom(RecordingExport):
        export_name = "boom"

        def update(self, plugins):
            super().update(plugins)
            raise RuntimeError("nope")

    config = make_config({"global": {"refresh": "0.05"}, "export": {"refresh": "0.05"}})
    store = StatsStoreV5()
    scheduler = AsyncScheduler(store, config)
    scheduler.register(TinyPlugin(store, config))
    boom = Boom(config)
    good = RecordingExport(config)
    scheduler.register_exporter(boom)
    scheduler.register_exporter(good)

    task = asyncio.create_task(scheduler.run_forever())
    with caplog.at_level("WARNING"):
        await asyncio.sleep(0.2)
    await scheduler.stop()
    task.cancel()

    assert boom.ticks >= 2
    assert good.ticks >= 2
    assert "nope" in caplog.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_export_loop_v5.py -v`
Expected: FAIL — `AttributeError: 'AsyncScheduler' object has no attribute 'register_exporter'`

- [ ] **Step 3: Write the implementation**

In `glances/scheduler_v5.py`:

1. Add the import guard at the top of the `TYPE_CHECKING` block (or a plain import if the file has none):

```python
if TYPE_CHECKING:
    from glances.exports.export_base_v5 import GlancesExportBase
```

2. In `__init__`, after `self._tasks`:

```python
        self._exporters: list[GlancesExportBase] = []
```

3. Add, after `register()`:

```python
    def register_exporter(self, exporter: GlancesExportBase) -> None:
        """Register an export module. Its loop starts with `run_forever()`.

        Unlike plugins, exporters share ONE loop and ONE cadence
        (`[export] refresh`): a backend write is a batch operation, and
        staggering it per plugin would multiply round-trips for no gain.
        """
        if self._running:
            raise RuntimeError("Cannot register an exporter while the scheduler is running")
        self._exporters.append(exporter)
```

4. In `run_forever()`, replace the task-list construction with:

```python
        self._tasks = [asyncio.create_task(self._plugin_loop(entry)) for entry in self._entries]
        if self._exporters:
            self._tasks.append(asyncio.create_task(self._export_loop()))
```

5. Add the cadence resolver as a **module-level function in
`glances/exports/export_base_v5.py`**, not on the scheduler. The InfluxDB2
exporter needs the same value to size its write buffer (see the G8-4 plan), and
two independent readings of one config key drift:

```python
# Hard-coded fallback, matching the scheduler's own. Used only when neither
# [export] refresh nor [global] refresh is set.
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
```

Then, on the scheduler, next to `_global_refresh_time()`:

```python
    def _export_refresh_time(self) -> float:
        """Cadence of the export loop. Delegates to the export layer so the
        exporters and the loop never read `[export] refresh` differently."""
        from glances.exports.export_base_v5 import resolve_export_refresh

        return resolve_export_refresh(self.config, self._global_refresh_time())
```

The import is local: it keeps `glances.exports` out of the TUI's import graph
until an exporter is actually registered.

6. Add the loop next to `_plugin_loop()`:

```python
    async def _export_loop(self) -> None:
        """Single loop driving every registered exporter, forever.

        One `to_thread` handoff per exporter per tick — never per plugin.
        Every exporter here is blocking (file IO, HTTP clients), and a
        handoff costs ~307 µs, so 34 plugins × N exporters per tick would
        dominate the cycle.

        An exporter that raises is logged and kept: a backend that is
        momentarily down must not cost the operator their other exports,
        nor silently stop exporting once it comes back.
        """
        while True:
            plugins = [entry.plugin for entry in self._entries]
            for exporter in self._exporters:
                try:
                    await asyncio.to_thread(exporter.update, plugins)
                except Exception as e:
                    logger.warning("Export %s failed: %s", exporter.export_name, e)
            await asyncio.sleep(self._export_refresh_time())
```

7. In `stop()`, after the plugin teardown loop:

```python
        for exporter in self._exporters:
            try:
                await asyncio.to_thread(exporter.exit)
            except Exception as e:
                logger.warning("Scheduler: exit() of export %s failed: %s", exporter.export_name, e)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_export_loop_v5.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Verify the scheduler suite still passes**

Run: `uv run pytest tests/ -k "scheduler or v5" -q`
Expected: no new failures.

- [ ] **Step 6: Stage**

```bash
git add glances/scheduler_v5.py tests/test_export_loop_v5.py
```

---

### Task 7: Discovery, CLI flags and wiring

**Files:**
- Modify: `glances/main_v5.py` (`build_parser()` around line 76-140; new `discover_exporters()` next to `discover_plugins()` at line 285; `assemble()` at line 364)
- Modify: `conf/glances.conf` (the `[export]` section, line 795)
- Test: `tests/test_export_loop_v5.py` (append)

**Interfaces:**
- Consumes: `GlancesExportBase`, `AsyncScheduler.register_exporter`.
- Produces:
  - `discover_exporters(config, args) -> list[GlancesExportBase]`
  - CLI: `--export`, `--export-csv-file`, `--export-csv-overwrite`, `--export-json-file`
  - `args.export_<name>` booleans set from the `--export` comma list.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_export_loop_v5.py`:

```python
def test_export_flag_sets_per_exporter_booleans():
    from glances.main_v5 import build_parser

    args = build_parser().parse_args(["--export", "csv,influxdb2"])
    from glances.main_v5 import apply_export_flags

    apply_export_flags(args)

    assert args.export_csv is True
    assert args.export_influxdb2 is True
    assert getattr(args, "export_json", False) is False


def test_discover_exporters_returns_nothing_without_the_flag():
    from glances.main_v5 import build_parser, discover_exporters, apply_export_flags

    args = build_parser().parse_args([])
    apply_export_flags(args)

    assert discover_exporters(make_config({}), args) == []


def test_csv_and_json_file_flags_have_v4_defaults():
    from glances.main_v5 import build_parser

    args = build_parser().parse_args([])

    assert args.export_csv_file == "./glances.csv"
    assert args.export_json_file == "./glances.json"
    assert args.export_csv_overwrite is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_export_loop_v5.py -k "export_flag or discover_exporters or file_flags" -v`
Expected: FAIL — `ImportError: cannot import name 'apply_export_flags'`

- [ ] **Step 3: Add the CLI flags**

In `build_parser()`, after the `--enable-mcp` argument, add:

```python
    parser.add_argument(
        "--export",
        dest="export",
        metavar="<a,b>",
        help="Enable export modules (comma-separated list, e.g. csv,influxdb2).",
    )
    parser.add_argument(
        "--export-csv-file",
        dest="export_csv_file",
        default="./glances.csv",
        metavar="<path>",
        help="File path for the CSV exporter (default ./glances.csv).",
    )
    parser.add_argument(
        "--export-csv-overwrite",
        dest="export_csv_overwrite",
        action="store_true",
        help="Overwrite the CSV file instead of appending to it.",
    )
    parser.add_argument(
        "--export-json-file",
        dest="export_json_file",
        default="./glances.json",
        metavar="<path>",
        help="File path for the JSON exporter (default ./glances.json).",
    )
```

- [ ] **Step 4: Add `apply_export_flags()` and `discover_exporters()`**

Add both next to `discover_plugins()`:

```python
def apply_export_flags(args: argparse.Namespace) -> None:
    """Expand ``--export a,b`` into ``args.export_a = True`` booleans.

    v4 parity (`glances/main.py:755`): each exporter reads its own
    ``args.export_<name>`` rather than parsing the list itself.
    """
    if not getattr(args, "export", None):
        return
    for name in args.export.split(","):
        name = name.strip()
        if name:
            setattr(args, f"export_{name}", True)


def discover_exporters(config: GlancesConfigV5, args: argparse.Namespace) -> list[GlancesExportBase]:
    """Instantiate every exporter the user asked for on the command line.

    Looks for ``glances.exports.glances_<name>.export_v5`` modules carrying
    an ``Export`` class. A module whose optional client library is missing
    raises ImportError: that is FATAL when the user asked for it (they
    passed ``--export influxdb2`` and deserve to know the library is not
    installed), and invisible when they did not.
    """
    exporters: list[GlancesExportBase] = []

    for module_info in pkgutil.iter_modules(_exports_pkg.__path__):
        if not module_info.ispkg or not module_info.name.startswith("glances_"):
            continue
        name = module_info.name[len("glances_") :]
        if not getattr(args, f"export_{name}", False):
            continue

        full_name = f"glances.exports.{module_info.name}.export_v5"
        try:
            module = importlib.import_module(full_name)
        except ModuleNotFoundError as e:
            logger.critical("Export %s requested but unavailable (%s)", name, e)
            sys.exit(2)

        cls = getattr(module, "Export", None)
        if cls is None or not isinstance(cls, type) or not issubclass(cls, GlancesExportBase):
            logger.critical("Export %s: module %s has no usable Export class", name, full_name)
            sys.exit(2)

        exporters.append(cls(config, args))
        logger.info("Export module %s enabled", name)

    return exporters
```

Add the imports at the top of `main_v5.py`, next to `import glances.plugins as _plugins_pkg`:

```python
import glances.exports as _exports_pkg
from glances.exports.export_base_v5 import GlancesExportBase
```

- [ ] **Step 5: Wire into `assemble()`**

In `assemble()`, immediately after the plugin registration loop
(`for plugin in plugins: scheduler.register(plugin)`), add:

```python
    apply_export_flags(args)
    for exporter in discover_exporters(config, args):
        scheduler.register_exporter(exporter)
```

Export runs in both modes — the call sits before the `if args.server:` branch, not inside it (architecture §7.1: export is available in all modes).

- [ ] **Step 6: Document the config key**

In `conf/glances.conf`, in the existing `[export]` section (line 795), after the `exclude_fields` comment block, add:

```ini
# Export refresh rate, in seconds.
# Default: the [global] refresh rate — one export per collection cycle.
# A value lower than the global refresh is clamped up to it: exporting
# faster than the stats are collected duplicates points in the backend.
#refresh=10
```

The key stays commented: default behaviour is unchanged.

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/test_export_loop_v5.py -v`
Expected: PASS (10 tests)

- [ ] **Step 8: Verify the whole suite**

Run: `uv run pytest -q`
Expected: 2513 + the new tests passed, 1 skipped, **no new failures**.

- [ ] **Step 9: Smoke-test that nothing changed without `--export`**

Run: `timeout 8 uv run python -m glances.main_v5 -s --port 61299` then Ctrl-C (or let the timeout fire).
Expected: server starts, no export-related log line, no traceback.

- [ ] **Step 10: Stage**

```bash
git add glances/main_v5.py conf/glances.conf tests/test_export_loop_v5.py
```

---

### Task 8: Correct architecture §7.1 and §7.3

**Files:**
- Modify: `docs/architecture/glances-v5-architecture-decisions.md` (§7.1 around lines 938-942, §7.3 around line 970)

**Interfaces:** none — documentation only.

The architecture document is the baseline every future contributor reads. G8
diverges from it twice, deliberately (spec §4.2 and §6). Leaving the document
saying otherwise would make the next contributor "fix" the code back.

- [ ] **Step 1: Correct §7.1 — the config key**

Replace the `export_refresh_time` paragraph and its INI block (lines ~938-942):

```markdown
- An `[export] refresh` option controls how frequently exporters flush data. A
  value lower than the global refresh is clamped up to it — exporting faster
  than the plugins are polled duplicates points without adding information:
  ```ini
  [export]
  refresh=10   # export every 10s even if plugins refresh every 2s
  ```
  Superseded decision: earlier drafts of this section proposed a separate
  `[exports]` section with a `refresh_time` key. A second section one letter
  away from the existing `[export]` (which already holds `exclude_fields`) is a
  configuration trap, and `refresh` is the key name every other section uses.
  Implemented as `[export] refresh` in G8.
```

- [ ] **Step 2: Correct §7.3 — the async claim**

Replace line ~970 (`- \`GlancesExportBase.update()\` becomes async. Modules integrate into the main asyncio loop.`) with:

```markdown
- `GlancesExportBase.update()` stays **synchronous**; the coroutine boundary
  lives in `AsyncScheduler._export_loop()`, which calls
  `await asyncio.to_thread(exporter.update, plugins)` once per exporter per
  tick. Every backend client is blocking (file IO, `influxdb_client`,
  `prometheus_client`), so an `async def` whose body is entirely blocking would
  still need a finer-grained `to_thread` for no gain — and one handoff per
  exporter per tick beats one per plugin per exporter (~307 µs each).
  Superseded decision: this section previously required an async `update()`.
```

- [ ] **Step 3: Verify no other section contradicts the two corrections**

```bash
grep -n "exports\]\|export_refresh_time\|update() becomes async" docs/architecture/glances-v5-architecture-decisions.md
```

Expected: no hit outside the two blocks just rewritten.

- [ ] **Step 4: Stage**

```bash
git add docs/architecture/glances-v5-architecture-decisions.md
```

---

### Task 9: Run the pre-commit hooks

**Files:** all files touched by Tasks 1-8.

- [ ] **Step 1: Stage everything**

```bash
git add -A
```

gitleaks scans the index, so staging must happen before the hooks run.

- [ ] **Step 2: Run the hooks**

Run: `make pre-commit`
Expected: all ~23 hooks pass. `ruff` may reformat — restage and re-run if so.

- [ ] **Step 3: Re-run the full suite after any hook reformat**

Run: `uv run pytest -q`
Expected: unchanged pass count.

- [ ] **Step 4: Stage the final state**

```bash
git add -A
git status --short
```

Do NOT commit. Report the staged file list to the maintainer.
