#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the WebUI's processlist column drop order is the TUI's.

`processlist/render_curses_v5.py:89` decides which column a narrow browser
loses first; js/v5/processlist_columns.js keeps a copy, because the browser
cannot import Python. A silent divergence there means the WebUI hides a
DIFFERENT column than the terminal, so this test makes drift a failure --
as tests/test_webui_v5_containers_drop_order_drift.py does for the
container block.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from glances.plugins.processlist.render_curses_v5 import _DROP_ORDER, _FIXED_COL_KEYS

_DROP_ORDER_JS = (
    Path(__file__).resolve().parent.parent / "glances" / "outputs" / "static" / "js" / "v5" / "processlist_columns.js"
)

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not available")


def _js_order() -> list[str]:
    """Import processlist_columns.js under node and return its array as data."""
    script = (
        f"import({json.dumps(_DROP_ORDER_JS.as_uri())})"
        ".then((m) => process.stdout.write(JSON.stringify(m.PROCESSLIST_DROP_ORDER)))"
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
    """`CPU%`, `MEM%`, `R/s`, `W/s` and `Command` are absent from
    `_DROP_ORDER` by design -- they are what the block is for. A future edit
    adding one to either copy must fail here even if both copies agree."""
    for column in ("CPU%", "MEM%", "R/s", "W/s", "Command"):
        assert column not in _js_order()


def test_every_droppable_column_has_a_fixed_key_in_the_tui():
    """The inverse mistake: a column dropped by the WebUI that the TUI has
    no fixed-column entry for is a name that no longer exists in the
    renderer."""
    known = set(_FIXED_COL_KEYS)
    assert set(_js_order()) <= known, f"unknown columns: {set(_js_order()) - known}"


def test_order_and_membership_match_exactly():
    """A same-membership, different-order drift (e.g. the maintainer
    reordering one side only) would slip past a set comparison alone."""
    assert _js_order() == list(_DROP_ORDER), "order AND membership must match, not just membership"
