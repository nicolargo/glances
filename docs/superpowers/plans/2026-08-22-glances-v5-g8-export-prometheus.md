# G8-3 — Prometheus exporter: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the Prometheus exporter onto the v5 export base.

**Architecture:** Prometheus is a pull backend: the exporter starts an HTTP server at init and thereafter only updates `Gauge` objects held in a dict. It implements `export()` and inherits the base `update()`, so it carries the merged limits like every non-CSV exporter. The one v5-specific adaptation is the source of each plugin's primary key: v4 read `stats.get_plugin(name).get_key()`, v5 reads `plugin._primary_key`.

**Tech Stack:** `prometheus_client` (optional dependency), pytest with the client mocked.

**Spec:** `docs/superpowers/specs/2026-08-22-glances-v5-g8-exporters-design.md` (§9, §10)

**Depends on:** `docs/superpowers/plans/2026-08-22-glances-v5-g8-export-base.md` (all 8 tasks complete).

## Global Constraints

- **Never commit.** Every task ends with `git add`, never `git commit`. The maintainer commits personally. Never add a `Co-Authored-By` trailer.
- **Never touch `NEWS.rst`.**
- **v4 code is read-only.** `glances/exports/glances_prometheus/__init__.py` must be byte-identical at the end of this plan.
- **`prometheus_client` is imported inside `__init__`, never at module level.** A module-level import makes discovery raise on a minimal install (spec §3).
- Fatal on init failure: `sys.exit(2)`, iso-v4 (design §8).
- Metric naming is iso-v4 — `<prefix>_<plugin>_<field>`, with ` .-/:[]` each replaced by `_`. Users' Prometheus rules and Grafana queries are keyed on these names.
- Run the full suite with `uv run pytest -q`.
- SPDX header on the new file (copy the 8-line header from `glances/exports/export_base_v5.py`).

---

## File Structure

| File | Responsibility |
|---|---|
| `glances/exports/glances_prometheus/export_v5.py` | `Export`: HTTP server at init, one `Gauge` per metric name, updated per cycle. |
| `tests/test_export_prometheus_v5.py` | Metric naming, label handling, primary-key resolution, non-numeric filtering, fatal init. |

---

### Task 1: Prometheus exporter

**Files:**
- Create: `glances/exports/glances_prometheus/export_v5.py`
- Test: `tests/test_export_prometheus_v5.py`

**Interfaces:**
- Consumes: `GlancesExportBase.__init__(config, args)`, `.load_conf(section, mandatories, options)`, `.parse_tags(tags)`, `.update(plugins)` (inherited unchanged), `GlancesPluginBase._primary_key`.
- Produces: `Export(GlancesExportBase)` with `export_name = "prometheus"`, `update(plugins)`, `export(name, columns, points)`, `init()`.

Reference to port from: `glances/exports/glances_prometheus/__init__.py` (99 lines).

- [ ] **Step 1: Write the failing test**

Create `tests/test_export_prometheus_v5.py` with the SPDX header, then:

