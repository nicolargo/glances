"""Glances v5 — tests for the diskio plugin's curses renderer."""

from __future__ import annotations

import pytest

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.diskio.model_v5 import PluginModel
from glances.plugins.diskio.render_curses_v5 import render


@pytest.fixture
def diskio_fields():
    """The REAL schema, as production passes it (curses_renderer_v5.py:1459).

    The column labels come from it (field_label), so a hand-written subset
    without `short_name` would test a header no user ever sees.
    """
    return PluginModel.fields_description


@pytest.fixture
def diskio_payload():
    return {
        "data": [
            {
                "disk_name": "sda",
                "read_count": 100.0,
                "write_count": 50.0,
                "read_bytes": 1_500_000.0,
                "write_bytes": 750_000.0,
            },
            {
                "disk_name": "nvme0n1",
                "read_count": 5.0,
                "write_count": 2.0,
                "read_bytes": 100.0,
                "write_bytes": 50.0,
            },
        ],
        "_levels": {},
    }


# ---------------------------------------------------------------- structure


def test_render_first_row_is_diskio_header(diskio_payload, diskio_fields):
    rows = render(diskio_payload, diskio_fields)
    text = " ".join(c.text for c in rows[0].cells)
    assert "DISK I/O" in text
    assert "R/s" in text
    assert "W/s" in text


def test_render_one_row_per_disk(diskio_payload, diskio_fields):
    rows = render(diskio_payload, diskio_fields)
    # 1 header + 2 disks
    assert len(rows) == 3


def test_render_disks_sorted_by_name(diskio_payload, diskio_fields):
    rows = render(diskio_payload, diskio_fields)
    names = [r.cells[0].text.strip() for r in rows[1:]]
    assert names == sorted(names)


def test_render_each_data_row_has_three_cells(diskio_payload, diskio_fields):
    rows = render(diskio_payload, diskio_fields)
    for r in rows[1:]:
        assert len(r.cells) == 3


def test_render_rate_cells_have_no_per_second_suffix(diskio_payload, diskio_fields):
    """The header carries the ``R/s`` / ``W/s`` labels so individual cells
    show the byte rate without ``/s`` (v4 parity — saves column width)."""
    rows = render(diskio_payload, diskio_fields)
    for r in rows[1:]:
        for c in r.cells[1:]:
            assert "/s" not in c.text


def test_render_rate_values_use_auto_unit(diskio_payload, diskio_fields):
    rows = render(diskio_payload, diskio_fields)
    flat = " ".join(c.text for row in rows[1:] for c in row.cells)
    # 1_500_000 B/s → "1.4M" ; 750_000 B/s → "732K" or "732.4K" depending
    # on the auto-unit decimal policy. We just check the suffix appears.
    assert "M" in flat or "K" in flat


def test_render_block_width_fits_sidebar_cap(diskio_payload, diskio_fields):
    """Row width ≤ 34 (left-sidebar cap)."""
    rows = render(diskio_payload, diskio_fields)
    for r in rows:
        natural_w = sum(len(c.text) for c in r.cells) + max(0, len(r.cells) - 1)
        assert natural_w <= 34, f"row width {natural_w} exceeds sidebar cap 34"


def test_render_columns_align_across_rows(diskio_payload, diskio_fields):
    rows = render(diskio_payload, diskio_fields)
    ncols = max(len(r.cells) for r in rows)
    for col in range(ncols):
        widths = {len(r.cells[col].text) for r in rows if col < len(r.cells)}
        assert len(widths) == 1, f"col {col} widths differ: {widths}"


def test_render_handles_empty_data(diskio_fields):
    rows = render({"data": [], "_levels": {}}, diskio_fields)
    assert len(rows) == 1


def test_render_handles_empty_payload(diskio_fields):
    rows = render({}, diskio_fields)
    assert len(rows) == 1
    flat = " ".join(c.text for c in rows[0].cells)
    assert "DISK I/O" in flat


def test_render_skips_disk_without_rate_yet(diskio_fields):
    """Cycle 1: read_bytes/write_bytes absent → skip the row entirely so
    the user does not see a "-" placeholder for every disk on startup."""
    payload = {
        "data": [
            {"disk_name": "sda", "read_count": 0.0, "write_count": 0.0},
            # No read_bytes/write_bytes keys (base class strips on cycle 1).
        ],
        "_levels": {},
    }
    rows = render(payload, diskio_fields)
    # Header only.
    assert len(rows) == 1


# ---------------------------------------------------------------- truncation


