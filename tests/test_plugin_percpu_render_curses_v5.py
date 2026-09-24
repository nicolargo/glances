"""Glances v5 — tests for the percpu plugin's curses renderer."""

from __future__ import annotations

import pytest

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.percpu.render_curses_v5 import render

_SCHEMA = {
    "cpu_number": {"unit": "number", "primary_key": True},
    "total": {"unit": "percent"},
    "user": {"unit": "percent"},
    "system": {"unit": "percent"},
    "idle": {"unit": "percent"},
    "iowait": {"unit": "percent"},
    "irq": {"unit": "percent"},
    "nice": {"unit": "percent"},
    "steal": {"unit": "percent"},
    "guest": {"unit": "percent"},
}


@pytest.fixture
def percpu_fields():
    return _SCHEMA


def _core(n: int, **overrides):
    base = {
        "cpu_number": n,
        "total": 20.0,
        "user": 10.0,
        "system": 5.0,
        "iowait": 0.5,
        "idle": 80.0,
        "irq": 0.0,
        "nice": 0.0,
        "steal": 0.0,
        "guest": 0.0,
    }
    base.update(overrides)
    return base


@pytest.fixture
def percpu_payload_4cores():
    return {
        "data": [
            _core(0, total=21.7, user=12.5, system=3.2, iowait=0.5, idle=83.8),
            _core(1, total=11.9, user=8.1, system=2.0, iowait=0.1, idle=89.8),
            _core(2, total=21.5, user=15.0, system=4.5, iowait=1.2, idle=79.3),
            _core(3, total=8.1, user=6.3, system=1.8, iowait=0.0, idle=91.9),
        ],
        "_levels": {},
    }


def _payload_with_cores(n: int):
    """`n` cores with descending `total` values (core `i` -> `90 - i * 10`)."""
    return {
        "data": [_core(i, total=float(90 - i * 10)) for i in range(n)],
        "_levels": {},
    }


# ---------------------------------------------------------------- structure


