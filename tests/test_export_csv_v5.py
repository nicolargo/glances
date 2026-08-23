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


class FakeLateScalarPlugin(GlancesPluginBase[dict]):
    """A second scalar plugin distinct from `FakeScalarPlugin` — used to
    simulate one plugin publishing a cycle or two after another (FIX 2)."""

    plugin_name = "fakelate"
    IS_COLLECTION = False
    fields_description = {
        "value": {"description": "v", "unit": "number"},
    }

    async def _grab_stats(self) -> dict:
        return {"value": 7}


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
    # First cycle is a warm-up deferral (FIX 2): the header only commits once
    # the contributing-plugin set repeats across two consecutive cycles.
    exporter.update([plugin])
    exporter.update([plugin])
    exporter.update([plugin])
    exporter.exit()

    rows = list(csv_module.reader(path.open()))
    assert rows[0] == ["timestamp", "fakescalar.percent", "fakescalar.total"]
    assert len(rows) == 3  # header + 2 rows (the very first cycle was the warm-up deferral)
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
    exporter.update([plugin])  # warm-up deferral (FIX 2)
    exporter.update([plugin])  # same contributing set -> commits
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
    exporter.update([plugin])  # warm-up deferral (FIX 2)
    exporter.update([plugin])  # same contributing set -> commits
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
    first.update([plugin])  # warm-up deferral (FIX 2)
    first.update([plugin])  # same contributing set -> commits header + row
    first.exit()

    # The file now carries a real on-disk header, so the second run's
    # old_header is not None -> it takes the "appending" branch, which is
    # unaffected by the warm-up gate (that gate only applies to a genuinely
    # new file) and commits on its very first cycle.
    second = Export(config, make_args(path))
    second.update([plugin])
    second.exit()

    rows = list(csv_module.reader(path.open()))
    assert len(rows) == 3  # header + one row per run
    assert rows[0][0] == "timestamp"


@pytest.mark.asyncio
async def test_csv_startup_mismatch_rotates_instead_of_refusing(tmp_path, caplog):
    """Rewrite of the old test_csv_refuses_to_append_when_headers_differ.

    v4 behaviour (and this module until yesterday): an incompatible on-disk
    header logs an ERROR and refuses to write, permanently, for the rest of
    the run (issue #1525). The maintainer now wants this routed through the
    same rotation mechanism as a mid-run divergence: WARNING, then roll over
    to `-001` with the new header, instead of losing every cycle after a
    restart whose header happens to have drifted (e.g. a plugin enabled).
    """
    from glances.exports.glances_csv.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({})
    path = tmp_path / "glances.csv"
    path.write_text("timestamp,something.else\n2026-01-01 00:00:00,1\n")

    plugin = FakeScalarPlugin(store, config)
    await plugin.update()
    exporter = Export(config, make_args(path))
    with caplog.at_level("WARNING"):
        exporter.update([plugin])
    exporter.exit()

    # Original file left exactly as it was found.
    assert path.read_text() == "timestamp,something.else\n2026-01-01 00:00:00,1\n"

    rotated = tmp_path / "glances-001.csv"
    assert rotated.exists()
    rows = list(csv_module.reader(rotated.open()))
    assert rows[0] == ["timestamp", "fakescalar.percent", "fakescalar.total"]
    assert len(rows) == 2  # new header + this cycle's row

    warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warning_records) == 1
    assert not [r for r in caplog.records if r.levelname == "ERROR"]


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
    # --export-csv-overwrite forces old_header=None (start fresh), so this
    # still goes through the "genuinely new file" warm-up gate (FIX 2).
    exporter.update([plugin])
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


