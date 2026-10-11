#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Every `glances` module the code and the tests import exists.

The Glances v4 modules were deleted when v5 replaced them. An import of a
deleted module inside a function or an optional branch only fails when that
path runs: this test reads every import statically.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _is_module(name):
    relative = ROOT.joinpath(*name.split("."))
    # A directory is a package, a namespace package (plugins/mpp/cards) included.
    return relative.with_suffix(".py").is_file() or any(relative.glob("*.py"))


def _glances_imports(path):
    """`(line, module)` for every `glances` module `path` imports."""
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names = [node.module]
        else:
            continue
        for name in names:
            if name == "glances" or name.startswith("glances."):
                yield node.lineno, name


def test_no_import_of_a_missing_glances_module():
    missing = [
        f"{path.relative_to(ROOT)}:{line}: {name}"
        for folder in ("glances", "tests")
        for path in sorted((ROOT / folder).rglob("*.py"))
        if "node_modules" not in path.parts
        for line, name in _glances_imports(path)
        if not _is_module(name)
    ]
    assert not missing, missing
