#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `amps` plugin (collection)."""

from __future__ import annotations

import asyncio
import textwrap
from pathlib import Path

import pytest

from glances import amps_list_v5 as amps_module
from glances.config_v5 import GlancesConfigV5
from glances.plugins.amps.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def cfg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def _make(body: str) -> GlancesConfigV5:
        xdg_conf = tmp_path / "xdg" / "glances" / "glances.conf"
        xdg_conf.parent.mkdir(parents=True, exist_ok=True)
        xdg_conf.write_text(textwrap.dedent(body).lstrip("\n"))
        monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
        return GlancesConfigV5()

    return _make


@pytest.fixture
def procs(monkeypatch):
    def _set(processlist):
        monkeypatch.setattr(amps_module.glances_processes, "get_list", lambda: list(processlist), raising=False)

    return _set


async def _settle(plugin: PluginModel) -> None:
    while plugin._amps_list._inflight:
        await asyncio.gather(*list(plugin._amps_list._inflight.values()), return_exceptions=True)
        await asyncio.sleep(0)


def test_plugin_identity(store, cfg):
    p = PluginModel(store, cfg("[global]\nrefresh = 2\n"))
    assert p.plugin_name == "amps"
    assert p.IS_COLLECTION is True
    assert p.EMITS_ALERTS is False
    assert p.SCHEDULE_AT_GLOBAL_REFRESH is True
    assert p._primary_key == "name"


def test_fields_description(store, cfg):
    p = PluginModel(store, cfg("[global]\nrefresh = 2\n"))
    assert set(p.fields_description) == {
        "name",
        "result",
        "result_float",
        "refresh",
        "timer",
        "count",
        "countmin",
        "countmax",
        "regex",
    }


async def test_no_amp_configured_publishes_an_empty_list(store, cfg, procs):
    procs([])
    p = PluginModel(store, cfg("[global]\nrefresh = 2\n"))
    await p.update()
    assert store.get("amps", {}).get("data") == []


async def test_payload_shape(store, cfg, procs):
    procs([])
    p = PluginModel(store, cfg("[amp_conntrack]\nenable=true\nrefresh=30\ncommand=echo tracked\n"))
    await p.update()
    await _settle(p)
    await p.update()
    item = store.get("amps", {})["data"][0]
    assert item["name"] == "Conntrack"  # default AMP capitalises (v4 parity)
    assert item["result"].strip() == "tracked"
    assert item["refresh"] == 30.0
    assert item["count"] == 0
    assert item["regex"] is False


async def test_regex_field_is_true_when_configured(store, cfg, procs):
    procs([])
    p = PluginModel(store, cfg("[amp_python]\nenable=true\nregex=.*python.*\nrefresh=3\n"))
    await p.update()
    await _settle(p)
    assert store.get("amps", {})["data"][0]["regex"] is True


@pytest.mark.parametrize(
    ("count", "count_min", "count_max", "expected"),
    [
        (2, None, None, "ok"),  # nothing configured -> always ok
        (2, 1, 3, "ok"),  # inside the band
        (5, 1, 3, "warning"),  # above countmax
        (1, 2, 3, "warning"),  # below countmin, but still running
        (0, None, None, "ok"),  # no countmin configured
        (0, 0, None, "ok"),  # countmin explicitly 0
        (0, 1, None, "critical"),  # required but absent
        (None, 1, 2, None),  # unreachable in practice, no level
    ],
)
def test_count_level_ladder(count, count_min, count_max, expected):
    assert PluginModel._count_level(count, count_min, count_max) == expected


async def test_levels_are_keyed_by_amp_name(store, cfg, procs):
    procs([])
    p = PluginModel(store, cfg("[amp_python]\nenable=true\nregex=.*python.*\nrefresh=3\ncountmin=1\n"))
    await p.update()
    await _settle(p)
    levels = store.get("amps", {})["_levels"]
    assert levels["Python"]["count"]["level"] == "critical"
    assert levels["Python"]["count"]["prominent"] is False


# ------------------------------------------------------- result_float (#3423)


async def test_result_float_carries_the_number(store, cfg, procs):
    """A numeric AMP result must reach InfluxDB as a number (issue #3423)."""
    procs([])
    p = PluginModel(store, cfg("[amp_queue]\nenable=true\nrefresh=30\ncommand=echo 42\n"))
    await p.update()
    await _settle(p)
    await p.update()

    item = store.get("amps", {})["data"][0]

    assert item["result"].strip() == "42"
    assert item["result_float"] == 42.0


async def test_result_float_is_none_for_text(store, cfg, procs):
    """A text result contributes no numeric series rather than a misleading 0.0."""
    procs([])
    p = PluginModel(store, cfg("[amp_conntrack]\nenable=true\nrefresh=30\ncommand=echo tracked\n"))
    await p.update()
    await _settle(p)
    await p.update()

    item = store.get("amps", {})["data"][0]

    assert item["result"].strip() == "tracked"
    assert item["result_float"] is None


def test_as_float_helper():
    from glances.plugins.amps.model_v5 import _as_float

    assert _as_float("42\n") == 42.0
    assert _as_float(7) == 7.0
    assert _as_float("3.5") == 3.5
    assert _as_float("tracked") is None
    assert _as_float(None) is None
    assert _as_float("") is None
