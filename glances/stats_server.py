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

"""The stats server manager."""

import collections

from glances.stats import GlancesStats


class GlancesStatsServer(GlancesStats):

    """This class stores, updates and gives stats for the server."""

    def __init__(self, config=None):
        # Init the stats
        super(GlancesStatsServer, self).__init__(config)

        # Init the all_stats dict used by the server
        # all_stats is a dict of dicts filled by the server
        self.all_stats = collections.defaultdict(dict)

    def update(self, input_stats=None):
        """Update the stats."""
        input_stats = input_stats or {}

        # Force update of all the stats
        super(GlancesStatsServer, self).update()

        # Build all_stats variable (concatenation of all the stats)
        self.all_stats = self._set_stats(input_stats)

    def _set_stats(self, input_stats):
        """Set the stats to the input_stats one."""
        # Build the all_stats with the get_raw() method of the plugins
        ret = collections.defaultdict(dict)
        for p in self._plugins:
            ret[p] = self._plugins[p].get_raw()
        return ret

    def getAll(self):
        """Return the stats as a list."""
        return self.all_stats

    def getAllAsDict(self):
        """Return the stats as a dict."""
        # Python > 2.6
        # return {p: self.all_stats[p] for p in self._plugins}
        ret = {}
        for p in self._plugins:
            ret[p] = self.all_stats[p]
        return ret
