#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Unit tests for the v5 ``mpp`` plugin.

The headline behaviour under test: Glances must never write to ``/proc``.
See docs/superpowers/specs/2026-08-04-glances-v5-g6c-design.md §5.2
"""

from __future__ import annotations

import asyncio
import builtins
import inspect
import logging

from glances.outputs.curses_renderer_v5 import TOP_SLOT, slot_for
from glances.plugins.mpp.cards import rockchip_mpp
from glances.plugins.mpp.cards.rockchip_mpp import RockchipMPP
from glances.plugins.mpp.model_v5 import PluginModel
from glances.plugins.mpp.render_curses_v5 import render

LOAD_CONTENT = """\
21f40000.rkvenc           load:  24.80% utilization:  24.39%
22140100.rkvdec           load:  28.23% utilization:  13.38%
22170000.jpegd            load:   0.00% utilization:   0.00%
"""


def _make_root(tmp_path, load_content="", sessions_content=""):
    """Build a fake `<root>/proc/mpp_service/` tree and return the root."""
    proc = tmp_path / "proc" / "mpp_service"
    proc.mkdir(parents=True)
    (proc / "load").write_text(load_content)
    (proc / "sessions-summary").write_text(sessions_content)
    (proc / "load_interval").write_text("0")
    return str(tmp_path)


def test_card_never_opens_a_file_for_writing(tmp_path, monkeypatch):
    """Regression guard for the design decision: no writes to /proc, ever."""
    root = _make_root(tmp_path, LOAD_CONTENT)
    real_open = builtins.open
    modes: list[str] = []

    def _recording_open(file, mode="r", *args, **kwargs):
        modes.append(mode)
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", _recording_open)
    RockchipMPP(mpp_root_folder=root).get_stats()

    assert modes, "the card should have opened at least one file"
    assert all("w" not in m and "a" not in m and "x" not in m and "+" not in m for m in modes), (
        f"the card opened a file for writing: {modes}"
    )


def test_load_interval_file_is_left_untouched(tmp_path):
    root = _make_root(tmp_path, LOAD_CONTENT)
    interval = tmp_path / "proc" / "mpp_service" / "load_interval"
    RockchipMPP(mpp_root_folder=root).get_stats()
    assert interval.read_text() == "0", "Glances must not change the kernel setting"


def test_no_load_interval_machinery_remains():
    """The removal must be complete, not just unreachable."""
    source = inspect.getsource(rockchip_mpp)
    assert "_ensure_load_interval" not in source
    assert "_LOAD_INTERVAL_MS" not in source
    assert "_load_interval_set" not in source


def test_get_stats_parses_engines(tmp_path):
    root = _make_root(tmp_path, LOAD_CONTENT)
    stats = RockchipMPP(mpp_root_folder=root).get_stats()
    by_id = {s["engine_id"]: s for s in stats}
    assert set(by_id) == {"rockchip_rkvenc", "rockchip_rkvdec", "rockchip_jpegd"}
    assert by_id["rockchip_rkvenc"]["load"] == 24.80
    assert by_id["rockchip_rkvdec"]["utilization"] == 13.38


def test_empty_load_file_yields_no_engines(tmp_path):
    """With load_interval at 0 the kernel writes nothing — the plugin goes silent."""
    root = _make_root(tmp_path, "")
    assert RockchipMPP(mpp_root_folder=root).get_stats() == []


def test_absent_proc_tree_is_unavailable(tmp_path):
    card = RockchipMPP(mpp_root_folder=str(tmp_path))
    assert card.is_available() is False
    assert card.get_stats() == []


# --- PluginModel tests (Task 2) ---


def _plugin_on(root, store_with, config_with):
    plugin = PluginModel(store_with(), config_with({}))
    plugin._card = RockchipMPP(mpp_root_folder=root)
    return plugin


def test_grab_stats_projects_the_card_output(tmp_path, store_with, config_with):
    plugin = _plugin_on(_make_root(tmp_path, LOAD_CONTENT), store_with, config_with)
    stats = asyncio.run(plugin._grab_stats())
    assert {s["engine_id"] for s in stats} == {
        "rockchip_rkvenc",
        "rockchip_rkvdec",
        "rockchip_jpegd",
    }


def test_load_thresholds_resolve(tmp_path, store_with, config_with):
    store = store_with()
    plugin = PluginModel(store, config_with({"mpp": {"load_warning": "20"}}))
    plugin._card = RockchipMPP(mpp_root_folder=_make_root(tmp_path, LOAD_CONTENT))
    asyncio.run(plugin.update())
    levels = store.get("mpp")["_levels"]
    # rkvenc is at 24.8%, above the configured warning of 20.
    assert levels["rockchip_rkvenc"]["load"]["level"] == "warning"


def test_empty_load_warns_once_across_cycles(tmp_path, store_with, config_with, caplog):
    plugin = _plugin_on(_make_root(tmp_path, ""), store_with, config_with)
    with caplog.at_level(logging.WARNING):
        asyncio.run(plugin.update())
        asyncio.run(plugin.update())
        asyncio.run(plugin.update())
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1, "the operator hint must not repeat every cycle"
    assert "load_interval" in warnings[0].getMessage()


def test_no_warning_when_engines_are_reported(tmp_path, store_with, config_with, caplog):
    plugin = _plugin_on(_make_root(tmp_path, LOAD_CONTENT), store_with, config_with)
    with caplog.at_level(logging.WARNING):
        asyncio.run(plugin.update())
    assert [r for r in caplog.records if r.levelno == logging.WARNING] == []


def test_no_warning_when_the_card_is_unavailable(tmp_path, store_with, config_with, caplog):
    """No Rockchip hardware is not an operator mistake — stay quiet."""
    plugin = _plugin_on(str(tmp_path), store_with, config_with)
    with caplog.at_level(logging.WARNING):
        asyncio.run(plugin.update())
    assert [r for r in caplog.records if r.levelno == logging.WARNING] == []


class _BoomCard:
    """Fake card whose `get_stats()` blows up — mirrors `_BoomCard` in
    `test_plugin_npu_v5.py`, the sibling plugin this disable-on-exception
    pattern was copied from verbatim."""

    def __init__(self):
        self.disabled = False

    def is_available(self):
        return True

    def get_stats(self):
        raise OSError("boom")

    def disable(self):
        self.disabled = True

    def exit(self):
        pass


def test_collect_disables_card_on_error(store_with, config_with):
    """A faulty card must not kill the loop: `_collect` catches the
    exception, disables the card, and returns an empty list for the cycle."""
    plugin = PluginModel(store_with(), config_with({}))
    boom = _BoomCard()
    plugin._card = boom
    out = plugin._collect()
    assert out == []
    assert boom.disabled is True


def test_mpp_class_flags():
    assert PluginModel.plugin_name == "mpp"
    assert PluginModel.IS_COLLECTION is True
    assert PluginModel.EMITS_ALERTS is True
    assert PluginModel.DISABLED_BY_DEFAULT is True


# --- Renderer tests (Task 3) ---

_MPP_FIELDS = PluginModel.fields_description


def test_mpp_sits_between_npu_and_gpu_in_the_top_slot():
    assert slot_for("mpp") == "top"
    assert TOP_SLOT.index("npu") < TOP_SLOT.index("mpp") < TOP_SLOT.index("gpu")


def test_render_empty_payload_returns_no_rows():
    assert render({}, _MPP_FIELDS) == []
    assert render({"data": []}, _MPP_FIELDS) == []


def test_render_one_row_per_engine_plus_header():
    payload = {
        "data": [
            {"engine_id": "rockchip_rkvenc", "name": "RKVENC", "type": "enc", "load": 24.8, "sessions": 2},
            {"engine_id": "rockchip_jpegd", "name": "JPEGD", "type": "jpeg", "load": 0.0, "sessions": 0},
        ],
        "_levels": {"rockchip_rkvenc": {"load": {"level": "careful", "prominent": True}}},
    }
    rows = render(payload, _MPP_FIELDS)
    assert len(rows) == 3
    assert "MPP" in "".join(c.text for c in rows[0].cells)
    first = "".join(c.text for c in rows[1].cells)
    assert "RKVENC" in first and "24.8%" in first
    assert "2 sess" in first
    # A zero session count is omitted, as in v4.
    assert "sess" not in "".join(c.text for c in rows[2].cells)


def test_render_skips_non_dict_items_in_data():
    """The renderer must gracefully skip non-dict items in the data list
    (mirrors the equivalent `irq` renderer test)."""
    payload = {
        "data": [
            {"engine_id": "rockchip_rkvenc", "name": "RKVENC", "type": "enc", "load": 24.8, "sessions": 0},
            "invalid_string",
            None,
            {"engine_id": "rockchip_jpegd", "name": "JPEGD", "type": "jpeg", "load": 0.0, "sessions": 0},
        ]
    }
    rows = render(payload, _MPP_FIELDS)
    # Header + 2 valid items, skipping the two non-dict entries.
    assert len(rows) == 3, f"Expected 3 rows (header + 2 valid items), got {len(rows)}"
    names = ["".join(c.text for c in rows[i].cells) for i in range(1, len(rows))]
    assert "RKVENC" in names[0]
    assert "JPEGD" in names[1]


def test_render_shows_na_when_load_is_missing():
    payload = {"data": [{"engine_id": "e", "name": "RKVDEC", "type": "dec", "load": None, "sessions": 0}]}
    rows = render(payload, _MPP_FIELDS)
    assert "N/A" in "".join(c.text for c in rows[1].cells)
