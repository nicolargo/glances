#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""LibreHardwareMonitor sensors (Windows).

psutil exposes no temperature nor fan sensor on Windows (see issue #3265).
Grab them from the LibreHardwareMonitor web server through the
librehardwaremonitor-api lib: https://pypi.org/project/librehardwaremonitor-api/

The "Remote Web Server" option should be enabled in LibreHardwareMonitor
(Options > Remote Web Server > Run). Default URL: http://localhost:8085
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

try:
    import aiohttp
    from librehardwaremonitor_api import LibreHardwareMonitorClient
    from librehardwaremonitor_api.sensor_type import SensorType
except ImportError:
    LibreHardwareMonitorClient = None

logger = logging.getLogger(__name__)

# Sensor types of the sensors plugin (mirror the model.py constants)
_TEMP_CORE = "temperature_core"
_FAN_SPEED = "fan_speed"
_TEMP_HDD = "temperature_hdd"

# NVMe drives expose their thresholds as pseudo temperature sensors: they are
# not readings but the warning/critical values of the drive temperatures
THRESHOLD_SENSORS = {'Warning Temperature': 'warning', 'Critical Temperature': 'critical'}

# Pseudo temperature sensors which are not actual readings
# ('Distance to TjMax' is an inverted thermal margin: higher means cooler)
EXCLUDED_SENSORS = ('Distance to TjMax',)

# The lib appends the type to the sensor names ("CPU Package Temperature",
# "Fan #1 Speed"): redundant with the unit displayed by Glances
NAME_SUFFIXES = {_TEMP_CORE: ' Temperature', _TEMP_HDD: ' Temperature', _FAN_SPEED: ' Speed'}


def is_available() -> bool:
    """Return True if the librehardwaremonitor-api lib is installed."""
    return LibreHardwareMonitorClient is not None


class GlancesGrabLHM:
    """Get the temperatures and fans speed from the LibreHardwareMonitor web server."""

    def __init__(self, host='127.0.0.1', port=8085, username=None, password=None):
        """Init the LibreHardwareMonitor stats."""
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.url = f'http://{host}:{port}/data.json'
        # The client and its HTTP session are bound to the event loop: built
        # on the first fetch, then reused (a session per fetch leaks memory)
        self.client = None
        self._session = None
        self._loop = None
        self.last_fetch_ok = True

    async def get(self) -> dict[str, list[dict[str, Any]]]:
        """Return the sensors rows, grouped by sensor type."""
        if self.client is None:
            self._loop = asyncio.get_running_loop()
            self._session = aiohttp.ClientSession()
            self.client = LibreHardwareMonitorClient(
                self.host, self.port, username=self.username, password=self.password, session=self._session
            )
        try:
            data = await self.client.get_data()
        except Exception as e:
            # Log only on state change to avoid flooding the logs at each refresh
            if self.last_fetch_ok:
                logger.debug("Cannot grab sensors from the LibreHardwareMonitor web server (%s => %r)", self.url, e)
            self.last_fetch_ok = False
            return {}
        self.last_fetch_ok = True
        return self.parse(data.sensor_data.values())

    def close(self) -> None:
        """Close the HTTP session (called from a worker thread, at Glances exit)."""
        if self._session is None or self._loop is None or self._loop.is_closed():
            return
        try:
            asyncio.run_coroutine_threadsafe(self._session.close(), self._loop).result(timeout=5)
        except Exception as e:
            logger.debug("Cannot close the LibreHardwareMonitor HTTP session: %r", e)
        self._session = None

    @staticmethod
    def parse(sensors) -> dict[str, list[dict[str, Any]]]:
        """Convert the librehardwaremonitor-api sensors to sensors plugin rows."""
        sensors = [s for s in sensors if s.value is not None]

        thresholds: dict[str, dict[str, float]] = {}
        for s in sensors:
            if s.type == SensorType.TEMPERATURE and s.name in THRESHOLD_SENSORS:
                thresholds.setdefault(s.device_id, {})[THRESHOLD_SENSORS[s.name]] = float(s.value)

        ret: dict[str, list[dict[str, Any]]] = {_TEMP_CORE: [], _TEMP_HDD: [], _FAN_SPEED: []}
        labels: set[str] = set()
        for s in sensors:
            if s.type == SensorType.TEMPERATURE:
                if s.name in THRESHOLD_SENSORS or any(e in s.name for e in EXCLUDED_SENSORS):
                    continue
                sensor_type = _TEMP_HDD if s.device_type == 'HDD' else _TEMP_CORE
                unit = 'C'
            elif s.type == SensorType.FAN:
                sensor_type = _FAN_SPEED
                unit = 'R'
            else:
                continue
            # Sensor name first so that the labels stay distinguishable when
            # truncated in the TUI (hardware names can be very long)
            name = s.name.removesuffix(NAME_SUFFIXES[sensor_type])
            label = f"{name} ({s.device_name})" if s.device_name else name
            # The label is the primary key of the sensors plugin: keep it unique
            # (e.g. two identical drives)
            index = 2
            unique_label = label
            while unique_label in labels:
                unique_label = f"{label} {index}"
                index += 1
            labels.add(unique_label)
            device_thresholds = thresholds.get(s.device_id, {}) if sensor_type == _TEMP_HDD else {}
            ret[sensor_type].append(
                {
                    'label': unique_label,
                    'unit': unit,
                    'value': round(float(s.value), 1),
                    'warning': device_thresholds.get('warning'),
                    'critical': device_thresholds.get('critical'),
                }
            )
        return ret
