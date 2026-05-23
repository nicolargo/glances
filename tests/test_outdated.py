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

import json
import os
import pickle
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
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

    def test_002_json_round_trip(self):
        """A fresh cache written by _save_cache must be re-read identically."""
        self.outdated.data = {
            'installed_version': '4.5.5',
            'latest_version': '4.5.6',
            'refresh_date': datetime.now(),
        }
        self.outdated._save_cache()

        # File on disk must be valid JSON, not pickle.
        with open(self.cache_file, encoding='utf-8') as f:
            raw = json.load(f)
        self.assertEqual(raw['installed_version'], '4.5.5')
        self.assertEqual(raw['latest_version'], '4.5.6')
        self.assertIsInstance(raw['refresh_date'], str)

        loaded = self.outdated._load_cache()
        self.assertEqual(loaded['installed_version'], '4.5.5')
        self.assertEqual(loaded['latest_version'], '4.5.6')
        self.assertIsInstance(loaded['refresh_date'], datetime)

    def test_003_legacy_pickle_cache_is_ignored_gracefully(self):
        """A pre-fix pickle cache must be discarded silently, not crash.

        Upgrade path: an existing user has a legitimate pickle cache from
        a previous Glances release. _load_cache() must treat it as a cache
        miss and return an empty dict so the caller refreshes from PyPI.
        """
        with open(self.cache_file, 'wb') as f:
            pickle.dump(
                {
                    'installed_version': '4.5.4',
                    'latest_version': '4.5.5',
                    'refresh_date': datetime.now(),
                },
                f,
            )
        self.assertEqual(self.outdated._load_cache(), {})

    def test_004_stale_cache_returns_empty(self):
        """A cache older than 7 days is treated as missing."""
        self.outdated.data = {
            'installed_version': '4.5.5',
            'latest_version': '4.5.6',
            'refresh_date': datetime.now() - timedelta(days=8),
        }
        self.outdated._save_cache()
        self.assertEqual(self.outdated._load_cache(), {})

    def test_005_version_mismatch_invalidates_cache(self):
        """A cache written by a different installed version is discarded."""
        self.outdated.data = {
            'installed_version': '4.5.4',
            'latest_version': '4.5.6',
            'refresh_date': datetime.now(),
        }
        self.outdated._save_cache()
        # Simulate that the user has since upgraded to 4.5.5.
        self.outdated.data['installed_version'] = '4.5.5'
        self.assertEqual(self.outdated._load_cache(), {})

    def test_006_missing_cache_file_returns_empty(self):
        """No cache file on disk is a normal first-run state, not an error."""
        self.assertFalse(os.path.exists(self.cache_file))
        self.assertEqual(self.outdated._load_cache(), {})


if __name__ == '__main__':
    unittest.main()
