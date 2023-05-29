#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2023 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances unitary tests suite for data model."""

import time
import unittest
import ujson

from glances.data.item import GlancesDataItem
from glances.data.plugin import GlancesDataPlugin


class TestGlancesData(unittest.TestCase):
    """Test Glances data class."""

    def setUp(self):
        """The function is called *every time* before test_*."""
        pass

    def test_000_item(self):
        """Test GlancesItem."""
        p = GlancesDataItem(name='percent',
                            description='description percent no rate',
                            unit='%')
        p.update(50.0)
        self.assertEqual(p.name, 'percent')
        self.assertEqual(p.description, 'description percent no rate')
        self.assertEqual(p.rate, False)
        self.assertEqual(p.value, 50.0)
        self.assertEqual(p.unit, '%')
        self.assertTrue(p.last_update is not None)

        r = GlancesDataItem(name='rate',
                            description='description rate',
                            rate=True,
                            unit='ps')
        r.update(1.0)
        self.assertEqual(r.name, 'rate')
        self.assertEqual(r.description, 'description rate')
        self.assertEqual(r.rate, True)
        self.assertEqual(r.value, None)
        self.assertEqual(r.unit, 'ps')
        self.assertTrue(r.last_update is not None)
        time.sleep(1)
        r.update(2.0)
        self.assertEqual(r.name, 'rate')
        self.assertEqual(r.description, 'description rate')
        self.assertEqual(r.rate, True)
        self.assertAlmostEqual(r.value, 1.0, places=1)
        self.assertEqual(r.unit, 'ps')
        self.assertTrue(r.last_update is not None)
        d = r.dict()
        self.assertTrue(isinstance(d, dict))

    def test_001_plugin(self):
        item1 = GlancesDataItem(name='percent',
                                description='description percent no rate',
                                unit='%')
        item1.update(50.0)
        item2 = GlancesDataItem(name='rate',
                                description='description rate',
                                rate=True,
                                unit='ps')
        item2.update(1.0)
        time.sleep(1)
        item2.update(2.0)

        plugin = GlancesDataPlugin()
        plugin.add_item(item1)
        plugin.add_item(item2)
        e_dict = plugin.export()
        self.assertTrue(isinstance(e_dict, dict))
        self.assertTrue('percent' in e_dict)
        self.assertTrue('rate' in e_dict)
        self.assertEqual(e_dict['percent'], 50.0)
        self.assertAlmostEqual(e_dict['rate'], 1.0, places=1)

        e_json = plugin.export(json=True)
        self.assertEqual(e_dict, ujson.loads(e_json))

        plugin.update_item('percent', 60.0)
        e_dict = plugin.export()
        self.assertEqual(plugin.get_item('percent'), 60.0)
        self.assertEqual(plugin.get_item('nonexist'), None)


if __name__ == '__main__':
    unittest.main()
