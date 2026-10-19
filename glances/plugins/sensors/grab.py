#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""psutil temperature and fan sensors, grabbed for the sensors plugin.

Moved out of the v4 plugin module at the v5 cutover; the v5 sensors model
uses them.
"""

import warnings

import psutil

from glances.logger import logger

# Define all kind of sensors available in Glances
sensors_definition = {
    'cpu_temp': {'type': 'temperature_core', 'unit': 'C'},
    'fan_speed': {'type': 'fan_speed', 'unit': 'R'},
    'battery': {'type': 'battery', 'unit': '%'},
}


class GlancesGrabSensors:
    """Get sensors stats."""

    def __init__(self, sensor_def: dict):
        """Init sensors stats."""
        self.sensor_type = sensor_def.get('type')
        self.sensor_unit = sensor_def.get('unit')

        self.init = False
        try:
            self.__fetch_data()
            self.init = True
        except AttributeError:
            logger.debug(f"Cannot grab {self.sensor_type}. Platform not supported.")

    def __fetch_data(self) -> dict[str, list]:
        if self.sensor_type == sensors_definition.get('cpu_temp').get('type'):
            # Solve an issue #1203 concerning a RunTimeError warning message displayed
            # in the curses interface.
            warnings.filterwarnings("ignore")

            # psutil>=5.1.0, Linux-only
            return psutil.sensors_temperatures()

        if self.sensor_type == sensors_definition.get('fan_speed').get('type'):
            # psutil>=5.2.0, Linux-only
            return psutil.sensors_fans()

        raise ValueError(f"Unsupported sensor: {self.sensor_type}")

    def update(self) -> list[dict]:
        """Update the stats."""
        if not self.init:
            return []

        # Temperatures sensors
        ret = []
        data = self.__fetch_data()
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
