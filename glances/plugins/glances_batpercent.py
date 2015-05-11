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

"""Battery plugin."""

# Import Glances libs
from glances.core.glances_logging import logger
from glances.plugins.glances_plugin import GlancesPlugin

# Batinfo library (optional; Linux-only)
try:
    import batinfo
except ImportError:
    logger.debug("Batinfo library not found. Glances cannot grab battery info.")


class Plugin(GlancesPlugin):

    """Glances battery capacity plugin.

    stats is a list
    """

    def __init__(self, args=None):
        """Init the plugin."""
        GlancesPlugin.__init__(self, args=args)

        # Init the sensor class
        self.glancesgrabbat = GlancesGrabBat()

        # We do not want to display the stat in a dedicated area
        # The HDD temp is displayed within the sensors plugin
        self.display_curse = False

        # Init stats
        self.reset()

    def reset(self):
        """Reset/init the stats."""
        self.stats = []

    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update battery capacity stats using the input method."""
        # Reset stats
        self.reset()

        if self.input_method == 'local':
            # Update stats
            self.glancesgrabbat.update()
            self.stats = self.glancesgrabbat.get()

        elif self.input_method == 'snmp':
            # Update stats using SNMP
            # Not avalaible
            pass

        return self.stats


class GlancesGrabBat(object):

    """Get batteries stats using the batinfo library."""

    def __init__(self):
        """Init batteries stats."""
        try:
            self.bat = batinfo.batteries()
            self.initok = True
            self.bat_list = []
            self.update()
        except Exception as e:
            self.initok = False
            logger.debug("Cannot init GlancesGrabBat class (%s)" % e)

    def update(self):
        """Update the stats."""
        if self.initok:
            self.bat.update()
            self.bat_list = [{
                'label': 'Battery',
                'value': self.battery_percent,
                'unit': '%'}]
        else:
            self.bat_list = []

    def get(self):
        """Get the stats."""
        return self.bat_list

    @property
    def battery_percent(self):
        """Get batteries capacity percent."""
        if not self.initok or not self.bat.stat:
            return []

        # Init the bsum (sum of percent)
        # and Loop over batteries (yes a computer could have more than 1 battery)
        bsum = 0
        for b in self.bat.stat:
            try:
                bsum += int(b.capacity)
            except ValueError:
                return []

        # Return the global percent
        return int(bsum / len(self.bat.stat))
