#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances unit tests for secure_popen (glances.secure).

Tests cover:
- secure_popen basic functionality (chain, pipe, redirect)
- Mustache fields land in exactly one argv slot (GHSA-56xw-p9qm-r437)
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from glances.secure import secure_popen

# Skip the whole module on Windows where echo -n behaves differently
pytestmark = pytest.mark.skipif(
    os.name == 'nt',
    reason='Shell command tests are POSIX-only',
)


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


class _FakeProcess:
    """Minimal Popen stand-in: no output, no exit status."""

    def __init__(self):
        self.stdout = MagicMock()

    def communicate(self, timeout=None):
        return (b'', b'')

    def wait(self, timeout=None):
        return 0


# ---------------------------------------------------------------------------
# Tests – argument injection through Mustache values (GHSA-56xw-p9qm-r437)
# ---------------------------------------------------------------------------

# The reported payload: a literal single quote closes the quoted Mustache field
# early, then three fully attacker-controlled argv tokens follow.
_POC_VALUE = "/mnt/usb/x' --evil-flag /etc/passwd http://attacker.example/leak 'y"


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
