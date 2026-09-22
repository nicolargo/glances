#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the WebUI's `--full-quicklook` hidden set is the TUI's.

`_FULL_QUICKLOOK_HIDDEN` (glances/outputs/curses_renderer_v5.py:91) is a
Python frozenset. The browser cannot import Python, so
js/v5/full_quicklook.js keeps a copy — and a silent divergence there would
hide (or fail to hide) the wrong blocks under `--full-quicklook`. This test
makes drift a failure, like tests/test_webui_v5_smart_keys_drift.py does for
`smart`'s LARGE_VALUE_KEYS and tests/test_webui_v5_degrade_drift.py does for
the degradation cascades.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from glances.outputs.curses_renderer_v5 import _FULL_QUICKLOOK_HIDDEN

_MODULE = Path(__file__).resolve().parent.parent / "glances" / "outputs" / "static" / "js" / "v5" / "full_quicklook.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not available")


def _js_hidden() -> list[str]:
    script = (
        f"import('{_MODULE.as_posix()}')"
        ".then((m) => process.stdout.write(JSON.stringify([...m.FULL_QUICKLOOK_HIDDEN].sort())))"
    )
    result = subprocess.run(
        ["node", "--no-warnings", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_the_js_copy_matches_the_curses_renderer_constant():
    assert _js_hidden() == sorted(_FULL_QUICKLOOK_HIDDEN)


def test_the_copy_is_not_empty():
    """Guard: an empty set on both sides would satisfy the comparison above.

    The count is `TOP_SLOT` minus `quicklook` -- the mode hides every sibling
    since 2026-09-22 (it was v4's 6 before, with `load` and `percpu` exempt).
    Asserted against `TOP_SLOT` rather than a literal so that adding a TOP
    plugin does not fail this guard for the wrong reason.
    """
    from glances.outputs.curses_renderer_v5 import TOP_SLOT

    assert len(_FULL_QUICKLOOK_HIDDEN) == len(TOP_SLOT) - 1
    assert "quicklook" not in _FULL_QUICKLOOK_HIDDEN
