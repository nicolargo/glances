#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the ProcessCount plugin."""

from unittest.mock import PropertyMock, patch

import pytest

from glances.processes import GlancesProcesses


class TestProcessesUpdateProcesscount:
    """Test GlancesProcesses.update_processcount (see issue #3637)."""

    @pytest.fixture
    def processes(self):
        """Return a standalone GlancesProcesses instance."""
        return GlancesProcesses()

    def test_pid_max_is_not_overwritten_by_the_status_count(self, processes):
        """Test that pid_max keeps the system value and is not reset to 0."""
        with patch.object(GlancesProcesses, 'pid_max', new_callable=PropertyMock) as pid_max:
            pid_max.return_value = 4194304
            processes.update_processcount([{'status': 'sleeping', 'num_threads': 1}])
        assert processes.processcount['pid_max'] == 4194304

    def test_status_count_uses_equality(self, processes):
        """Test that the status count does not rely on the string interning."""
        plist = [
            # Build a non interned 'running' string
            {'status': ''.join(['run', 'ning']), 'num_threads': 1},
            {'status': 'sleeping', 'num_threads': 2},
            {'status': 'disk-sleep', 'num_threads': 3},
        ]
        processes.update_processcount(plist)
        assert processes.processcount['running'] == 1
        assert processes.processcount['sleeping'] == 1
        assert processes.processcount['total'] == 3
        assert processes.processcount['thread'] == 6


class TestProcessesCount:
    """Test GlancesProcesses.processes_count (see issue #3221)."""

    @pytest.fixture
    def processes(self):
        """Return a standalone GlancesProcesses instance."""
        return GlancesProcesses()

    def test_processes_count_none_max_processes(self, processes):
        """processes_count must not crash when max_processes is None (client/server mode)."""
        processes.max_processes = None
        assert processes.processes_count == 0  # nosec B101

    def test_processes_count_does_not_raise_with_max_processes(self, processes):
        """processes_count returns an int (no crash) when max_processes is set."""
        processes.max_processes = 50
        assert isinstance(processes.processes_count, int)  # nosec B101
