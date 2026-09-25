#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the WebUI's hotkeys are the TUI's.

The `hide` entries of `TuiV5._HOTKEYS` (glances/outputs/glances_curses_v5.py)
are a Python dict. The browser cannot import Python, so js/v5/hotkeys.js keeps
a copy — and a silent divergence there would bind a key to the wrong plugins,
or (worse, because it is invisible) describe it differently in the two help
screens. This test makes drift a failure, like
tests/test_webui_v5_full_quicklook_drift.py does for `_FULL_QUICKLOOK_HIDDEN`
and tests/test_webui_v5_degrade_drift.py does for the degradation cascades.

The two slot keys (`2`, `5`) are NOT literal lists in the JS: they resolve
against the plugin registry at press time. They are compared here by resolving
them against the registry's own slot membership, which is what the browser
does — so this test also fails if the registry's slots drift from the TUI's.

The TOGGLE VIEW group (`1`, `j`, `4`, `/`) is covered the same way, further
down: those keys carry no plugin list, so what is compared is the key set and
the descriptions, plus the requirement that each one names the `serverArgs`
flag it overrides.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from glances.outputs.curses_renderer_v5 import LEFT_SLOT, TOP_SLOT
from glances.outputs.glances_curses_v5 import TuiV5

_STATIC = Path(__file__).resolve().parent.parent / "glances" / "outputs" / "static" / "js" / "v5"
_MODULE = _STATIC / "hotkeys.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not available")

# What the browser's registry holds for the two slot keys. Resolving against
# the TUI's own tuples keeps this honest without importing the .vue registry.
_SLOT_MEMBERS = {"left": LEFT_SLOT, "top": TOP_SLOT}


def _python_hide_table() -> dict[str, dict[str, object]]:
    return {
        key: {"plugins": list(spec["hide"]), "desc": spec["desc"]}
        for key, spec in TuiV5._HOTKEYS.items()
        if "hide" in spec
    }


def _js_hide_table() -> dict[str, dict[str, object]]:
    """The JS table, with slot keys resolved exactly as the browser resolves
    them: `hideTargets()` against a registry carrying each plugin's slot."""
    registry = [{"name": name, "slot": slot} for slot, names in _SLOT_MEMBERS.items() for name in names]
    script = f"""
    import('{_MODULE.as_posix()}').then((m) => {{
        const registry = {json.dumps(registry)};
        const out = {{}};
        for (const [key, entry] of Object.entries(m.HIDE_KEYS)) {{
            out[key] = {{ plugins: m.hideTargets(key, registry), desc: entry.desc }};
        }}
        for (const [key, entry] of Object.entries(m.HIDE_SLOT_KEYS)) {{
            out[key] = {{ plugins: m.hideTargets(key, registry), desc: entry.desc }};
        }}
        process.stdout.write(JSON.stringify(out));
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


def test_the_js_copy_binds_the_same_keys():
    assert sorted(_js_hide_table()) == sorted(_python_hide_table())


def test_every_key_hides_the_same_plugins_in_both_surfaces():
    """Order matters as well as membership: the dispatcher keys the flip on the
    FIRST name, so a reordered compound key would flip on a different member."""
    js, py = _js_hide_table(), _python_hide_table()
    for key in sorted(py):
        assert js[key]["plugins"] == py[key]["plugins"], key


def test_every_key_is_described_identically_in_both_surfaces():
    """The two help screens must not tell a user different things about the
    same key — the drift no one notices until it is confusing."""
    js, py = _js_hide_table(), _python_hide_table()
    for key in sorted(py):
        assert js[key]["desc"] == py[key]["desc"], key


def test_the_copy_is_not_empty():
    """Guard: two empty tables would satisfy every comparison above."""
    py = _python_hide_table()
    assert len(py) == 24, sorted(py)


def _python_view_table() -> dict[str, str]:
    """The TUI's TOGGLE VIEW group: key -> description."""
    return {key: spec["desc"] for key, spec in TuiV5._HOTKEYS.items() if spec.get("group") == "TOGGLE VIEW"}


def _js_view_table() -> dict[str, dict[str, str]]:
    script = f"""
    import('{_MODULE.as_posix()}').then((m) => process.stdout.write(JSON.stringify(m.VIEW_KEYS)));
    """
    result = subprocess.run(
        ["node", "--no-warnings", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_the_js_copy_binds_the_same_toggle_view_keys():
    """`1`, `j`, `4`, `/` -- the keys that change HOW something is shown rather
    than whether it is shown."""
    assert sorted(_js_view_table()) == sorted(_python_view_table())


def test_every_toggle_view_key_is_described_identically_in_both_surfaces():
    js, py = _js_view_table(), _python_view_table()
    for key in sorted(py):
        assert js[key]["desc"] == py[key], key


def test_every_toggle_view_key_names_a_flag():
    """The flag is what the browser overrides on top of `serverArgs`. An entry
    without one would be a key that dispatches and does nothing."""
    for key, entry in _js_view_table().items():
        assert entry.get("flag"), key


def test_the_help_overlay_documents_every_bound_key():
    """The TUI generates its overlay from `_HOTKEYS` itself, so a bound key
    cannot go undocumented. `helpRows()` gives the browser the same property —
    this test is what holds it, across BOTH groups."""
    script = f"""
    import('{_MODULE.as_posix()}').then((m) => {{
        process.stdout.write(JSON.stringify(m.helpRows().map((r) => r.key)));
    }});
    """
    result = subprocess.run(
        ["node", "--no-warnings", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    documented = sorted(json.loads(result.stdout))
    assert documented == sorted([*_python_hide_table(), *_python_view_table()])


def test_the_startup_flags_press_the_same_keys_in_both_surfaces():
    """`-2`/`-3`/`-5`/`--disable-process`/`--light`: in server mode only the
    browser can honour them, so its table must be the TUI's."""
    from glances.outputs.glances_curses_v5 import STARTUP_HIDE_KEYS

    script = f"""
    import('{_MODULE.as_posix()}').then((m) => process.stdout.write(JSON.stringify(m.STARTUP_HIDE_KEYS)));
    """
    result = subprocess.run(
        ["node", "--no-warnings", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    js = json.loads(result.stdout)
    assert js == {flag: list(keys) for flag, keys in STARTUP_HIDE_KEYS.items()}
