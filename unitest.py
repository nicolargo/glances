#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances unitary tests suite."""

import time
import unittest
import sys

# Check Python version
if sys.version_info < (3, 4):
    print('Glances requires at least Python 3.4 to run.')
    sys.exit(1)

from glances.main import GlancesMain
from glances.stats import GlancesStats
from glances import __version__
from glances.globals import WINDOWS, LINUX, subsample, string_value_to_float
from glances.outputs.glances_bars import Bar
from glances.thresholds import GlancesThresholdOk
from glances.thresholds import GlancesThresholdCareful
from glances.thresholds import GlancesThresholdWarning
from glances.thresholds import GlancesThresholdCritical
from glances.thresholds import GlancesThresholds
from glances.plugins.plugin.model import GlancesPluginModel
from glances.programs import processes_to_programs
from glances.secure import secure_popen

# Global variables
# =================

# Init Glances core
core = GlancesMain()
test_config = core.get_config()
test_args = core.get_args()

# Init Glances stats
stats = GlancesStats(config=test_config,
                     args=test_args)

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
    def test_014_gpu(self):
        """Check GPU plugin."""
        print('INFO: [TEST_014] Check GPU stats')
        stats_grab = stats.get_plugin('gpu').get_raw()
        self.assertTrue(type(stats_grab) is list, msg='GPU stats is not a list')
        print('INFO: GPU stats: %s' % stats_grab)

    def test_015_sorted_stats(self):
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

        gp = GlancesPluginModel()
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

    def test_016_subsample(self):
        """Test subsampling function."""
        print('INFO: [TEST_016] Subsampling')
        for l_test in [([1, 2, 3], 4),
                       ([1, 2, 3, 4], 4),
                       ([1, 2, 3, 4, 5, 6, 7], 4),
                       ([1, 2, 3, 4, 5, 6, 7, 8], 4),
                       (list(range(1, 800)), 4),
                       (list(range(1, 8000)), 800)]:
            l_subsample = subsample(l_test[0], l_test[1])
            self.assertLessEqual(len(l_subsample), l_test[1])

    def test_017_hddsmart(self):
        """Check hard disk SMART data plugin."""
        try:
            from glances.globals import is_admin
        except ImportError:
            print("INFO: [TEST_017] pySMART not found, not running SMART plugin test")
            return

        stat = 'DeviceName'
        print('INFO: [TEST_017] Check SMART stats: {}'.format(stat))
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

    def test_017_programs(self):
        """Check Programs function (it's not a plugin)."""
        # stats_to_check = [ ]
        print('INFO: [TEST_017] Check PROGRAM stats')
        stats_grab = processes_to_programs(stats.get_plugin('processlist').get_raw())
        self.assertTrue(type(stats_grab) is list, msg='Programs stats is not a list')
        print('INFO: PROGRAM list stats: %s items in the list' % len(stats_grab))
        # Check if number of processes in the list equal counter
        # self.assertEqual(total, len(stats_grab))

    def test_018_string_value_to_float(self):
        """Check string_value_to_float function"""
        print('INFO: [TEST_018] Check string_value_to_float function')
        self.assertEqual(string_value_to_float('32kB'), 32000.0)
        self.assertEqual(string_value_to_float('32 KB'), 32000.0)
        self.assertEqual(string_value_to_float('15.5MB'), 15500000.0)
        self.assertEqual(string_value_to_float('25.9'), 25.9)
        self.assertEqual(string_value_to_float('12'), 12)
        self.assertEqual(string_value_to_float('--'), None)

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
            stats.get_plugin(plugin).get_raw()
            views_grab = stats.get_plugin(plugin).get_views()
            self.assertTrue(type(views_grab) is dict,
                            msg='{} view is not a dict'.format(plugin))

    def test_097_attribute(self):
        """Test GlancesAttribute classes"""
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
        """Test GlancesHistory classes"""
        print('INFO: [TEST_098] Test history')
        # GlancesHistory
        from glances.history import GlancesHistory
        h = GlancesHistory()
        h.add('a', 1, history_max_size=100)
        h.add('a', 2, history_max_size=100)
        h.add('a', 3, history_max_size=100)
        h.add('b', 10, history_max_size=100)
        h.add('b', 20, history_max_size=100)
        h.add('b', 30, history_max_size=100)
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

    def test_100_secure(self):
        """Test secure functions"""
        print('INFO: [TEST_100] Secure functions')

        if WINDOWS:
            self.assertIn(secure_popen('echo TEST'), ['TEST\n',
                                                      'TEST\r\n'])
            self.assertIn(secure_popen('echo TEST1 && echo TEST2'), ['TEST1\nTEST2\n',
                                                                     'TEST1\r\nTEST2\r\n'])
        else:
            self.assertEqual(secure_popen('echo -n TEST'), 'TEST')
            self.assertEqual(secure_popen('echo -n TEST1 && echo -n TEST2'), 'TEST1TEST2')
            # Make the test failed on Github (AssertionError: '' != 'FOO\n')
            # but not on my localLinux computer...
            # self.assertEqual(secure_popen('echo FOO | grep FOO'), 'FOO\n')

    def test_200_memory_leak(self):
        """Memory leak check"""
        import tracemalloc
        print('INFO: [TEST_200] Memory leak check')
        tracemalloc.start()
        # 3 iterations just to init the stats and fill the memory
        for _ in range(3):
            stats.update()

        # Start the memory leak check
        snapshot_begin = tracemalloc.take_snapshot()
        for _ in range(3):
            stats.update()
        snapshot_end = tracemalloc.take_snapshot()
        snapshot_diff = snapshot_end.compare_to(snapshot_begin, 'filename')
        memory_leak = sum([s.size_diff for s in snapshot_diff])
        print('INFO: Memory leak: {} bytes'.format(memory_leak))

        # snapshot_begin = tracemalloc.take_snapshot()
        for _ in range(30):
            stats.update()
        snapshot_end = tracemalloc.take_snapshot()
        snapshot_diff = snapshot_end.compare_to(snapshot_begin, 'filename')
        memory_leak = sum([s.size_diff for s in snapshot_diff])
        print('INFO: Memory leak: {} bytes'.format(memory_leak))

        # snapshot_begin = tracemalloc.take_snapshot()
        for _ in range(300):
            stats.update()
        snapshot_end = tracemalloc.take_snapshot()
        snapshot_diff = snapshot_end.compare_to(snapshot_begin, 'filename')
        memory_leak = sum([s.size_diff for s in snapshot_diff])
        print('INFO: Memory leak: {} bytes'.format(memory_leak))
        snapshot_top = snapshot_end.compare_to(snapshot_begin, 'traceback')
        print("Memory consumption (top 5):")
        for stat in snapshot_top[:5]:
            print(stat)
            for line in stat.traceback.format():
                print(line)

    def test_999_the_end(self):
        """Free all the stats"""
        print('INFO: [TEST_999] Free the stats')
        stats.end()
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