def test_csv_exit_calls_super_first(tmp_path, monkeypatch):
    """super().exit() is the barrier — it must run BEFORE the file is closed.

    Asserting only that super().exit() was called is not enough: closing the
    file first and calling the barrier afterwards would still satisfy that,
    while reintroducing the race where AsyncScheduler.stop() closes csv_file
    while an in-flight update() is still writing from a worker thread.
    """
    from glances.exports.export_base_v5 import GlancesExportBase
    from glances.exports.glances_csv.export_v5 import Export

    observed = []
    real_exit = GlancesExportBase.exit

    def spy(self):
        # Captured at barrier time: the file must still be open here.
        observed.append(self.csv_file.closed)
        return real_exit(self)

    monkeypatch.setattr(GlancesExportBase, "exit", spy)

    exporter = Export(make_config({}), make_args(tmp_path / "g.csv"))
    exporter.exit()

    assert observed == [False], "super().exit() must run before csv_file is closed"
    assert exporter.csv_file.closed, "exit() must still close the file"


@pytest.mark.asyncio
async def test_csv_skips_a_cycle_where_no_plugin_has_published_yet(tmp_path):
    """Race between the export loop and the per-plugin loops (v5 concurrent

    scheduler): the export tick can fire before any plugin has published to
    the store. Writing a bare ["timestamp"] header would corrupt the file
    for every later, full-width row — so this cycle must write nothing.
    """
    from glances.exports.glances_csv.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({})
    plugin = FakeScalarPlugin(store, config)
    # Deliberately NOT calling `await plugin.update()`: the plugin is
    # registered but has not published anything to the store yet.

    path = tmp_path / "glances.csv"
    exporter = Export(config, make_args(path))
    exporter.update([plugin])
    exporter.exit()

    assert path.read_text() == ""
    assert exporter.first_line is True


@pytest.mark.asyncio
async def test_csv_writes_the_real_header_once_the_plugin_publishes(tmp_path):
    """The deferred cycle above must not permanently suppress the header:

    once the plugin has real data, the header commits once that
    contributing set has repeated across two consecutive cycles (FIX 2) —
    still well before the row count reflects every skipped/deferred cycle.
    """
    from glances.exports.glances_csv.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({})
    plugin = FakeScalarPlugin(store, config)

    path = tmp_path / "glances.csv"
    exporter = Export(config, make_args(path))
    exporter.update([plugin])  # no data yet -> skipped (total-empty guard), nothing written

    await plugin.update()  # plugin now publishes to the store
    exporter.update([plugin])  # first cycle with real data -> warm-up deferral (FIX 2)
    exporter.update([plugin])  # same contributing set as previous cycle -> commits + writes row
    exporter.exit()

    rows = list(csv_module.reader(path.open()))
    assert len(rows) == 2  # header + one data row (the skipped/deferred cycles wrote nothing)
    assert rows[0] == ["timestamp", "fakescalar.percent", "fakescalar.total"]
    assert rows[1][1:] == ["50.0", "1024"]
    # This is the assertion that would have caught the shipped bug: the
    # header and its data row must have the same number of columns.
    assert len(rows[0]) == len(rows[1])


class FakeVariableCollectionPlugin(GlancesPluginBase[list]):
    """A collection plugin whose item count changes between calls.

    Simulates a new network interface / container appearing mid-run: the
    column set legitimately widens because of the per-item prefix.
    """

    plugin_name = "fakevar"
    IS_COLLECTION = True
    fields_description = {
        "name": {"description": "n", "unit": "string", "primary_key": True},
        "rx": {"description": "r", "unit": "bytespers"},
    }
    items: list[dict] = [{"name": "eth0", "rx": 10}]

    async def _grab_stats(self) -> list:
        return self.items


