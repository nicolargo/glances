#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — run the WebUI's pure JS modules under node's built-in runner.

No npm test dependency: node ships a runner (`node --test`, 18+) and
auto-detects ESM syntax in a `.js` file when the nearest package.json has no
`type` field (22+) -- which is exactly the case for
`glances/outputs/static/`. Verified before this plan was written.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_JS_TESTS = Path(__file__).resolve().parent / "js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not available")


def _run(*paths: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["node", "--no-warnings", "--test", *paths],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _js_test_files() -> list[str]:
    return sorted(f"tests/js/{p.name}" for p in _JS_TESTS.glob("*.test.mjs"))


def test_js_test_files_exist():
    """Guard: an empty file list would make node exit 0 and prove nothing."""
    assert _js_test_files()


def test_pure_modules_pass_their_unit_tests():
    result = _run(*_js_test_files())
    assert result.returncode == 0, result.stdout + result.stderr
