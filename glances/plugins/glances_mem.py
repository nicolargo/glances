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
"""
Glances virtual memory plugin
"""

# Import system libs
# Check for PSUtil already done in the glances_core script
from psutil import virtual_memory

# from ..plugins.glances_plugin import GlancesPlugin
from glances.plugins.glances_plugin import GlancesPlugin


class Plugin(GlancesPlugin):
    """
    Glances's memory Plugin

    stats is a dict
    """

    def __init__(self):
        GlancesPlugin.__init__(self)

        # We want to display the stat in the curse interface
        self.display_curse = True
        # Set the message position
        # It is NOT the curse position but the Glances column/line
        # Enter -1 to right align
        self.column_curse = 2
        # Enter -1 to diplay bottom
        self.line_curse = 1

    def update(self):
        """
        Update MEM (RAM) stats
        """

        # Grab MEM using the PSUtil virtual_memory method
        vm_stats = virtual_memory()

        # Get all the memory stats (copy/paste of the PsUtil documentation)
        # total: total physical memory available.
        # available: the actual amount of available memory that can be given instantly to processes that request more memory in bytes; this is calculated by summing different memory values depending on the platform (e.g. free + buffers + cached on Linux) and it is supposed to be used to monitor actual memory usage in a cross platform fashion.
        # percent: the percentage usage calculated as (total - available) / total * 100.
        # used: memory used, calculated differently depending on the platform and designed for informational purposes only.
        # free: memory not being used at all (zeroed) that is readily available; note that this doesn’t reflect the actual memory available (use ‘available’ instead).
        # Platform-specific fields:
        # active: (UNIX): memory currently in use or very recently used, and so it is in RAM.
        # inactive: (UNIX): memory that is marked as not used.
        # buffers: (Linux, BSD): cache for things like file system metadata.
        # cached: (Linux, BSD): cache for various things.
        # wired: (BSD, OSX): memory that is marked to always stay in RAM. It is never moved to disk.
        # shared: (BSD): memory that may be simultaneously accessed by multiple processes.
        mem_stats = {}
        for mem in ['total', 'available', 'percent', 'used', 'free',
                    'active', 'inactive', 'buffers', 'cached',
                    'wired', 'shared']:
            if (hasattr(vm_stats, mem)):
                mem_stats[mem] = getattr(vm_stats, mem)

        # Use the 'free'/htop calculation
        # free=available+buffer+cached
        mem_stats['free'] = mem_stats['available']
        if (hasattr(mem_stats, 'buffer')):
            mem_stats['free'] += mem_stats['buffer']
        if (hasattr(mem_stats, 'cached')):
            mem_stats['free'] += mem_stats['cached']
        # used=total-free
        mem_stats['used'] = mem_stats['total'] - mem_stats['free']

        # Set the global variable to the new stats
        self.stats = mem_stats

        return self.stats

    def msg_curse(self, args=None):
        """
        Return the dict to display in the curse interface
        """
        # Init the return message
        ret = []

        # Only process if stats exist...
        if (self.stats == {}):
            return ret

        # Build the string message
        # Header
        msg = "{0:5} ".format(_("MEM"))
        ret.append(self.curse_add_line(msg, "TITLE"))
        # Percent memory usage
        msg = "{0}".format(format(self.stats['percent'] / 100, '>6.1%'))
        ret.append(self.curse_add_line(msg))
        # Active memory usage
        if ('active' in self.stats):
            msg = "  {0:8}".format(_("actif:"))
            ret.append(self.curse_add_line(msg, optional=True))
            msg = "{0}".format(format(self.auto_unit(self.stats['active']), '>6'))
            ret.append(self.curse_add_line(msg, optional=True))
        # New line
        ret.append(self.curse_new_line())
        # Total memory usage
        msg = "{0:8}".format(_("total:"))
        ret.append(self.curse_add_line(msg))
        msg = "{0}".format(format(self.auto_unit(self.stats['total'], '>6')))
        ret.append(self.curse_add_line(msg))
        # Inactive memory usage
        if ('inactive' in self.stats):
            msg = "  {0:8}".format(_("inactif:"))
            ret.append(self.curse_add_line(msg, optional=True))
            msg = "{0}".format(format(self.auto_unit(self.stats['inactive']), '>6'))
            ret.append(self.curse_add_line(msg, optional=True))
        # New line
        ret.append(self.curse_new_line())
        # Used memory usage
        msg = "{0:8}".format(_("used:"))
        ret.append(self.curse_add_line(msg))
        msg = "{0}".format(format(self.auto_unit(self.stats['used'], '>6')))
        ret.append(self.curse_add_line(
            msg, self.get_alert_log(self.stats['used'], max=self.stats['total'])))
        # Buffers memory usage
        if ('buffers' in self.stats):
            msg = "  {0:8}".format(_("buffers:"))
            ret.append(self.curse_add_line(msg, optional=True))
            msg = "{0}".format(format(self.auto_unit(self.stats['buffers']), '>6'))
            ret.append(self.curse_add_line(msg, optional=True))
        # New line
        ret.append(self.curse_new_line())
        # Free memory usage
        msg = "{0:8}".format(_("free:"))
        ret.append(self.curse_add_line(msg))
        msg = "{0}".format(format(self.auto_unit(self.stats['free'], '>6')))
        ret.append(self.curse_add_line(msg))
        # Cached memory usage
        if ('cached' in self.stats):
            msg = "  {0:8}".format(_("cached:"))
            ret.append(self.curse_add_line(msg, optional=True))
            msg = "{0}".format(format(self.auto_unit(self.stats['cached']), '>6'))
            ret.append(self.curse_add_line(msg, optional=True))

        return ret
