#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances unitary test
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

# import os
# import time
# import signal
import unittest
import multiprocessing

from glances import glances


class TestGlancesStat(unittest.TestCase):

    def setUp(self):
        self.stats = glances.GlancesStats()
        self.stats.update()

    def test_Glances_getSystem(self):
        system = self.stats.getSystem()
        #~ print("System info: %s" % system)
        self.assertTrue(type(system) == dict)
        self.assertTrue(len(system) > 1)

    def test_Glances_getCore(self):
        core = self.stats.getCore()
        #~ print("CPU Core number: %s" % core)
        self.assertTrue(type(core) == int)
        self.assertEqual(core, multiprocessing.cpu_count())

    def test_Glances_getCpu(self):
        cpu = self.stats.getCpu()
        #~ print("CPU stat %s:" % cpu)
        self.assertTrue(type(cpu) == dict)
        self.assertTrue(len(cpu) > 1)

    def test_Glances_getPerCpu(self):
        percpu = self.stats.getPerCpu()
        #~ print("PerCPU stat %s:" % percpu)
        self.assertTrue(type(percpu) == list)
        self.assertEqual(len(percpu), multiprocessing.cpu_count())

    def test_Glances_getMem(self):
        mem = self.stats.getMem()
        #~ print("Mem stat %s:" % mem)
        self.assertTrue(type(mem) == dict)
        self.assertTrue(len(mem) > 2)

    def test_Glances_getMemSwap(self):
        memswap = self.stats.getMemSwap()
        #~ print("MemSwap stat %s:" % memswap)
        self.assertTrue(type(memswap) == dict)
        self.assertTrue(len(memswap) > 2)

    def test_Glances_getNetwork(self):
        net = self.stats.getNetwork()
        #~ print("Network stat %s:" % net)
        self.assertTrue(type(net) == list)
        self.assertTrue(len(net) > 0)

    def test_Glances_getDiskIO(self):
        diskio = self.stats.getDiskIO()
        #~ print("DiskIO stat %s:" % diskio)
        self.assertTrue(type(diskio) == list)
        self.assertTrue(len(diskio) > 0)

    def test_Glances_getFs(self):
        fs = self.stats.getFs()
        #~ print("File system stat %s:" % fs)
        self.assertTrue(type(fs) == list)
        self.assertTrue(len(fs) > 0)

    def test_Glances_getProcess(self):
        pc = self.stats.getProcessCount()
        pl = self.stats.getProcessList()
        #~ print("Processes stat %s:" % pc)
        #~ print("Processes list %s:" % pl)
        self.assertTrue(type(pc) == dict)
        self.assertTrue(len(pc) > 2)
        self.assertTrue(type(pl) == list)
        self.assertTrue(len(pl) > 0)

    def test_Glances_getSensors(self):
        sensors = self.stats.getSensors()
        #~ print("Optionnal sensors stat %s:" % sensors)
        self.assertTrue(type(sensors) == list)
        #~ self.assertTrue(len(sensors) > 0)

    def test_Glances_getHDDTemp(self):
        hddtemp = self.stats.getHDDTemp()
        #~ print("Optionnal hddtemp stat %s:" % hddtemp)
        self.assertTrue(type(hddtemp) == list)
        #~ self.assertTrue(len(hddtemp) > 0)

if __name__ == '__main__':
    unittest.main()
