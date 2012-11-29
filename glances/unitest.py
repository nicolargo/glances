#!/usr/bin/env python
#
# Glances unitary test
#
# Syntax:
# ./unitest.py
#
# or ./unitest.py -v
#
# Copyright (C) Nicolargo 2012 <nicolas@nicolargo.com>
#
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Glances is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.";
#

import unittest
import glances
import multiprocessing

class TestGlancesStat(unittest.TestCase):

    def setUp(self):
        self.stats = glances.glancesStats()
        self.stats.update()

    def test_Glances_getCore(self):
        self.assertEqual(self.stats.getCore(), multiprocessing.cpu_count())

    def test_Glances_getCpu(self):
        self.stats.update()
        self.assertEqual(len(self.stats.getCpu()), 4)

    def test_Glances_getPerCpu(self):
        self.stats.update()
        self.assertEqual(len(self.stats.getPerCpu()), multiprocessing.cpu_count())

    def test_Glances_getMem(self):
        self.stats.update()
        self.assertTrue(len(self.stats.getMem()) > 2)

    def test_Glances_getMemSwap(self):
        self.stats.update()
        self.assertTrue(len(self.stats.getMemSwap()) > 2)

if __name__ == '__main__':
    unittest.main()
