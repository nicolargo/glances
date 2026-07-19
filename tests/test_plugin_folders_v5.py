#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `folders` plugin (collection)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.folder_list import FolderList
from glances.plugins.folders.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture(autouse=True)
def _reset_folder_list_class_state():
    """FolderList keeps its item list as a CLASS attribute
    (glances/folder_list.py:30-32) that every instance constructed with a
    `[folders]` config section APPENDS onto rather than replacing — a
    pre-existing v4 bug (see plan's "Key implementation findings" #2),
    left untouched per the "reuse verbatim" mandate. Left unreset, folder
    items from one test would leak into the next. Reset the class
    attribute (test-time state only — does not modify folder_list.py)
    before and after every test in this file.
    """
    FolderList._FolderList__folder_list = []
    yield
    FolderList._FolderList__folder_list = []


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


def _cfg_with(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str) -> GlancesConfigV5:
    xdg_conf = tmp_path / "xdg" / "glances" / "glances.conf"
    xdg_conf.parent.mkdir(parents=True, exist_ok=True)
    xdg_conf.write_text(textwrap.dedent(body).lstrip("\n"))
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


def test_plugin_identity(store, config):
    p = PluginModel(store, config)
    assert p.plugin_name == "folders"
    assert p.IS_COLLECTION is True
    assert p.EMITS_ALERTS is True
    assert p._primary_key == "path"


def test_fields_description():
    fd = PluginModel.fields_description
    assert set(fd) == {"path", "size", "refresh", "errno", "careful", "warning", "critical"}
    assert fd["path"]["primary_key"] is True


def test_no_folders_section_returns_empty(store, config):
    p = PluginModel(store, config)
    assert list(p._folders.get()) == []


@pytest.mark.asyncio
async def test_no_folders_section_grab_returns_empty(store, config):
    p = PluginModel(store, config)
    assert await p._grab_stats() == []


@pytest.mark.asyncio
async def test_folders_section_with_no_paths_returns_empty(tmp_path, monkeypatch):
    config = _cfg_with(tmp_path, monkeypatch, "[folders]\ndisable=False\n")
    p = PluginModel(StatsStoreV5(), config)
    assert await p._grab_stats() == []


@pytest.mark.asyncio
async def test_single_folder_collected(tmp_path, monkeypatch):
    watched = tmp_path / "watched"
    watched.mkdir()
    (watched / "f.bin").write_bytes(b"\x00" * 4096)
    config = _cfg_with(
        tmp_path,
        monkeypatch,
        f"""
        [folders]
        disable=False
        folder_1_path={watched}
        """,
    )
    p = PluginModel(StatsStoreV5(), config)
    stats = await p._grab_stats()
    assert len(stats) == 1
    assert stats[0]["path"] == str(watched)
    assert stats[0]["size"] >= 4096
    assert stats[0]["errno"] == 0


@pytest.mark.asyncio
async def test_nonexistent_folder_has_nonzero_errno(tmp_path, monkeypatch):
    missing = tmp_path / "does-not-exist"
    config = _cfg_with(
        tmp_path,
        monkeypatch,
        f"""
        [folders]
        disable=False
        folder_1_path={missing}
        """,
    )
    p = PluginModel(StatsStoreV5(), config)
    stats = await p._grab_stats()
    assert len(stats) == 1
    assert stats[0]["path"] == str(missing)
    assert stats[0]["errno"] != 0
    assert stats[0]["size"] == 0


def _levels(p, items):
    p._stats = items
    p._derived_parameters()
    return p._levels


def _item(path="/tmp", size=0, errno=0, careful=None, warning=None, critical=None):
    return {
        "path": path,
        "size": size,
        "errno": errno,
        "careful": careful,
        "warning": warning,
        "critical": critical,
        "refresh": 30,
    }


def test_mb_to_byte_conversion_fires_at_decimal_magnitude(store, config):
    # careful="10" -> 10 * 1_000_000 = 10,000,000 bytes (decimal MB).
    # A WRONG *1024**2 conversion would give 10,485,760 bytes instead.
    # 10_200_000 sits strictly between the two: it must trigger "careful"
    # under the correct (decimal) conversion, and would NOT under the
    # wrong (binary) one — this is the discriminating assertion.
    p = PluginModel(store, config)
    lv = _levels(p, [_item(size=10_200_000, careful="10", warning="50", critical="100")])
    assert lv["/tmp"]["size"]["level"] == "careful"


def test_mb_to_byte_conversion_boundary_just_under_stays_ok(store, config):
    # One byte under the decimal-MB threshold (10,000,000) -> ok. Pins the
    # exact magnitude rather than merely "some threshold eventually fires".
    p = PluginModel(store, config)
    lv = _levels(p, [_item(size=9_999_999, careful="10", warning="50", critical="100")])
    assert lv["/tmp"]["size"]["level"] == "ok"


def test_errno_short_circuits_and_emits_no_level(store, config):
    # No thresholds configured at all -> the ladder alone would say "ok".
    # errno != 0 must still short-circuit it and emit NO _levels entry at
    # all (v4 parity: no alert, no history, no action dispatch).
    p = PluginModel(store, config)
    lv = _levels(p, [_item(size=100, errno=2, careful=None, warning=None, critical=None)])
    assert "/tmp" not in lv


def test_errno_outranks_the_size_ladder_even_over_threshold(store, config):
    # A folder that is BOTH over a size threshold AND has errno != 0 must
    # still emit no level — errno short-circuits before the size ladder is
    # ever consulted, so it is never "size-derived" instead.
    p = PluginModel(store, config)
    lv = _levels(p, [_item(size=999_999_999, errno=2, careful="10", warning="50", critical="100")])
    assert "/tmp" not in lv


def test_ok_when_no_thresholds_configured(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_item(size=999_999_999, careful=None, warning=None, critical=None)])
    assert lv["/tmp"]["size"]["level"] == "ok"


def test_levels_indexed_by_path(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_item(path="/a", size=1), _item(path="/b", size=2)])
    assert set(lv) == {"/a", "/b"}
    assert lv["/a"]["size"]["prominent"] is False