@pytest.mark.asyncio
async def test_csv_mid_run_divergence_logs_warning_and_rotates(tmp_path, caplog):
    """Rewrite of the old test_csv_width_guard_skips_row_and_logs_error_on_divergence.

    Old behaviour: ERROR logged, row skipped, file stops growing. New
    behaviour: WARNING logged, exporter rolls over to `<base>-001.csv` and
    that file's first line is the new (widened) header.
    """
    from glances.exports.glances_csv.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({})
    plugin = FakeVariableCollectionPlugin(store, config)
    plugin.items = [{"name": "eth0", "rx": 10}]
    await plugin.update()

    path = tmp_path / "glances.csv"
    exporter = Export(config, make_args(path))
    exporter.update([plugin])  # warm-up deferral (FIX 2)
    exporter.update([plugin])  # commits the header (1 item)
    original_content_after_first_row = path.read_text()

    # A new interface appears mid-run: the column set widens.
    plugin.items = [{"name": "eth0", "rx": 10}, {"name": "eth1", "rx": 20}]
    await plugin.update()
    with caplog.at_level("WARNING"):
        exporter.update([plugin])
    exporter.exit()

    warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warning_records) == 1
    assert not [r for r in caplog.records if r.levelname == "ERROR"]

    # The original file is left intact — same content as right after the
    # first row, not truncated or appended to.
    assert path.read_text() == original_content_after_first_row

    rotated = tmp_path / "glances-001.csv"
    assert rotated.exists()
    rotated_rows = list(csv_module.reader(rotated.open()))
    assert "fakevar.eth1.rx" in rotated_rows[0]  # new header on the first line
    # Every row in the new file has exactly that file's header column count —
    # the property the whole mechanism protects.
    for row in rotated_rows[1:]:
        assert len(row) == len(rotated_rows[0])


@pytest.mark.asyncio
async def test_csv_second_divergence_rotates_again(tmp_path, caplog):
    """Rewrite of the old test_csv_width_guard_logs_once_per_distinct_divergence.

    The old per-episode dedup no longer applies: rotation opens a fresh file
    per divergence, so the same divergence cannot repeat within one file.
    What still matters is that a further, distinct column-set change (here:
    shrinking back down) rotates again, to `-002`.
    """
    from glances.exports.glances_csv.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({})
    plugin = FakeVariableCollectionPlugin(store, config)
    plugin.items = [{"name": "eth0", "rx": 10}]
    await plugin.update()

    path = tmp_path / "glances.csv"
    exporter = Export(config, make_args(path))
    exporter.update([plugin])  # warm-up deferral (FIX 2)
    exporter.update([plugin])  # commits the header (1 item) -> base file

    plugin.items = [{"name": "eth0", "rx": 10}, {"name": "eth1", "rx": 20}]
    await plugin.update()
    with caplog.at_level("WARNING"):
        exporter.update([plugin])  # 1st divergence -> rotates to -001
        exporter.update([plugin])  # same column set as -001's header -> no rotation

    # Interface disappears again: this now diverges from -001's (2-item)
    # committed header, so it rotates again, to -002.
    plugin.items = [{"name": "eth0", "rx": 10}]
    await plugin.update()
    exporter.update([plugin])
    exporter.exit()

    warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warning_records) == 2

    second_rotation = tmp_path / "glances-002.csv"
    assert second_rotation.exists()
    rows = list(csv_module.reader(second_rotation.open()))
    assert "fakevar.eth1.rx" not in rows[0]  # back to the 1-item header
    for row in rows[1:]:
        assert len(row) == len(rows[0])


@pytest.mark.asyncio
async def test_csv_rotation_collision_without_overwrite_advances_to_first_free_index(tmp_path):
    """A `-001` left by a previous run, --export-csv-overwrite not set.

    The exporter must skip past it to `-002` and leave the pre-existing
    `-001` untouched — and its internal counter must remember `-002` was
    used, so a later rotation this run does not retry `-001`.
    """
    from glances.exports.glances_csv.export_v5 import Export

    path = tmp_path / "glances.csv"
    collision = tmp_path / "glances-001.csv"
    collision.write_text("pre-existing content\n")

    store = StatsStoreV5()
    config = make_config({})
    plugin = FakeVariableCollectionPlugin(store, config)
    plugin.items = [{"name": "eth0", "rx": 10}]
    await plugin.update()

    exporter = Export(config, make_args(path, overwrite=False))
    exporter.update([plugin])  # warm-up deferral (FIX 2)
    exporter.update([plugin])  # commits the header (1 item)

    plugin.items = [{"name": "eth0", "rx": 10}, {"name": "eth1", "rx": 20}]
    await plugin.update()
    exporter.update([plugin])  # diverges -> -001 taken, must use -002
    exporter.exit()

    assert collision.read_text() == "pre-existing content\n"
    assert (tmp_path / "glances-002.csv").exists()
    assert exporter._rotation_index == 2


