#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances - An eye on your system
#
# Copyright (C) 2016 Nicolargo <nicolas@nicolargo.com>
#
# Glances is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Glances is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""Glances unitary tests suite."""

import sys
import time
import unittest

# Global variables
# =================

# Init Glances core
from glances.main import GlancesMain
core = GlancesMain()
if not core.is_standalone():
    print('ERROR: Glances core should be ran in standalone mode')
    sys.exit(1)

# Init Glances stats
from glances.stats import GlancesStats
stats = GlancesStats()

from glances import __version__
from glances.globals import WINDOWS
from glances.outputs.glances_bars import Bar

# Unitest class
# ==============
print('Unitary tests for Glances %s' % __version__)


class TestGlances(unittest.TestCase):
    """Test Glances class."""

    def setUp(self):
        """The function is called *every time* before test_*."""
        print('\n' + '=' * 78)

    def test_000_update(self):
        """Update stats (mandatory step for all the stats).

        The update is made twice (for rate computation).
        """
        print('INFO: [TEST_000] Test the stats update function')
        try:
            stats.update()
        except Exception as e:
            print('ERROR: Stats update failed: %s' % e)
            self.assertTrue(False)
        time.sleep(1)
        try:
            stats.update()
        except Exception as e:
            print('ERROR: Stats update failed: %s' % e)
            self.assertTrue(False)

        self.assertTrue(True)

    def test_001_plugins(self):
        """Check mandatory plugins."""
        plugins_to_check = ['system', 'cpu', 'load', 'mem', 'memswap', 'network', 'diskio', 'fs']
        print('INFO: [TEST_001] Check the mandatory plugins list: %s' % ', '.join(plugins_to_check))
        plugins_list = stats.getAllPlugins()
        for plugin in plugins_to_check:
            self.assertTrue(plugin in plugins_list)

    def test_002_cpu(self):
        """Check SYSTEM plugin."""
        stats_to_check = ['hostname', 'os_name']
        print('INFO: [TEST_002] Check SYSTEM stats: %s' % ', '.join(stats_to_check))
        stats_grab = stats.get_plugin('system').get_raw()
        for stat in stats_to_check:
            # Check that the key exist
            self.assertTrue(stat in stats_grab, msg='Cannot find key: %s' % stat)
        print('INFO: SYSTEM stats: %s' % stats_grab)

    def test_003_cpu(self):
        """Check CPU plugin."""
        stats_to_check = ['system', 'user', 'idle']
        print('INFO: [TEST_003] Check mandatory CPU stats: %s' % ', '.join(stats_to_check))
        stats_grab = stats.get_plugin('cpu').get_raw()
        for stat in stats_to_check:
            # Check that the key exist
            self.assertTrue(stat in stats_grab, msg='Cannot find key: %s' % stat)
            # Check that % is > 0 and < 100
            self.assertGreaterEqual(stats_grab[stat], 0)
            self.assertLessEqual(stats_grab[stat], 100)
        print('INFO: CPU stats: %s' % stats_grab)

    @unittest.skipIf(WINDOWS, "Load average not available on Windows")
    def test_004_load(self):
        """Check LOAD plugin."""
        stats_to_check = ['cpucore', 'min1', 'min5', 'min15']
        print('INFO: [TEST_004] Check LOAD stats: %s' % ', '.join(stats_to_check))
        stats_grab = stats.get_plugin('load').get_raw()
        for stat in stats_to_check:
            # Check that the key exist
            self.assertTrue(stat in stats_grab, msg='Cannot find key: %s' % stat)
            # Check that % is > 0
            self.assertGreaterEqual(stats_grab[stat], 0)
        print('INFO: LOAD stats: %s' % stats_grab)

    def test_005_mem(self):
        """Check MEM plugin."""
        stats_to_check = ['available', 'used', 'free', 'total']
        print('INFO: [TEST_005] Check MEM stats: %s' % ', '.join(stats_to_check))
        stats_grab = stats.get_plugin('mem').get_raw()
        for stat in stats_to_check:
            # Check that the key exist
            self.assertTrue(stat in stats_grab, msg='Cannot find key: %s' % stat)
            # Check that % is > 0
            self.assertGreaterEqual(stats_grab[stat], 0)
        print('INFO: MEM stats: %s' % stats_grab)

    def test_006_swap(self):
        """Check MEMSWAP plugin."""
        stats_to_check = ['used', 'free', 'total']
        print('INFO: [TEST_006] Check SWAP stats: %s' % ', '.join(stats_to_check))
        stats_grab = stats.get_plugin('memswap').get_raw()
        for stat in stats_to_check:
            # Check that the key exist
            self.assertTrue(stat in stats_grab, msg='Cannot find key: %s' % stat)
            # Check that % is > 0
            self.assertGreaterEqual(stats_grab[stat], 0)
        print('INFO: SWAP stats: %s' % stats_grab)

    def test_007_network(self):
        """Check NETWORK plugin."""
        print('INFO: [TEST_007] Check NETWORK stats')
        stats_grab = stats.get_plugin('network').get_raw()
        self.assertTrue(type(stats_grab) is list, msg='Network stats is not a list')
        print('INFO: NETWORK stats: %s' % stats_grab)

    def test_008_diskio(self):
        """Check DISKIO plugin."""
        print('INFO: [TEST_008] Check DISKIO stats')
        stats_grab = stats.get_plugin('diskio').get_raw()
        self.assertTrue(type(stats_grab) is list, msg='DiskIO stats is not a list')
        print('INFO: diskio stats: %s' % stats_grab)

    def test_009_fs(self):
        """Check File System plugin."""
        # stats_to_check = [ ]
        print('INFO: [TEST_009] Check FS stats')
        stats_grab = stats.get_plugin('fs').get_raw()
        self.assertTrue(type(stats_grab) is list, msg='FileSystem stats is not a list')
        print('INFO: FS stats: %s' % stats_grab)

    def test_010_processes(self):
        """Check Process plugin."""
        # stats_to_check = [ ]
        print('INFO: [TEST_010] Check PROCESS stats')
        stats_grab = stats.get_plugin('processcount').get_raw()
        # total = stats_grab['total']
        self.assertTrue(type(stats_grab) is dict, msg='Process count stats is not a dict')
        print('INFO: PROCESS count stats: %s' % stats_grab)
        stats_grab = stats.get_plugin('processlist').get_raw()
        self.assertTrue(type(stats_grab) is list, msg='Process count stats is not a list')
        print('INFO: PROCESS list stats: %s items in the list' % len(stats_grab))
        # Check if number of processes in the list equal counter
        # self.assertEqual(total, len(stats_grab))

    def test_011_folders(self):
        """Check File System plugin."""
        # stats_to_check = [ ]
        print('INFO: [TEST_011] Check FOLDER stats')
        stats_grab = stats.get_plugin('folders').get_raw()
        self.assertTrue(type(stats_grab) is list, msg='Folders stats is not a list')
        print('INFO: Folders stats: %s' % stats_grab)

    def test_012_ip(self):
        """Check IP plugin."""
        print('INFO: [TEST_012] Check IP stats')
        stats_grab = stats.get_plugin('ip').get_raw()
        self.assertTrue(type(stats_grab) is dict, msg='IP stats is not a dict')
        print('INFO: IP stats: %s' % stats_grab)

    def test_099_output_bars_must_be_between_0_and_100_percent(self):
        """Test quick look plugin.

        > bar.min_value
        0
        > bar.max_value
        100
        > bar.percent = -1
        > bar.percent
        0
        > bar.percent = 101
        > bar.percent
        100
        """
        print('INFO: [TEST_011] Test progress bar')
        bar = Bar(size=1)
        bar.percent = -1
        self.assertLessEqual(bar.percent, bar.min_value)
        bar.percent = 101
        self.assertGreaterEqual(bar.percent, bar.max_value)

if __name__ == '__main__':
    unittest.main()
