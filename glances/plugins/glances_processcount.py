#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances - An eye on your system
#
# Copyright (C) 2014 Nicolargo <nicolas@nicolargo.com>
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

from glances_plugin import GlancesPlugin
from _processes import processes

class Plugin(GlancesPlugin):
    """
    Glances's processes Plugin

    stats is a list
    """

    def __init__(self):
        GlancesPlugin.__init__(self)

        # Nothing else to do...
        # 'processes' is already init in the _processes.py script
        

    def update(self):
        """
        Update processes stats
        """

        # !!! Update is call twisse (one for processcount and one for processlist)
        processes.update()
        self.stats = processes.getcount()