```python
"""Glances v5 — unit tests for the Prometheus export module.

`prometheus_client` is mocked: these tests assert on metric names, labels
and values, not on a live HTTP endpoint.
"""

from __future__ import annotations

import sys
import types

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5


class FakeGauge:
    """Stand-in for prometheus_client.Gauge."""

    def __init__(self, name, doc, labelnames=()):
        self.name = name
        self.labelnames = list(labelnames)
        self.values: list[float] = []
        self.last_labels: dict | None = None

    def labels(self, **kwargs):
        self.last_labels = kwargs
        return self

    def set(self, value):
        self.values.append(value)


@pytest.fixture
def prometheus_client(monkeypatch):
    """Install a fake `prometheus_client` module for the duration of a test."""
    created: dict[str, FakeGauge] = {}
    started: list[dict] = []

    def gauge_factory(name, doc, labelnames=()):
        gauge = FakeGauge(name, doc, labelnames)
        created[name] = gauge
        return gauge

    module = types.ModuleType("prometheus_client")
    module.Gauge = gauge_factory
    module.start_http_server = lambda port, addr: started.append({"port": port, "addr": addr})
    monkeypatch.setitem(sys.modules, "prometheus_client", module)
    module.created = created
    module.started = started
    return module


class FakeScalarPlugin(GlancesPluginBase[dict]):
    plugin_name = "fakescalar"
    IS_COLLECTION = False
    fields_description = {
        "percent": {"description": "p", "unit": "percent"},
        "label": {"description": "l", "unit": "string"},
    }

    async def _grab_stats(self) -> dict:
        return {"percent": 50.0, "label": "not-a-number"}


class FakeCollectionPlugin(GlancesPluginBase[list]):
    plugin_name = "fakecollection"
    IS_COLLECTION = True
    fields_description = {
        "name": {"description": "n", "unit": "string", "primary_key": True},
        "rx": {"description": "r", "unit": "bytespers"},
    }

    async def _grab_stats(self) -> list:
        return [{"name": "eth0", "rx": 10}]


def make_config(sections: dict) -> GlancesConfigV5:
    config = GlancesConfigV5()
    config._merged = {s: dict(opts) for s, opts in sections.items()}
    return config


PROM_SECTION = {"prometheus": {"host": "127.0.0.1", "port": "9091", "labels": "src:glances"}}


def test_prometheus_starts_the_http_server(prometheus_client):
    from glances.exports.glances_prometheus.export_v5 import Export

    Export(make_config(PROM_SECTION), args=None)

    assert prometheus_client.started == [{"port": 9091, "addr": "127.0.0.1"}]


def test_prometheus_exits_when_the_section_is_missing(prometheus_client):
    from glances.exports.glances_prometheus.export_v5 import Export

    with pytest.raises(SystemExit) as excinfo:
        Export(make_config({}), args=None)
    assert excinfo.value.code == 2


def test_prometheus_exits_when_the_server_cannot_start(prometheus_client):
    def boom(port, addr):
        raise OSError("address already in use")

    prometheus_client.start_http_server = boom
    from glances.exports.glances_prometheus.export_v5 import Export

    with pytest.raises(SystemExit) as excinfo:
        Export(make_config(PROM_SECTION), args=None)
    assert excinfo.value.code == 2


@pytest.mark.asyncio
async def test_prometheus_metric_name_and_value(prometheus_client):
    from glances.exports.glances_prometheus.export_v5 import Export

    store = StatsStoreV5()
    config = make_config(PROM_SECTION)
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()

    exporter = Export(config, args=None)
    exporter.update([plugin])

    assert "glances_fakescalar_percent" in prometheus_client.created
    assert prometheus_client.created["glances_fakescalar_percent"].values == [50.0]


@pytest.mark.asyncio
async def test_prometheus_skips_non_numeric_fields(prometheus_client):
    from glances.exports.glances_prometheus.export_v5 import Export

    store = StatsStoreV5()
    config = make_config(PROM_SECTION)
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()

    exporter = Export(config, args=None)
    exporter.update([plugin])

    assert "glances_fakescalar_label" not in prometheus_client.created


@pytest.mark.asyncio
async def test_prometheus_turns_the_primary_key_into_a_label(prometheus_client):
    from glances.exports.glances_prometheus.export_v5 import Export

    store = StatsStoreV5()
    config = make_config(PROM_SECTION)
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()

    exporter = Export(config, args=None)
    exporter.update([plugin])

    gauge = prometheus_client.created["glances_fakecollection_rx"]
    assert gauge.last_labels == {"src": "glances", "name": "eth0"}
    assert gauge.values == [10.0]


@pytest.mark.asyncio
async def test_prometheus_honours_a_custom_prefix(prometheus_client):
    from glances.exports.glances_prometheus.export_v5 import Export

    sections = {"prometheus": dict(PROM_SECTION["prometheus"], prefix="myhost")}
    store = StatsStoreV5()
    config = make_config(sections)
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()

    exporter = Export(config, args=None)
    exporter.update([plugin])

    assert "myhost_fakescalar_percent" in prometheus_client.created


@pytest.mark.asyncio
async def test_prometheus_sanitises_characters_forbidden_in_metric_names(prometheus_client):
    from glances.exports.glances_prometheus.export_v5 import Export

    exporter = Export(make_config(PROM_SECTION), args=None)
    exporter.keys_name = {"fs": "mnt_point"}
    exporter.export("fs", ["/media/data.percent"], [42.0])

    assert "glances_fs_percent" in prometheus_client.created
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_export_prometheus_v5.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glances.exports.glances_prometheus.export_v5'`

- [ ] **Step 3: Write the implementation**

Create `glances/exports/glances_prometheus/export_v5.py` with the SPDX header, then:

