#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Sensors plugin."""

import warnings
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import Any, Literal

import psutil

from glances.globals import to_fahrenheit
from glances.logger import logger
from glances.outputs.glances_unicode import unicode_message
from glances.plugins.plugin.model import GlancesPluginModel
from glances.plugins.sensors.sensor.glances_batpercent import PluginModel as BatPercentPluginModel
from glances.plugins.sensors.sensor.glances_hddtemp import PluginModel as HddTempPluginModel
from glances.timer import Counter


class SensorType(str, Enum):
    # Switch to `enum.StrEnum` when we only support py311+
    CPU_TEMP = 'temperature_core'
    FAN_SPEED = 'fan_speed'
    HDD_TEMP = 'temperature_hdd'
    BATTERY = 'battery'


CPU_TEMP_UNIT = 'C'
FAN_SPEED_UNIT = 'R'
HDD_TEMP_UNIT = 'C'
BATTERY_UNIT = '%'

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
        super().__init__(args=args, config=config, stats_init_value=[], fields_description=fields_description)
        start_duration = Counter()

        # Init the sensor class
        start_duration.reset()
        glances_grab_sensors_cpu_temp = GlancesGrabSensors(SensorType.CPU_TEMP)
        logger.debug(f"CPU Temp sensor plugin init duration: {start_duration.get()} seconds")

        start_duration.reset()
        glances_grab_sensors_fan_speed = GlancesGrabSensors(SensorType.FAN_SPEED)
        logger.debug(f"Fan speed sensor plugin init duration: {start_duration.get()} seconds")

        # Instance for the HDDTemp Plugin in order to display the hard disks temperatures
        start_duration.reset()
        hddtemp_plugin = HddTempPluginModel(args=args, config=config)
        logger.debug(f"HDDTemp sensor plugin init duration: {start_duration.get()} seconds")

        # Instance for the BatPercent in order to display the batteries capacities
        start_duration.reset()
        batpercent_plugin = BatPercentPluginModel(args=args, config=config)
        logger.debug(f"Battery sensor plugin init duration: {start_duration.get()} seconds")

        self.sensors_grab_map: dict[SensorType, Any] = {}

        if glances_grab_sensors_cpu_temp.init:
            self.sensors_grab_map[SensorType.CPU_TEMP] = glances_grab_sensors_cpu_temp

        if glances_grab_sensors_fan_speed.init:
            self.sensors_grab_map[SensorType.FAN_SPEED] = glances_grab_sensors_fan_speed

        self.sensors_grab_map[SensorType.HDD_TEMP] = hddtemp_plugin
        self.sensors_grab_map[SensorType.BATTERY] = batpercent_plugin

        self.sensors_grab_map: dict[SensorType, Any] = {}

        if glances_grab_sensors_cpu_temp.init:
            self.sensors_grab_map[SensorType.CPU_TEMP] = glances_grab_sensors_cpu_temp

        if glances_grab_sensors_fan_speed.init:
            self.sensors_grab_map[SensorType.FAN_SPEED] = glances_grab_sensors_fan_speed

        self.sensors_grab_map[SensorType.HDD_TEMP] = hddtemp_plugin
        self.sensors_grab_map[SensorType.BATTERY] = batpercent_plugin

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Not necessary to refresh every refresh time
        if args and self.get_refresh() == args.time:
            self.set_refresh(self.get_refresh() * DEFAULT_REFRESH)

    def get_key(self):
        """Return the key of the list."""
        return 'label'

    def __get_sensor_data(self, sensor_type: SensorType) -> list[dict]:
        try:
            data = self.sensors_grab_map[sensor_type].update()
            data = self.__set_type(data, sensor_type)
        except Exception as e:
            logger.error(f"Cannot grab sensors `{sensor_type}` ({e})")
            return []
        else:
            return self.__transform_sensors(data)

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
        return sorted(stats_transformed, key=lambda d: d['label'])

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update sensors stats using the input method."""
        # Init new stats
        stats = self.get_init_value()

        if self.input_method == 'local':
            with ThreadPoolExecutor(max_workers=len(self.sensors_grab_map)) as executor:
                logger.debug(f"Sensors enabled sub plugins: {list(self.sensors_grab_map.keys())}")
                futures = {t: executor.submit(self.__get_sensor_data, t) for t in self.sensors_grab_map.keys()}

            # Merge the results
            for sensor_type, future in futures.items():
                try:
                    stats.extend(future.result())
                except Exception as e:
                    logger.error(f"Cannot parse sensors data for `{sensor_type}` ({e})")

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
        if self.has_alias("{}_{}".format(stats["label"], stats["type"]).lower()):
            return self.has_alias("{}_{}".format(stats["label"], stats["type"]).lower())
        return stats["label"]

    def __set_type(self, stats: list[dict[str, Any]], sensor_type: SensorType) -> list[dict[str, Any]]:
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

    def __get_system_thresholds(self, sensor):
        """Return the alert level thanks to the system thresholds"""
        alert = 'OK'
        if sensor['critical'] is None:
            alert = 'DEFAULT'
        elif sensor['value'] >= sensor['critical']:
            alert = 'CRITICAL'
        elif sensor['warning'] is None:
            alert = 'DEFAULT'
        elif sensor['value'] >= sensor['warning']:
            alert = 'WARNING'
        return alert

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super().update_views()

        # Add specifics information
        # Alert
        for i in self.stats:
            if not i['value']:
                continue
            # Alert processing
            if i['type'] == SensorType.CPU_TEMP:
                if self.is_limit('critical', stat_name=i["type"].value + '_' + i['label']):
                    # Get thresholds for the specific sensor in the glances.conf file (see #2058)
                    alert = self.get_alert(current=i['value'], header=i["type"].value + '_' + i['label'])
                elif self.is_limit('critical', stat_name=i["type"].value):
                    # Get thresholds for the sensor type in the glances.conf file (see #3049)
                    logger.info("Using sensor type thresholds")
                    logger.info(self._limits)
                    alert = self.get_alert(current=i['value'], header=i["type"].value)
                else:
                    # Else use the system thresholds
                    alert = self.__get_system_thresholds(i)
            elif i['type'] == SensorType.BATTERY:
                # Battery is in %
                alert = self.get_alert(current=100 - i['value'], header=i['type'].value)
            else:
                alert = self.get_alert(current=i['value'], header=i['type'].value)
            # Set the alert in the view
            self.views[i[self.get_key()]]['value']['decoration'] = alert

    def battery_trend(self, stats):
        """Return the trend character for the battery"""
        if 'status' not in stats:
            return ''
        if stats['status'].startswith('Charg'):
            return unicode_message('ARROW_UP')
        if stats['status'].startswith('Discharg'):
            return unicode_message('ARROW_DOWN')
        if stats['status'].startswith('Full'):
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
            # No max_width defined, return an empty curse message
            logger.debug(f"No max_width defined for the {self.plugin_name} plugin, it will not be displayed.")
            return ret

        # Header
        msg = '{:{width}}'.format('SENSORS', width=name_max_width)
        ret.append(self.curse_add_line(msg, "TITLE"))

        # Stats
        for i in self.stats:
            # Do not display anything if no battery are detected
            if i['type'] == SensorType.BATTERY and i['value'] == []:
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
                if args.fahrenheit and i['type'] != SensorType.BATTERY and i['type'] != SensorType.FAN_SPEED:
                    trend = ''
                    value = to_fahrenheit(i['value'])
                    unit = 'F'
                else:
                    trend = self.battery_trend(i)
                    value = i['value']
                    unit = i['unit']
                try:
                    msg = f'{value:.0f}{unit}{trend}'
                    msg = f'{msg:>14}'
                    ret.append(
                        self.curse_add_line(
                            msg, self.get_views(item=i[self.get_key()], key='value', option='decoration')
                        )
                    )
                except (TypeError, ValueError):
                    pass

        return ret


class GlancesGrabSensors:
    """Get sensors stats."""

    def __init__(self, sensor_type: Literal[SensorType.FAN_SPEED, SensorType.CPU_TEMP]):
        """Init sensors stats."""
        self.sensor_type = sensor_type
        self.sensor_unit = CPU_TEMP_UNIT if self.sensor_type == SensorType.CPU_TEMP else FAN_SPEED_UNIT

        self.init = False
        try:
            self.__fetch_psutil()
            self.init = True
        except AttributeError:
            logger.debug(f"Cannot grab {sensor_type}. Platform not supported.")

    def __fetch_psutil(self) -> dict[str, list]:
        if self.sensor_type == SensorType.CPU_TEMP:
            # Solve an issue #1203 concerning a RunTimeError warning message displayed
            # in the curses interface.
            warnings.filterwarnings("ignore")

            # psutil>=5.1.0, Linux-only
            return psutil.sensors_temperatures()

        if self.sensor_type == SensorType.FAN_SPEED:
            # psutil>=5.2.0, Linux-only
            return psutil.sensors_fans()

        raise ValueError(f"Unsupported sensor_type: {self.sensor_type}")

    def update(self) -> list[dict]:
        """Update the stats."""
        if not self.init:
            return []

        # Temperatures sensors
        ret = []
        data = self.__fetch_psutil()
        for chip_name, chip in data.items():
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
                sensors_current['unit'] = self.sensor_unit
                sensors_current['value'] = int(getattr(feature, 'current', 0) if getattr(feature, 'current', 0) else 0)
                system_warning = getattr(feature, 'high', None)
                system_critical = getattr(feature, 'critical', None)
                sensors_current['warning'] = int(system_warning) if system_warning is not None else None
                sensors_current['critical'] = int(system_critical) if system_critical is not None else None
                # Add sensor to the list
                ret.append(sensors_current)
        return ret
