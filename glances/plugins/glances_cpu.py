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

from ..plugins.glances_plugin import GlancesPlugin

class CpuPlugin(GlancesPlugin):
	"""
	Glances' Cpu Plugin

	stats is a dict
	"""

	def __init__(self):
		GlancesPlugin.__init__(self)
		self.update()

	def update(self):
		# !!! Example
		self.stats = { 'user': 15, 'iowait': 10 }

	def __str__(self):
		ret = "CPU\n"
		for k in self.stats:
			ret += "{0} {1}\n".format(k, self.stats[k])
		return ret