def test_render_long_disk_name_truncated_with_underscore(diskio_fields):
    long_name = "very_long_disk_identifier_that_overflows"
    payload = {
        "data": [{"disk_name": long_name, "read_bytes": 0.0, "write_bytes": 0.0}],
        "_levels": {long_name: {}},
    }
    rows = render(payload, diskio_fields)
    name_text = rows[1].cells[0].text
    assert name_text.startswith("_")
    assert len(name_text) == len(rows[0].cells[0].text)


# ---------------------------------------------------------------- color


def test_render_rate_cells_default_color_when_no_thresholds(diskio_payload, diskio_fields):
    """No ``_levels`` entry → cells render in DEFAULT (no green)."""
    rows = render(diskio_payload, diskio_fields)
    for r in rows[1:]:
        for c in r.cells[1:]:
            assert c.color == ColorRole.DEFAULT
            assert c.prominent is False


def test_render_rate_cell_inherits_level_when_threshold_fires(diskio_fields):
    """Per-disk ``_levels.<disk>.read_bytes`` drives the R/s cell color."""
    payload = {
        "data": [{"disk_name": "sda", "read_bytes": 15_000.0, "write_bytes": 100.0}],
        "_levels": {"sda": {"read_bytes": {"level": "warning", "prominent": False}}},
    }
    rows = render(payload, diskio_fields)
    rx_cell = rows[1].cells[1]
    assert rx_cell.color == ColorRole.WARNING
    assert rx_cell.prominent is False


def test_render_title_role_header_when_no_alert(diskio_payload, diskio_fields):
    rows = render(diskio_payload, diskio_fields)
    title = rows[0].cells[0]
    assert title.color == ColorRole.HEADER
    assert title.bold is True


def test_item_rows_are_marked_for_the_truncation_counter(diskio_payload, diskio_fields):
    rows = render(diskio_payload, diskio_fields)
    assert rows[0].item_start is False  # header
    assert sum(r.item_start for r in rows) == len(diskio_payload["data"])


# ---------------------------------------------------------------- hide_zero (design §5.1)


def test_render_skips_hidden_disks(diskio_fields):
    payload = {
        "data": [
            {"disk_name": "sda", "read_bytes": 100.0, "write_bytes": 50.0, "hidden": False},
            {"disk_name": "loop0", "read_bytes": 0.0, "write_bytes": 0.0, "hidden": True},
        ],
        "_levels": {},
    }
    rows = render(payload, diskio_fields)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "sda" in flat
    assert "loop0" not in flat


def test_render_keeps_disk_when_hidden_key_absent(diskio_fields):
    payload = {
        "data": [{"disk_name": "sda", "read_bytes": 100.0, "write_bytes": 50.0}],
        "_levels": {},
    }
    rows = render(payload, diskio_fields)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "sda" in flat


# ---------------------------------------------------------------- alias (design §5.5)


def test_render_displays_alias_instead_of_disk_name(diskio_fields):
    """v4 parity (`diskio/__init__.py:262`): the alias REPLACES the raw
    disk name in the rendered row."""
    payload = {
        "data": [{"disk_name": "sda", "alias": "SystemDisk", "read_bytes": 0.0, "write_bytes": 0.0}],
        "_levels": {"sda": {}},
    }
    rows = render(payload, diskio_fields)
    name_cell = rows[1].cells[0].text
    assert "SystemDisk" in name_cell
    assert name_cell.strip() != "sda"


def test_render_falls_back_to_disk_name_when_no_alias(diskio_fields):
    payload = {
        "data": [{"disk_name": "sda", "read_bytes": 0.0, "write_bytes": 0.0}],
        "_levels": {"sda": {}},
    }
    rows = render(payload, diskio_fields)
    assert "sda" in rows[1].cells[0].text


def test_iops_mode_swaps_both_the_columns_and_the_header():
    """`B` (v4 `_handle_diskio_iops`). The labels come from the schema, so
    swapping the field pair swaps the header with it."""
    from glances.plugins.diskio.render_curses_v5 import render

    payload = {
        "data": [
            {"disk_name": "sda", "read_bytes": 2048.0, "write_bytes": 0.0, "read_count": 2500.0, "write_count": 7.4}
        ],
        "_levels": {},
    }
    fields = {
        "read_bytes": {"short_name": "R/s"},
        "write_bytes": {"short_name": "W/s"},
        "read_count": {"short_name": "IOR/s"},
        "write_count": {"short_name": "IOW/s"},
    }

    default_rows = render(payload, fields)
    iops_rows = render(payload, fields, view={"diskio_iops": True})

    assert [c.text.strip() for c in default_rows[0].cells][1:] == ["R/s", "W/s"]
    assert [c.text.strip() for c in iops_rows[0].cells][1:] == ["IOR/s", "IOW/s"]
    # Byte rates take the 1024 scale and a `B`; counts take 1000 and no unit.
    assert [c.text.strip() for c in default_rows[1].cells][1:] == ["2.0K", "0B"]
    assert [c.text.strip() for c in iops_rows[1].cells][1:] == ["2.5K", "7"]


