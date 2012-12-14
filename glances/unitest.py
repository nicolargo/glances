#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances unitary test
#
# Syntax:
# ./unitest.py
# or
# ./unitest.py -v
#
# Copyright (C) 2012 Nicolargo <nicolas@nicolargo.com>
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

import unittest
import glances
import multiprocessing
# import time


class TestGlancesStat(unittest.TestCase):

    def setUp(self):
        self.stats = glances.GlancesStats()
        self.stats.update()

    def test_Glances_getSystem(self):
        self.stats.update()
        system = self.stats.getSystem()
        print "System info: %s" % system
        self.assertTrue(len(system) > 1)

    def test_Glances_getCore(self):
        self.stats.update()
        core = self.stats.getCore()
        print "CPU Core number: %s" % core
        self.assertEqual(core, multiprocessing.cpu_count())

    def test_Glances_getCpu(self):
        self.stats.update()
        cpu = self.stats.getCpu()
        print "CPU stat %s:" % cpu
        self.assertTrue(len(cpu) > 1)

    def test_Glances_getPerCpu(self):
        self.stats.update()
        percpu = self.stats.getPerCpu()
        print "PerCPU stat %s:" % percpu
        self.assertEqual(len(percpu), multiprocessing.cpu_count())

    def test_Glances_getMem(self):
        self.stats.update()
        mem = self.stats.getMem()
        print "Mem stat %s:" % mem
        self.assertTrue(len(mem) > 2)

    def test_Glances_getMemSwap(self):
        self.stats.update()
        memswap = self.stats.getMemSwap()
        print "MemSwap stat %s:" % memswap
        self.assertTrue(len(self.stats.getMemSwap()) > 2)


if __name__ == '__main__':
    unittest.main()
