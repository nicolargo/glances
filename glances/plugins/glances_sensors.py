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
from sets import Set
# sensors library (optional; Linux-only)
try:
    import sensors
except:
    pass

from glances_plugin import GlancesPlugin, getTimeSinceLastUpdate


class Plugin(GlancesPlugin):
    """
    Glances's sensors Plugin

    stats is a list
    """

    def __init__(self):
        GlancesPlugin.__init__(self)

        # Init the sensor class
        self.glancesgrabsensors = glancesGrabSensors()


    def update(self):
        """
        Update Sensors stats
        """

        self.stats = self.glancesgrabsensors.get()


    def get_stats(self):
        # Return the stats object for the RPC API
        # !!! Sort it by label name (why do it here ? Better in client side ?)
        self.stats = sorted(self.stats, key=lambda sensors: sensors['label'])
        return GlancesPlugin.get_stats(self)


class glancesGrabSensors:
    """
    Get sensors stats using the PySensors library
    """

    def __init__(self):
        """
        Init sensors stats
        """
        try:
            sensors.init()
        except Exception:
            self.initok = False
        else:
            self.initok = True

        self.sensors_list = []


    def __update__(self):
        """
        Update the stats
        """
        # Reset the list
        self.sensors_list = []

        # grab only temperature stats
        if self.initok:
            for chip in sensors.iter_detected_chips():
                for feature in chip:
                    sensors_current = {}
                    if feature.name.startswith('temp'):
                        sensors_current['label'] = feature.label[:20]
                        sensors_current['value'] = int(feature.get_value())
                        self.sensors_list.append(sensors_current)
        

    def get(self):
        self.__update__()
        return self.sensors_list


    def quit(self):
        if self.initok:
            sensors.cleanup()