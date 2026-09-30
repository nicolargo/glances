#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the WebUI's sortable headers are the TUI's.

Each renderer maps a header to the engine sort key it underlines. The browser
cannot import those maps, so it keeps copies (js/v5/process_shared.js,
js/v5/sort_headers.js). A drifted copy would underline one column while the
terminal underlines another, and a click would sort by a column the header
does not name. Shared sort design, 2026-09-30.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from glances.plugins.containers.render_curses_v5 import _HEADER_SORT_KEY as CONTAINERS
from glances.plugins.processlist.render_curses_v5 import _HEADER_SORT_KEY as PROCESSES
from glances.plugins.vms.render_curses_v5 import _HEADER_SORT_FIELD as VMS
from glances.processes import sort_processes_stats_list

_STATIC = Path(__file__).resolve().parent.parent / "glances" / "outputs" / "static" / "js" / "v5"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not available")


def _js(module: str, name: str) -> dict[str, str]:
    script = f"""
    import('{(_STATIC / module).as_posix()}').then((m) => process.stdout.write(JSON.stringify(m.{name})));
    """
    result = subprocess.run(
        ["node", "--no-warnings", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize(
    ("module", "name", "python"),
    [
        ("process_shared.js", "HEADER_SORT_KEY", PROCESSES),
        ("sort_headers.js", "CONTAINERS_HEADER_SORT_KEY", CONTAINERS),
        ("sort_headers.js", "VMS_HEADER_SORT_KEY", VMS),
    ],
)
def test_the_js_header_map_is_the_tuis(module, name, python):
    assert _js(module, name) == python


@pytest.mark.parametrize("python", [PROCESSES, CONTAINERS, VMS])
def test_every_mapped_header_sorts_by_a_key_the_route_accepts(python):
    for label, key in python.items():
        assert key in sort_processes_stats_list, label
