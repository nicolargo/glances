# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Sensors plugin."""

import psutil
import warnings
import threading

from glances.logger import logger
from glances.globals import iteritems, to_fahrenheit
from glances.timer import Counter
from glances.plugins.sensors.sensor.glances_batpercent import PluginModel as BatPercentPluginModel
from glances.plugins.sensors.sensor.glances_hddtemp import PluginModel as HddTempPluginModel
from glances.outputs.glances_unicode import unicode_message
from glances.plugins.plugin.model import GlancesPluginModel

SENSOR_TEMP_TYPE = 'temperature_core'
SENSOR_TEMP_UNIT = 'C'

SENSOR_FAN_TYPE = 'fan_speed'
SENSOR_FAN_UNIT = 'R'

SENSOR_HDDTEMP_TYPE = 'temperature_hdd'
SENSOR_HDDTEMP_UNIT = 'C'

SENSORS_BATTERY_TYPE = 'battery'
SENSORS_BATTERY_UNIT = '%'

# Define the default refresh multiplicator
# Default value is 3 * Glances refresh time
# Can be overwritten by the refresh option in the sensors section of the glances.conf file
DEFAULT_REFRESH = 3

# Fields description
# description: human readable description
# short_name: shortname to use un UI
# unit: unit type
# rate: is it a rate ? If yes, // by time_since_update when displayed,
# min_symbol: Auto unit should be used if value > than 1 'X' (K, M, G)...
fields_description = {
    'label': {
        'description': 'Sensor label',
    },
    'unit': {
        'description': 'Sensor unit',
    },
    'value': {
        'description': 'Sensor value',
        'unit': 'number',
    },
    'warning': {
        'description': 'Warning threshold',
        'unit': 'number',
    },
    'critical': {
        'description': 'Critical threshold',
        'unit': 'number',
    },
    'type': {
        'description': 'Sensor type (one of battery, temperature_core, fan_speed)',
    },
}


