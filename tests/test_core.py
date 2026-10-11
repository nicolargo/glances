#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#
# Refactor by @ariel-anieli in 2024

"""Glances unit tests for the shared helpers (globals, filter, bars)."""

import unittest
from datetime import datetime

# Ugly hack waiting for Python 3.10 deprecation
try:
    from datetime import UTC
except ImportError:
    from datetime import timezone

    UTC = timezone.utc

from glances.filter import GlancesFilter, GlancesFilterList
from glances.globals import auto_unit, pretty_date, split_esc, string_value_to_float, subsample
from glances.outputs.glances_bars import Bar


class TestGlances(unittest.TestCase):
    """Test the shared helpers."""

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

    def test_018_string_value_to_float(self):
        """Check string_value_to_float function"""
        print('INFO: [TEST_018] Check string_value_to_float function')
        self.assertEqual(string_value_to_float('32kB'), 32000.0)
        self.assertEqual(string_value_to_float('32 KB'), 32000.0)
        self.assertEqual(string_value_to_float('15.5MB'), 15500000.0)
        self.assertEqual(string_value_to_float('25.9'), 25.9)
        self.assertEqual(string_value_to_float('12'), 12)
        self.assertEqual(string_value_to_float('--'), None)

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
        # The regex may itself contain a colon: a Windows path is the common case,
        # and every absolute one has a drive colon. Splitting on every colon kept only
        # the fragment before the second one -- and silently, because that fragment
        # usually still compiles, so the filter matched nothing and reported nothing.
        gf.filter = 'cmdline:C:/Program Files/.*'
        self.assertEqual(gf.filter, 'C:/Program Files/.*')
        self.assertEqual(gf.filter_key, 'cmdline')
        self.assertTrue(gf.is_filtered({'cmdline': 'C:/Program Files/app.exe'}))
        self.assertFalse(gf.is_filtered({'cmdline': 'D:/Other/app.exe'}))
        # Same shape without a path, so the case is not Windows-only.
        gf.filter = 'name:foo:bar'
        self.assertEqual(gf.filter, 'foo:bar')
        self.assertEqual(gf.filter_key, 'name')
        self.assertTrue(gf.is_filtered({'name': 'foo:bar'}))
        # A backslash is a regex escape, not a separator escape: `split_esc` would
        # strip it and mangle the pattern, which is why plain maxsplit is the right
        # tool here.
        gf.filter = r'cmdline:C:\\Windows\\.*'
        self.assertEqual(gf.filter, r'C:\\Windows\\.*')
        self.assertTrue(gf.is_filtered({'cmdline': r'C:\Windows\system32'}))
        gfl = GlancesFilterList()
        gfl.filter = '.*python.*,username:nicolargo'
        self.assertTrue(gfl.is_filtered({'name': 'python is in the place'}))
        self.assertFalse(gfl.is_filtered({'name': 'snake is in the place'}))
        self.assertTrue(gfl.is_filtered({'name': 'snake is in the place', 'username': 'nicolargo'}))
        self.assertFalse(gfl.is_filtered({'name': 'snake is in the place', 'username': 'notme'}))
        # Setting the filter replaces the list rather than adding to it. glances.conf
        # is read when the processlist plugin loads and --process-focus is applied
        # just after, so a setter that appended left both lists live and OR-ed: the
        # command line could widen the focus set in glances.conf but never narrow it.
        gfl = GlancesFilterList()
        gfl.filter = '.*firefox.*'
        gfl.filter = '.*python.*'
        self.assertEqual([f.filter for f in gfl.filter], ['.*python.*'])
        self.assertTrue(gfl.is_filtered({'name': 'python is in the place'}))
        self.assertFalse(gfl.is_filtered({'name': 'firefox is in the place'}))

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

    def test_024_split_esc(self):
        """Test split_esc function"""
        print('INFO: [TEST_024] split_esc')
        self.assertEqual(split_esc(r''), [])
        self.assertEqual(split_esc('\\'), [])
        self.assertEqual(split_esc(r'abcd'), [r'abcd'])
        self.assertEqual(split_esc(r'abcd efg'), [r'abcd', r'efg'])
        self.assertEqual(split_esc('abcd      \n\t\f efg'), [r'abcd', r'efg'])
        self.assertEqual(split_esc(r'abcd\ efg'), [r'abcd efg'])
        self.assertEqual(split_esc(r'', ':'), [''])
        self.assertEqual(split_esc(r'abcd', ':'), [r'abcd'])
        self.assertEqual(split_esc(r'abcd:efg', ':'), [r'abcd', r'efg'])
        self.assertEqual(split_esc(r'abcd\:efg', ':'), [r'abcd:efg'])
        self.assertEqual(split_esc(r'abcd:efg:hijk', ':'), [r'abcd', r'efg', r'hijk'])
        self.assertEqual(split_esc(r'abcd\:efg:hijk', ':'), [r'abcd:efg', r'hijk'])
        self.assertEqual(split_esc(r'abcd\:efg:hijk\:lmnop:qrs', ':', maxsplit=0), [r'abcd\:efg:hijk\:lmnop:qrs'])
        self.assertEqual(split_esc(r'abcd\:efg:hijk\:lmnop:qrs', ':', maxsplit=1), [r'abcd:efg', r'hijk\:lmnop:qrs'])
        self.assertEqual(
            split_esc(r'abcd\:efg:hijk\:lmnop:qrs', ':', maxsplit=10), [r'abcd:efg', r'hijk:lmnop', r'qrs']
        )
        self.assertEqual(split_esc(r'ahellobhelloc', r'hello'), [r'a', r'b', r'c'])
        self.assertEqual(split_esc(r'a\hellobhelloc', r'hello'), [r'ahellob', r'c'])
        self.assertEqual(split_esc(r'ahe\llobhelloc', r'hello'), [r'ahellob', r'c'])

    def test_093_auto_unit(self):
        """Test auto_unit classe"""
        print('INFO: [TEST_093] Auto unit')
        self.assertEqual(auto_unit(1.1234), '1.12')
        self.assertEqual(auto_unit(1024), '1024')
        self.assertEqual(auto_unit(1025), '1K')
        self.assertEqual(auto_unit(613421788), '585M')
        self.assertEqual(auto_unit(613421788, low_precision=True), '585M')
        self.assertEqual(auto_unit(5307033647), '4.94G')
        self.assertEqual(auto_unit(5307033647, low_precision=True), '4.9G')
        self.assertEqual(auto_unit(44968414685), '41.9G')
        self.assertEqual(auto_unit(44968414685, low_precision=True), '41.9G')
        self.assertEqual(auto_unit(838471403472), '781G')
        self.assertEqual(auto_unit(838471403472, low_precision=True), '781G')
        self.assertEqual(auto_unit(9683209690677), '8.81T')
        self.assertEqual(auto_unit(9683209690677, low_precision=True), '8.8T')
        self.assertEqual(auto_unit(1073741824), '1024M')
        self.assertEqual(auto_unit(1073741824, low_precision=True), '1024M')
        self.assertEqual(auto_unit(1181116006), '1.10G')
        self.assertEqual(auto_unit(1181116006, low_precision=True), '1.1G')
        # Edge cases:
        m = 2**20
        g = 2**30
        self.assertEqual(auto_unit(9.9 * m), '9.90M')
        self.assertEqual(auto_unit(9.99 * m), '9.99M')
        self.assertEqual(auto_unit(9.991 * m), '9.99M')
        self.assertEqual(auto_unit(9.994 * m), '9.99M')
        self.assertEqual(auto_unit(9.995 * m), '9.99M')
        self.assertEqual(auto_unit(10 * m), '10.0M')
        self.assertEqual(auto_unit(99 * m), '99.0M')
        self.assertEqual(auto_unit(99.9 * m), '99.9M')
        self.assertEqual(auto_unit(99.91 * m), '99.9M')
        self.assertEqual(auto_unit(99.94 * m), '99.9M')
        self.assertEqual(auto_unit(100 * m), '100M')
        # Special cases that used to overflow and misalign columns
        self.assertEqual(auto_unit(9.996 * m), '10.0M')  # was 10.00M
        self.assertEqual(auto_unit(9.999 * m), '10.0M')  # was 10.00M
        self.assertEqual(auto_unit(99.95 * m), '100M')  # was 100.0M
        self.assertEqual(auto_unit(99.96 * m), '100M')  # was 100.0M
        self.assertEqual(auto_unit(99.99 * m), '100M')  # was 100.0M
        self.assertEqual(auto_unit(10 * m - 1), '10.0M')  # was 10.00M
        self.assertEqual(auto_unit(100 * m - 1), '100M')  # was 100.0M
        self.assertEqual(auto_unit(10 * g - 1), '10.0G')  # was 10.00G
        self.assertEqual(auto_unit(100 * g - 1), '100G')  # was 100.0G

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
