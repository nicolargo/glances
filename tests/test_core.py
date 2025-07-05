#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#
# Refactor by @ariel-anieli in 2024

"""Glances unitary tests suite."""

import json
import time
import unittest
from datetime import datetime

# Ugly hack waiting for Python 3.10 deprecation
try:
    from datetime import UTC
except ImportError:
    from datetime import timezone

    UTC = timezone.utc

from glances import __version__
from glances.events_list import GlancesEventsList
from glances.filter import GlancesFilter, GlancesFilterList
from glances.globals import LINUX, WINDOWS, pretty_date, string_value_to_float, subsample
from glances.main import GlancesMain
from glances.outputs.glances_bars import Bar
from glances.plugins.plugin.model import GlancesPluginModel
from glances.stats import GlancesStats
from glances.thresholds import (
    GlancesThresholdCareful,
    GlancesThresholdCritical,
    GlancesThresholdOk,
    GlancesThresholds,
    GlancesThresholdWarning,
)

# Global variables
# =================

# Init Glances core
core = GlancesMain(args_begin_at=2)
test_config = core.get_config()
test_args = core.get_args()

# Init Glances stats
stats = GlancesStats(config=test_config, args=test_args)

# Unitest class
# ==============
print(f'Unitary tests for Glances {__version__}')