```python
"""Glances v5 — Prometheus export module.

Ported from the v4 module in this directory.

Prometheus is a PULL backend: `start_http_server()` runs once at init and
the export cycle only refreshes `Gauge` values. Metric names are built
exactly as in v4 — `<prefix>_<plugin>_<field>`, every character in
` .-/:[]` replaced by `_` — because users' recording rules and Grafana
queries are keyed on them.

One v5 adaptation: v4 resolved a plugin's primary key through
`stats.get_plugin(name).get_key()`. v5 reads `plugin._primary_key`, which
`GlancesPluginBase` resolves once from `fields_description`.

`prometheus_client` is imported inside `__init__`, never at module level:
the exporter discovery walk imports this module on every start-up, and a
minimal install has no `prometheus_client`.
"""

from __future__ import annotations

import sys
from numbers import Number
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5
    from glances.plugins.plugin.base_v5 import GlancesPluginBase


class Export(GlancesExportBase):
    """Expose Glances stats as Prometheus gauges."""

    export_name = "prometheus"

    METRIC_SEPARATOR = "_"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)

        # Optional keys — left as None when absent, then defaulted below.
        self.prefix: str | None = None
        self.labels: str | None = None

        if not self.load_conf("prometheus", mandatories=("host", "port", "labels"), options=("prefix",)):
            logger.critical("Missing prometheus config")
            sys.exit(2)

        if self.prefix is None:
            self.prefix = "glances"
        if self.labels is None:
            self.labels = "src:glances"

        self._metric_dict: dict[str, Any] = {}
        # plugin name -> primary key field name (None for scalar plugins).
        self.keys_name: dict[str, str | None] = {}

        self.init()

    def init(self) -> None:
        """Start the Prometheus HTTP endpoint."""
        from prometheus_client import start_http_server

        try:
            start_http_server(port=int(self.port), addr=self.host)
        except Exception as e:
            logger.critical("Can not start Prometheus exporter on %s:%s (%s)", self.host, self.port, e)
            sys.exit(2)
        logger.info("Start Prometheus exporter on %s:%s", self.host, self.port)

    def update(self, plugins: list[GlancesPluginBase]) -> None:
        """Refresh the primary-key map, then run the standard export cycle."""
        self.keys_name = {plugin.plugin_name: getattr(plugin, "_primary_key", None) for plugin in plugins}
        super().update(plugins)

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        """Write one plugin's numeric fields to their gauges."""
        from prometheus_client import Gauge

        logger.debug("Export %s stats to Prometheus exporter", name)

        # Only numbers reach Prometheus; booleans convert to 1.0/0.0.
        data = {str(k): float(v) for k, v in zip(columns, points) if isinstance(v, Number)}

        for metric, value in data.items():
            labels = self.labels
            metric_name = self.prefix + self.METRIC_SEPARATOR + name + self.METRIC_SEPARATOR
            try:
                obj, stat = metric.split(".")
                metric_name += stat
                labels += f",{self.keys_name.get(name)}:{obj}"
            except ValueError:
                metric_name += metric

            # Prometheus is very sensitive to metric names.
            # See: https://prometheus.io/docs/practices/naming/
            for c in " .-/:[]":
                metric_name = metric_name.replace(c, self.METRIC_SEPARATOR)

            parsed_labels = self.parse_tags(labels)
            if metric_name not in self._metric_dict:
                self._metric_dict[metric_name] = Gauge(metric_name, "", labelnames=list(parsed_labels.keys()))
            gauge = self._metric_dict[metric_name]
            if hasattr(gauge, "labels"):
                # Add the labels (see issue #1255)
                gauge.labels(**parsed_labels).set(value)
            else:
                gauge.set(value)
```

Note: `metric.split(".")` raises `ValueError` when the metric has no dot **or more than one** — v4 relies on that to route both plain fields and multi-dot names to the un-labelled branch. Keep the `try/except ValueError`; do not replace it with a `"." in metric` check, which would behave differently for `/media/data.percent`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_export_prometheus_v5.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: End-to-end smoke test**

Requires `prometheus_client` installed (`uv run python -c "import prometheus_client"`). Skip this step if it is absent and say so in the task report.

Ensure `conf/glances.conf` has a `[prometheus]` section with `host`, `port`, `labels` (it does — line 992), then:

```bash
timeout 15 uv run python -m glances.main_v5 --quiet --export prometheus &
sleep 6
curl -s http://localhost:9091/metrics | grep -c '^glances_'
```

Expected: a non-zero count, and metric names of the form `glances_cpu_total`, `glances_network_rx{name="eth0",src="glances"}`.

- [ ] **Step 6: Verify the v4 module is untouched**

```bash
git diff --stat HEAD -- glances/exports/glances_prometheus/__init__.py
```

Expected: empty output.

- [ ] **Step 7: Stage**

```bash
git add glances/exports/glances_prometheus/export_v5.py tests/test_export_prometheus_v5.py
```

---

### Task 2: Run the hooks

**Files:** all files touched by Task 1.

- [ ] **Step 1: Run the full suite**

Run: `uv run pytest -q`
Expected: no new failures.

- [ ] **Step 2: Run the hooks**

```bash
git add -A
make pre-commit
```

Expected: all hooks pass. Restage and re-run if `ruff` reformats.

- [ ] **Step 3: Stage the final state**

```bash
git add -A
git status --short
```

Do NOT commit.