def test_render_first_row_is_header(percpu_payload_4cores, percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    rows = render(percpu_payload_4cores, percpu_fields)
    flat = " ".join(c.text for c in rows[0].cells)
    assert "CPU" in flat
    assert "total" in flat
    assert "user" in flat
    assert "system" in flat


def test_render_header_includes_linux_columns(percpu_payload_4cores, percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    rows = render(percpu_payload_4cores, percpu_fields)
    flat = " ".join(c.text for c in rows[0].cells)
    # Linux: user, system, iowait, idle, irq, nice, steal, guest
    for col in ("iowait", "idle", "irq", "nice", "steal", "guest"):
        assert col in flat, f"missing column {col}"


def test_render_one_row_per_cpu_plus_header(percpu_payload_4cores, percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    rows = render(percpu_payload_4cores, percpu_fields)
    # 1 header + 4 cores = 5 rows (no overflow when len <= max_cpu_display).
    assert len(rows) == 5


def test_render_cpu_labels_for_single_digit_ids(percpu_payload_4cores, percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    rows = render(percpu_payload_4cores, percpu_fields)
    labels = [r.cells[0].text.strip() for r in rows[1:]]
    # cores are sorted by total desc, but each row label should be CPU<n>.
    assert all(lbl.startswith("CPU") for lbl in labels)
    assert {"CPU0", "CPU1", "CPU2", "CPU3"} == set(labels)


def test_render_data_rows_sorted_by_total_desc(percpu_payload_4cores, percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    rows = render(percpu_payload_4cores, percpu_fields)
    # Top-N by total: CPU2 (21.5), CPU0 (21.7) → highest first.
    # Wait: CPU0=21.7, CPU2=21.5 → CPU0 first.
    labels = [r.cells[0].text.strip() for r in rows[1:]]
    assert labels[0] == "CPU0"
    assert labels[-1] == "CPU3"  # 8.1, lowest


def test_render_each_data_row_has_label_plus_one_cell_per_column(percpu_payload_4cores, percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    rows = render(percpu_payload_4cores, percpu_fields)
    # Header on Linux: title + total + 8 stats = 10 cells.
    header_ncells = len(rows[0].cells)
    for r in rows[1:]:
        assert len(r.cells) == header_ncells


def test_render_value_cells_use_percent_format(percpu_payload_4cores, percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    rows = render(percpu_payload_4cores, percpu_fields)
    flat = " ".join(c.text for row in rows[1:] for c in row.cells)
    # 12.5% formatted as "  12.5%" must appear for CPU0.user.
    assert "12.5%" in flat


def test_render_columns_align_across_rows(percpu_payload_4cores, percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    rows = render(percpu_payload_4cores, percpu_fields)
    ncols = max(len(r.cells) for r in rows)
    for col in range(ncols):
        widths = {len(r.cells[col].text) for r in rows if col < len(r.cells)}
        assert len(widths) == 1, f"col {col} widths differ: {widths}"


# ---------------------------------------------------------------- overflow


def test_render_more_than_max_cpu_display_adds_overflow_row(percpu_fields, monkeypatch):
    """6 cores → 4 displayed + 1 CPU* overflow row (default max_cpu_display=4)."""
    monkeypatch.setattr("sys.platform", "linux")
    payload = {
        "data": [_core(i, total=float(i * 10)) for i in range(6)],
        "_levels": {},
    }
    rows = render(payload, percpu_fields)
    # 1 header + 4 displayed + 1 overflow = 6 rows.
    assert len(rows) == 6
    labels = [r.cells[0].text.strip() for r in rows[1:]]
    assert labels[-1] == "CPU*"


def test_render_overflow_row_averages_the_hidden_cores(percpu_fields, monkeypatch):
    """The CPU* row summarizes the cores that did NOT fit on screen."""
    monkeypatch.setattr("sys.platform", "linux")
    # 6 cores, total = 0, 10, 20, 30, 40, 50. The 4 busiest (50, 40, 30, 20) are
    # displayed; the CPU* row must average the 2 hidden ones (10, 0) -> 5.0.
    payload = {
        "data": [_core(i, total=float(i * 10), user=float(i)) for i in range(6)],
        "_levels": {},
    }
    rows = render(payload, percpu_fields)
    overflow_row = rows[-1]
    assert overflow_row.cells[0].text.strip() == "CPU*"
    assert overflow_row.cells[1].text.strip() == "5.0%"
    # Same for a non-`total` column: user = 1 and 0 -> 0.5.
    assert overflow_row.cells[2].text.strip() == "0.5%"


def test_the_core_cap_comes_from_the_payload():
    """`[percpu] max_cpu_display` caps the listed cores; the rest collapse into
    the CPU* mean row. Before this fix the renderer used its own constant and
    the config key was inert for this plugin (its TODO(G2+) said so), while
    `quicklook` honoured the same key — so two blocks disagreed on one setting.
    """
    payload = _payload_with_cores(6)
    payload["max_cpu_display"] = 2
    rows = render(payload, _SCHEMA)
    labels = [r.cells[0].text.strip() for r in rows[1:]]
    assert labels == ["CPU0", "CPU1", "CPU*"], f"got {labels!r}"


def test_an_older_server_without_the_field_falls_back_to_four():
    """A payload that predates the field must not raise: the renderer keeps its
    own constant as the fallback (same contract as quicklook's renderer)."""
    rows = render(_payload_with_cores(6), _SCHEMA)
    labels = [r.cells[0].text.strip() for r in rows[1:]]
    assert labels == ["CPU0", "CPU1", "CPU2", "CPU3", "CPU*"], f"got {labels!r}"


def test_render_no_overflow_row_when_exact_max(percpu_payload_4cores, percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    rows = render(percpu_payload_4cores, percpu_fields)
    labels = [r.cells[0].text.strip() for r in rows[1:]]
    assert "CPU*" not in labels


# ---------------------------------------------------------------- OS variation


def test_render_macos_headers(percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")
    payload = {"data": [_core(0)], "_levels": {}}
    rows = render(payload, percpu_fields)
    flat = " ".join(c.text for c in rows[0].cells)
    assert "user" in flat
    assert "system" in flat
    assert "idle" in flat
    assert "nice" in flat
    # iowait is Linux-only
    assert "iowait" not in flat


def test_render_windows_headers(percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "win32")
    payload = {"data": [_core(0)], "_levels": {}}
    rows = render(payload, percpu_fields)
    flat = " ".join(c.text for c in rows[0].cells)
    assert "dpc" in flat
    assert "interrupt" in flat
    # iowait/idle exclusive to other OSes shouldn't appear here.
    assert "iowait" not in flat


# ---------------------------------------------------------------- edge cases


def test_render_empty_payload(percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    rows = render({}, percpu_fields)
    # Header only.
    assert len(rows) == 1


def test_render_empty_data_list(percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    rows = render({"data": [], "_levels": {}}, percpu_fields)
    assert len(rows) == 1


def test_render_double_digit_cpu_label(percpu_fields, monkeypatch):
    """cpu_number=10 → right-aligned numeric label (no `CPU` prefix per v4)."""
    monkeypatch.setattr("sys.platform", "linux")
    payload = {"data": [_core(10)], "_levels": {}}
    rows = render(payload, percpu_fields)
    label_text = rows[1].cells[0].text
    # v4: `f'{cpu_id:4}'` → "  10" (4-char right-aligned).
    assert "10" in label_text
    assert "CPU10" not in label_text


def test_render_handles_missing_value(percpu_fields, monkeypatch):
    """A missing stat field falls back to a `?` placeholder, not a crash."""
    monkeypatch.setattr("sys.platform", "linux")
    payload = {"data": [{"cpu_number": 0, "total": 10.0}], "_levels": {}}
    rows = render(payload, percpu_fields)
    flat = " ".join(c.text for row in rows[1:] for c in row.cells)
    assert "?" in flat


# ---------------------------------------------------------------- title


def test_render_title_cell_is_header_bold(percpu_payload_4cores, percpu_fields, monkeypatch):
    """Percpu carries no _levels (per model_v5 docstring) → title stays HEADER."""
    monkeypatch.setattr("sys.platform", "linux")
    rows = render(percpu_payload_4cores, percpu_fields)
    title = rows[0].cells[0]
    assert "CPU" in title.text
    assert title.color == ColorRole.HEADER
    assert title.bold is True


def test_render_column_names_are_neither_bold_nor_header(percpu_payload_4cores, percpu_fields, monkeypatch):
    """v4 parity: column names (`total`, `user`, …) are plain text — no
    HEADER color, no bold (only the leading `CPU` title gets decoration)."""
    monkeypatch.setattr("sys.platform", "linux")
    rows = render(percpu_payload_4cores, percpu_fields)
    for cell in rows[0].cells[1:]:
        assert cell.bold is False, f"column header {cell.text!r} is bold"
        assert cell.color == ColorRole.DEFAULT, f"column header {cell.text!r} has color {cell.color}"


# ---------------------------------------------------------------- quicklook on screen


def test_quicklook_shown_drops_the_title_the_total_column_and_the_labels():
    """v4 parity (glances/plugins/percpu/__init__.py:158,183,210): with
    quicklook on screen, percpu does not repeat what quicklook already shows.
    """
    rows = render(_payload_with_cores(2), _SCHEMA, view={"quicklook_enabled": True})
    header = " ".join(c.text for c in rows[0].cells)
    assert "CPU" not in header, f"no title cell: {header!r}"
    assert "total" not in header, f"no total column: {header!r}"
    assert not any(r.cells[0].text.strip().startswith("CPU") for r in rows[1:]), (
        f"no row labels: {[r.cells[0].text for r in rows[1:]]!r}"
    )


# ---------------------------------------------------------------- stat_fields (server-resolved)


def test_render_uses_the_payload_s_stat_fields_when_present(monkeypatch):
    """Final review, Important 3: the model is the platform authority — its
    published `stat_fields` (a Windows order here) must win over the
    renderer's own `_os_headers()`, which the `sys.platform` patch below
    would otherwise resolve to the Linux set.
    """
    monkeypatch.setattr("sys.platform", "linux")
    payload = {
        "data": [_core(0)],
        "_levels": {},
        "stat_fields": ["system", "user", "dpc", "interrupt"],
    }
    rows = render(payload, _SCHEMA)
    flat = " ".join(c.text for c in rows[0].cells)
    assert flat.split()[2:] == ["system", "user", "dpc", "interrupt"], f"got {flat!r}"


def test_render_falls_back_to_os_headers_without_stat_fields(monkeypatch):
    """A payload from an older server carries no `stat_fields` — the renderer
    keeps resolving from `sys.platform` itself, same contract as
    `max_cpu_display`."""
    monkeypatch.setattr("sys.platform", "darwin")
    payload = {"data": [_core(0)], "_levels": {}}
    rows = render(payload, _SCHEMA)
    flat = " ".join(c.text for c in rows[0].cells)
    assert flat.split()[2:] == ["user", "system", "idle", "nice"], f"got {flat!r}"


def test_quicklook_absent_keeps_the_title_the_total_column_and_the_labels():
    """The other half of the same v4 branch — and the default for every
    caller that passes no view at all."""
    for view in ({"quicklook_enabled": False}, None):
        rows = render(_payload_with_cores(2), _SCHEMA, view=view)
        header = " ".join(c.text for c in rows[0].cells)
        assert "CPU" in header, f"view={view!r}: {header!r}"
        assert "total" in header, f"view={view!r}: {header!r}"
        assert rows[1].cells[0].text.strip() == "CPU0", f"view={view!r}: {rows[1].cells[0].text!r}"


# ---------------------------------------------------------------- threshold colouring


def _cells_by_header(rows):
    """Map each data row's cells to the header row's column names."""
    names = [c.text.strip() for c in rows[0].cells]
    return [dict(zip(names, r.cells)) for r in rows[1:]]


def test_a_core_cell_takes_its_colour_from_levels():
    """v4 `get_alert(cpu[stat], header=stat)` — font colour, no background."""
    payload = {
        "data": [_core(0, user=75.0)],
        "stat_fields": ["user", "system", "iowait"],
        "_levels": {
            0: {"user": {"level": "warning", "prominent": False}, "system": {"level": "ok", "prominent": False}}
        },
    }
    row = _cells_by_header(render(payload, _SCHEMA))[0]
    assert row["user"].color is ColorRole.WARNING
    assert row["user"].prominent is False
    assert row["system"].color is ColorRole.OK
    # No level entry: uncoloured, as v4's DEFAULT for an unconfigured column.
    assert row["iowait"].color is ColorRole.DEFAULT
    assert row["total"].color is ColorRole.DEFAULT


def test_levels_keyed_by_string_after_json_still_colour():
    """Through REST the `_levels` keys are strings — a remote TUI must colour too."""
    payload = {
        "data": [_core(3, user=95.0)],
        "stat_fields": ["user"],
        "_levels": {"3": {"user": {"level": "critical", "prominent": False}}},
    }
    row = _cells_by_header(render(payload, _SCHEMA))[0]
    assert row["user"].color is ColorRole.CRITICAL


def test_the_mean_row_is_graded_against_the_published_thresholds():
    """v4 ran `get_alert` on the CPU* mean too (`summarize_all_cpus_not_displayed`)."""
    # 6 cores, cap 4: the two hidden cores have user 60 and 80 -> mean 70 = warning.
    data = [_core(i, total=float(90 - i * 10), user=10.0) for i in range(4)]
    data += [_core(4, total=5.0, user=60.0), _core(5, total=1.0, user=80.0)]
    payload = {
        "data": data,
        "stat_fields": ["user", "iowait"],
        "_levels": {},
        "thresholds": {"user": {"careful": 50.0, "warning": 70.0, "critical": 90.0}},
    }
    mean = _cells_by_header(render(payload, _SCHEMA))[-1]
    assert mean["CPU"].text.strip() == "CPU*"
    assert mean["user"].color is ColorRole.WARNING
    assert mean["iowait"].color is ColorRole.DEFAULT


def test_the_mean_row_stays_uncoloured_without_published_thresholds():
    """A payload from an older server carries no `thresholds`: no colour, no crash."""
    rows = render(_payload_with_cores(6), _SCHEMA)
    assert all(c.color is ColorRole.DEFAULT for c in rows[-1].cells[1:])