class PluginModel(GlancesPluginModel):
    """Glances sensors plugin.

    The stats list includes both sensors and hard disks stats, if any.
    The sensors are already grouped by chip type and then sorted by label.
    The hard disks are already sorted by label.
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(PluginModel, self).__init__(
            args=args, config=config, stats_init_value=[], fields_description=fields_description
        )

        start_duration = Counter()

        # Init the sensor class
        start_duration.reset()
        self.glances_grab_sensors = GlancesGrabSensors()
        logger.debug("Generic sensor plugin init duration: {} seconds".format(start_duration.get()))

        # Instance for the HDDTemp Plugin in order to display the hard disks
        # temperatures
        start_duration.reset()
        self.hddtemp_plugin = HddTempPluginModel(args=args, config=config)
        logger.debug("HDDTemp sensor plugin init duration: {} seconds".format(start_duration.get()))

        # Instance for the BatPercent in order to display the batteries
        # capacities
        start_duration.reset()
        self.batpercent_plugin = BatPercentPluginModel(args=args, config=config)
        logger.debug("Battery sensor plugin init duration: {} seconds".format(start_duration.get()))

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Not necessary to refresh every refresh time
        if args and self.get_refresh() == args.time:
            self.set_refresh(self.get_refresh() * DEFAULT_REFRESH)

    def get_key(self):
        """Return the key of the list."""
        return 'label'

    def __get_temperature(self, stats, index):
        try:
            temperature = self.__set_type(self.glances_grab_sensors.get(SENSOR_TEMP_TYPE), SENSOR_TEMP_TYPE)
        except Exception as e:
            logger.error("Cannot grab sensors temperatures (%s)" % e)
        else:
            stats[index] = self.__transform_sensors(temperature)

    def __get_fan_speed(self, stats, index):
        try:
            fan_speed = self.__set_type(self.glances_grab_sensors.get(SENSOR_FAN_TYPE), SENSOR_FAN_TYPE)
        except Exception as e:
            logger.error("Cannot grab FAN speed (%s)" % e)
        else:
            stats[index] = self.__transform_sensors(fan_speed)

    def __get_hddtemp(self, stats, index):
        try:
            hddtemp = self.__set_type(self.hddtemp_plugin.update(), SENSOR_HDDTEMP_TYPE)
        except Exception as e:
            logger.error("Cannot grab HDD temperature (%s)" % e)
        else:
            stats[index] = self.__transform_sensors(hddtemp)

    def __get_bat_percent(self, stats, index):
        try:
            bat_percent = self.__set_type(self.batpercent_plugin.update(), SENSORS_BATTERY_TYPE)
        except Exception as e:
            logger.error("Cannot grab battery percent (%s)" % e)
        else:
            stats[index] = self.__transform_sensors(bat_percent)

    def __transform_sensors(self, threads_stats):
        """Hide, alias and sort the result"""
        stats_transformed = []
        for stat in threads_stats:
            # Hide sensors configured in the hide ou show configuration key
            if not self.is_display(stat["label"].lower()):
                continue
            # Set alias for sensors
            stat["label"] = self.__get_alias(stat)
            # Add the stat to the stats_transformed list
            stats_transformed.append(stat)
        # Remove duplicates thanks to https://stackoverflow.com/a/9427216/1919431
        stats_transformed = [dict(t) for t in {tuple(d.items()) for d in stats_transformed}]
        # Sort by label
        stats_transformed = sorted(stats_transformed, key=lambda d: d['label'])
        return stats_transformed

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update sensors stats using the input method."""
        # Init new stats
        stats = self.get_init_value()

        if self.input_method == 'local':
            threads_stats = [None] * 4
            threads = [
                threading.Thread(name=SENSOR_TEMP_TYPE, target=self.__get_temperature, args=(threads_stats, 0)),
                threading.Thread(name=SENSOR_FAN_TYPE, target=self.__get_fan_speed, args=(threads_stats, 1)),
                threading.Thread(name=SENSOR_HDDTEMP_TYPE, target=self.__get_hddtemp, args=(threads_stats, 2)),
                threading.Thread(name=SENSORS_BATTERY_TYPE, target=self.__get_bat_percent, args=(threads_stats, 3)),
            ]
            # Start threads in //
            for t in threads:
                t.start()
            # Wait threads are finished
            for t in threads:
                t.join()
            # Merge the results
            for s in threads_stats:
                stats.extend(s)
        elif self.input_method == 'snmp':
            # Update stats using SNMP
            # No standard:
            # http://www.net-snmp.org/wiki/index.php/Net-SNMP_and_lm-sensors_on_Ubuntu_10.04
            pass

        # Update the stats
        self.stats = stats

        return self.stats

    def __get_alias(self, stats):
        """Return the alias of the sensor."""
        # Get the alias for each stat
        if self.has_alias(stats["label"].lower()):
            return self.has_alias(stats["label"].lower())
        elif self.has_alias("{}_{}".format(stats["label"], stats["type"]).lower()):
            return self.has_alias("{}_{}".format(stats["label"], stats["type"]).lower())
        else:
            return stats["label"]

    def __set_type(self, stats, sensor_type):
        """Set the plugin type.

        4 types of stats is possible in the sensors plugin:
        - Core temperature: SENSOR_TEMP_TYPE
        - Fan speed: SENSOR_FAN_TYPE
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
        super(PluginModel, self).update_views()

        # Add specifics information
        # Alert
        for i in self.stats:
            if not i['value']:
                continue
            # Alert processing
            if i['type'] == SENSOR_TEMP_TYPE:
                if self.is_limit('critical', stat_name=SENSOR_TEMP_TYPE + '_' + i['label']):
                    # By default use the thresholds configured in the glances.conf file (see #2058)
                    alert = self.get_alert(current=i['value'], header=SENSOR_TEMP_TYPE + '_' + i['label'])
                else:
                    # Else use the system thresholds
                    if i['critical'] is None:
                        alert = 'DEFAULT'
                    elif i['value'] >= i['critical']:
                        alert = 'CRITICAL'
                    elif i['warning'] is None:
                        alert = 'DEFAULT'
                    elif i['value'] >= i['warning']:
                        alert = 'WARNING'
                    else:
                        alert = 'OK'
            elif i['type'] == SENSORS_BATTERY_TYPE:
                # Battery is in %
                alert = self.get_alert(current=100 - i['value'], header=i['type'])
            else:
                alert = self.get_alert(current=i['value'], header=i['type'])
            # Set the alert in the view
            self.views[i[self.get_key()]]['value']['decoration'] = alert

    def battery_trend(self, stats):
        """Return the trend character for the battery"""
        if 'status' not in stats:
            return ''
        if stats['status'].startswith('Charg'):
            return unicode_message('ARROW_UP')
        elif stats['status'].startswith('Discharg'):
            return unicode_message('ARROW_DOWN')
        elif stats['status'].startswith('Full'):
            return unicode_message('CHECK')
        return ''

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or self.is_disabled():
            return ret

        # Max size for the interface name
        if max_width:
            name_max_width = max_width - 12
        else:
            # No max_width defined, return an emptu curse message
            logger.debug("No max_width defined for the {} plugin, it will not be displayed.".format(self.plugin_name))
            return ret

        # Header
        msg = '{:{width}}'.format('SENSORS', width=name_max_width)
        ret.append(self.curse_add_line(msg, "TITLE"))

        # Stats
        for i in self.stats:
            # Do not display anything if no battery are detected
            if i['type'] == SENSORS_BATTERY_TYPE and i['value'] == []:
                continue
            # New line
            ret.append(self.curse_new_line())
            msg = '{:{width}}'.format(i["label"][:name_max_width], width=name_max_width)
            ret.append(self.curse_add_line(msg))
            if i['value'] in (b'ERR', b'SLP', b'UNK', b'NOS'):
                msg = '{:>14}'.format(i['value'])
                ret.append(
                    self.curse_add_line(msg, self.get_views(item=i[self.get_key()], key='value', option='decoration'))
                )
            else:
                if args.fahrenheit and i['type'] != SENSORS_BATTERY_TYPE and i['type'] != SENSOR_FAN_TYPE:
                    trend = ''
                    value = to_fahrenheit(i['value'])
                    unit = 'F'
                else:
                    trend = self.battery_trend(i)
                    value = i['value']
                    unit = i['unit']
                try:
                    msg = '{:.0f}{}{}'.format(value, unit, trend)
                    msg = '{:>14}'.format(msg)
                    ret.append(
                        self.curse_add_line(
                            msg, self.get_views(item=i[self.get_key()], key='value', option='decoration')
                        )
                    )
                except (TypeError, ValueError):
                    pass

        return ret


class GlancesGrabSensors(object):
    """Get sensors stats."""

    def __init__(self):
        """Init sensors stats."""
        # Temperatures
        self.init_temp = False
        self.sensor_temps = {}
        try:
            # psutil>=5.1.0, Linux-only
            self.sensor_temps = psutil.sensors_temperatures()
        except AttributeError:
            logger.debug("Cannot grab temperatures. Platform not supported.")
        else:
            self.init_temp = True
            # Solve an issue #1203 concerning a RunTimeError warning message displayed
            # in the curses interface.
            warnings.filterwarnings("ignore")

        # Fans
        self.init_fan = False
        self.sensor_fans = {}
        try:
            # psutil>=5.2.0, Linux-only
            self.sensor_fans = psutil.sensors_fans()
        except AttributeError:
            logger.debug("Cannot grab fans speed. Platform not supported.")
        else:
            self.init_fan = True

        # Init the stats
        self.reset()

    def reset(self):
        """Reset/init the stats."""
        self.sensors_list = []

    def __update__(self):
        """Update the stats."""
        # Reset the list
        self.reset()

        if not self.init_temp:
            return self.sensors_list

        # Temperatures sensors
        self.sensors_list.extend(self.build_sensors_list(SENSOR_TEMP_UNIT))

        # Fans sensors
        self.sensors_list.extend(self.build_sensors_list(SENSOR_FAN_UNIT))

        return self.sensors_list

    def build_sensors_list(self, type):
        """Build the sensors list depending of the type.

        type: SENSOR_TEMP_UNIT or SENSOR_FAN_UNIT

        output: a list
        """
        ret = []
        if type == SENSOR_TEMP_UNIT and self.init_temp:
            input_list = self.sensor_temps
            self.sensor_temps = psutil.sensors_temperatures()
        elif type == SENSOR_FAN_UNIT and self.init_fan:
            input_list = self.sensor_fans
            self.sensor_fans = psutil.sensors_fans()
        else:
            return ret
        for chip_name, chip in iteritems(input_list):
            label_index = 1
            for chip_name_index, feature in enumerate(chip):
                sensors_current = {}
                # Sensor name
                if feature.label == '':
                    sensors_current['label'] = chip_name + ' ' + str(chip_name_index)
                elif feature.label in [i['label'] for i in ret]:
                    sensors_current['label'] = feature.label + ' ' + str(label_index)
                    label_index += 1
                else:
                    sensors_current['label'] = feature.label
                # Sensors value, limit and unit
                sensors_current['unit'] = type
                sensors_current['value'] = int(getattr(feature, 'current', 0) if getattr(feature, 'current', 0) else 0)
                system_warning = getattr(feature, 'high', None)
                system_critical = getattr(feature, 'critical', None)
                sensors_current['warning'] = int(system_warning) if system_warning is not None else None
                sensors_current['critical'] = int(system_critical) if system_critical is not None else None
                # Add sensor to the list
                ret.append(sensors_current)
        return ret

    def get(self, sensor_type=SENSOR_TEMP_TYPE):
        """Get sensors list."""
        self.__update__()
        if sensor_type == SENSOR_TEMP_TYPE:
            ret = [s for s in self.sensors_list if s['unit'] == SENSOR_TEMP_UNIT]
        elif sensor_type == SENSOR_FAN_TYPE:
            ret = [s for s in self.sensors_list if s['unit'] == SENSOR_FAN_UNIT]
        else:
            # Unknown type
            logger.debug("Unknown sensor type %s" % sensor_type)
            ret = []
        return ret
