#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the `e` block says the same thing in both surfaces.

The terminal builds it in `_extended_rows`
(glances/plugins/processlist/render_curses_v5.py); the browser builds it in
js/v5/process_extended.js. A silent divergence there would have one surface
quietly dropping a field the other shows — the same class of defect the
hotkey drift test exists for, applied to a stats block.

What is compared is the LABELS, in order: the segments the terminal renders
in the default colour, which are exactly the ones the browser renders without
emphasis. The numbers are deliberately not compared — the terminal pads them
into fixed-width columns and a browser has no columns to pad into.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.processlist.render_curses_v5 import _extended_rows

_MODULE = (
    Path(__file__).resolve().parent.parent / "glances" / "outputs" / "static" / "js" / "v5" / "process_extended.js"
)

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not available")

# The shape the live engine produces — verified against it in
# tests/test_processes_extended.py, not invented here.
_PAYLOAD = {
    "pid": 1,
    "name": "hot",
    "cmdline": ["/bin/hot", "--go"],
    "extended_stats": True,
    "cpu_min": 0.5,
    "cpu_max": 78.4,
    "cpu_mean": 12.25,
    "memory_min": 1.0,
    "memory_max": 12.5,
    "memory_mean": 6.0,
    "cpu_affinity": [0, 1, 2, 3],
    "ionice": {"ioclass": 2, "value": 4},
    "memory_info": {"rss": 33554432, "vms": 125829120},
    "memory_swap": 4194304,
    "num_threads": 20,
    "num_fds": 45,
    "tcp": 3,
    "udp": 1,
}


def _python_labels(payload: dict) -> list[list[str]]:
    """Per line, the default-coloured cell texts. The title row is skipped:
    the browser titles the block with the command line where the terminal uses
    the process name (a width difference, recorded in `pinnedTitle`)."""
    rows = _extended_rows(payload)[1:]
    return [[c.text.strip() for c in row.cells if c.color is ColorRole.DEFAULT] for row in rows]


def _js_labels(payload: dict) -> list[list[str]]:
    script = f"""
    import('{_MODULE.as_posix()}').then((m) => {{
        const lines = m.extendedLines({json.dumps(payload)});
        process.stdout.write(JSON.stringify(lines.map((l) => l.filter((s) => !s.value).map((s) => s.text))));
    }});
    """
    result = subprocess.run(
        ["node", "--no-warnings", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_both_surfaces_render_the_same_number_of_lines():
    assert len(_js_labels(_PAYLOAD)) == len(_python_labels(_PAYLOAD))


def test_both_surfaces_carry_the_same_labels_in_the_same_order():
    js, py = _js_labels(_PAYLOAD), _python_labels(_PAYLOAD)
    for i, (a, b) in enumerate(zip(js, py)):
        assert a == b, f"line {i}"


def test_the_comparison_is_not_vacuous():
    """Two empty label lists would satisfy every assertion above."""
    py = _python_labels(_PAYLOAD)
    assert sum(len(line) for line in py) >= 8, py


@pytest.mark.parametrize(
    "missing",
    ["cpu_affinity", "ionice", "memory_info", "memory_swap", "num_fds", "tcp", "udp"],
)
def test_an_absent_field_is_dropped_by_both_surfaces(missing):
    """Each of these is conditional. A field the terminal drops and the
    browser keeps (or the reverse) is exactly the drift worth catching."""
    payload = {k: v for k, v in _PAYLOAD.items() if k != missing}
    assert _js_labels(payload) == _python_labels(payload)


def test_a_windows_only_counter_appears_in_both_when_present():
    """`num_handles` is Windows'; neither surface may invent it, and both must
    show it when the platform reports it."""
    payload = {**_PAYLOAD, "num_handles": 99}
    js, py = _js_labels(payload), _python_labels(payload)
    assert "handles" in py[-1]
    assert js == py


def test_the_io_nice_tables_match():
    """v4 never renders this line at all (its guard tests an attribute on what
    is already a dict), so there is no v4 output to compare against — only the
    two v5 surfaces to keep equal."""
    from glances.plugins.processlist.render_curses_v5 import (
        _IONICE_CLASSES,
        _IONICE_CLASSES_WINDOWS,
    )

    script = f"""
    import('{_MODULE.as_posix()}').then((m) => {{
        process.stdout.write(JSON.stringify({{ linux: m.IONICE_CLASSES, windows: m.IONICE_CLASSES_WINDOWS }}));
    }});
    """
    result = subprocess.run(
        ["node", "--no-warnings", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    js = json.loads(result.stdout)

    assert {int(k): v for k, v in js["linux"].items()} == _IONICE_CLASSES
    assert {int(k): v for k, v in js["windows"].items()} == _IONICE_CLASSES_WINDOWS
