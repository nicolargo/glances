#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — tests for the folders plugin's curses renderer."""

from __future__ import annotations

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.folders.render_curses_v5 import render


def _payload(items, levels=None):
    return {"data": items, "_levels": levels or {}}


def _folder(path="/tmp", size=1000, errno=0):
    return {"path": path, "size": size, "errno": errno}


def test_empty_returns_nothing():
    assert render(_payload([])) == []


def test_missing_data_key_returns_nothing():
    assert render({}) == []


def test_title_row_is_folders_header():
    rows = render(_payload([_folder()]))
    assert rows[0].cells[0].text.strip() == "FOLDERS"
    assert rows[0].cells[0].color == ColorRole.HEADER
    assert rows[0].cells[0].bold is True
    assert len(rows[0].cells) == 1  # no column headers — v4 parity


def test_one_row_per_folder():
    rows = render(_payload([_folder("/tmp"), _folder("/home")]))
    assert len(rows) == 3  # title + 2 folders


def test_short_path_not_truncated():
    rows = render(_payload([_folder("/tmp")]))
    assert rows[1].cells[0].text.strip() == "/tmp"


def test_long_path_truncated_from_left_with_underscore():
    long_path = "/very/long/path/that/exceeds/the/name/column/width/tail-marker"
    rows = render(_payload([_folder(long_path)]))
    cell_text = rows[1].cells[0].text
    assert cell_text.startswith("_")
    assert cell_text.strip().endswith("tail-marker")
    assert len(cell_text) == 24  # _NAME_MAX_WIDTH


def test_path_at_exactly_name_max_width_not_truncated():
    path_24 = "/" + "a" * 23  # exactly _NAME_MAX_WIDTH (24) chars
    assert len(path_24) == 24
    rows = render(_payload([_folder(path_24)]))
    cell_text = rows[1].cells[0].text
    assert cell_text == path_24
    assert not cell_text.startswith("_")


def test_path_one_over_name_max_width_is_truncated():
    path_25 = "/" + "a" * 24  # one over _NAME_MAX_WIDTH (24) chars
    assert len(path_25) == 25
    rows = render(_payload([_folder(path_25)]))
    cell_text = rows[1].cells[0].text
    assert cell_text.startswith("_")
    assert len(cell_text) == 24


def test_size_formatted_and_right_aligned():
    rows = render(_payload([_folder("/tmp", size=125 * 1024 * 1024)]))
    size_text = rows[1].cells[1].text
    assert len(size_text) == 9
    assert size_text == "   125.0M"  # right-justified: padding on the left
    assert size_text.rstrip() == size_text  # no trailing padding


def test_errno_prefixes_question_mark():
    rows = render(_payload([_folder("/missing", size=0, errno=2)]))
    size_text = rows[1].cells[1].text
    assert len(size_text) == 9
    assert size_text == "?      0B"  # right-justified: "0B" preceded by spaces
    assert size_text.startswith("?")
    assert size_text.rstrip() == size_text  # no trailing padding


def test_size_none_renders_dash_and_stays_padded():
    rows = render(_payload([_folder("/tmp", size=None)]))
    size_text = rows[1].cells[1].text
    assert len(size_text) == 9
    assert size_text == "        -"  # right-justified: "-" preceded by 8 spaces


def test_size_none_with_errno_prefixes_question_mark():
    rows = render(_payload([_folder("/missing", size=None, errno=2)]))
    size_text = rows[1].cells[1].text
    assert len(size_text) == 9
    assert size_text == "?       -"


def test_size_colour_careful():
    levels = {"/tmp": {"size": {"level": "careful", "prominent": False}}}
    rows = render(_payload([_folder("/tmp", size=5_000_000)], levels))
    assert rows[1].cells[1].color == ColorRole.CAREFUL


def test_errno_renders_bold_default_not_alert_coloured():
    # v4 parity: a broken folder is never alert-coloured, even if a
    # (synthetic, shouldn't-happen) _levels entry is present for its path —
    # errno rendering must win outright.
    levels = {"/missing": {"size": {"level": "critical", "prominent": True}}}
    rows = render(_payload([_folder("/missing", size=0, errno=2)], levels))
    cell = rows[1].cells[1]
    assert cell.color == ColorRole.DEFAULT
    assert cell.bold is True
    assert cell.prominent is False


def test_errno_renders_bold_default_with_no_levels_entry():
    # The real-world case: the model emits no _levels entry at all for a
    # broken folder.
    rows = render(_payload([_folder("/missing", size=0, errno=2)], {}))
    cell = rows[1].cells[1]
    assert cell.color == ColorRole.DEFAULT
    assert cell.bold is True


def test_no_level_entry_defaults_to_default_color():
    rows = render(_payload([_folder("/tmp")]))
    assert rows[1].cells[1].color == ColorRole.DEFAULT


def test_size_prominent_forwarded_when_levels_carry_it():
    levels = {"/tmp": {"size": {"level": "critical", "prominent": True}}}
    rows = render(_payload([_folder("/tmp", size=5_000_000)], levels))
    assert rows[1].cells[1].prominent is True


def test_size_prominent_not_set_when_levels_lack_it():
    levels = {"/tmp": {"size": {"level": "critical"}}}
    rows = render(_payload([_folder("/tmp", size=5_000_000)], levels))
    assert rows[1].cells[1].prominent is False


def test_render_works_with_one_positional_arg():
    # A bare render(payload) call must work — fields_desc/view both default.
    rows = render(_payload([_folder()]))
    assert rows


def test_item_rows_are_marked_for_the_truncation_counter():
    rows = render(_payload([_folder("/tmp"), _folder("/home")]))
    assert rows[0].item_start is False  # title
    assert sum(r.item_start for r in rows) == 2
