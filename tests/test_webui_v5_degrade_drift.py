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
copies from drifting apart, so this test makes drift a failure.

It also guards the inverse mistake, the one that actually shipped once
(G9-8 Task 6): `quicklook`'s two steps were flagged `notApplicable: true` when
the WebUI did not render quicklook yet, and porting the plugin (Task 5) left
them in place with an all-green suite, because the old guard here
(`test_only_the_unported_steps_are_marked_not_applicable`) only compared a
hardcoded key list against itself — it never looked at what the JS plugin
registry actually renders. `test_no_step_is_marked_not_applicable_for_a_live_plugin`
derives the rendered plugin names from js/v5/plugins/index.js instead, so it
keeps working the day a future step is flagged `notApplicable` for a plugin
that is already on screen.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from glances.outputs.glances_curses_v5 import _DEGRADE_STEPS, _HEADER_DEGRADE_STEPS

_JS_V5 = Path(__file__).resolve().parent.parent / "glances" / "outputs" / "static" / "js" / "v5"
_DEGRADE_JS = _JS_V5 / "degrade.js"
_PLUGINS_INDEX_JS = _JS_V5 / "plugins" / "index.js"
_PLUGIN_NAME_RE = re.compile(r'name:\s*"([a-zA-Z0-9_]+)"')
# Every registry entry pairs one `import PluginX from "../PluginX.vue";` with one
# `{ name: "x", ... }` object (the registry's own module docstring: "Adding a
# plugin is ONE new .vue file plus ONE entry here"). Counting the imports gives
# a plausibility check for `_rendered_plugin_names()` that needs no hardcoded
# number and adapts by itself as plugins are ported: a regex that silently
# drops one entry (e.g. `quicklook`) from the PLUGINS array leaves this count
# unequal to the import count, even though the extracted list stays non-empty.
_PLUGIN_IMPORT_RE = re.compile(r'^import \w+ from "\.\./\w+\.vue";$', re.MULTILINE)

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


def _rendered_plugin_names() -> list[str]:
    """The registry's plugin names, read from plugins/index.js.

    `index.js` imports one `.vue` file per plugin, and plain node cannot
    `import()` a `.vue` specifier -- `Unknown file extension ".vue"` --
    without a bundler-grade loader this project does not otherwise need
    (adding one would be a new dependency for a single test). Every entry's
    `name: "..."` field is plain, regular text, so reading it directly off
    the same file the bundle is built from derives the registry without a
    second hardcoded list and without needing to actually execute the
    module.
    """
    text = _PLUGINS_INDEX_JS.read_text()
    return _PLUGIN_NAME_RE.findall(text)


def _plugin_import_count() -> int:
    return len(_PLUGIN_IMPORT_RE.findall(_PLUGINS_INDEX_JS.read_text()))


def test_the_top_cascade_matches_the_tui():
    top = [[step["key"], step["value"]] for step in _cascades()["top"]]
    assert top == [list(step) for step in _DEGRADE_STEPS]


def test_the_header_cascade_matches_the_tui():
    header = [[step["key"], step["value"]] for step in _cascades()["header"]]
    assert header == [list(step) for step in _HEADER_DEGRADE_STEPS]


def test_every_step_is_live():
    """Every TOP/HEADER step now acts on a plugin the v5 WebUI renders --
    `quicklook`, the last one, was ported in G9-8. Renamed from
    `test_only_the_unported_steps_are_marked_not_applicable`, which this
    replaces: there is no unported step left to name."""
    assert not [s for s in _cascades()["top"] if s.get("notApplicable")]
    assert not [s for s in _cascades()["header"] if s.get("notApplicable")]


def test_no_step_is_marked_not_applicable_for_a_live_plugin():
    """The guard `test_every_step_is_live` alone does not provide: a future
    step flagged `notApplicable` for a plugin the registry already renders
    must fail, not silently ship (this is exactly how the two `quicklook`
    steps survived the plugin's port). A step's key names its plugin as a
    substring (`hide_gpu` -> `gpu`, `quicklook_freq_only` -> `quicklook`),
    so this needs no second hardcoded mapping.
    """
    plugin_names = _rendered_plugin_names()
    assert plugin_names, "guard: the registry read must not come back empty"
    # `quicklook` is the plugin this guard was built for: it is the one whose
    # cascade steps shipped as `notApplicable` long after the plugin itself was
    # ported (G9-8). Its disappearance from the extraction -- e.g. a regex that
    # stops matching just this one entry while the other 24 still match -- must
    # be a failure here, not a silent pass that leaves the exact gap this guard
    # exists to close wide open again.
    assert "quicklook" in plugin_names, f"guard: `quicklook` missing from the extraction: {plugin_names!r}"
    # A non-empty list alone does not catch a PARTIAL extraction (e.g. 24 of 25
    # names). Comparing against the `.vue` import count instead of a hardcoded
    # number needs no upkeep as plugins are ported -- both counts grow together
    # by construction (index.js's own docstring: one new .vue file, one new
    # registry entry) -- and it is exact, not just a plausibility floor.
    assert len(plugin_names) == _plugin_import_count(), (
        f"guard: {len(plugin_names)} names extracted but {_plugin_import_count()} "
        f".vue imports in the same file -- a partial extraction: {plugin_names!r}"
    )

    steps = _cascades()["top"] + _cascades()["header"]
    for step in steps:
        if not step.get("notApplicable"):
            continue
        matches = [name for name in plugin_names if name in step["key"]]
        assert not matches, (
            f"step {step['key']!r} is marked notApplicable but names a plugin the registry renders: {matches!r}"
        )
