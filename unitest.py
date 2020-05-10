#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances - An eye on your system
#
# Copyright (C) 2019 Nicolargo <nicolas@nicolargo.com>
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

import time
import unittest

from glances.main import GlancesMain
from glances.stats import GlancesStats
from glances import __version__
from glances.globals import WINDOWS, LINUX
from glances.outputs.glances_bars import Bar
from glances.thresholds import GlancesThresholdOk
from glances.thresholds import GlancesThresholdCareful
from glances.thresholds import GlancesThresholdWarning
from glances.thresholds import GlancesThresholdCritical
from glances.thresholds import GlancesThresholds
from glances.plugins.glances_plugin import GlancesPlugin
from glances.compat import subsample, range

# Global variables
# =================


# Init Glances core
core = GlancesMain()

# Init Glances stats
stats = GlancesStats(config=core.get_config(),
                     args=core.get_args())

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
        plugins_list = stats.getPluginsList()
        for plugin in plugins_to_check:
            self.assertTrue(plugin in plugins_list)

    def test_002_system(self):
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

    @unittest.skipIf(not LINUX, "IRQs available only on Linux")
    def test_013_irq(self):
        """Check IRQ plugin."""
        print('INFO: [TEST_013] Check IRQ stats')
        stats_grab = stats.get_plugin('irq').get_raw()
        self.assertTrue(type(stats_grab) is list, msg='IRQ stats is not a list')
        print('INFO: IRQ stats: %s' % stats_grab)

    @unittest.skipIf(not LINUX, "GPU available only on Linux")
    def test_013_gpu(self):
        """Check GPU plugin."""
        print('INFO: [TEST_014] Check GPU stats')
        stats_grab = stats.get_plugin('gpu').get_raw()
        self.assertTrue(type(stats_grab) is list, msg='GPU stats is not a list')
        print('INFO: GPU stats: %s' % stats_grab)

    def test_014_sorted_stats(self):
        """Check sorted stats method."""
        print('INFO: [TEST_015] Check sorted stats method')
        aliases = {
            "key2": "alias11",
            "key5": "alias2",
        }
        unsorted_stats = [
            {"key": "key4"},
            {"key": "key2"},
            {"key": "key5"},
            {"key": "key21"},
            {"key": "key3"},
        ]

        gp = GlancesPlugin()
        gp.get_key = lambda: "key"
        gp.has_alias = aliases.get
        gp.stats = unsorted_stats

        sorted_stats = gp.sorted_stats()
        self.assertEqual(len(sorted_stats), 5)
        self.assertEqual(sorted_stats[0]["key"], "key5")
        self.assertEqual(sorted_stats[1]["key"], "key2")
        self.assertEqual(sorted_stats[2]["key"], "key3")
        self.assertEqual(sorted_stats[3]["key"], "key4")
        self.assertEqual(sorted_stats[4]["key"], "key21")

    def test_015_subsample(self):
        """Test subsampling function."""
        print('INFO: [TEST_015] Subsampling')
        for l in [([1, 2, 3], 4),
                  ([1, 2, 3, 4], 4),
                  ([1, 2, 3, 4, 5, 6, 7], 4),
                  ([1, 2, 3, 4, 5, 6, 7, 8], 4),
                  (list(range(1, 800)), 4),
                  (list(range(1, 8000)), 800)]:
            l_subsample = subsample(l[0], l[1])
            self.assertLessEqual(len(l_subsample), l[1])

    def test_016_hddsmart(self):
        """Check hard disk SMART data plugin."""
        try:
            from glances.compat import is_admin
        except ImportError:
            print("INFO: [TEST_016] pySMART not found, not running SMART plugin test")
            return

        stat = 'DeviceName'
        print('INFO: [TEST_016] Check SMART stats: {}'.format(stat))
        stats_grab = stats.get_plugin('smart').get_raw()
        if not is_admin():
            print("INFO: Not admin, SMART list should be empty")
            assert len(stats_grab) == 0
        elif stats_grab == {}:
            print("INFO: Admin but SMART list is empty")
            assert len(stats_grab) == 0
        else:
            print(stats_grab)
            self.assertTrue(stat in stats_grab[0].keys(), msg='Cannot find key: %s' % stat)

        print('INFO: SMART stats: %s' % stats_grab)

    def test_094_thresholds(self):
        """Test thresholds classes"""
        print('INFO: [TEST_094] Thresholds')
        ok = GlancesThresholdOk()
        careful = GlancesThresholdCareful()
        warning = GlancesThresholdWarning()
        critical = GlancesThresholdCritical()
        self.assertTrue(ok < careful)
        self.assertTrue(careful < warning)
        self.assertTrue(warning < critical)
        self.assertFalse(ok > careful)
        self.assertEqual(ok, ok)
        self.assertEqual(str(ok), 'OK')
        thresholds = GlancesThresholds()
        thresholds.add('cpu_percent', 'OK')
        self.assertEqual(thresholds.get(stat_name='cpu_percent').description(), 'OK')

    def test_095_methods(self):
        """Test mandatories methods"""
        print('INFO: [TEST_095] Mandatories methods')
        mandatories_methods = ['reset', 'update']
        plugins_list = stats.getPluginsList()
        for plugin in plugins_list:
            for method in mandatories_methods:
                self.assertTrue(hasattr(stats.get_plugin(plugin), method),
                                msg='{} has no method {}()'.format(plugin, method))

    def test_096_views(self):
        """Test get_views method"""
        print('INFO: [TEST_096] Test views')
        plugins_list = stats.getPluginsList()
        for plugin in plugins_list:
            stats_grab = stats.get_plugin(plugin).get_raw()
            views_grab = stats.get_plugin(plugin).get_views()
            self.assertTrue(type(views_grab) is dict,
                            msg='{} view is not a dict'.format(plugin))

    def test_097_attribute(self):
        """Test GlancesAttribute classe"""
        print('INFO: [TEST_097] Test attribute')
        # GlancesAttribute
        from glances.attribute import GlancesAttribute
        a = GlancesAttribute('a', description='ad', history_max_size=3)
        self.assertEqual(a.name, 'a')
        self.assertEqual(a.description, 'ad')
        a.description = 'adn'
        self.assertEqual(a.description, 'adn')
        a.value = 1
        a.value = 2
        self.assertEqual(len(a.history), 2)
        a.value = 3
        self.assertEqual(len(a.history), 3)
        a.value = 4
        # Check if history_max_size=3 is OK
        self.assertEqual(len(a.history), 3)
        self.assertEqual(a.history_size(), 3)
        self.assertEqual(a.history_len(), 3)
        self.assertEqual(a.history_value()[1], 4)
        self.assertEqual(a.history_mean(nb=3), 4.5)

    def test_098_history(self):
        """Test GlancesHistory classe"""
        print('INFO: [TEST_098] Test history')
        # GlancesHistory
        from glances.history import GlancesHistory
        h = GlancesHistory()
        h.add('a', 1)
        h.add('a', 2)
        h.add('a', 3)
        h.add('b', 10)
        h.add('b', 20)
        h.add('b', 30)
        self.assertEqual(len(h.get()), 2)
        self.assertEqual(len(h.get()['a']), 3)
        h.reset()
        self.assertEqual(len(h.get()), 2)
        self.assertEqual(len(h.get()['a']), 0)

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
        print('INFO: [TEST_099] Test progress bar')
        bar = Bar(size=1)
        bar.percent = -1
        self.assertLessEqual(bar.percent, bar.min_value)
        bar.percent = 101
        self.assertGreaterEqual(bar.percent, bar.max_value)

    def test_999_the_end(self):
        """Free all the stats"""
        print('INFO: [TEST_999] Free the stats')
        stats.end()
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
