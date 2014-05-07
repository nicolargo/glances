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
# Py3Sensors: https://bitbucket.org/gleb_zhulik/py3sensors
try:
    import sensors
except ImportError:
    pass

# Import Glances lib
from glances.core.glances_globals import is_python3
from glances.plugins.glances_hddtemp import Plugin as HddTempPlugin
from glances.plugins.glances_plugin import GlancesPlugin


class Plugin(GlancesPlugin):
    """
    Glances' sensors plugin

    The stats list includes both sensors and hard disks stats, if any
    The sensors are already grouped by chip type and then sorted by name
    The hard disks are already sorted by name
    """

    def __init__(self, args=None):
        GlancesPlugin.__init__(self, args=args)

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

        # Init the stats
        self.reset()        

    def reset(self):
        """
        Reset/init the stats
        """
        self.stats = []

    def update(self, input='local'):
        """
        Update sensors stats using the input method
        Input method could be: local (mandatory) or snmp (optionnal)
        """

        # Reset the stats
        self.reset()        

        if input == 'local':
            # Update stats using the standard system lib
            self.hddtemp_plugin.update()
            self.stats = self.glancesgrabsensors.get()
            self.stats.extend(self.hddtemp_plugin.stats)
        elif input == 'snmp':
            # Update stats using SNMP
            # No standard: http://www.net-snmp.org/wiki/index.php/Net-SNMP_and_lm-sensors_on_Ubuntu_10.04
            pass

        return self.stats

    def msg_curse(self, args=None):
        """
        Return the dict to display in the curse interface
        """
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if self.stats == [] or args.disable_sensors:
            return ret

        # Build the string message
        # Header
        msg = "{0:18}".format(_("SENSORS"))
        ret.append(self.curse_add_line(msg, "TITLE"))
        if is_python3:
            msg = "{0:>5}".format(_("°C"))
        else:
            msg = "{0:>6}".format(_("°C"))
        ret.append(self.curse_add_line(msg))

        for item in self.stats:
            # New line
            ret.append(self.curse_new_line())
            msg = "{0:18}".format(item['label'][:18])
            ret.append(self.curse_add_line(msg))
            msg = "{0:>5}".format(item['value'])
            ret.append(self.curse_add_line(msg))

        return ret


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

        # Init the stats
        self.reset()

    def reset(self):
        """
        Reset/init the stats
        """
        self.sensors_list = []

    def __update__(self):
        """
        Update the stats
        """
        # Reset the list
        self.reset()

        # grab only temperature stats
        if self.initok:
            for chip in sensors.iter_detected_chips():
                for feature in chip:
                    sensors_current = {}
                    if feature.name.startswith(b'temp'):
                        sensors_current['label'] = feature.label
                        sensors_current['value'] = int(feature.get_value())
                        self.sensors_list.append(sensors_current)

        return self.sensors_list

    def get(self):
        self.__update__()
        return self.sensors_list

    def quit(self):
        if self.initok:
            sensors.cleanup()
