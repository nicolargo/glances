#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the WebUI's LARGE_VALUE_KEYS is the plugin's.

`smart` formats six attribute keys with auto_unit() and prints every other one
raw (glances/plugins/smart/__init__.py:70-79, :257-259). The browser cannot
import Python, so js/v5/smart_keys.js keeps a copy — and a silent divergence
there changes displayed NUMBERS, not layout. This test makes drift a failure,
like tests/test_webui_v5_degrade_drift.py does for the degradation cascades.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from glances.plugins.smart import LARGE_VALUE_KEYS

_MODULE = Path(__file__).resolve().parent.parent / "glances" / "outputs" / "static" / "js" / "v5" / "smart_keys.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not available")


def _js_keys() -> list[str]:
    script = (
        f"import('{_MODULE.as_posix()}')"
        ".then((m) => process.stdout.write(JSON.stringify([...m.LARGE_VALUE_KEYS].sort())))"
    )
    result = subprocess.run(
        ["node", "--no-warnings", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_the_js_copy_matches_the_plugin_constant():
    assert _js_keys() == sorted(LARGE_VALUE_KEYS)


def test_the_copy_is_not_empty():
    """Guard: an empty Set on both sides would satisfy the comparison above."""
    assert len(LARGE_VALUE_KEYS) == 6
