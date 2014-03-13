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
# sensors library (optional; Linux-only)
try:
    import sensors
except:
    pass

# Import Glances lib
from glances.core.glances_globals import is_python3
from glances_hddtemp import Plugin as HddTempPlugin
from glances_plugin import GlancesPlugin
# from glances.core.glances_timer import getTimeSinceLastUpdate


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
                    if feature.name.startswith(b'temp'):
                        sensors_current['label'] = feature.label[:20]
                        sensors_current['value'] = int(feature.get_value())
                        self.sensors_list.append(sensors_current)

    def get(self):
        self.__update__()
        return self.sensors_list

    def quit(self):
        if self.initok:
            sensors.cleanup()


class Plugin(GlancesPlugin):
    """
    Glances's sensors Plugin

    stats is a list
    """

    def __init__(self):
        GlancesPlugin.__init__(self)

        # Init the sensor class
        self.glancesgrabsensors = glancesGrabSensors()

        # Instance for the CorePlugin in order to display the core number
        self.hddtemp_plugin = HddTempPlugin()

        # We want to display the stat in the curse interface
        self.display_curse = True
        # Set the message position
        # It is NOT the curse position but the Glances column/line
        # Enter -1 to right align
        self.column_curse = 0
        # Enter -1 to diplay bottom
        self.line_curse = 5

    def update(self):
        """
        Update sensors stats
        """
        self.stats = self.glancesgrabsensors.get()

    def msg_curse(self, args=None):
        """
        Return the dict to display in the curse interface
        """
        # Init the return message
        ret = []

        # Build the string message
        # Header
        msg = "{0:8}".format(_("SENSORS"))
        ret.append(self.curse_add_line(msg, "TITLE"))
        if is_python3:
            msg = "{0:>15}".format(_("°C"))
        else:
            msg = "{0:>16}".format(_("°C"))
        ret.append(self.curse_add_line(msg))
        # Sensors list (sorted by name): Sensors
        sensor_list = sorted(self.stats, key=lambda sensors: sensors['label'])
        for i in sensor_list:
            # New line
            ret.append(self.curse_new_line())
            msg = "{0:<15}".format(i['label'])
            ret.append(self.curse_add_line(msg))
            msg = "{0:>8}".format(i['value'])
            ret.append(self.curse_add_line(msg))
        # Sensors list (sorted by name): HDDTemp
        self.hddtemp_plugin.update()
        sensor_list = sorted(self.hddtemp_plugin.stats, key=lambda sensors: sensors['label'])
        for i in sensor_list:
            # New line
            ret.append(self.curse_new_line())
            msg = "{0:<15}".format("Disk " + i['label'])
            ret.append(self.curse_add_line(msg))
            msg = "{0:>8}".format(i['value'])
            ret.append(self.curse_add_line(msg))

        return ret
