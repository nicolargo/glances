#!/usr/bin/env python
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Glances version cache safety:
- Insecure pickle deserialization (GHSA-9837-48hr-q32j / CVE-2026-46607)."""

import os
import pickle
import shutil
import tempfile
import unittest
from datetime import datetime
from types import SimpleNamespace

from glances.outdated import Outdated

# Module-level marker. If a poisoned pickle is deserialized via
# pickle.load(), its __reduce__ callable will flip this flag.
PICKLE_PAYLOAD_EXECUTED = False


def _mark_pickle_executed():
    """Module-level callable referenced by the poisoned pickle payload.

    pickle requires the __reduce__ callable to be importable, so it must
    live at module level (not inside a test method).
    """
    global PICKLE_PAYLOAD_EXECUTED
    PICKLE_PAYLOAD_EXECUTED = True
    return 0


class _Poison:
    """Pickle payload whose deserialization invokes _mark_pickle_executed."""

    def __reduce__(self):
        return (_mark_pickle_executed, ())


class TestOutdatedCache(unittest.TestCase):
    """Verify the version cache file is not deserialized via pickle."""

    def setUp(self):
        global PICKLE_PAYLOAD_EXECUTED
        PICKLE_PAYLOAD_EXECUTED = False
        self.tmpdir = tempfile.mkdtemp(prefix='glances-test-outdated-')
        self.cache_file = os.path.join(self.tmpdir, 'glances-version.db')
        # Build an Outdated instance bypassing __init__ so we don't trigger
        # the background PyPI HTTP request during unit tests.
        self.outdated = object.__new__(Outdated)
        self.outdated.args = SimpleNamespace(disable_check_update=False, time=2)
        self.outdated.data = {
            'installed_version': '4.5.5',
            'latest_version': '0.0',
            'refresh_date': datetime.now(),
        }
        self.outdated.cache_dir = self.tmpdir
        self.outdated.cache_file = self.cache_file

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_001_malicious_pickle_is_not_executed(self):
        """A pickle planted at the cache path must NOT be deserialized.

        Regression test for CVE-2026-46607 / GHSA-9837-48hr-q32j: the cache
        file must be parsed with a non-executable format. Before the fix
        this assertion fails because pickle.load() invokes the payload's
        __reduce__ callable.
        """
        with open(self.cache_file, 'wb') as f:
            pickle.dump(_Poison(), f)

        # _load_cache must not raise to the caller and must not execute
        # the embedded callable. We tolerate any exception here because
        # the pre-fix code path also raises a TypeError after the payload
        # has already fired — but the side effect (PICKLE_PAYLOAD_EXECUTED)
        # is what proves the vulnerability.
        try:
            self.outdated._load_cache()
        except Exception:
            pass

        self.assertFalse(
            PICKLE_PAYLOAD_EXECUTED,
            "Pickle deserialization fired — RCE vector still present (CVE-2026-46607).",
        )


if __name__ == '__main__':
    unittest.main()
