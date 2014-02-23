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

# Import system libs
# Check for PSUtil already done in the glances_core script
from psutil import cpu_times, cpu_times_percent

# from ..plugins.glances_plugin import GlancesPlugin
from glances_plugin import GlancesPlugin


class Plugin(GlancesPlugin):
    """
    Glances' Cpu Plugin

    stats is a dict
    """

    def __init__(self):
        GlancesPlugin.__init__(self)

        # We want to display the stat in the curse interface
        self.display_curse = True
        # Set the message position
        # It is NOT the curse position but the Glances column/line
        # Enter -1 to right align 
        self.column_curse = 0
        # Enter -1 to diplay bottom
        self.line_curse = 1


    def update(self):
        """
        Update CPU stats
        """

        # Grab CPU using the PSUtil cpu_times_percent method (PSUtil 0.7 or higher)
        try:
            cputimespercent = cpu_times_percent(interval=0, percpu=False)
        except:
            return self.update_deprecated()

        self.stats = {}
        for cpu in ['user', 'system', 'idle', 'nice', 
                    'iowait', 'irq', 'softirq', 'steal']:
            if hasattr(cputimespercent, cpu):
                self.stats[cpu] = getattr(cputimespercent, cpu)

        return self.stats


    def update_deprecated(self):
        """
        Update CPU stats
        Only used if cpu_times_percent failed
        """

        # Grab CPU using the PSUtil cpu_times method
        cputime = cpu_times(percpu=False)
        cputime_total = cputime.user + cputime.system + cputime.idle

        # Only available on some OS
        if hasattr(cputime, 'nice'):
            cputime_total += cputime.nice
        if hasattr(cputime, 'iowait'):
            cputime_total += cputime.iowait
        if hasattr(cputime, 'irq'):
            cputime_total += cputime.irq
        if hasattr(cputime, 'softirq'):
            cputime_total += cputime.softirq
        if hasattr(cputime, 'steal'):
            cputime_total += cputime.steal
        if not hasattr(self, 'cputime_old'):
            self.cputime_old = cputime
            self.cputime_total_old = cputime_total
            self.stats = {}
        else:
            self.cputime_new = cputime
            self.cputime_total_new = cputime_total
            try:
                percent = 100 / (self.cputime_total_new -
                                 self.cputime_total_old)
                self.stats = {'user': (self.cputime_new.user -
                                      self.cputime_old.user) * percent,
                               'system': (self.cputime_new.system -
                                         self.cputime_old.system) * percent,
                               'idle': (self.cputime_new.idle -
                                       self.cputime_old.idle) * percent}
                if hasattr(self.cputime_new, 'nice'):
                    self.stats['nice'] = (self.cputime_new.nice -
                                          self.cputime_old.nice) * percent
                if hasattr(self.cputime_new, 'iowait'):
                    self.stats['iowait'] = (self.cputime_new.iowait -
                                            self.cputime_old.iowait) * percent
                if hasattr(self.cputime_new, 'irq'):
                    self.stats['irq'] = (self.cputime_new.irq -
                                         self.cputime_old.irq) * percent
                if hasattr(self.cputime_new, 'softirq'):
                    self.stats['softirq'] = (self.cputime_new.softirq -
                                             self.cputime_old.softirq) * percent
                if hasattr(self.cputime_new, 'steal'):
                    self.stats['steal'] = (self.cputime_new.steal -
                                           self.cputime_old.steal) * percent
                self.cputime_old = self.cputime_new
                self.cputime_total_old = self.cputime_total_new
            except Exception, err:
                self.stats = {}

        return self.stats


    def msg_curse(self, args=None):
        """
        Return the dict to display in the curse interface
        """

        # Init the return message
        ret = []

        # Build the string message
        # Header
        msg = "{0:8}".format(_("CPU"))
        ret.append(self.curse_add_line(msg, "TITLE"))
        # Total CPU usage
        msg = "{0}".format(format((100 - self.stats['idle']) / 100, '>6.1%'))
        ret.append(self.curse_add_line(msg))
        # Steal CPU usage
        if ('steal' in self.stats):
            msg = "  {0:8}".format(_("steal:"))
            ret.append(self.curse_add_line(msg, optional=True))
            msg = "{0}".format(format(self.stats['steal'] / 100, '>6.1%'))
            ret.append(self.curse_add_line(msg, self.get_alert(self.stats['steal']), optional=True))
        # New line
        ret.append(self.curse_new_line())
        # User CPU
        if ('user' in self.stats):
            msg = "{0:8}".format(_("user:"))
            ret.append(self.curse_add_line(msg))
            msg = "{0}".format(format(self.stats['user'] / 100, '>6.1%'))
            ret.append(self.curse_add_line(msg, self.get_alert_log(self.stats['user'])))
        # IOWait CPU
        if ('iowait' in self.stats):
            msg = "  {0:8}".format(_("iowait:"))
            ret.append(self.curse_add_line(msg))
            msg = "{0}".format(format(self.stats['iowait'] / 100, '>6.1%'))
            ret.append(self.curse_add_line(msg, self.get_alert_log(self.stats['iowait']), optional=True))
        # New line
        ret.append(self.curse_new_line())
        # System CPU
        if ('system' in self.stats):
            msg = "{0:8}".format(_("system:"))
            ret.append(self.curse_add_line(msg))
            msg = "{0}".format(format(self.stats['system'] / 100, '>6.1%'))
            ret.append(self.curse_add_line(msg, self.get_alert_log(self.stats['system'])))
        # IRQ CPU
        if ('irq' in self.stats):
            msg = "  {0:7} {1}".format(
                    _("irq:"),
                    format(self.stats['irq'] / 100, '>6.1%'))
            ret.append(self.curse_add_line(msg, optional=True))
        # New line
        ret.append(self.curse_new_line())
        # Nice CPU
        if ('nice' in self.stats):
            msg = "{0:7} {1}".format(
                    _("nice:"), 
                    format(self.stats['nice'] / 100, '>6.1%'))
            ret.append(self.curse_add_line(msg, optional=True))
        # Idles CPU
        if ('idle' in self.stats):
            msg = "  {0:7} {1}".format(
                    _("idle:"),
                    format(self.stats['idle'] / 100, '>6.1%'))
            ret.append(self.curse_add_line(msg))
  
        # Return the message with decoration 
        return ret
