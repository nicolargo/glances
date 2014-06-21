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

"""Sensors plugin."""

# Sensors library (optional; Linux-only)
# Py3Sensors: https://bitbucket.org/gleb_zhulik/py3sensors
try:
    import sensors
except ImportError:
    pass

# Import Glances lib
from glances.core.glances_globals import is_py3
from glances.plugins.glances_batpercent import Plugin as BatPercentPlugin
from glances.plugins.glances_hddtemp import Plugin as HddTempPlugin
from glances.plugins.glances_plugin import GlancesPlugin


class Plugin(GlancesPlugin):

    """Glances' sensors plugin.

    The stats list includes both sensors and hard disks stats, if any.
    The sensors are already grouped by chip type and then sorted by name.
    The hard disks are already sorted by name.
    """

    def __init__(self, args=None):
        """Init the plugin."""
        GlancesPlugin.__init__(self, args=args)

        # Init the sensor class
        self.glancesgrabsensors = GlancesGrabSensors()

        # Instance for the HDDTemp Plugin in order to display the hard disks temperatures
        self.hddtemp_plugin = HddTempPlugin()

        # Instance for the BatPercent in order to display the batteries capacities
        self.batpercent_plugin = BatPercentPlugin()

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
        """Reset/init the stats."""
        self.stats = []

    def update(self):
        """Update sensors stats using the input method."""
        # Reset the stats
        self.reset()

        if self.get_input() == 'local':
            # Update stats using the dedicated lib
            try:
                self.stats = self.__set_type(self.glancesgrabsensors.get(), 
                                             'temperature_core')
            except:
                pass
            # Update HDDtemp stats
            try:
                hddtemp = self.__set_type(self.hddtemp_plugin.update(), 
                                          'temperature_hdd')
            except:
                pass
            else:
                # Append HDD temperature
                self.stats.extend(hddtemp)
            # Update batteries stats
            try:
                batpercent = self.__set_type(self.batpercent_plugin.update(), 
                                             'battery')
            except:
                pass
            else:
                # Append Batteries %
                self.stats.extend(batpercent)
        elif self.get_input() == 'snmp':
            # Update stats using SNMP
            # No standard: http://www.net-snmp.org/wiki/index.php/Net-SNMP_and_lm-sensors_on_Ubuntu_10.04
            pass

        return self.stats

    def __set_type(self, stats, sensor_type):
        """Set the plugin type.

        3 types of stats is possible in the sensors plugin:
        - Core temperature
        - HDD temperature
        - Battery capacity
        """
        for i in stats:
            i.update({'type': sensor_type})
        return stats

    def msg_curse(self, args=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if self.stats == [] or args.disable_sensors:
            return ret

        # Build the string message
        # Header
        msg = '{0:18}'.format(_("SENSORS"))
        ret.append(self.curse_add_line(msg, "TITLE"))
        if is_py3:
            msg = '{0:>5}'.format(_("°C"))
        else:
            msg = '{0:>6}'.format(_("°C"))
        ret.append(self.curse_add_line(msg))

        for item in self.stats:
            # New line
            ret.append(self.curse_new_line())
            msg = '{0:18}'.format(item['label'][:18])
            ret.append(self.curse_add_line(msg))
            msg = '{0:>5}'.format(item['value'])
            if item['type'] == 'battery':
                try:
                    ret.append(self.curse_add_line(msg, self.get_alert(100 - item['value'], header=item['type'])))
                except TypeError:
                    pass
            else:
                ret.append(self.curse_add_line(msg, self.get_alert(item['value'], header=item['type'])))

        return ret


class GlancesGrabSensors(object):

    """Get sensors stats using the py3sensors library."""

    def __init__(self):
        """Init sensors stats."""
        try:
            sensors.init()
        except Exception:
            self.initok = False
        else:
            self.initok = True

        # Init the stats
        self.reset()

    def reset(self):
        """Reset/init the stats."""
        self.sensors_list = []

    def __update__(self):
        """Update the stats."""
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
        """Get sensors list."""
        self.__update__()
        return self.sensors_list

    def quit(self):
        """End of connection."""
        if self.initok:
            sensors.cleanup()
