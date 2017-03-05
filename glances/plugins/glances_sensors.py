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

"""Sensors plugin."""

import psutil

from glances.logger import logger
from glances.compat import iteritems
from glances.plugins.glances_batpercent import Plugin as BatPercentPlugin
from glances.plugins.glances_hddtemp import Plugin as HddTempPlugin
from glances.plugins.glances_plugin import GlancesPlugin

SENSOR_TEMP_UNIT = 'C'
SENSOR_FAN_UNIT = 'rpm'


def to_fahrenheit(celsius):
    """Convert Celsius to Fahrenheit."""
    return celsius * 1.8 + 32


class Plugin(GlancesPlugin):

    """Glances sensors plugin.

    The stats list includes both sensors and hard disks stats, if any.
    The sensors are already grouped by chip type and then sorted by name.
    The hard disks are already sorted by name.
    """

    def __init__(self, args=None):
        """Init the plugin."""
        super(Plugin, self).__init__(args=args)

        # Init the sensor class
        self.glancesgrabsensors = GlancesGrabSensors()

        # Instance for the HDDTemp Plugin in order to display the hard disks
        # temperatures
        self.hddtemp_plugin = HddTempPlugin(args=args)

        # Instance for the BatPercent in order to display the batteries
        # capacities
        self.batpercent_plugin = BatPercentPlugin(args=args)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init the stats
        self.reset()

    def get_key(self):
        """Return the key of the list."""
        return 'label'

    def reset(self):
        """Reset/init the stats."""
        self.stats = []

    @GlancesPlugin._check_decorator
    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update sensors stats using the input method."""
        # Reset the stats
        self.reset()

        if self.input_method == 'local':
            # Update stats using the dedicated lib
            self.stats = []
            # Get the temperature
            try:
                temperature = self.__set_type(self.glancesgrabsensors.get('temperature_core'),
                                              'temperature_core')
            except Exception as e:
                logger.error("Cannot grab sensors temperatures (%s)" % e)
            else:
                # Append temperature
                self.stats.extend(temperature)
            # Get the FAN speed
            try:
                fan_speed = self.__set_type(self.glancesgrabsensors.get('fan_speed'),
                                            'fan_speed')
            except Exception as e:
                logger.error("Cannot grab FAN speed (%s)" % e)
            else:
                # Append FAN speed
                self.stats.extend(fan_speed)
            # Update HDDtemp stats
            try:
                hddtemp = self.__set_type(self.hddtemp_plugin.update(),
                                          'temperature_hdd')
            except Exception as e:
                logger.error("Cannot grab HDD temperature (%s)" % e)
            else:
                # Append HDD temperature
                self.stats.extend(hddtemp)
            # Update batteries stats
            try:
                batpercent = self.__set_type(self.batpercent_plugin.update(),
                                             'battery')
            except Exception as e:
                logger.error("Cannot grab battery percent (%s)" % e)
            else:
                # Append Batteries %
                self.stats.extend(batpercent)

        elif self.input_method == 'snmp':
            # Update stats using SNMP
            # No standard:
            # http://www.net-snmp.org/wiki/index.php/Net-SNMP_and_lm-sensors_on_Ubuntu_10.04

            pass

        return self.stats

    def __set_type(self, stats, sensor_type):
        """Set the plugin type.

        4 types of stats is possible in the sensors plugin:
        - Core temperature: 'temperature_core'
        - Fan speed: 'fan_speed'
        - HDD temperature: 'temperature_hdd'
        - Battery capacity: 'battery'
        """
        for i in stats:
            # Set the sensors type
            i.update({'type': sensor_type})
            # also add the key name
            i.update({'key': self.get_key()})

        return stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super(Plugin, self).update_views()

        # Add specifics informations
        # Alert
        for i in self.stats:
            if not i['value']:
                continue
            if i['type'] == 'battery':
                self.views[i[self.get_key()]]['value']['decoration'] = self.get_alert(100 - i['value'], header=i['type'])
            else:
                self.views[i[self.get_key()]]['value']['decoration'] = self.get_alert(i['value'], header=i['type'])

    def msg_curse(self, args=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or args.disable_sensors:
            return ret

        # Build the string message
        # Header
        msg = '{:18}'.format('SENSORS')
        ret.append(self.curse_add_line(msg, "TITLE"))

        for i in self.stats:
            # Do not display anything if no battery are detected
            if i['type'] == 'battery' and i['value'] == []:
                continue
            # New line
            ret.append(self.curse_new_line())
            # Alias for the lable name ?
            label = self.has_alias(i['label'].lower())
            if label is None:
                label = i['label']
            if i['type'] != 'fan_speed':
                msg = '{:15}'.format(label[:15])
            else:
                msg = '{:13}'.format(label[:13])
            ret.append(self.curse_add_line(msg))
            if i['value'] in (b'ERR', b'SLP', b'UNK', b'NOS'):
                msg = '{:>8}'.format(i['value'])
                ret.append(self.curse_add_line(
                    msg, self.get_views(item=i[self.get_key()],
                                        key='value',
                                        option='decoration')))
            else:
                if (args.fahrenheit and i['type'] != 'battery' and
                        i['type'] != 'fan_speed'):
                    value = to_fahrenheit(i['value'])
                    unit = 'F'
                else:
                    value = i['value']
                    unit = i['unit']
                try:
                    msg = '{:>7.0f}{}'.format(value, unit)
                    ret.append(self.curse_add_line(
                        msg, self.get_views(item=i[self.get_key()],
                                            key='value',
                                            option='decoration')))
                except (TypeError, ValueError):
                    pass

        return ret


class GlancesGrabSensors(object):

    """Get sensors stats."""

    def __init__(self):
        """Init sensors stats."""
        # Temperatures
        try:
            # psutil>=5.1.0 is required
            self.stemps = psutil.sensors_temperatures()
        except AttributeError:
            logger.warning("PsUtil 5.1.0 or higher is needed to grab temperatures sensors")
            self.initok = False
            self.stemps = {}
        else:
            self.initok = True

        # Fans
        try:
            # psutil>=5.2.0 is required
            self.sfans = psutil.sensors_fans()
        except AttributeError:
            logger.warning("PsUtil 5.2.0 or higher is needed to grab fans sensors")
            self.sfans = {}

        # Init the stats
        self.reset()

    def reset(self):
        """Reset/init the stats."""
        self.sensors_list = []

    def __update__(self):
        """Update the stats."""
        # Reset the list
        self.reset()

        if not self.initok:
            return self.sensors_list

        # Temperatures sensors
        self.sensors_list.extend(self.build_sensors_list(SENSOR_TEMP_UNIT))

        # Fans sensors
        self.sensors_list.extend(self.build_sensors_list(SENSOR_FAN_UNIT))

        return self.sensors_list

    def build_sensors_list(self, type):
        """Build the sensors list depending of the type.

        type: SENSOR_TEMP_UNIT or SENSOR_FAN_UNIT

        output: a list"""
        ret = []
        if type == SENSOR_TEMP_UNIT:
            input_list = self.stemps
        elif type == SENSOR_FAN_UNIT:
            input_list = self.sfans
        else:
            return ret
        for chipname, chip in iteritems(input_list):
            i = 1
            for feature in chip:
                sensors_current = {}
                # Sensor name
                if feature.label == '':
                    sensors_current['label'] = chipname + ' ' + str(i)
                else:
                    sensors_current['label'] = feature.label
                # Fan speed and unit
                sensors_current['value'] = int(feature.current)
                sensors_current['unit'] = type
                # Add sensor to the list
                ret.append(sensors_current)
                i += 1
        return ret

    def get(self, sensor_type='temperature_core'):
        """Get sensors list."""
        self.__update__()
        if sensor_type == 'temperature_core':
            ret = [s for s in self.sensors_list if s['unit'] == SENSOR_TEMP_UNIT]
        elif sensor_type == 'fan_speed':
            ret = [s for s in self.sensors_list if s['unit'] == SENSOR_FAN_UNIT]
        else:
            # Unknown type
            logger.debug("Unknown sensor type %s" % sensor_type)
            ret = []
        return ret

    def quit(self):
        """End of connection."""
        if self.initok:
            sensors.cleanup()
