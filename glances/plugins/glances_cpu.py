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
from psutil import cpu_times

# from ..plugins.glances_plugin import GlancesPlugin
from glances_plugin import GlancesPlugin

class Plugin(GlancesPlugin):
	"""
	Glances' Cpu Plugin

	stats is a dict
	"""

	def __init__(self):
		GlancesPlugin.__init__(self)


	def update(self):
		"""
		Update CPU stats
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
