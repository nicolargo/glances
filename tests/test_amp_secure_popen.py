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
import time
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


# ---------------------------------------------------------------------------
# secure_popen(timeout=...)
# ---------------------------------------------------------------------------


def test_timeout_none_is_the_default_and_changes_nothing():
    """Default behaviour must be bit-for-bit v4: no timeout at all."""
    assert secure_popen('echo hello').strip() == 'hello'
    assert secure_popen('echo hello', timeout=None).strip() == 'hello'


def test_timeout_not_reached_returns_the_output():
    assert secure_popen('echo hello', timeout=10).strip() == 'hello'


def test_timeout_kills_a_hanging_command():
    start = time.monotonic()
    ret = secure_popen('sleep 30', timeout=0.5)
    elapsed = time.monotonic() - start
    assert 'timeout' in ret.lower()
    assert elapsed < 10, 'the command was not killed'


def test_timeout_applies_without_operators():
    start = time.monotonic()
    ret = secure_popen('sleep 30', allow_operators=False, timeout=0.5)
    elapsed = time.monotonic() - start
    assert 'timeout' in ret.lower()
    assert elapsed < 10, 'the command was not killed'


def test_amp_timeout_accessor_defaults_to_none():
    amp = _make_amp('echo hello', disable_config_exec=False)
    assert amp.timeout() is None


def test_amp_timeout_accessor_reads_the_config_key():
    amp = _make_amp('echo hello', disable_config_exec=False)
    amp.configs['timeout'] = 2.0
    assert amp.timeout() == 2.0


def test_amp_timeout_accessor_coerces_string_to_float():
    amp = _make_amp('echo hello', disable_config_exec=False)
    amp.configs['timeout'] = '2.5'
    assert amp.timeout() == 2.5


def test_amp_timeout_accessor_rejects_non_numeric_value(caplog):
    """A non-numeric `timeout=` (e.g. `10s`) must not dead-end the AMP with
    an unhandled TypeError/AttributeError deep in Popen.communicate() /
    set_result(); it is logged and treated as unset instead."""
    amp = _make_amp('echo hello', disable_config_exec=False)
    amp.configs['timeout'] = '10s'
    with caplog.at_level('WARNING'):
        result = amp.timeout()
    assert result is None
    assert 'Poc' in caplog.text
    assert '10s' in caplog.text


# ---------------------------------------------------------------------------
# secure_popen(timeout=...) — pipeline where an UPSTREAM stage hangs
# ---------------------------------------------------------------------------


def test_timeout_bounds_a_pipeline_whose_upstream_stage_hangs():
    """`__communicate` only applies `timeout` to the LAST stage. When the
    last stage exits first (e.g. `echo done` in `sleep 20 | echo done`),
    communicate() returns normally and the reap loop over the earlier
    stages must still be bounded by `timeout`, not block for `sleep 20`."""
    start = time.monotonic()
    ret = secure_popen('sleep 20 | echo done', timeout=0.5)
    elapsed = time.monotonic() - start
    assert elapsed < 5, f'the hung upstream stage was not bounded (took {elapsed:.1f}s): {ret!r}'


def test_timeout_kills_and_reaps_a_multi_process_pipeline():
    """Every stage hangs: both must be killed and reaped promptly, and the
    timeout error string returned (not the unbounded reap-loop hang)."""
    start = time.monotonic()
    ret = secure_popen('sleep 30 | sleep 30', timeout=0.5)
    elapsed = time.monotonic() - start
    assert 'timeout' in ret.lower()
    assert elapsed < 5, f'the pipeline was not killed and reaped promptly (took {elapsed:.1f}s)'
