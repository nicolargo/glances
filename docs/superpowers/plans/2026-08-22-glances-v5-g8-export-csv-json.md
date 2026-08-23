# G8-2 — CSV and JSON exporters: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the two file-based exporters — `csv` and `json` — onto the v5 export base.

**Architecture:** Both override `update()` rather than implementing `export()` alone, because both need to see a whole cycle before writing: CSV emits one row per cycle with a stable header, JSON truncates and rewrites its file per cycle. Both write through plain file IO inside the worker thread the scheduler hands them.

**Tech Stack:** Python stdlib `csv`, `glances.globals.json_dumps` (orjson), pytest `tmp_path`.

**Spec:** `docs/superpowers/specs/2026-08-22-glances-v5-g8-exporters-design.md` (§9, §10)

**Depends on:** `docs/superpowers/plans/2026-08-22-glances-v5-g8-export-base.md` (all 8 tasks complete).

## Global Constraints

- **Never commit.** Every task ends with `git add`, never `git commit`. The maintainer commits personally. Never add a `Co-Authored-By` trailer.
- **Never touch `NEWS.rst`.**
- **v4 code is read-only.** `glances/exports/glances_csv/__init__.py` and `glances/exports/glances_json/__init__.py` must be byte-identical at the end of this plan.
- **No v4 import leaks.** Neither new module may import `glances.exports.export`.
- **CSV carries no limits — JSON does.** This asymmetry is v4 behaviour, not an oversight: v4's CSV exporter overrides `update()` and reads `getAllExportsAsDict()` directly, bypassing the parent's limits merge, while JSON goes through the parent. Reproduce it exactly. See Task 1 Step 3.
- Fatal on init failure: `sys.exit(2)`, iso-v4 (design §8).
- **Lifecycle lock (added by G8-1's final review, after this plan was written).**
  `GlancesExportBase` holds a non-reentrant `threading.Lock`, taken by the base
  `update()` and by `exit()`. Two rules follow, and both are tested in Task 3:
  1. An overriding `exit()` MUST call `super().exit()` **first** — acquiring and
     releasing the lock is the barrier that waits for an in-flight `update()`
     running in a worker thread. Teardown after the barrier is safe because the
     scheduler cancels the export task before calling `exit()`.
  2. An `update()` override that does NOT call `super().update()` — the CSV
     exporter — must take `self._lifecycle_lock` itself, or the barrier has
     nothing to wait for. Never take the lock *and* call `super().update()`:
     the lock is not reentrant and that deadlocks.
- Run the full suite with `uv run pytest -q`.
- SPDX header on every new file (copy the 8-line header from `glances/exports/export_base_v5.py`).

---

## File Structure

| File | Responsibility |
|---|---|
| `glances/exports/glances_csv/export_v5.py` | `Export`: one CSV row per cycle, header written once and checked on append. |
| `glances/exports/glances_json/export_v5.py` | `Export`: one JSON object per cycle, file truncated each time. |
| `tests/test_export_csv_v5.py` | Real file assertions on `tmp_path`, including the header-mismatch path. |
| `tests/test_export_json_v5.py` | Real file assertions on `tmp_path`. |

Shared test scaffolding (`FakeScalarPlugin`, `FakeCollectionPlugin`, `make_config`) is duplicated in each test module rather than imported across test files — the repo's v5 test modules are self-contained, and a shared conftest fixture would couple six exporter test modules to one file.

---

### Task 1: CSV exporter

**Files:**
- Create: `glances/exports/glances_csv/export_v5.py`
- Test: `tests/test_export_csv_v5.py`

**Interfaces:**
- Consumes: `GlancesExportBase.__init__(config, args)`, `.build_export(payload)`, `._inject_key(plugin, payload)`, `.export_name`.
- Produces: `Export(GlancesExportBase)` with `export_name = "csv"`, `update(plugins)`, `export(name, columns, points)` (no-op), `exit()`.

Reference to port from: `glances/exports/glances_csv/__init__.py` (117 lines).

- [ ] **Step 1: Write the failing test**

Create `tests/test_export_csv_v5.py`. It MUST start with the repo's 8-line SPDX header — the
repository carries a `.reuse/` configuration and a licensing hook checks it:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the CSV export module."""

from __future__ import annotations

import argparse
import csv as csv_module

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
    }

    async def _grab_stats(self) -> dict:
        return {"percent": 50.0, "total": 1024}


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


def make_args(path, overwrite=False) -> argparse.Namespace:
    return argparse.Namespace(export_csv_file=str(path), export_csv_overwrite=overwrite)


@pytest.mark.asyncio
async def test_csv_writes_header_then_one_row_per_cycle(tmp_path):
    from glances.exports.glances_csv.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({})
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()

    path = tmp_path / "glances.csv"
    exporter = Export(config, make_args(path))
    exporter.update([plugin])
    exporter.update([plugin])
    exporter.exit()

    rows = list(csv_module.reader(path.open()))
    assert rows[0] == ["timestamp", "fakescalar.percent", "fakescalar.total"]
    assert len(rows) == 3
    assert rows[1][1:] == ["50.0", "1024"]


@pytest.mark.asyncio
async def test_csv_prefixes_collection_items_with_the_primary_key(tmp_path):
    from glances.exports.glances_csv.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({})
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()

    path = tmp_path / "glances.csv"
    exporter = Export(config, make_args(path))
    exporter.update([plugin])
    exporter.exit()

    header = list(csv_module.reader(path.open()))[0]
    assert "fakecollection.eth0.rx" in header


@pytest.mark.asyncio
async def test_csv_never_writes_limit_columns(tmp_path):
    """v4 parity: the CSV exporter bypasses the limits merge."""
    from glances.exports.glances_csv.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({"fakescalar": {"careful": "50", "warning": "70"}})
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()

    path = tmp_path / "glances.csv"
    exporter = Export(config, make_args(path))
    exporter.update([plugin])
    exporter.exit()

    header = list(csv_module.reader(path.open()))[0]
    assert not [column for column in header if "careful" in column or "warning" in column]


@pytest.mark.asyncio
async def test_csv_appends_to_an_existing_file_with_a_matching_header(tmp_path):
    from glances.exports.glances_csv.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({})
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()
    path = tmp_path / "glances.csv"

    first = Export(config, make_args(path))
    first.update([plugin])
    first.exit()

    second = Export(config, make_args(path))
    second.update([plugin])
    second.exit()

    rows = list(csv_module.reader(path.open()))
    assert len(rows) == 3  # header + one row per run
    assert rows[0][0] == "timestamp"


@pytest.mark.asyncio
async def test_csv_refuses_to_append_when_headers_differ(tmp_path, caplog):
    from glances.exports.glances_csv.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({})
    path = tmp_path / "glances.csv"
    path.write_text("timestamp,something.else\n2026-01-01 00:00:00,1\n")

    plugin = FakeScalarPlugin(store, config)
    await plugin.update()
    exporter = Export(config, make_args(path))
    with caplog.at_level("ERROR"):
        exporter.update([plugin])
    exporter.exit()

    rows = list(csv_module.reader(path.open()))
    assert len(rows) == 2  # nothing appended
    assert "Headers are different" in caplog.text


@pytest.mark.asyncio
async def test_csv_overwrite_flag_truncates(tmp_path):
    from glances.exports.glances_csv.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({})
    path = tmp_path / "glances.csv"
    path.write_text("timestamp,something.else\n2026-01-01 00:00:00,1\n")

    plugin = FakeScalarPlugin(store, config)
    await plugin.update()
    exporter = Export(config, make_args(path, overwrite=True))
    exporter.update([plugin])
    exporter.exit()

    rows = list(csv_module.reader(path.open()))
    assert rows[0] == ["timestamp", "fakescalar.percent", "fakescalar.total"]
    assert len(rows) == 2


def test_csv_exits_when_the_file_cannot_be_opened(tmp_path):
    from glances.exports.glances_csv.export_v5 import Export

    unreachable = tmp_path / "no-such-dir" / "glances.csv"
    with pytest.raises(SystemExit) as excinfo:
        Export(make_config({}), make_args(unreachable))
    assert excinfo.value.code == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_export_csv_v5.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glances.exports.glances_csv.export_v5'`

- [ ] **Step 3: Write the implementation**

Create `glances/exports/glances_csv/export_v5.py` with the SPDX header, then:

```python
"""Glances v5 — CSV export module.

Ported from the v4 module in this directory. Two behaviours are preserved
deliberately:

- **The header is written once and checked on append.** Restarting Glances
  against an existing CSV whose columns no longer match must not corrupt
  the file, so a mismatch logs an error and writes nothing (issue #1525).
- **No limits are exported.** v4's CSV exporter overrides ``update()`` and
  reads the plugins' export payloads directly, bypassing the limits merge
  that every other exporter inherits. A CSV therefore carries measurements
  only. Reproduced here so existing CSV pipelines keep their column set.
"""

from __future__ import annotations

import csv
import os.path
import sys
import time
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5
    from glances.plugins.plugin.base_v5 import GlancesPluginBase


class Export(GlancesExportBase):
    """Write one CSV row per export cycle."""

    export_name = "csv"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace) -> None:
        super().__init__(config, args)

        self.csv_filename = args.export_csv_file

        # Overwrite, or append to an existing file after a header check.
        if not os.path.isfile(self.csv_filename) or args.export_csv_overwrite:
            file_mode = "w"
            self.old_header: list[str] | None = None
        else:
            file_mode = "a"
            try:
                with open(self.csv_filename, newline="") as existing:
                    self.old_header = next(csv.reader(existing), None)
            except OSError as e:
                logger.critical("Cannot open existing CSV file: %s", e)
                sys.exit(2)

        try:
            self.csv_file = open(self.csv_filename, file_mode, newline="")
        except OSError as e:
            logger.critical("Cannot create the CSV file: %s", e)
            sys.exit(2)
        self.writer = csv.writer(self.csv_file)

        logger.info("Stats exported to CSV file: %s", self.csv_filename)
        self.first_line = True

    def update(self, plugins: list[GlancesPluginBase]) -> None:
        """Write the header (first cycle only) then one row of values.

        Overrides the base implementation: a CSV row spans every plugin, so
        the whole cycle must be assembled before anything is written.

        Takes ``self._lifecycle_lock`` explicitly. The base ``update()``
        takes it, but this override never calls ``super().update()``, so
        without this the lock would never be held on the CSV path and
        ``exit()``'s barrier would have nothing to wait for — ``stop()``
        could close ``self.csv_file`` mid-row.
        """
        with self._lifecycle_lock:
            self._write_cycle(plugins)

    def _write_cycle(self, plugins: list[GlancesPluginBase]) -> None:
        """One CSV row. Always called with ``_lifecycle_lock`` held."""
        csv_header: list[str] = ["timestamp"]
        csv_data: list[Any] = [time.strftime("%Y-%m-%d %H:%M:%S")]

        for plugin in plugins:
            if not getattr(plugin, "EXPORTABLE", True):
                continue
            payload = plugin.get_export()
            if not payload:
                continue
            payload = self._inject_key(plugin, payload)
            export_names, export_values = self.build_export(payload)
            csv_header += [f"{plugin.plugin_name}.{name}" for name in export_names]
            csv_data += export_values

        if self.first_line:
            if self.old_header is None:
                self.writer.writerow(csv_header)
            elif self.old_header != csv_header:
                logger.error("Cannot append data to existing CSV file. Headers are different.")
                logger.debug("Old header: %s", self.old_header)
                logger.debug("New header: %s", csv_header)
            else:
                self.old_header = None
            self.first_line = False

        if self.old_header is None:
            self.writer.writerow(csv_data)
            self.csv_file.flush()

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        """Unused — everything happens in update()."""

    def exit(self) -> None:
        # super().exit() FIRST: acquiring and releasing the lock is a barrier
        # that waits for any in-flight update() to finish. Only then is it
        # safe to close the file — the scheduler has already cancelled the
        # export task, so no new update() can start after the barrier.
        super().exit()
        self.csv_file.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_export_csv_v5.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: End-to-end smoke test**

Run:

```bash
timeout 12 uv run python -m glances.main_v5 --quiet --export csv --export-csv-file /tmp/g5.csv
head -c 400 /tmp/g5.csv
```

Expected: a header line starting with `timestamp,` and at least one data row. Columns are `<plugin>.<field>`, with no `*_careful` / `*_action` columns.

- [ ] **Step 6: Stage**

```bash
git add glances/exports/glances_csv/export_v5.py tests/test_export_csv_v5.py
```

---

### Task 2: JSON exporter

**Files:**
- Create: `glances/exports/glances_json/export_v5.py`
- Test: `tests/test_export_json_v5.py`

**Interfaces:**
- Consumes: `GlancesExportBase.__init__(config, args)`, `.build_export`, `._inject_key`, `._merge_limits`.
- Produces: `Export(GlancesExportBase)` with `export_name = "json"`, `update(plugins)`, `export(name, columns, points)`, `exit()`.

Reference to port from: `glances/exports/glances_json/__init__.py` (60 lines).

Unlike CSV, the JSON exporter **does** carry the merged limits: v4's JSON module implements only `export()` and inherits the parent `update()`, which merges them.

v4 buffers per plugin and flushes when the first plugin of the list comes round again — a sentinel needed only because the parent owned the loop. In v5 the exporter owns its own `update()`, so the buffer is built and written in one pass. Same file, same format: a single JSON object, rewritten (not appended) each cycle.

- [ ] **Step 1: Write the failing test**

Create `tests/test_export_json_v5.py`. It MUST start with the repo's 8-line SPDX header — the
repository carries a `.reuse/` configuration and a licensing hook checks it:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the JSON export module."""

from __future__ import annotations

import argparse
import json

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
    }

    async def _grab_stats(self) -> dict:
        return {"percent": 50.0, "total": 1024}


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


def make_args(path) -> argparse.Namespace:
    return argparse.Namespace(export_json_file=str(path))


@pytest.mark.asyncio
async def test_json_writes_one_object_per_cycle(tmp_path):
    from glances.exports.glances_json.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({})
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()

    path = tmp_path / "glances.json"
    exporter = Export(config, make_args(path))
    exporter.update([plugin])
    exporter.exit()

    payload = json.loads(path.read_text())
    assert payload["fakescalar"]["percent"] == 50.0
    assert payload["fakescalar"]["total"] == 1024


@pytest.mark.asyncio
async def test_json_rewrites_the_file_each_cycle(tmp_path):
    from glances.exports.glances_json.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({})
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()

    path = tmp_path / "glances.json"
    exporter = Export(config, make_args(path))
    exporter.update([plugin])
    exporter.update([plugin])
    exporter.exit()

    assert len(path.read_text().strip().splitlines()) == 1


@pytest.mark.asyncio
async def test_json_carries_the_merged_limits(tmp_path):
    """Unlike CSV, the JSON exporter inherits v4's limits merge."""
    from glances.exports.glances_json.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({"fakescalar": {"careful": "50"}})
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()

    path = tmp_path / "glances.json"
    exporter = Export(config, make_args(path))
    exporter.update([plugin])
    exporter.exit()

    payload = json.loads(path.read_text())
    assert payload["fakescalar"]["fakescalar_careful"] == 50.0


@pytest.mark.asyncio
async def test_json_never_carries_action_templates(tmp_path):
    from glances.exports.glances_json.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({"fakescalar": {"careful": "50", "critical_action": "/usr/bin/mail ops@example.com"}})
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()

    path = tmp_path / "glances.json"
    exporter = Export(config, make_args(path))
    exporter.update([plugin])
    exporter.exit()

    assert "/usr/bin/mail" not in path.read_text()


@pytest.mark.asyncio
async def test_json_prefixes_collection_items(tmp_path):
    from glances.exports.glances_json.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({})
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()

    path = tmp_path / "glances.json"
    exporter = Export(config, make_args(path))
    exporter.update([plugin])
    exporter.exit()

    payload = json.loads(path.read_text())
    assert payload["fakecollection"]["eth0.rx"] == 10


def test_json_exits_when_the_file_cannot_be_created(tmp_path):
    from glances.exports.glances_json.export_v5 import Export

    unreachable = tmp_path / "no-such-dir" / "glances.json"
    with pytest.raises(SystemExit) as excinfo:
        Export(make_config({}), make_args(unreachable))
    assert excinfo.value.code == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_export_json_v5.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glances.exports.glances_json.export_v5'`

- [ ] **Step 3: Write the implementation**

Create `glances/exports/glances_json/export_v5.py` with the SPDX header, then:

```python
"""Glances v5 — JSON export module.

Ported from the v4 module in this directory. The file holds ONE JSON
object describing the latest cycle and is rewritten — not appended — every
time, exactly as in v4. Consumers tail the file and re-read it whole.

v4 buffered per plugin and flushed when the first plugin of the list came
round again; that sentinel existed only because the parent class owned the
plugin loop. In v5 the exporter owns its own ``update()``, so the buffer is
assembled and written in one pass. Same output, no sentinel.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase
from glances.globals import json_dumps
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5
    from glances.plugins.plugin.base_v5 import GlancesPluginBase


class Export(GlancesExportBase):
    """Write the whole cycle to a JSON file."""

    export_name = "json"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace) -> None:
        super().__init__(config, args)

        self.json_filename = args.export_json_file

        # Fail fast on an unwritable path rather than at the first cycle.
        # Snap's strict confinement blocks at open(), so the open() call
        # itself must be inside the try — not just the write.
        try:
            with open(self.json_filename, "w"):
                pass
        except OSError as e:
            logger.critical("Cannot create the JSON file: %s", e)
            sys.exit(2)

        logger.info("Exporting stats to file: %s", self.json_filename)
        self.buffer: dict[str, Any] = {}

    def update(self, plugins: list[GlancesPluginBase]) -> None:
        """Fill the buffer from every exportable plugin, then flush once."""
        self.buffer = {}
        super().update(plugins)

        try:
            with open(self.json_filename, "wb") as json_file:
                json_file.write(json_dumps(self.buffer) + b"\n")
        except Exception as e:
            logger.error("Can not export data to JSON (%s)", e)

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        """Buffer one plugin's flattened stats. Flushed by update()."""
        self.buffer[name] = dict(zip(columns, points))

    def exit(self) -> None:
        # Nothing to release — each flush opens and closes its own handle.
        # super().exit() is still called for the barrier, so the pattern is
        # uniform across exporters and a future resource added here is
        # protected by default.
        super().exit()
```

Note the shape: `update()` delegates the per-plugin loop to `super().update()` — which applies the `EXPORTABLE` filter, the `key` injection and the limits merge — and only owns the flush. That is why JSON carries limits and CSV does not.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_export_json_v5.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: End-to-end smoke test**

Run:

```bash
timeout 12 uv run python -m glances.main_v5 --quiet --export json --export-json-file /tmp/g5.json
python -c "import json; d=json.load(open('/tmp/g5.json')); print(sorted(d)[:8]); print(d['cpu'])"
```

Expected: a plugin list, and a `cpu` object carrying both measurements (`total`, `user`, …) and merged limits (`cpu_careful`, …), with no `*_action` key.

- [ ] **Step 6: Stage**

```bash
git add glances/exports/glances_json/export_v5.py tests/test_export_json_v5.py
```

---

### Task 3: Verify both exporters together and run the hooks

**Files:** all files touched by Tasks 1-2.

- [ ] **Step 1: Run both exporters at once**

```bash
timeout 12 uv run python -m glances.main_v5 --quiet \
    --export csv,json --export-csv-file /tmp/g5.csv --export-json-file /tmp/g5.json
wc -l /tmp/g5.csv /tmp/g5.json
```

Expected: both files written, no traceback, no warning about a failing exporter.

- [ ] **Step 1b: Prove the lifecycle-lock protocol holds**

Both exporters hold OS resources or write from a worker thread, so the two rules
in the Global Constraints must be verified, not assumed. Add these to
`tests/test_export_csv_v5.py`:

```python
def test_csv_exit_calls_super_first(tmp_path, monkeypatch):
    """super().exit() is the barrier — it must run BEFORE the file is closed.

    Asserting only that super().exit() was called is NOT enough: closing the
    file first and calling the barrier afterwards would still satisfy that,
    while reintroducing the race where AsyncScheduler.stop() closes csv_file
    while an in-flight update() is still writing from a worker thread. So the
    test observes the file's state from INSIDE the barrier, the same way
    test_csv_update_holds_the_lifecycle_lock observes the lock.
    """
    from glances.exports.export_base_v5 import GlancesExportBase
    from glances.exports.glances_csv.export_v5 import Export

    observed = []
    real_exit = GlancesExportBase.exit

    def spy(self):
        observed.append(self.csv_file.closed)
        return real_exit(self)

    monkeypatch.setattr(GlancesExportBase, "exit", spy)

    exporter = Export(make_config({}), make_args(tmp_path / "g.csv"))
    exporter.exit()

    assert observed == [False], "super().exit() must run before csv_file is closed"
    assert exporter.csv_file.closed, "exit() must still close the file"


def test_csv_update_holds_the_lifecycle_lock(tmp_path):
    """CSV overrides update() without calling super(), so it must lock itself."""
    from glances.exports.glances_csv.export_v5 import Export

    exporter = Export(make_config({}), make_args(tmp_path / "g.csv"))
    held = []

    original = exporter._write_cycle

    def spy(plugins):
        held.append(exporter._lifecycle_lock.locked())
        return original(plugins)

    exporter._write_cycle = spy
    exporter.update([])
    exporter.exit()

    assert held == [True], "update() must hold _lifecycle_lock while writing"
```

and this to `tests/test_export_json_v5.py`:

```python
def test_json_exit_calls_super_first(tmp_path, monkeypatch):
    from glances.exports.export_base_v5 import GlancesExportBase
    from glances.exports.glances_json.export_v5 import Export

    calls = []
    real_exit = GlancesExportBase.exit
    monkeypatch.setattr(
        GlancesExportBase, "exit", lambda self: (calls.append("base"), real_exit(self))[1]
    )

    exporter = Export(make_config({}), make_args(tmp_path / "g.json"))
    exporter.exit()

    assert calls == ["base"], "Export.exit() must call super().exit()"
```

Run: `uv run pytest tests/test_export_csv_v5.py tests/test_export_json_v5.py -v`
Expected: PASS.

- [ ] **Step 1c: Prove there is no deadlock**

The lock is NOT reentrant, so an `update()` override that both takes the lock and
calls `super().update()` would hang forever. Confirm neither exporter does:

```bash
grep -n "_lifecycle_lock" glances/exports/glances_csv/export_v5.py glances/exports/glances_json/export_v5.py
grep -n "super().update" glances/exports/glances_csv/export_v5.py glances/exports/glances_json/export_v5.py
```

Expected: the lock appears only in the CSV `update()`; `super().update()` appears
only in the JSON `update()`. Never both in one file. The full-suite run in Step 2
would hang rather than fail if this were wrong — if pytest stalls, this is why.

- [ ] **Step 2: Run the full suite**

Run: `uv run pytest -q`
Expected: no new failures.

- [ ] **Step 3: Confirm the v4 modules are untouched**

```bash
git diff --stat HEAD -- glances/exports/glances_csv/__init__.py glances/exports/glances_json/__init__.py
```

Expected: empty output.

- [ ] **Step 4: Run the hooks**

```bash
git add -A
make pre-commit
```

Expected: all hooks pass. Restage and re-run if `ruff` reformats.

- [ ] **Step 5: Stage the final state**

```bash
git add -A
git status --short
```

Do NOT commit.