@pytest.mark.asyncio
async def test_csv_rotation_collision_with_overwrite_replaces_target(tmp_path):
    """Same collision, but --export-csv-overwrite is set: -001 is overwritten."""
    from glances.exports.glances_csv.export_v5 import Export

    path = tmp_path / "glances.csv"
    collision = tmp_path / "glances-001.csv"
    collision.write_text("pre-existing content\n")

    store = StatsStoreV5()
    config = make_config({})
    plugin = FakeVariableCollectionPlugin(store, config)
    plugin.items = [{"name": "eth0", "rx": 10}]
    await plugin.update()

    exporter = Export(config, make_args(path, overwrite=True))
    exporter.update([plugin])  # warm-up deferral (FIX 2)
    exporter.update([plugin])  # commits the header (1 item)

    plugin.items = [{"name": "eth0", "rx": 10}, {"name": "eth1", "rx": 20}]
    await plugin.update()
    exporter.update([plugin])  # diverges -> -001 overwritten
    exporter.exit()

    rows = list(csv_module.reader(collision.open()))
    assert "fakevar.eth1.rx" in rows[0]
    assert "pre-existing content" not in collision.read_text()


@pytest.mark.asyncio
async def test_csv_empty_cycle_after_header_committed_does_not_rotate(tmp_path):
    """A cycle producing no plugin column is not a divergence.

    Passing an empty plugin list mid-run must write nothing and must NOT be
    mistaken for a column-set change against the already-committed header.
    """
    from glances.exports.glances_csv.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({})
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()

    path = tmp_path / "glances.csv"
    exporter = Export(config, make_args(path))
    exporter.update([plugin])  # warm-up deferral (FIX 2)
    exporter.update([plugin])  # commits the header + one row

    exporter.update([])  # no plugin data this cycle
    exporter.exit()

    rows = list(csv_module.reader(path.open()))
    assert len(rows) == 2  # header + the one real row; the empty cycle wrote nothing
    assert not (tmp_path / "glances-001.csv").exists()


def test_csv_rotated_path_naming(tmp_path):
    """Direct test of the `-NNN` naming helper: extension, no extension, multiple dots."""
    from glances.exports.glances_csv.export_v5 import Export

    assert Export._rotated_path("/tmp/glances.csv", 1) == "/tmp/glances-001.csv"
    assert Export._rotated_path("/tmp/glances", 1) == "/tmp/glances-001"
    assert Export._rotated_path("/tmp/my.data.csv", 1) == "/tmp/my.data-001.csv"
    assert Export._rotated_path("/tmp/glances.csv", 12) == "/tmp/glances-012.csv"


@pytest.mark.asyncio
async def test_csv_width_guard_every_written_row_matches_header_width(tmp_path, caplog):
    """The property the whole guard exists to protect."""
    from glances.exports.glances_csv.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({})
    plugin = FakeVariableCollectionPlugin(store, config)
    plugin.items = [{"name": "eth0", "rx": 10}]
    await plugin.update()

    path = tmp_path / "glances.csv"
    exporter = Export(config, make_args(path))
    exporter.update([plugin])  # warm-up deferral (FIX 2)
    exporter.update([plugin])  # commits the header

    plugin.items = [{"name": "eth0", "rx": 10}, {"name": "eth1", "rx": 20}]
    await plugin.update()
    with caplog.at_level("ERROR"):
        exporter.update([plugin])
        exporter.update([plugin])

    plugin.items = [{"name": "eth0", "rx": 10}]
    await plugin.update()
    exporter.update([plugin])
    exporter.exit()

    rows = list(csv_module.reader(path.open()))
    header = rows[0]
    for row in rows[1:]:
        assert len(row) == len(header)


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


