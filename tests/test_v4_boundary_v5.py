#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""The modules outside v5 that the v5 code imports (security audit 2026-10-04, B1).

The v4 code is deleted when `develop-v5` is merged into `develop`. Until
then the weekly `develop -> develop-v5` merge keeps both, and the v4 files
must not be touched here. This test freezes what v5 reaches outside its own
modules, so the list can only shrink before the cutover
(`docs/architecture/glances-v5-cutover-plan.md`):

- `SHARED` modules stay after the merge: v4 and v5 both run them.
- `BORROWED` modules are v4 code v5 uses as a library: what v5 needs is
  moved out of them at the cutover, before the v4 code goes.

A new import outside both lists fails here: import a shared module, or add
the borrowing to `BORROWED` and to the cutover plan.

Only direct imports are checked. Importing `glances.plugins.<x>.model_v5`
also runs `glances/plugins/<x>/__init__.py`, the v4 plugin: that is the
package-parent half of B1, handled by the cutover plan.
"""

import ast
from fnmatch import fnmatchcase
from pathlib import Path

GLANCES = Path(__file__).resolve().parent.parent / "glances"

SHARED = {
    # Namespace packages, empty __init__.py.
    "glances.plugins": "namespace package",
    "glances.exports": "namespace package",
    "glances.outputs": "namespace package",
    # Engine shared by v4 and v5.
    "glances.globals": "helpers",
    "glances.logger": "log configuration",
    "glances.processes": "process engine",
    "glances.filter": "process filter",
    "glances.timer": "timers",
    "glances.secure": "secure_popen",
    "glances.folder_list": "folders plugin list",
    "glances.ports_list": "ports plugin list",
    "glances.web_list": "ports plugin URL list",
    "glances.amps.amp": "AMP base class",
    "glances.outputs.glances_bars": "TUI bars",
    "glances.outputs.glances_unicode": "TUI symbols",
    "glances.outputs.glances_mcp": "MCP server",
    # Drivers.
    "glances.plugins.*.engines": "container / VM engines",
    "glances.plugins.*.engines.*": "container / VM engines",
    "glances.plugins.*.cards.*": "GPU / NPU / MPP cards",
    "glances.plugins.sensors.sensor.*": "sensor grabbers",
    "glances.plugins.fs.zfs": "ZFS ARC reader (mem)",
}

BORROWED = {
    "glances": "psutil_version_info (psutilversion/model_v5.py); __init__ imports the v4 CLI",
    "glances.plugins.ports": "ThreadScanner (ports/model_v5.py)",
    "glances.plugins.sensors": "GlancesGrabSensors, sensors_definition (sensors/model_v5.py)",
    "glances.plugins.smart": "get_smart_data, LARGE_VALUE_KEYS (smart/model_v5.py, smart/render_curses_v5.py)",
}


def _v5_files():
    for path in GLANCES.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if "_v5" in path.stem or "actions_v5" in path.parts:
            yield path


def _module_name(path):
    parts = path.relative_to(GLANCES.parent).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _is_module(name):
    relative = Path(*name.split("."))
    return (GLANCES.parent / relative).with_suffix(".py").is_file() or (
        GLANCES.parent / relative / "__init__.py"
    ).is_file()


def _imported_modules(path):
    """Every `glances` module `path` imports, `from glances.x import y` included when `y` is a module."""
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            yield node.module
            for alias in node.names:
                if _is_module(f"{node.module}.{alias.name}"):
                    yield f"{node.module}.{alias.name}"


def _outside_imports():
    """`{module: {importer, ...}}` for the glances modules outside v5 that v5 imports."""
    files = list(_v5_files())
    v5_modules = {_module_name(path) for path in files}
    found = {}
    for path in files:
        for name in _imported_modules(path):
            if (name == "glances" or name.startswith("glances.")) and name not in v5_modules:
                found.setdefault(name, set()).add(_module_name(path))
    return found


def _listed(name, patterns):
    return any(fnmatchcase(name, pattern) for pattern in patterns)


def test_v5_reaches_only_shared_or_known_borrowed_modules():
    unlisted = {
        name: sorted(importers)
        for name, importers in _outside_imports().items()
        if not _listed(name, SHARED) and not _listed(name, BORROWED)
    }
    assert not unlisted, (
        "v5 imports modules outside v5 that are neither SHARED nor BORROWED; "
        f"use a shared module, or list the borrowing here and in the cutover plan: {unlisted}"
    )


def test_every_listed_module_is_still_imported():
    """A stale entry would let a borrowing come back unnoticed: remove it once unused."""
    imported = set(_outside_imports())
    stale = [pattern for pattern in {**SHARED, **BORROWED} if not any(fnmatchcase(n, pattern) for n in imported)]
    assert not stale, stale


def test_shared_and_borrowed_do_not_overlap():
    assert not set(SHARED) & set(BORROWED)
