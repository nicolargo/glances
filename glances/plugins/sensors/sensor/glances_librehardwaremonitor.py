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
(File > Web Server > Run). Default URL: http://localhost:8085
"""

import json
from urllib.request import urlopen

from glances.logger import logger
from glances.plugins.plugin.model import GlancesPluginModel


class LibrehardwaremonitorPlugin(GlancesPluginModel):
    """Glances LibreHardwareMonitor temperatures plugin.

    stats is a list
    """

    def __init__(self, args=None, config=None):
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
        self.lhm = GlancesGrabLHM(host=lhm_host, port=lhm_port)

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

    def __init__(self, host='127.0.0.1', port=8085):
        """Init the LibreHardwareMonitor stats."""
        self.url = f'http://{host}:{port}/data.json'
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

    def _walk(self, node, chain, ret):
        """Walk the data.json tree and add the temperature sensors to the ret list.

        chain is the list of the parent nodes names (used to build the sensor label).
        """
        children = node.get('Children') or []
        if children:
            for child in children:
                self._walk(child, chain + [node.get('Text', '')], ret)
        elif self._is_temperature(node):
            value = self._parse_value(node.get('Value'))
            if value is None:
                return
            # chain example: ['Sensor', 'MY-PC', 'Nuvoton NCT6793D', 'Temperatures']
            # The hardware name is the parent of the 'Temperatures' category node
            hardware = chain[-2] if len(chain) >= 2 else ''
            label = f"{hardware} {node.get('Text', '')}".strip()
            ret.append(
                {
                    'label': label,
                    'unit': 'C',
                    'value': value,
                    'warning': None,
                    'critical': None,
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
