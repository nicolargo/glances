#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the v5 smart plugin model."""

from __future__ import annotations

import pytest

import glances.plugins.smart as smart_module
from glances.config_v5 import GlancesConfigV5
from glances.plugins.smart.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    return GlancesConfigV5()


def _cfg_with(tmp_path, monkeypatch, body: str) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    xdg = tmp_path / "xdg"
    cfg_dir = xdg / "glances"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "glances.conf").write_text(body)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    return GlancesConfigV5()


def test_plugin_identity(store, config):
    p = PluginModel(store, config)
    assert p.plugin_name == "smart"
    assert p.IS_COLLECTION is True
    assert p._primary_key == "name"


def test_fields_description_flags():
    fd = PluginModel.fields_description
    assert fd["name"]["primary_key"] is True
    # attributes is an internal, non-watched nested list (survives the flat filter).
    assert fd["attributes"].get("internal") is True
    assert fd["attributes"].get("watched", False) is False


def test_emits_alerts_false():
    # v4 smart has no colouring/alerts — the port must not raise alerts.
    assert PluginModel.EMITS_ALERTS is False


def _fake_device(name="/dev/sda Samsung SSD 850"):
    # v4 shape: DeviceName + numeric attribute keys (out of order on purpose).
    return {
        "DeviceName": name,
        5: {"name": "Reallocated_Sector_Ct", "key": "Reallocated_Sector_Ct", "raw": 0, "value": 100},
        1: {"name": "Raw_Read_Error_Rate", "key": "Raw_Read_Error_Rate", "raw": 200, "value": 100},
        9: {"name": "Power_On_Hours", "key": "Power_On_Hours", "raw": 12345, "value": 99},
    }


@pytest.mark.asyncio
async def test_grab_reshapes_numeric_keys_to_attributes_list(store, config, monkeypatch):
    p = PluginModel(store, config)
    monkeypatch.setattr("glances.plugins.smart.model_v5.is_admin", lambda: True)
    monkeypatch.setattr(smart_module, "import_error_tag", False)
    monkeypatch.setattr(smart_module, "get_smart_data", lambda hide: [_fake_device()])

    rows = await p._grab_stats()
    assert len(rows) == 1
    dev = rows[0]
    assert dev["name"] == "/dev/sda Samsung SSD 850"
    # Numeric keys flattened into a list, sorted by the v4 numeric order (1,5,9).
    assert [a["name"] for a in dev["attributes"]] == [
        "Raw_Read_Error_Rate",
        "Reallocated_Sector_Ct",
        "Power_On_Hours",
    ]
    # DeviceName is not smuggled into the attributes list.
    assert all("DeviceName" not in a for a in dev["attributes"])


@pytest.mark.asyncio
async def test_grab_passes_hide_attributes_to_helper(tmp_path, monkeypatch, store):
    config = _cfg_with(tmp_path, monkeypatch, "[smart]\nhide_attributes=Self-tests,Errors\n")
    p = PluginModel(store, config)
    assert p._hide_attributes == ["Self-tests", "Errors"]

    captured = {}

    def _grab(hide):
        captured["hide"] = hide
        return []

    monkeypatch.setattr("glances.plugins.smart.model_v5.is_admin", lambda: True)
    monkeypatch.setattr(smart_module, "import_error_tag", False)
    monkeypatch.setattr(smart_module, "get_smart_data", _grab)
    await p._grab_stats()
    assert captured["hide"] == ["Self-tests", "Errors"]


@pytest.mark.asyncio
async def test_grab_empty_when_not_root(store, config, monkeypatch):
    p = PluginModel(store, config)
    monkeypatch.setattr("glances.plugins.smart.model_v5.is_admin", lambda: False)
    # get_smart_data must NOT be called when not root.
    monkeypatch.setattr(smart_module, "get_smart_data", lambda hide: (_ for _ in ()).throw(AssertionError("called")))
    assert await p._grab_stats() == []


@pytest.mark.asyncio
async def test_grab_empty_when_import_error(store, config, monkeypatch):
    p = PluginModel(store, config)
    monkeypatch.setattr("glances.plugins.smart.model_v5.is_admin", lambda: True)
    monkeypatch.setattr(smart_module, "import_error_tag", True)
    monkeypatch.setattr(smart_module, "get_smart_data", lambda hide: (_ for _ in ()).throw(AssertionError("called")))
    assert await p._grab_stats() == []


@pytest.mark.asyncio
async def test_grab_non_numeric_keys_keep_insertion_order(store, config, monkeypatch):
    """#2904: some attribute keys are not numeric — reshape must not crash and
    must preserve insertion order for that device."""
    p = PluginModel(store, config)
    dev = {"DeviceName": "/dev/nvme0 NVMe", "bytesWritten": {"name": "Bytes written", "key": "bytesWritten", "raw": 1}}
    monkeypatch.setattr("glances.plugins.smart.model_v5.is_admin", lambda: True)
    monkeypatch.setattr(smart_module, "import_error_tag", False)
    monkeypatch.setattr(smart_module, "get_smart_data", lambda hide: [dev])
    rows = await p._grab_stats()
    assert [a["key"] for a in rows[0]["attributes"]] == ["bytesWritten"]


def test_reshape_mixed_numeric_and_non_numeric_keeps_full_insertion_order():
    """#2904: when a device mixes numeric and non-numeric attribute keys the
    `sorted(key=int)` raises mid-sort, so the WHOLE key list must fall back to
    dict insertion order (not a partial sort). Guards against a regression where
    the numeric keys get sorted before the exception aborts."""
    dev = {
        "DeviceName": "/dev/nvme0 NVMe",
        5: {"name": "Reallocated_Sector_Ct", "key": "Reallocated_Sector_Ct", "raw": 0},
        1: {"name": "Raw_Read_Error_Rate", "key": "Raw_Read_Error_Rate", "raw": 200},
        "bytesWritten": {"name": "Bytes written", "key": "bytesWritten", "raw": 1},
    }
    reshaped = PluginModel._reshape(dev)
    assert reshaped["name"] == "/dev/nvme0 NVMe"
    # Insertion order preserved verbatim (5, 1, bytesWritten) — NOT sorted to 1, 5.
    assert [a["key"] for a in reshaped["attributes"]] == [
        "Reallocated_Sector_Ct",
        "Raw_Read_Error_Rate",
        "bytesWritten",
    ]