class TestGlances(unittest.TestCase):
    """Test Glances class."""

    def setUp(self):
        """The function is called *every time* before test_*."""
        print('\n' + '=' * 78)

    def _common_plugin_tests(self, plugin):
        """Common method to test a Glances plugin
        This method is called multiple time by test 100 to 1xx"""

        # Reset all the stats, history and views
        plugin_instance = stats.get_plugin(plugin)
        plugin_instance.reset()  # reset stats
        plugin_instance.reset_views()  # reset views
        plugin_instance.reset_stats_history()  # reset history

        # Check before update
        self.assertEqual(plugin_instance.get_raw(), plugin_instance.stats_init_value)
        self.assertEqual(plugin_instance.is_enabled(), True)
        self.assertEqual(plugin_instance.is_disabled(), False)
        self.assertEqual(plugin_instance.get_views(), {})
        self.assertIsInstance(plugin_instance.get_raw(), (dict, list))
        if plugin_instance.history_enable() and isinstance(plugin_instance.get_raw(), dict):
            self.assertEqual(plugin_instance.get_key(), None)
            self.assertTrue(
                all(
                    f in [h['name'] for h in plugin_instance.items_history_list]
                    for f in plugin_instance.get_raw_history()
                )
            )
        elif plugin_instance.history_enable() and isinstance(plugin_instance.get_raw(), list):
            self.assertNotEqual(plugin_instance.get_key(), None)

        # Update stats (add first element)
        plugin_instance.update()
        plugin_instance.update_stats_history()
        plugin_instance.update_views()

        # Check stats
        self.assertIsInstance(plugin_instance.get_raw(), (dict, list))
        if isinstance(plugin_instance.get_raw(), dict) and plugin_instance.get_raw() != {}:
            res = False
            for f in plugin_instance.fields_description:
                if f not in plugin_instance.get_raw():
                    print(f"WARNING: {f} field not found in {plugin} plugin stats")
                else:
                    res = True
            self.assertTrue(res)
        elif isinstance(plugin_instance.get_raw(), list) and len(plugin_instance.get_raw()) > 0:
            res = False
            for i in plugin_instance.get_raw():
                for f in i:
                    if f in plugin_instance.fields_description:
                        res = True
            self.assertTrue(res)

        self.assertEqual(plugin_instance.get_raw(), plugin_instance.get_export())
        self.assertEqual(plugin_instance.get_stats(), plugin_instance.get_json())
        self.assertEqual(json.loads(plugin_instance.get_stats()), plugin_instance.get_raw())
        if len(plugin_instance.fields_description) > 0:
            # Get first item of the fields_description
            first_field = list(plugin_instance.fields_description.keys())[0]
            self.assertIsInstance(plugin_instance.get_raw_stats_item(first_field), dict)
            self.assertIsInstance(json.loads(plugin_instance.get_stats_item(first_field)), dict)
            self.assertIsInstance(plugin_instance.get_item_info(first_field, 'description'), str)
        # Filter stats
        current_stats = plugin_instance.get_raw()
        if isinstance(plugin_instance.get_raw(), dict):
            current_stats['foo'] = 'bar'
            current_stats = plugin_instance.filter_stats(current_stats)
            self.assertTrue('foo' not in current_stats)
        elif isinstance(plugin_instance.get_raw(), list) and len(plugin_instance.get_raw()) > 0:
            current_stats[0]['foo'] = 'bar'
            current_stats = plugin_instance.filter_stats(current_stats)
            self.assertTrue('foo' not in current_stats[0])

        # Update stats (add second element)
        plugin_instance.update()
        plugin_instance.update_stats_history()
        plugin_instance.update_views()

        # Check stats history
        # Not working on WINDOWS
        if plugin_instance.history_enable() and not WINDOWS:
            if isinstance(plugin_instance.get_raw(), dict):
                first_history_field = plugin_instance.get_items_history_list()[0]['name']
            elif isinstance(plugin_instance.get_raw(), list) and len(plugin_instance.get_raw()) > 0:
                first_history_field = '_'.join(
                    [
                        plugin_instance.get_raw()[0][plugin_instance.get_key()],
                        plugin_instance.get_items_history_list()[0]['name'],
                    ]
                )
            if len(plugin_instance.get_raw()) > 0:
                self.assertEqual(len(plugin_instance.get_raw_history(first_history_field)), 2)
                self.assertGreater(
                    plugin_instance.get_raw_history(first_history_field)[1][0],
                    plugin_instance.get_raw_history(first_history_field)[0][0],
                )
                # Check time
                self.assertEqual(
                    plugin_instance.get_raw_history(first_history_field)[1][0].tzinfo,
                    UTC,
                )

            # Update stats (add third element)
            plugin_instance.update()
            plugin_instance.update_stats_history()
            plugin_instance.update_views()

            if len(plugin_instance.get_raw()) > 0:
                self.assertEqual(len(plugin_instance.get_raw_history(first_history_field)), 3)
                self.assertEqual(len(plugin_instance.get_raw_history(first_history_field, 2)), 2)
                self.assertIsInstance(json.loads(plugin_instance.get_stats_history()), dict)

        # Check views
        self.assertIsInstance(plugin_instance.get_views(), dict)
        self.assertIsInstance(json.loads(plugin_instance.get_json_views()), dict)
        self.assertEqual(json.loads(plugin_instance.get_json_views()), plugin_instance.get_views())
        # Check views history
        # Not working on WINDOWS
        if plugin_instance.history_enable() and not WINDOWS:
            if isinstance(plugin_instance.get_raw(), dict):
                self.assertIsInstance(plugin_instance.get_views(first_history_field), dict)
                self.assertTrue('decoration' in plugin_instance.get_views(first_history_field))
            elif isinstance(plugin_instance.get_raw(), list) and len(plugin_instance.get_raw()) > 0:
                first_history_field = plugin_instance.get_items_history_list()[0]['name']
                first_item = plugin_instance.get_raw()[0][plugin_instance.get_key()]
                self.assertIsInstance(plugin_instance.get_views(item=first_item, key=first_history_field), dict)
                self.assertTrue('decoration' in plugin_instance.get_views(item=first_item, key=first_history_field))

    def test_000_update(self):
        """Update stats (mandatory step for all the stats).

        The update is made twice (for rate computation).
        """
        print('INFO: [TEST_000] Test the stats update function')
        try:
            stats.update()
        except Exception as e:
            print(f'ERROR: Stats update failed: {e}')
            self.assertTrue(False)
        time.sleep(1)
        try:
            stats.update()
        except Exception as e:
            print(f'ERROR: Stats update failed: {e}')
            self.assertTrue(False)

        self.assertTrue(True)

    def test_001_plugins(self):
        """Check mandatory plugins."""
        plugins_to_check = ['system', 'cpu', 'load', 'mem', 'memswap', 'network', 'diskio', 'fs']
        print('INFO: [TEST_001] Check the mandatory plugins list: {}'.format(', '.join(plugins_to_check)))
        plugins_list = stats.getPluginsList()
        for plugin in plugins_to_check:
            self.assertTrue(plugin in plugins_list)

    def test_002_system(self):
        """Check SYSTEM plugin."""
        stats_to_check = ['hostname', 'os_name']
        print('INFO: [TEST_002] Check SYSTEM stats: {}'.format(', '.join(stats_to_check)))
        stats_grab = stats.get_plugin('system').get_raw()
        for stat in stats_to_check:
            # Check that the key exist
            self.assertTrue(stat in stats_grab, msg=f'Cannot find key: {stat}')
        print(f'INFO: SYSTEM stats: {stats_grab}')

    def test_003_cpu(self):
        """Check CPU plugin."""
        stats_to_check = ['system', 'user', 'idle']
        print('INFO: [TEST_003] Check mandatory CPU stats: {}'.format(', '.join(stats_to_check)))
        stats_grab = stats.get_plugin('cpu').get_raw()
        for stat in stats_to_check:
            # Check that the key exist
            self.assertTrue(stat in stats_grab, msg=f'Cannot find key: {stat}')
            # Check that % is > 0 and < 100
            self.assertGreaterEqual(stats_grab[stat], 0)
            self.assertLessEqual(stats_grab[stat], 100)
        print(f'INFO: CPU stats: {stats_grab}')

    @unittest.skipIf(WINDOWS, "Load average not available on Windows")
    def test_004_load(self):
        """Check LOAD plugin."""
        stats_to_check = ['cpucore', 'min1', 'min5', 'min15']
        print('INFO: [TEST_004] Check LOAD stats: {}'.format(', '.join(stats_to_check)))
        stats_grab = stats.get_plugin('load').get_raw()
        for stat in stats_to_check:
            # Check that the key exist
            self.assertTrue(stat in stats_grab, msg=f'Cannot find key: {stat}')
            # Check that % is > 0
            self.assertGreaterEqual(stats_grab[stat], 0)
        print(f'INFO: LOAD stats: {stats_grab}')

    def test_005_mem(self):
        """Check MEM plugin."""
        plugin_name = 'mem'
        stats_to_check = ['available', 'used', 'free', 'total']
        print('INFO: [TEST_005] Check {} stats: {}'.format(plugin_name, ', '.join(stats_to_check)))
        stats_grab = stats.get_plugin('mem').get_raw()
        for stat in stats_to_check:
            # Check that the key exist
            self.assertTrue(stat in stats_grab, msg=f'Cannot find key: {stat}')
            # Check that % is > 0
            self.assertGreaterEqual(stats_grab[stat], 0)
        print(f'INFO: MEM stats: {stats_grab}')

    def test_006_memswap(self):
        """Check MEMSWAP plugin."""
        stats_to_check = ['used', 'free', 'total']
        print('INFO: [TEST_006] Check MEMSWAP stats: {}'.format(', '.join(stats_to_check)))
        stats_grab = stats.get_plugin('memswap').get_raw()
        for stat in stats_to_check:
            # Check that the key exist
            self.assertTrue(stat in stats_grab, msg=f'Cannot find key: {stat}')
            # Check that % is > 0
            self.assertGreaterEqual(stats_grab[stat], 0)
        print(f'INFO: MEMSWAP stats: {stats_grab}')

    def test_007_network(self):
        """Check NETWORK plugin."""
        print('INFO: [TEST_007] Check NETWORK stats')
        stats_grab = stats.get_plugin('network').get_raw()
        self.assertTrue(isinstance(stats_grab, list), msg='Network stats is not a list')
        print(f'INFO: NETWORK stats: {stats_grab}')

    def test_008_diskio(self):
        """Check DISKIO plugin."""
        print('INFO: [TEST_008] Check DISKIO stats')
        stats_grab = stats.get_plugin('diskio').get_raw()
        self.assertTrue(isinstance(stats_grab, list), msg='DiskIO stats is not a list')
        print(f'INFO: diskio stats: {stats_grab}')

    def test_009_fs(self):
        """Check File System plugin."""
        # stats_to_check = [ ]
        print('INFO: [TEST_009] Check FS stats')
        stats_grab = stats.get_plugin('fs').get_raw()
        self.assertTrue(isinstance(stats_grab, list), msg='FileSystem stats is not a list')
        print(f'INFO: FS stats: {stats_grab}')

    def test_010_processes(self):
        """Check Process plugin."""
        # stats_to_check = [ ]
        print('INFO: [TEST_010] Check PROCESS stats')
        stats_grab = stats.get_plugin('processcount').get_raw()
        # total = stats_grab['total']
        self.assertTrue(isinstance(stats_grab, dict), msg='Process count stats is not a dict')
        print(f'INFO: PROCESS count stats: {stats_grab}')
        stats_grab = stats.get_plugin('processlist').get_raw()
        self.assertTrue(isinstance(stats_grab, list), msg='Process count stats is not a list')
        print(f'INFO: PROCESS list stats: {len(stats_grab)} items in the list')
        # Check if number of processes in the list equal counter
        # self.assertEqual(total, len(stats_grab))

    def test_011_folders(self):
        """Check File System plugin."""
        # stats_to_check = [ ]
        print('INFO: [TEST_011] Check FOLDER stats')
        stats_grab = stats.get_plugin('folders').get_raw()
        self.assertTrue(isinstance(stats_grab, list), msg='Folders stats is not a list')
        print(f'INFO: Folders stats: {stats_grab}')

    def test_012_ip(self):
        """Check IP plugin."""
        print('INFO: [TEST_012] Check IP stats')
        stats_grab = stats.get_plugin('ip').get_raw()
        self.assertTrue(isinstance(stats_grab, dict), msg='IP stats is not a dict')
        print(f'INFO: IP stats: {stats_grab}')

    @unittest.skipIf(not LINUX, "IRQs available only on Linux")
    def test_013_irq(self):
        """Check IRQ plugin."""
        print('INFO: [TEST_013] Check IRQ stats')
        stats_grab = stats.get_plugin('irq').get_raw()
        self.assertTrue(isinstance(stats_grab, list), msg='IRQ stats is not a list')
        print(f'INFO: IRQ stats: {stats_grab}')

    @unittest.skipIf(not LINUX, "GPU available only on Linux")
    def test_014_gpu(self):
        """Check GPU plugin."""
        print('INFO: [TEST_014] Check GPU stats')
        stats_grab = stats.get_plugin('gpu').get_raw()
        self.assertTrue(isinstance(stats_grab, list), msg='GPU stats is not a list')
        print(f'INFO: GPU stats: {stats_grab}')

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
        for l_test in [
            ([1, 2, 3], 4),
            ([1, 2, 3, 4], 4),
            ([1, 2, 3, 4, 5, 6, 7], 4),
            ([1, 2, 3, 4, 5, 6, 7, 8], 4),
            (list(range(1, 800)), 4),
            (list(range(1, 8000)), 800),
        ]:
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
        print(f'INFO: [TEST_017] Check SMART stats: {stat}')
        stats_grab = stats.get_plugin('smart').get_raw()
        if not is_admin():
            print("INFO: Not admin, SMART list should be empty")
            assert len(stats_grab) == 0
        elif stats_grab == {}:
            print("INFO: Admin but SMART list is empty")
            assert len(stats_grab) == 0
        else:
            print(stats_grab)
            self.assertTrue(stat in stats_grab[0].keys(), msg=f'Cannot find key: {stat}')

        print(f'INFO: SMART stats: {stats_grab}')

    def test_017_programs(self):
        """Check Programs plugin."""
        # stats_to_check = [ ]
        print('INFO: [TEST_022] Check PROGRAMS stats')
        stats_grab = stats.get_plugin('programlist').get_raw()
        self.assertTrue(isinstance(stats_grab, list), msg='Programs stats is not a list')
        if stats_grab:
            self.assertTrue(isinstance(stats_grab[0], dict), msg='Programs stats is not a list of dict')
            self.assertTrue('nprocs' in stats_grab[0], msg='No nprocs')

    def test_018_string_value_to_float(self):
        """Check string_value_to_float function"""
        print('INFO: [TEST_018] Check string_value_to_float function')
        self.assertEqual(string_value_to_float('32kB'), 32000.0)
        self.assertEqual(string_value_to_float('32 KB'), 32000.0)
        self.assertEqual(string_value_to_float('15.5MB'), 15500000.0)
        self.assertEqual(string_value_to_float('25.9'), 25.9)
        self.assertEqual(string_value_to_float('12'), 12)
        self.assertEqual(string_value_to_float('--'), None)

    def test_019_events(self):
        """Test events class"""
        print('INFO: [TEST_019] Test events')
        # Init events
        events = GlancesEventsList(max_events=5, min_duration=1, min_interval=3)
        # Minimal event duration not reached
        events.add('WARNING', 'LOAD', 4)
        events.add('CRITICAL', 'LOAD', 5)
        events.add('OK', 'LOAD', 1)
        self.assertEqual(len(events.get()), 0)
        # Minimal event duration LOAD reached
        events.add('WARNING', 'LOAD', 4)
        time.sleep(1)
        events.add('CRITICAL', 'LOAD', 5)
        time.sleep(1)
        events.add('OK', 'LOAD', 1)
        self.assertEqual(len(events.get()), 1)
        self.assertEqual(events.get()[0]['type'], 'LOAD')
        self.assertEqual(events.get()[0]['state'], 'CRITICAL')
        self.assertEqual(events.get()[0]['max'], 5)
        # Minimal event duration CPU reached
        events.add('WARNING', 'CPU', 60)
        time.sleep(1)
        events.add('WARNING', 'CPU', 70)
        time.sleep(1)
        events.add('OK', 'CPU', 10)
        self.assertEqual(len(events.get()), 2)
        self.assertEqual(events.get()[0]['type'], 'CPU')
        self.assertEqual(events.get()[0]['state'], 'WARNING')
        self.assertEqual(events.get()[0]['min'], 60)
        self.assertEqual(events.get()[0]['max'], 70)
        self.assertEqual(events.get()[0]['count'], 2)
        # Minimal event duration CPU reached (again)
        # but time between two events (min_interval) is too short
        # a merge will be done
        time.sleep(0.5)
        events.add('WARNING', 'CPU', 60)
        time.sleep(1)
        events.add('WARNING', 'CPU', 80)
        time.sleep(1)
        events.add('OK', 'CPU', 10)
        self.assertEqual(len(events.get()), 2)
        self.assertEqual(events.get()[0]['type'], 'CPU')
        self.assertEqual(events.get()[0]['state'], 'WARNING')
        self.assertEqual(events.get()[0]['min'], 60)
        self.assertEqual(events.get()[0]['max'], 80)
        self.assertEqual(events.get()[0]['count'], 4)
        # Clean WARNING events
        events.clean()
        self.assertEqual(len(events.get()), 1)

    def test_020_filter(self):
        """Test filter classes"""
        print('INFO: [TEST_020] Test filter')
        gf = GlancesFilter()
        gf.filter = '.*python.*'
        self.assertEqual(gf.filter, '.*python.*')
        self.assertEqual(gf.filter_key, None)
        self.assertTrue(gf.is_filtered({'name': 'python'}))
        self.assertTrue(gf.is_filtered({'name': '/usr/bin/python -m glances'}))
        self.assertFalse(gf.is_filtered({'noname': 'python'}))
        self.assertFalse(gf.is_filtered({'name': 'snake'}))
        gf.filter = 'username:nicolargo'
        self.assertEqual(gf.filter, 'nicolargo')
        self.assertEqual(gf.filter_key, 'username')
        self.assertTrue(gf.is_filtered({'username': 'nicolargo'}))
        self.assertFalse(gf.is_filtered({'username': 'notme'}))
        self.assertFalse(gf.is_filtered({'notuser': 'nicolargo'}))
        gfl = GlancesFilterList()
        gfl.filter = '.*python.*,username:nicolargo'
        self.assertTrue(gfl.is_filtered({'name': 'python is in the place'}))
        self.assertFalse(gfl.is_filtered({'name': 'snake is in the place'}))
        self.assertTrue(gfl.is_filtered({'name': 'snake is in the place', 'username': 'nicolargo'}))
        self.assertFalse(gfl.is_filtered({'name': 'snake is in the place', 'username': 'notme'}))

    def test_021_pretty_date(self):
        """Test pretty_date"""
        print('INFO: [TEST_021] pretty_date')
        self.assertEqual(pretty_date(datetime(2024, 1, 1, 12, 0), datetime(2024, 1, 1, 12, 0)), 'just now')
        self.assertEqual(pretty_date(datetime(2024, 1, 1, 11, 59), datetime(2024, 1, 1, 12, 0)), 'a min')
        self.assertEqual(pretty_date(datetime(2024, 1, 1, 11, 55), datetime(2024, 1, 1, 12, 0)), '5 mins')
        self.assertEqual(pretty_date(datetime(2024, 1, 1, 11, 0), datetime(2024, 1, 1, 12, 0)), 'an hour')
        self.assertEqual(pretty_date(datetime(2024, 1, 1, 0, 0), datetime(2024, 1, 1, 12, 0)), '12 hours')
        self.assertEqual(pretty_date(datetime(2023, 12, 20, 0, 0), datetime(2024, 1, 1, 12, 0)), 'a week')
        self.assertEqual(pretty_date(datetime(2023, 12, 5, 0, 0), datetime(2024, 1, 1, 12, 0)), '3 weeks')
        self.assertEqual(pretty_date(datetime(2023, 12, 1, 0, 0), datetime(2024, 1, 1, 12, 0)), 'a month')
        self.assertEqual(pretty_date(datetime(2023, 6, 1, 0, 0), datetime(2024, 1, 1, 12, 0)), '7 months')
        self.assertEqual(pretty_date(datetime(2023, 1, 1, 0, 0), datetime(2024, 1, 1, 12, 0)), 'an year')
        self.assertEqual(pretty_date(datetime(2020, 1, 1, 0, 0), datetime(2024, 1, 1, 12, 0)), '4 years')

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
                self.assertTrue(hasattr(stats.get_plugin(plugin), method), msg=f'{plugin} has no method {method}()')

    def test_096_views(self):
        """Test get_views method"""
        print('INFO: [TEST_096] Test views')
        plugins_list = stats.getPluginsList()
        for plugin in plugins_list:
            stats.get_plugin(plugin).get_raw()
            views_grab = stats.get_plugin(plugin).get_views()
            self.assertTrue(isinstance(views_grab, dict), msg=f'{plugin} view is not a dict')

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

    def test_099_output_bars(self):
        """Test quick look plugin.

        > bar.min_value
        0
        > bar.max_value
        100
        > bar.percent = -1
        > bar.percent
        0
        """
        print('INFO: [TEST_099] Test progress bar')

        bar = Bar(size=1)
        # Percent value can not be lower than min_value
        bar.percent = -1
        self.assertLessEqual(bar.percent, bar.min_value)
        # but... percent value can be higher than max_value
        bar.percent = 101
        self.assertLessEqual(bar.percent, 101)

        # Test display
        bar = Bar(size=50)
        bar.percent = 0
        self.assertEqual(bar.get(), '                                              0.0%')
        bar.percent = 70
        self.assertEqual(bar.get(), '|||||||||||||||||||||||||||||||              70.0%')
        bar.percent = 100
        self.assertEqual(bar.get(), '||||||||||||||||||||||||||||||||||||||||||||  100%')
        bar.percent = 110
        self.assertEqual(bar.get(), '|||||||||||||||||||||||||||||||||||||||||||| >100%')

    # Error in Github Action. Do not remove the comment.
    # def test_100_system_plugin_method(self):
    #     """Test system plugin methods"""
    #     print('INFO: [TEST_100] Test system plugin methods')
    #     self._common_plugin_tests('system')

    def test_101_cpu_plugin_method(self):
        """Test cpu plugin methods"""
        print('INFO: [TEST_100] Test cpu plugin methods')
        self._common_plugin_tests('cpu')

    @unittest.skipIf(WINDOWS, "Load average not available on Windows")
    def test_102_load_plugin_method(self):
        """Test load plugin methods"""
        print('INFO: [TEST_102] Test load plugin methods')
        self._common_plugin_tests('load')

    def test_103_mem_plugin_method(self):
        """Test mem plugin methods"""
        print('INFO: [TEST_103] Test mem plugin methods')
        self._common_plugin_tests('mem')

    def test_104_memswap_plugin_method(self):
        """Test memswap plugin methods"""
        print('INFO: [TEST_104] Test memswap plugin methods')
        self._common_plugin_tests('memswap')

    def test_105_network_plugin_method(self):
        """Test network plugin methods"""
        print('INFO: [TEST_105] Test network plugin methods')
        self._common_plugin_tests('network')

    # Error in Github Action. Do not remove the comment.
    # def test_106_diskio_plugin_method(self):
    #     """Test diskio plugin methods"""
    #     print('INFO: [TEST_106] Test diskio plugin methods')
    #     self._common_plugin_tests('diskio')

    def test_107_fs_plugin_method(self):
        """Test fs plugin methods"""
        print('INFO: [TEST_107] Test fs plugin methods')
        self._common_plugin_tests('fs')

    def test_200_views_hidden(self):
        """Test hide feature"""
        print('INFO: [TEST_200] Test views hidden feature')
        # Test will be done with the diskio plugin, first available interface (read_bytes fields)
        plugin = 'diskio'
        field = 'read_bytes_rate_per_sec'
        plugin_instance = stats.get_plugin(plugin)
        if len(plugin_instance.get_views()) == 0 or not test_config.get_bool_value(plugin, 'hide_zero', False):
            # No diskIO interface, test can not be done
            return
        # Get first disk interface
        key = list(plugin_instance.get_views().keys())[0]
        # Test
        ######
        # Init the stats
        plugin_instance.update()
        raw_stats = plugin_instance.get_raw()
        # Reset the views
        plugin_instance.set_views({})
        # Set field to 0 (should be hidden)
        raw_stats[0][field] = 0
        plugin_instance.set_stats(raw_stats)
        self.assertEqual(plugin_instance.get_raw()[0][field], 0)
        plugin_instance.update_views()
        self.assertTrue(plugin_instance.get_views()[key][field]['hidden'])
        # Set field to 0 (should be hidden)
        raw_stats[0][field] = 0
        plugin_instance.set_stats(raw_stats)
        self.assertEqual(plugin_instance.get_raw()[0][field], 0)
        plugin_instance.update_views()
        self.assertTrue(plugin_instance.get_views()[key][field]['hidden'])
        # Set field to 1 (should not be hidden)
        raw_stats[0][field] = 1
        plugin_instance.set_stats(raw_stats)
        self.assertEqual(plugin_instance.get_raw()[0][field], 1)
        plugin_instance.update_views()
        self.assertFalse(plugin_instance.get_views()[key][field]['hidden'])
        # Set field back to 0 (should not be hidden)
        raw_stats[0][field] = 0
        plugin_instance.set_stats(raw_stats)
        self.assertEqual(plugin_instance.get_raw()[0][field], 0)
        plugin_instance.update_views()
        self.assertFalse(plugin_instance.get_views()[key][field]['hidden'])

    # def test_700_secure(self):
    #     """Test secure functions"""
    #     print('INFO: [TEST_700] Secure functions')

    #     if WINDOWS:
    #         self.assertIn(secure_popen('echo TEST'), ['TEST\n', 'TEST\r\n'])
    #         self.assertIn(secure_popen('echo TEST1 && echo TEST2'), ['TEST1\nTEST2\n', 'TEST1\r\nTEST2\r\n'])
    #     else:
    #         self.assertEqual(secure_popen('echo -n TEST'), 'TEST')
    #         self.assertEqual(secure_popen('echo -n TEST1 && echo -n TEST2'), 'TEST1TEST2')
    #         # Make the test failed on Github (AssertionError: '' != 'FOO\n')
    #         # but not on my localLinux computer...
    #         # self.assertEqual(secure_popen('echo FOO | grep FOO'), 'FOO\n')

    def test_999_the_end(self):
        """Free all the stats"""
        print('INFO: [TEST_999] Free the stats')
        stats.end()
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
