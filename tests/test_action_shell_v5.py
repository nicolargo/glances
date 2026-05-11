#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the shell `GlancesActionBase` subclass."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest

from glances.actions_v5.shell import ShellAction

# ---------------------------------------------------------- helpers


class _FakeProcess:
    def __init__(self, returncode: int = 0, stderr: bytes = b"") -> None:
        self.returncode = returncode
        self._stderr = stderr

    async def communicate(self) -> tuple[bytes, bytes]:
        return (b"", self._stderr)


@pytest.fixture
def shell_action() -> ShellAction:
    return ShellAction()


# ---------------------------------------------------------- contract


def test_action_name_is_action(shell_action):
    assert shell_action.action_name == "action"


def test_is_available_true(shell_action):
    assert shell_action.is_available() is True


# ---------------------------------------------------------- render & exec


async def test_renders_simple_template_and_executes(shell_action):
    fake_proc = _FakeProcess(returncode=0)
    with patch(
        "glances.actions_v5.shell.asyncio.create_subprocess_shell",
        new=AsyncMock(return_value=fake_proc),
    ) as mock_exec:
        await shell_action.execute("mem", "warning", {"percent": 75.0}, "echo {{percent}}", repeat=False)
    mock_exec.assert_awaited_once()
    # Shell command is the first positional arg.
    rendered_command = mock_exec.await_args.args[0]
    assert rendered_command == "echo 75.0"


async def test_builtin_variables_substituted(shell_action):
    fake_proc = _FakeProcess()
    with patch(
        "glances.actions_v5.shell.asyncio.create_subprocess_shell",
        new=AsyncMock(return_value=fake_proc),
    ) as mock_exec:
        await shell_action.execute(
            "mem",
            "critical",
            {
                "percent": 95.0,
                "_glances_hostname": "myhost",
                "_glances_plugin": "mem",
                "_glances_level": "critical",
                "_glances_timestamp": "2026-05-11T10:00:00+00:00",
            },
            "logger glances-{{_glances_plugin}}-{{_glances_level}}: {{percent}}",
        )
    cmd = mock_exec.await_args.args[0]
    assert cmd == "logger glances-mem-critical: 95.0"


async def test_shell_metacharacters_are_quoted_to_defeat_injection(shell_action):
    """Malicious metric value cannot break out of the shell context (CVE-2026-32608)."""
    fake_proc = _FakeProcess()
    malicious = "foo; rm -rf /"
    with patch(
        "glances.actions_v5.shell.asyncio.create_subprocess_shell",
        new=AsyncMock(return_value=fake_proc),
    ) as mock_exec:
        await shell_action.execute(
            "containers",
            "critical",
            {"name": malicious},
            "logger {{name}}",
        )
    cmd = mock_exec.await_args.args[0]
    # shlex.quote wraps it in single quotes — the `;` cannot start a new command.
    assert "'foo; rm -rf /'" in cmd
    assert cmd.startswith("logger ")


async def test_returncode_non_zero_is_logged(shell_action, caplog):
    fake_proc = _FakeProcess(returncode=2, stderr=b"command not found")
    with (
        patch(
            "glances.actions_v5.shell.asyncio.create_subprocess_shell",
            new=AsyncMock(return_value=fake_proc),
        ),
        caplog.at_level(logging.WARNING),
    ):
        await shell_action.execute("mem", "warning", {}, "false")
    assert "non-zero exit" in caplog.text
    assert "returncode=2" in caplog.text


async def test_subprocess_exception_is_logged_not_raised(shell_action, caplog):
    """OSError during subprocess startup is captured, not propagated."""
    with (
        patch(
            "glances.actions_v5.shell.asyncio.create_subprocess_shell",
            new=AsyncMock(side_effect=OSError("fork failed")),
        ),
        caplog.at_level(logging.WARNING),
    ):
        await shell_action.execute("mem", "warning", {}, "some-cmd")
    assert "execution failed" in caplog.text


async def test_template_render_error_is_logged_and_skips_exec(shell_action, caplog):
    """A malformed template logs a warning and never invokes the subprocess."""
    with (
        patch(
            "glances.actions_v5.shell.asyncio.create_subprocess_shell",
            new=AsyncMock(),
        ) as mock_exec,
        patch("glances.actions_v5.shell.chevron.render", side_effect=ValueError("bad template")),
        caplog.at_level(logging.WARNING),
    ):
        await shell_action.execute("mem", "warning", {}, "echo {{percent}}")
    mock_exec.assert_not_awaited()
    assert "template render failed" in caplog.text


async def test_repeat_flag_passed_through(shell_action):
    """`repeat=True` is honoured by the action signature (logged on failure)."""
    fake_proc = _FakeProcess(returncode=1, stderr=b"oops")
    with (
        patch(
            "glances.actions_v5.shell.asyncio.create_subprocess_shell",
            new=AsyncMock(return_value=fake_proc),
        ),
        # Use caplog to inspect the log line which carries repeat= info.
        patch("glances.actions_v5.shell.logger") as mock_logger,
    ):
        await shell_action.execute("mem", "warning", {}, "false", repeat=True)
    # repeat=True must appear in the warning args of the non-zero-exit log line.
    mock_logger.warning.assert_called_once()
    args = mock_logger.warning.call_args.args
    # The format string positional args include repeat — check it's True somewhere.
    assert True in args
