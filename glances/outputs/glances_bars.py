# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2015 Nicolargo <nicolas@nicolargo.com>
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

"""Manage bars for Glances output."""

# Import system lib
from math import modf

# Global vars
curses_bars = [" ", "▏", "▎", "▍", "▌", "▋", "▊", "▉", "█"]


class Bar(object):
    """Manage bar (progression or status)

    import sys
    import time
    b = Bar(10)
    for p in range(0, 100):
        b.set_percent(p)
        print("\r%s" % b),
        time.sleep(0.1)
        sys.stdout.flush()

    """

    def __init__(self, size):
        # Bar size
        self.__size = size
        # Bar current percent
        self.__percent = 0

    def get_size(self):
        return self.__size

    def set_size(self, size):
        self.__size = size
        return self.__size

    def get_percent(self):
        return self.__percent

    def set_percent(self, percent):
        assert percent >= 0
        assert percent <= 100
        self.__percent = percent
        return self.__percent

    def __str__(self):
        """Return the bars"""
        frac, whole = modf(self.get_size() * self.get_percent() / 100.0)
        ret = curses_bars[8] * int(whole)
        if frac > 0:
            ret += curses_bars[int(frac * 8)]
            whole += 1
        ret += '_' * int(self.get_size() - whole)
        return ret
