#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the WebUI's container column drop order is the TUI's.

`containers/render_curses_v5.py:60` decides which column a narrow terminal
loses first; js/v5/drop_order.js keeps a copy, because the browser cannot
import Python. A silent divergence there means the WebUI hides a DIFFERENT
column than the terminal, so this test makes drift a failure — as
tests/test_webui_v5_degrade_drift.py does for the two zone cascades.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from glances.plugins.containers.render_curses_v5 import _COL_GEOMETRY, _DROP_ORDER

_DROP_ORDER_JS = (
    Path(__file__).resolve().parent.parent / "glances" / "outputs" / "static" / "js" / "v5" / "drop_order.js"
)

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not available")


def _js_order() -> list[str]:
    """Import drop_order.js under node and return its array as data."""
    script = (
        f"import({json.dumps(_DROP_ORDER_JS.as_uri())})"
        ".then((m) => process.stdout.write(JSON.stringify(m.CONTAINERS_DROP_ORDER)))"
    )
    result = subprocess.run(
        ["node", "--no-warnings", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_the_js_copy_is_the_tui_order():
    assert _js_order() == list(_DROP_ORDER)


def test_the_copy_is_not_empty():
    """Guard: an empty list would make the comparison above vacuous if the
    plugin constant ever emptied too."""
    assert _js_order()


def test_no_undroppable_column_leaked_into_the_order():
    """`name`, `cpu` and `mem` are absent from `_DROP_ORDER` by design —
    they are what the block is for. A future edit adding one to either copy
    must fail here even if both copies agree."""
    for column in ("name", "cpu", "mem"):
        assert column not in _js_order()


def test_every_droppable_column_has_a_geometry_in_the_tui():
    """The inverse mistake: a column dropped by the WebUI that the TUI has
    no geometry for is a name that no longer exists in the renderer."""
    known = set(_COL_GEOMETRY) | {"name"}
    assert set(_js_order()) <= known, f"unknown columns: {set(_js_order()) - known}"
