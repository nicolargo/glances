#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for GlancesActionBase + discover_actions().

Test stack: pytest + pytest-asyncio (auto mode). See architecture decisions §9.

Coverage:
- Contract: action_name empty rejected, execute() abstract, requires probing
- Discovery: module on disk → registry; missing requires → skip; broken
  module → skip; duplicate action_name → ValueError
- Discovery skips action_base.py itself
- Re-exported subclasses from another module are not double-registered
"""

from __future__ import annotations

import logging
import textwrap
from pathlib import Path

import pytest

from glances.actions_v5 import GlancesActionBase, discover_actions

# ---------------------------------------------------------- contract


def test_action_name_empty_raises():
    class NoName(GlancesActionBase):
        async def execute(self, plugin_name, level, context, action_value, repeat=False):
            return None

    with pytest.raises(ValueError, match="action_name"):
        NoName()


def test_cannot_instantiate_abstract_base():
    with pytest.raises(TypeError):
        GlancesActionBase()  # type: ignore[abstract]


def test_is_available_true_when_no_requires():
    class NoDeps(GlancesActionBase):
        action_name = "nodeps"

        async def execute(self, plugin_name, level, context, action_value, repeat=False):
            return None

    assert NoDeps().is_available() is True


def test_is_available_true_when_requires_importable():
    class WithStdlib(GlancesActionBase):
        action_name = "withstdlib"
        requires = ["json", "os"]  # stdlib modules always available

        async def execute(self, plugin_name, level, context, action_value, repeat=False):
            return None

    assert WithStdlib().is_available() is True


def test_is_available_false_when_requires_missing():
    class MissingDep(GlancesActionBase):
        action_name = "missing"
        requires = ["this_module_does_not_exist_xyz123"]

        async def execute(self, plugin_name, level, context, action_value, repeat=False):
            return None

    assert MissingDep().is_available() is False


# ---------------------------------------------------------- discovery
#
# Each test builds a tiny on-disk package with one or more action modules,
# adds it to sys.path via monkeypatch, then calls discover_actions().


@pytest.fixture
def fake_package(tmp_path: Path, monkeypatch, request):
    """Build an empty fake action package, return its dotted name + a writer.

    Each test gets a unique package name (derived from the test node id) so
    Python's `sys.modules` cache cannot leak module state between tests.
    """

    # Sanitise the test name into a valid Python package name.
    suffix = request.node.name.replace("[", "_").replace("]", "_").replace("-", "_")
    pkg_name = f"fake_actions_pkg_{suffix}"

    pkg_dir = tmp_path / pkg_name
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    monkeypatch.syspath_prepend(str(tmp_path))

    def write_module(name: str, body: str) -> None:
        (pkg_dir / f"{name}.py").write_text(textwrap.dedent(body))

    yield pkg_name, write_module

    # Teardown: drop any cached entries to keep tests hermetic if the same
    # name ever recurs (e.g. parametrised tests).
    import sys

    for mod_name in list(sys.modules):
        if mod_name == pkg_name or mod_name.startswith(f"{pkg_name}."):
            del sys.modules[mod_name]


def test_discover_finds_concrete_action(fake_package):
    package, write = fake_package
    write(
        "shell",
        """
        from glances.actions_v5 import GlancesActionBase

        class ShellAction(GlancesActionBase):
            action_name = "shell"

            async def execute(self, plugin_name, level, context, action_value, repeat=False):
                return None
        """,
    )

    registry = discover_actions(package)

    assert "shell" in registry
    assert isinstance(registry["shell"], GlancesActionBase)
    assert type(registry["shell"]).__name__ == "ShellAction"


def test_discover_skips_module_with_missing_requires(fake_package, caplog):
    package, write = fake_package
    write(
        "needs_apprise",
        """
        from glances.actions_v5 import GlancesActionBase

        class AppriseAction(GlancesActionBase):
            action_name = "apprise"
            requires = ["this_module_does_not_exist_xyz123"]

            async def execute(self, plugin_name, level, context, action_value, repeat=False):
                return None
        """,
    )

    with caplog.at_level(logging.WARNING):
        registry = discover_actions(package)

    assert "apprise" not in registry
    assert "missing dependencies" in caplog.text


def test_discover_skips_broken_module(fake_package, caplog):
    package, write = fake_package
    write("broken", "raise RuntimeError('boom')")

    with caplog.at_level(logging.WARNING):
        registry = discover_actions(package)

    assert registry == {}
    assert "import failed" in caplog.text


def test_discover_raises_on_duplicate_action_name(fake_package):
    package, write = fake_package
    write(
        "shell_a",
        """
        from glances.actions_v5 import GlancesActionBase

        class ShellA(GlancesActionBase):
            action_name = "shell"

            async def execute(self, plugin_name, level, context, action_value, repeat=False):
                return None
        """,
    )
    write(
        "shell_b",
        """
        from glances.actions_v5 import GlancesActionBase

        class ShellB(GlancesActionBase):
            action_name = "shell"

            async def execute(self, plugin_name, level, context, action_value, repeat=False):
                return None
        """,
    )

    with pytest.raises(ValueError, match="Duplicate action_name"):
        discover_actions(package)


def test_discover_ignores_reexported_classes(fake_package):
    """A module that imports a class from elsewhere must not re-register it."""

    package, write = fake_package
    write(
        "real",
        """
        from glances.actions_v5 import GlancesActionBase

        class WebhookAction(GlancesActionBase):
            action_name = "webhook"

            async def execute(self, plugin_name, level, context, action_value, repeat=False):
                return None
        """,
    )
    # Second module re-exports the class — should be ignored by discovery.
    write(
        "reexport",
        f"from {package}.real import WebhookAction",
    )

    registry = discover_actions(package)

    assert list(registry.keys()) == ["webhook"]


def test_discover_real_v5_package_contains_shell_action():
    """Phase 1.4 ships the shell action — it must be discoverable in the real package."""
    registry = discover_actions("glances.actions_v5")
    assert "action" in registry
    assert type(registry["action"]).__name__ == "ShellAction"


def test_discover_rejects_non_package(tmp_path, monkeypatch):
    # Create a plain module (no __path__).
    (tmp_path / "notapkg.py").write_text("x = 1")
    monkeypatch.syspath_prepend(str(tmp_path))

    with pytest.raises(ValueError, match="not a package"):
        discover_actions("notapkg")
