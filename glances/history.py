# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2016 Nicolargo <nicolas@nicolargo.com>
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

"""Manage stats history"""

from glances.attribute import GlancesAttribute


class GlancesHistory(object):

    """This class manage a dict of GlancesAttribute
    - key: stats name
    - GlancesAttribute: history value"""

    def __init__(self):
        """
        items_history_list: list of stats to historized (define inside plugins)
        """
        self.stats_history = {}

    def add(self, key, value,
            description='',
            history_max_size=None,
            is_rate=False):
        """Add an new item (key, value) to the current history."""
        if key not in self.stats_history:
            self.stats_history[key] = GlancesAttribute(key,
                                                       description=description,
                                                       history_max_size=history_max_size,
                                                       is_rate=is_rate)
        self.stats_history[key].value = value

    def reset(self):
        """Reset all the stats history"""
        for a in self.stats_history:
            self.stats_history[a].history_reset()

    def get(self):
        """Get the history as a dict of list"""
        return {i: self.stats_history[i].history for i in self.stats_history}