def test_iops_mode_skips_a_disk_with_no_count_yet():
    """Cycle 1 leaves every rate field None, counts included."""
    from glances.plugins.diskio.render_curses_v5 import render

    payload = {
        "data": [{"disk_name": "sda", "read_bytes": 1.0, "write_bytes": 1.0, "read_count": None, "write_count": None}],
        "_levels": {},
    }
    assert len(render(payload, {}, view={"diskio_iops": True})) == 1, "header only"


# ---------------------------------------------------------------- `L` latency and `T` combined


def _one_disk(**fields):
    base = {
        "disk_name": "sda",
        "read_bytes": 2048.0,
        "write_bytes": 1024.0,
        "read_count": 2500.0,
        "write_count": 500.0,
        "read_latency": 4,
        "write_latency": 1200,
    }
    base.update(fields)
    return {"data": [base], "_levels": {}}


def _texts(row):
    return [c.text.strip() for c in row.cells][1:]


def test_latency_mode_shows_ms_per_operation_under_v4_headers(diskio_fields):
    """`L` / --diskio-latency (v4 `diskio_latency`): `ms/opR` / `ms/opW`,
    unitless ms counts (v4 `auto_unit(..., low_precision=True)`)."""
    rows = render(_one_disk(), diskio_fields, view={"diskio_latency": True})
    assert _texts(rows[0]) == ["ms/opR", "ms/opW"]
    assert _texts(rows[1]) == ["4", "1.2K"]


def test_latency_cells_take_their_colour_from_levels(diskio_fields):
    payload = _one_disk()
    payload["_levels"] = {"sda": {"read_latency": {"level": "critical", "prominent": False}}}
    row = render(payload, diskio_fields, view={"diskio_latency": True})[1]
    assert row.cells[1].color is ColorRole.CRITICAL
    assert row.cells[2].color is ColorRole.DEFAULT


def test_iops_wins_over_latency_like_v4(diskio_fields):
    """v4's if/elif: `diskio_iops` is tested before `diskio_latency`."""
    rows = render(_one_disk(), diskio_fields, view={"diskio_iops": True, "diskio_latency": True})
    assert _texts(rows[0]) == ["IOR/s", "IOW/s"]


def test_latency_mode_skips_a_disk_with_no_latency_yet(diskio_fields):
    payload = _one_disk(read_latency=None, write_latency=None)
    assert len(render(payload, diskio_fields, view={"diskio_latency": True})) == 1, "header only"


def test_t_folds_the_byte_rates_into_one_sum(diskio_fields):
    """`T` (network's `network_sum`) applied to disks: R/s + W/s, one column
    spanning the two it replaces so the block keeps its width."""
    default = render(_one_disk(), diskio_fields)
    combined = render(_one_disk(), diskio_fields, view={"network_sum": True})
    assert _texts(combined[0]) == ["R+W/s"]
    assert _texts(combined[1]) == ["3.0K"]
    assert combined[0].cells[1].text == "R+W/s".rjust(15)
    assert render_width(combined) == render_width(default)


def test_t_in_iops_mode_sums_the_operations(diskio_fields):
    rows = render(_one_disk(), diskio_fields, view={"network_sum": True, "diskio_iops": True})
    assert _texts(rows[0]) == ["IOR+W/s"]
    assert _texts(rows[1]) == ["3.0K"]


def test_t_is_ignored_in_latency_mode(diskio_fields):
    """The sum of two per-operation means is not a latency."""
    rows = render(_one_disk(), diskio_fields, view={"network_sum": True, "diskio_latency": True})
    assert _texts(rows[0]) == ["ms/opR", "ms/opW"]


def test_the_sum_is_never_coloured(diskio_fields):
    """Each field has its own level; a sum belongs to neither (as network's)."""
    payload = _one_disk()
    payload["_levels"] = {"sda": {"read_bytes": {"level": "warning", "prominent": False}}}
    row = render(payload, diskio_fields, view={"network_sum": True})[1]
    assert row.cells[1].color is ColorRole.DEFAULT


def render_width(rows):
    return max(sum(len(c.text) for c in r.cells) + len(r.cells) - 1 for r in rows)
