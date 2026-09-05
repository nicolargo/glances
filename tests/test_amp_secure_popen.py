#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Regression tests for GHSA-3vwc-qwhc-3mj7.

AMP `command` / `service_cmd` values are loaded verbatim from glances.conf and
passed to secure_popen(), which interprets the shell operators '&&', '|' and
'>'. The '>' operator allows arbitrary file writes.

These tests verify that:
- secure_popen(allow_operators=False) never interprets these operators, and
- the AMP path disables operator interpretation when --disable-config-exec is
  set, while keeping the historical (operator-enabled) behaviour by default.
"""

import os
import tempfile
from argparse import Namespace

from glances.amps.default import Amp as DefaultAmp
from glances.secure import secure_popen


def _make_amp(command, disable_config_exec):
    args = Namespace(disable_config_exec=disable_config_exec)
    amp = DefaultAmp(name='poc', args=args)
    amp.configs = {'enable': 'true', 'refresh': '3', 'command': command}
    return amp


# ---------------------------------------------------------------------------
# secure_popen(allow_operators=False)
# ---------------------------------------------------------------------------


class TestSecurePopenNoOperators:
    """When operators are disallowed, '&&', '|' and '>' are literal arguments."""

    def test_redirect_does_not_write_file(self):
        with tempfile.NamedTemporaryFile(mode='r', suffix='.txt', delete=True) as f:
            tmpfile = f.name
        # The temp file is now removed; secure_popen must NOT recreate it.
        assert not os.path.exists(tmpfile)
        result = secure_popen(f'echo -n HELLO > {tmpfile}', allow_operators=False)
        assert not os.path.exists(tmpfile), 'redirection must not write a file'
        # '>' and the path are echoed back as plain arguments.
        assert '>' in result and tmpfile in result

    def test_chaining_is_not_interpreted(self):
        result = secure_popen('echo -n A && echo -n B', allow_operators=False)
        assert result != 'AB', '&& must not chain commands'
        assert '&&' in result

    def test_pipe_is_not_interpreted(self):
        result = secure_popen('echo PIPED | grep PIPED', allow_operators=False)
        assert '|' in result, '| must not pipe between processes'


# ---------------------------------------------------------------------------
# AMP path gated by --disable-config-exec
# ---------------------------------------------------------------------------


class TestAmpRedirectMitigation:
    """Default AMP must honour --disable-config-exec for command operators."""

    def test_disable_config_exec_blocks_file_write(self):
        with tempfile.NamedTemporaryFile(mode='r', suffix='.txt', delete=True) as f:
            marker = f.name
        assert not os.path.exists(marker)
        amp = _make_amp(f'echo POC_ARBITRARY_FILE_WRITE > {marker}', disable_config_exec=True)
        amp.update([])
        assert not os.path.exists(marker), 'AMP must not write arbitrary files when hardened'

    def test_default_behaviour_unchanged(self):
        """Non-regression: without the flag the operator still works as before."""
        with tempfile.NamedTemporaryFile(mode='r', suffix='.txt', delete=True) as f:
            marker = f.name
        assert not os.path.exists(marker)
        amp = _make_amp(f'echo -n LEGIT > {marker}', disable_config_exec=False)
        try:
            amp.update([])
            assert os.path.exists(marker), 'default operator behaviour must be preserved'
            with open(marker) as fh:
                assert fh.read() == 'LEGIT'
        finally:
            if os.path.exists(marker):
                os.unlink(marker)
