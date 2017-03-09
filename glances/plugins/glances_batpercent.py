# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2017 Nicolargo <nicolas@nicolargo.com>
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

import psutil

from glances.logger import logger
from glances.plugins.glances_plugin import GlancesPlugin

# Batinfo library (optional; Linux-only)
batinfo_tag = True
try:
    import batinfo
except ImportError:
    logger.debug("batpercent plugin - Batinfo library not found. Trying fallback to PsUtil.")
    batinfo_tag = False

# PsUtil library 5.2.0 or higher (optional; Linux-only)
psutil_tag = True
try:
    psutil.sensors_battery()
except AttributeError:
    logger.debug("batpercent plugin - PsUtil 5.2.0 or higher is needed to grab battery stats.")
    psutil_tag = False


class Plugin(GlancesPlugin):

    """Glances battery capacity plugin.

    stats is a list
    """

    def __init__(self, args=None):
        """Init the plugin."""
        super(Plugin, self).__init__(args=args)

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

    @GlancesPlugin._check_decorator
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
        self.bat_list = []

        if batinfo_tag:
            self.bat = batinfo.batteries()
        elif psutil_tag:
            self.bat = psutil
        else:
            self.bat = None

    def update(self):
        """Update the stats."""
        if batinfo_tag:
            # Use the batinfo lib to grab the stats
            # Compatible with multiple batteries
            self.bat.update()
            self.bat_list = [{
                'label': 'Battery',
                'value': self.battery_percent,
                'unit': '%'}]
        elif psutil_tag and hasattr(self.bat.sensors_battery(), 'percent'):
            # Use the PSUtil 5.2.0 or higher lib to grab the stats
            # Give directly the battery percent
            self.bat_list = [{
                'label': 'Battery',
                'value': int(self.bat.sensors_battery().percent),
                'unit': '%'}]
        else:
            # No stats...
            self.bat_list = []

    def get(self):
        """Get the stats."""
        return self.bat_list

    @property
    def battery_percent(self):
        """Get batteries capacity percent."""
        if not batinfo_tag or not self.bat.stat:
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
