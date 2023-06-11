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

    # def test_001_plugin_without_key(self):
    #     item1 = GlancesDataItem(name='percent',
    #                             description='description percent no rate',
    #                             unit='%')
    #     item1.update(50.0)
    #     item2 = GlancesDataItem(name='rate',
    #                             description='description rate',
    #                             rate=True,
    #                             unit='ps')
    #     item2.update(1.0)
    #     time.sleep(1)
    #     item2.update(2.0)

    #     plugin = GlancesDataPlugin()
    #     plugin.add_item(item1)
    #     plugin.add_item(item2)
    #     e_dict = plugin.export()
    #     self.assertTrue(isinstance(e_dict, dict))
    #     self.assertTrue('percent' in e_dict)
    #     self.assertTrue('rate' in e_dict)
    #     self.assertEqual(e_dict['percent'], 50.0)
    #     self.assertAlmostEqual(e_dict['rate'], 1.0, places=1)

    #     e_json = plugin.export(json=True)
    #     self.assertEqual(e_dict, ujson.loads(e_json))

    #     plugin.update_item('percent', 60.0)
    #     e_dict = plugin.export()
    #     self.assertEqual(plugin.get_item('percent'), 60.0)
    #     self.assertEqual(plugin.get_item('nonexist'), None)

    def test_001_plugin_without_key(self):
        from glances.plugins.mem.model import fields_description
        plugin_mem = GlancesDataPlugin(fields_description=fields_description)
        self.assertTrue(plugin_mem.has_no_data())
        self.assertEqual(plugin_mem.key(), None)
        items = {"total":7836184576,"available":1398910976,"percent":82.1,"used":6437273600,"free":1398910976,"active":3354587136,"inactive":3322765312,"buffers":107741184,"cached":2038280192,"shared":594182144}
        plugin_mem.update_data(items)
        self.assertEqual(plugin_mem.export()['percent'], 82.1)
        time.sleep(1)
        items = {"total":7836184576,"available":1449926656,"percent":81.5,"used":6386257920,"free":1449926656,"active":3372138496,"inactive":3200061440,"buffers":104906752,"cached":2044624896,"shared":607055872}
        plugin_mem.update_data(items)
        self.assertEqual(plugin_mem.export()['percent'], 81.5)

    def test_002_plugin_with_key(self):
        from glances.plugins.fs.model import fields_description
        plugin_fs = GlancesDataPlugin(fields_description=fields_description)
        self.assertTrue(plugin_fs.has_no_data())
        self.assertEqual(plugin_fs.key(), 'mnt_point')
        items1 = {"device_name":"/dev/mapper/ubuntu--gnome--vg-root","fs_type":"ext4","mnt_point":"/","size":243334156288,"used":201981718528,"free":28964982784,"percent":87.5,"key":"mnt_point"}
        plugin_fs.update_data(items1)
        # print(plugin_fs.export())
        self.assertEqual(len(plugin_fs.export()), 1)
        self.assertEqual(plugin_fs.export()[0]['percent'], 87.5)
        items2 = {"device_name":"zsfpool","fs_type":"zfs","mnt_point":"/zsfpool","size":41943040,"used":131072,"free":41811968,"percent":0.3,"key":"mnt_point"}
        plugin_fs.update_data(items2)
        # print(plugin_fs.export())
        self.assertEqual(len(plugin_fs.export()), 2)
        self.assertEqual(plugin_fs.export()[0]['percent'], 87.5)
        self.assertEqual(plugin_fs.export()[1]['percent'], 0.3)


if __name__ == '__main__':
    unittest.main()