# ---------------------------------------------------------- FIX 2: warm-up header guard


@pytest.mark.asyncio
async def test_csv_header_waits_for_a_stable_contributing_set_across_staggered_plugins(tmp_path):
    """The scenario FIX 2 targets: plugins publish at staggered times.

    `fakescalar` has data from cycle 1; `fakelate` only starts publishing at
    cycle 2. The committed header must reflect BOTH plugins, never a
    warm-up-only subset — so nothing is written until the same contributing
    set (here: both plugins) repeats across two consecutive cycles.
    """
    from glances.exports.glances_csv.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({})
    early = FakeScalarPlugin(store, config)
    late = FakeLateScalarPlugin(store, config)
    await early.update()
    # `late` is registered but has not produced stats yet.

    path = tmp_path / "glances.csv"
    exporter = Export(config, make_args(path))

    exporter.update([early, late])  # contributing={fakescalar}; previous=None -> deferred
    assert path.read_text() == ""

    await late.update()  # late plugin now publishes too
    exporter.update([early, late])  # contributing={fakescalar,fakelate} != previous -> deferred again
    assert path.read_text() == ""

    exporter.update([early, late])  # same set as previous cycle -> commits
    exporter.exit()

    rows = list(csv_module.reader(path.open()))
    assert len(rows) == 2  # header + one row
    assert rows[0] == ["timestamp", "fakescalar.percent", "fakescalar.total", "fakelate.value"]


# ---------------------------------------------------------- FIX 4: rotation must not sys.exit()


@pytest.mark.asyncio
async def test_csv_rotation_failure_does_not_exit_and_keeps_original_file_usable(tmp_path, caplog, monkeypatch):
    """A rotation-target OSError must log an ERROR and survive, not sys.exit().

    The exporter runs inside a worker thread; an uncaught SystemExit there
    propagates out of asyncio.run and takes the whole TUI/REST server down
    with it (design §8: runtime failures log and continue, they are not
    fatal like an init failure).
    """
    import builtins

    from glances.exports.glances_csv import export_v5

    store = StatsStoreV5()
    config = make_config({})
    plugin = FakeVariableCollectionPlugin(store, config)
    plugin.items = [{"name": "eth0", "rx": 10}]
    await plugin.update()

    path = tmp_path / "glances.csv"
    exporter = export_v5.Export(config, make_args(path))
    exporter.update([plugin])  # warm-up deferral (FIX 2)
    exporter.update([plugin])  # commits the header (1 item)

    # Widen the column set so the next cycle attempts a rotation.
    plugin.items = [{"name": "eth0", "rx": 10}, {"name": "eth1", "rx": 20}]
    await plugin.update()

    rotation_target = str(tmp_path / "glances-001.csv")
    real_open = builtins.open

    def failing_open(file, *args, **kwargs):
        if str(file) == rotation_target:
            raise OSError("disk full (simulated)")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(export_v5, "open", failing_open, raising=False)
    with caplog.at_level("ERROR"):
        exporter.update([plugin])  # rotation fails -> must not raise SystemExit

    error_records = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(error_records) == 1
    assert not exporter.csv_file.closed, "original file must stay open after a failed rotation"
    assert exporter.csv_filename == str(path), "must not have switched to the (failed) rotation target"

    # Original file still receives rows on a later, non-diverging cycle.
    monkeypatch.undo()
    plugin.items = [{"name": "eth0", "rx": 10}]
    await plugin.update()
    exporter.update([plugin])
    exporter.exit()

    rows = list(csv_module.reader(path.open()))
    assert len(rows) == 3  # header + first row + this last row (the failed cycle wrote nothing)
    for row in rows[1:]:
        assert len(row) == len(rows[0])
