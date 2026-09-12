#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the WebUI's degradation cascades are the TUI's.

The WebUI keeps its own copy of `_DEGRADE_STEPS` / `_HEADER_DEGRADE_STEPS`
(js/v5/degrade.js): the browser cannot import Python. Nothing prevents the two
copies from drifting apart, so this test makes drift a failure — including the
two `quicklook` steps the WebUI declares but cannot act on yet, which is what
turns "quicklook was ported and nobody revisited the cascade" into a red test.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from glances.outputs.glances_curses_v5 import _DEGRADE_STEPS, _HEADER_DEGRADE_STEPS

_DEGRADE_JS = Path(__file__).resolve().parent.parent / "glances" / "outputs" / "static" / "js" / "v5" / "degrade.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not available")


def _cascades() -> dict:
    """Import degrade.js under node and return its two cascades as data."""
    script = (
        f"import({json.dumps(_DEGRADE_JS.as_uri())})"
        ".then((m) => process.stdout.write(JSON.stringify({top: m.TOP_CASCADE, header: m.HEADER_CASCADE})))"
    )
    result = subprocess.run(
        ["node", "--no-warnings", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_the_top_cascade_matches_the_tui():
    top = [[step["key"], step["value"]] for step in _cascades()["top"]]
    assert top == [list(step) for step in _DEGRADE_STEPS]


def test_the_header_cascade_matches_the_tui():
    header = [[step["key"], step["value"]] for step in _cascades()["header"]]
    assert header == [list(step) for step in _HEADER_DEGRADE_STEPS]


def test_only_the_unported_steps_are_marked_not_applicable():
    """`quicklook` is the only TOP plugin the v5 WebUI does not render yet."""
    top = _cascades()["top"]
    assert [s["key"] for s in top if s.get("notApplicable")] == ["quicklook_freq_only", "hide_quicklook"]
    assert not [s for s in _cascades()["header"] if s.get("notApplicable")]
