#!/usr/bin/env python
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Virsh VM engine command-injection safety.

Regression tests for GHSA-v5r2-qh84-fjx5 / CVE-2026-46606: VM domain names
parsed from `virsh list --all` output reached secure_popen() through an
f-string. secure_popen() interprets `&&`, `|` and `>` as shell operators, so
any libvirt-privileged user could create a VM whose name embedded an extra
command and gain code execution under the Glances process (typically root on
hypervisor hosts).

The fix routes the two affected calls (update_stats, update_title) through a
subprocess.run([...], shell=False) helper so that the domain name is opaque.
"""

import os
import shutil
import tempfile
from unittest.mock import patch

import pytest

# POSIX-only: the canary tests rely on /usr/bin/echo and /usr/bin/touch.
pytestmark = pytest.mark.skipif(
    os.name == 'nt',
    reason='Command-injection tests are POSIX-only',
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_extension():
    """Build a VmExtension instance without triggering the import-time check.

    The module sets ``import_virsh_error_tag`` at import time based on
    /usr/bin/virsh existence. We only need the class methods, not the tag, so
    instantiating the class is sufficient.
    """
    from glances.plugins.vms.engines.virsh import VmExtension

    return VmExtension()


# ---------------------------------------------------------------------------
# Real-injection canary tests
# ---------------------------------------------------------------------------


class TestUpdateStatsInjectionCanary:
    """Run update_stats() with /usr/bin/echo as VIRSH_PATH and check the canary.

    With the vulnerable code, the `&&`/`|`/`>` operator in the domain name is
    interpreted by secure_popen() and a real second command is executed. The
    canary file ends up created/written. With the fix, the domain is a single
    opaque subprocess argument and the canary never appears.
    """

    def _run_with_canary(self, payload_fmt, canary_name='pwned'):
        """Build a domain whose name embeds an injection that touches a canary.

        Returns the canary path so the caller can assert it does NOT exist.
        """
        tmpdir = tempfile.mkdtemp(prefix='glances-virsh-injection-')
        canary = os.path.join(tmpdir, canary_name)
        domain = payload_fmt.format(canary=canary)

        ext = _make_extension()
        with patch('glances.plugins.vms.engines.virsh.VIRSH_PATH', '/usr/bin/echo'):
            # Discard the return value; we only care about side effects.
            ext.update_stats(domain)

        return canary, tmpdir

    def _cleanup(self, _canary, tmpdir):
        # Use rmtree so any extra files spawned by the injection are removed too.
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_double_ampersand_injection_blocked(self):
        canary, tmpdir = self._run_with_canary('fakevm && /usr/bin/touch {canary}')
        try:
            assert not os.path.exists(canary), f'Command injection via && succeeded: {canary} was created'
        finally:
            self._cleanup(canary, tmpdir)

    def test_pipe_injection_blocked(self):
        canary, tmpdir = self._run_with_canary('fakevm | /usr/bin/tee {canary}')
        try:
            assert not os.path.exists(canary), f'Command injection via | succeeded: {canary} was created'
        finally:
            self._cleanup(canary, tmpdir)

    def test_redirect_injection_blocked(self):
        canary, tmpdir = self._run_with_canary('fakevm > {canary}')
        try:
            assert not os.path.exists(canary), f'Command injection via > succeeded: {canary} was created'
        finally:
            self._cleanup(canary, tmpdir)


class TestUpdateTitleInjectionCanary:
    """Same canary scenarios for update_title()."""

    def _run_with_canary(self, payload_fmt, canary_name):
        tmpdir = tempfile.mkdtemp(prefix='glances-virsh-injection-')
        # update_title is functools.cache-decorated. Vary the canary file
        # name so each test passes a unique domain string and the cache
        # cannot mask the call.
        canary = os.path.join(tmpdir, canary_name)
        domain = payload_fmt.format(canary=canary)

        ext = _make_extension()
        with patch('glances.plugins.vms.engines.virsh.VIRSH_PATH', '/usr/bin/echo'):
            ext.update_title(domain)

        return canary, tmpdir

    def _cleanup(self, _canary, tmpdir):
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_double_ampersand_injection_blocked(self):
        canary, tmpdir = self._run_with_canary('fakevm && /usr/bin/touch {canary}', canary_name='title-and')
        try:
            assert not os.path.exists(canary), f'Command injection via && succeeded: {canary} was created'
        finally:
            self._cleanup(canary, tmpdir)

    def test_pipe_injection_blocked(self):
        canary, tmpdir = self._run_with_canary('fakevm | /usr/bin/tee {canary}', canary_name='title-pipe')
        try:
            assert not os.path.exists(canary), f'Command injection via | succeeded: {canary} was created'
        finally:
            self._cleanup(canary, tmpdir)

    def test_redirect_injection_blocked(self):
        canary, tmpdir = self._run_with_canary('fakevm > {canary}', canary_name='title-redirect')
        try:
            assert not os.path.exists(canary), f'Command injection via > succeeded: {canary} was created'
        finally:
            self._cleanup(canary, tmpdir)


# ---------------------------------------------------------------------------
# Argument-shape tests (defence-in-depth: enforce shell=False contract)
# ---------------------------------------------------------------------------


class TestArgumentShape:
    """The domain must reach subprocess as a single, untouched argument.

    These tests pin the post-fix contract: shell=False, list-form args, and
    the domain string is preserved verbatim (no quoting, no splitting).
    """

    def test_update_stats_passes_domain_as_single_arg(self):
        ext = _make_extension()
        domain = 'foo && touch /tmp/should-not-happen | tee >x'
        with patch('glances.plugins.vms.engines.virsh.subprocess_run') as mock_run:
            mock_run.return_value = type('R', (), {'returncode': 0, 'stdout': b'', 'stderr': b''})()
            ext.update_stats(domain)

        assert mock_run.called, 'subprocess.run must be invoked (not secure_popen)'
        call_args, call_kwargs = mock_run.call_args
        argv = call_args[0]
        assert isinstance(argv, list), 'args must be a list, not a shell string'
        assert call_kwargs.get('shell', False) is False, 'shell=False required'
        assert argv[-1] == domain, 'domain must be passed as one opaque argv element'
        # The virsh binary and the domstats sub-command come first
        assert argv[0].endswith('virsh') or argv[0] == '/usr/bin/virsh'
        assert 'domstats' in argv

    def test_update_title_passes_domain_as_single_arg(self):
        ext = _make_extension()
        # Unique value to avoid functools.cache hits from other tests
        domain = 'titletest && cmd | x > y unique-arg-shape'
        with patch('glances.plugins.vms.engines.virsh.subprocess_run') as mock_run:
            mock_run.return_value = type('R', (), {'returncode': 0, 'stdout': b'', 'stderr': b''})()
            ext.update_title(domain)

        assert mock_run.called, 'subprocess.run must be invoked (not secure_popen)'
        call_args, call_kwargs = mock_run.call_args
        argv = call_args[0]
        assert isinstance(argv, list)
        assert call_kwargs.get('shell', False) is False
        assert argv[-1] == domain
        assert 'desc' in argv
