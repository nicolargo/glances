#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""LibreHardwareMonitor temperatures plugin (Windows only).

Grab temperatures from the LibreHardwareMonitor embedded web server:
https://github.com/LibreHardwareMonitor/LibreHardwareMonitor

The "Remote Web Server" option should be enabled in LibreHardwareMonitor
(Options > Remote Web Server > Run). Default URL: http://localhost:8085
"""

import json
from urllib.request import urlopen

from glances.logger import logger
from glances.plugins.plugin.model import GlancesPluginModel

# NVMe drives expose their thresholds constants as pseudo temperature sensors:
# do not report them as readings but as the warning/critical values of the
# real temperature sensors of the same hardware
GROUP_THRESHOLDS = {'Warning Temperature': 'warning', 'Critical Temperature': 'critical'}

# Pseudo temperature sensors which are not actual readings
# ('Distance to TjMax' is an inverted thermal margin: higher means cooler)
EXCLUDED_SENSORS = ('Distance to TjMax',)


class LibrehardwaremonitorPlugin(GlancesPluginModel):
    """Glances LibreHardwareMonitor temperatures plugin.

    If storage is True, only the disks temperatures are grabbed (to be
    displayed as temperature_hdd), else only the non disks ones (CPU,
    motherboard, GPU... to be displayed as temperature_core).

    stats is a list
    """

    def __init__(self, args=None, config=None, storage=False):
        """Init the plugin."""
        super().__init__(args=args, config=config, stats_init_value=[])

        # Init the sensor class
        # Note: the [librehardwaremonitor] section is read from the config object
        # because plugin_name is 'sensors' for all the sensors sub-plugins
        lhm_host = '127.0.0.1'
        lhm_port = 8085
        if config is not None and config.has_section('librehardwaremonitor'):
            lhm_host = config.get_value('librehardwaremonitor', 'host', default=lhm_host)
            lhm_port = int(config.get_value('librehardwaremonitor', 'port', default=lhm_port))
        self.lhm = GlancesGrabLHM(host=lhm_host, port=lhm_port, storage=storage)

        # We do not want to display the stat in a dedicated area
        # The LibreHardwareMonitor temperatures are displayed within the sensors plugin
        self.display_curse = False

    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update LibreHardwareMonitor stats using the input method."""
        # Init new stats
        stats = self.get_init_value()

        if self.input_method == 'local':
            # Update stats using the LibreHardwareMonitor web server
            stats = self.lhm.get()

        else:
            # Update stats using SNMP
            # Not available for the moment
            pass

        # Update the stats
        self.stats = stats

        return self.stats


class GlancesGrabLHM:
    """Get temperatures from the LibreHardwareMonitor web server (data.json)."""

    def __init__(self, host='127.0.0.1', port=8085, storage=False):
        """Init the LibreHardwareMonitor stats."""
        self.url = f'http://{host}:{port}/data.json'
        self.storage = storage
        self.last_fetch_ok = True

    def fetch(self):
        """Fetch the sensors tree from the LibreHardwareMonitor web server."""
        try:
            with urlopen(self.url, timeout=3) as response:
                data = json.load(response)
        except Exception as e:
            # Log only on state change to avoid flooding the logs at each refresh
            if self.last_fetch_ok:
                logger.debug(f"Cannot connect to the LibreHardwareMonitor web server ({self.url} => {e})")
            self.last_fetch_ok = False
            return None
        self.last_fetch_ok = True
        return data

    @staticmethod
    def _is_temperature(node):
        """Return True if the given leaf node is a temperature sensor."""
        # Recent LibreHardwareMonitor releases expose the sensor type in data.json
        # Fall back to the value unit for older releases
        if 'Type' in node:
            return node['Type'] == 'Temperature'
        return '°C' in node.get('Value', '')

    @staticmethod
    def _parse_value(raw_value):
        """Parse a LibreHardwareMonitor value like '44,5 °C' and return a float (or None).

        The decimal separator depends on the system locale (',' or '.').
        """
        try:
            return float(raw_value.split(' ')[0].replace(',', '.'))
        except (AttributeError, IndexError, ValueError):
            return None

    def _group_thresholds(self, children):
        """Return the warning/critical thresholds exposed as pseudo sensors (NVMe)."""
        thresholds = {}
        for child in children:
            if child.get('Text') in GROUP_THRESHOLDS and self._is_temperature(child):
                value = self._parse_value(child.get('Value'))
                if value is not None:
                    thresholds[GROUP_THRESHOLDS[child.get('Text')]] = int(value)
        return thresholds

    def _walk(self, node, ancestors, ret):
        """Walk the data.json tree and add the temperature sensors to the ret list.

        ancestors is the list of the parent nodes (used to get the hardware name).
        """
        children = node.get('Children') or []
        if not children:
            return

        thresholds = self._group_thresholds(children)

        for child in children:
            if child.get('Children'):
                self._walk(child, ancestors + [node], ret)
                continue
            if not self._is_temperature(child):
                continue
            text = child.get('Text', '')
            if text in GROUP_THRESHOLDS or any(e in text for e in EXCLUDED_SENSORS):
                continue
            value = self._parse_value(child.get('Value'))
            if value is None:
                continue
            # The parent of the sensors category node ("Temperatures") is the hardware node
            hardware = ancestors[-1] if ancestors else {}
            # Grab either the disks temperatures or the other ones (see storage flag)
            if ('hdd' in hardware.get('ImageURL', '')) != self.storage:
                continue
            # Sensor name first so that the labels stay distinguishable when
            # truncated in the TUI (hardware names can be very long)
            hardware_text = hardware.get('Text', '')
            ret.append(
                {
                    'label': f"{text} ({hardware_text})" if hardware_text else text,
                    'unit': 'C',
                    'value': value,
                    'warning': thresholds.get('warning'),
                    'critical': thresholds.get('critical'),
                }
            )

    def get(self):
        """Get the temperatures list."""
        data = self.fetch()
        if data is None:
            return []
        ret = []
        self._walk(data, [], ret)
        return ret
