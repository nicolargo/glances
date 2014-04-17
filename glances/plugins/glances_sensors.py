# -*- coding: utf-8 -*-
#
# This file is part of Glances.
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

# Sensors library (optional; Linux-only)
try:
    import sensors
except ImportError:
    pass

# Import Glances lib
from glances.core.glances_globals import is_python3
from glances.plugins.glances_hddtemp import Plugin as HddTempPlugin
from glances.plugins.glances_plugin import GlancesPlugin


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
    Glances' sensors plugin

    The stats list includes both sensors and hard disks stats, if any
    The sensors are already grouped by chip type and then sorted by name
    The hard disks are already sorted by name
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
        self.hddtemp_plugin.update()
        self.stats = self.glancesgrabsensors.get()
        self.stats.extend(self.hddtemp_plugin.stats)

    def msg_curse(self, args=None):
        """
        Return the dict to display in the curse interface
        """
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if ((self.stats == []) or (args.disable_sensors)):
            return ret

        # Build the string message
        # Header
        msg = "{0:9}".format(_("SENSORS"))
        ret.append(self.curse_add_line(msg, "TITLE"))
        if is_python3:
            msg = "{0:>14}".format(_("°C"))
        else:
            msg = "{0:>15}".format(_("°C"))
        ret.append(self.curse_add_line(msg))

        for item in self.stats:
            # New line
            ret.append(self.curse_new_line())
            msg = "{0:9}".format(item['label'])
            ret.append(self.curse_add_line(msg))
            msg = "{0:>14}".format(item['value'])
            ret.append(self.curse_add_line(msg))

        return ret
