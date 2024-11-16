#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""HDD temperature plugin."""

import os
import socket

from glances.globals import nativestr
from glances.logger import logger
from glances.plugins.plugin.model import GlancesPluginModel


class PluginModel(GlancesPluginModel):
    """Glances HDD temperature sensors plugin.

    stats is a list
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(args=args, config=config, stats_init_value=[])

        # Init the sensor class
        hddtemp_host = self.get_conf_value("host", default=["127.0.0.1"])[0]
        hddtemp_port = int(self.get_conf_value("port", default="7634"))
        self.hddtemp = GlancesGrabHDDTemp(args=args, host=hddtemp_host, port=hddtemp_port)

        # We do not want to display the stat in a dedicated area
        # The HDD temp is displayed within the sensors plugin
        self.display_curse = False

    # @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update HDD stats using the input method."""
        # Init new stats
        stats = self.get_init_value()

        if self.input_method == 'local':
            # Update stats using the standard system lib
            stats = self.hddtemp.get()

        else:
            # Update stats using SNMP
            # Not available for the moment
            pass

        # Update the stats
        self.stats = stats

        return self.stats


class GlancesGrabHDDTemp:
    """Get hddtemp stats using a socket connection."""

    def __init__(self, host='127.0.0.1', port=7634, args=None):
        """Init hddtemp stats."""
        self.args = args
        self.host = host
        self.port = port
        self.cache = ""
        self.reset()

    def reset(self):
        """Reset/init the stats."""
        self.hddtemp_list = []

    def __update__(self):
        """Update the stats."""
        # Reset the list
        self.reset()

        # Fetch the data
        # data = ("|/dev/sda|WDC WD2500JS-75MHB0|44|C|"
        #         "|/dev/sdb|WDC WD2500JS-75MHB0|35|C|"
        #         "|/dev/sdc|WDC WD3200AAKS-75B3A0|45|C|"
        #         "|/dev/sdd|WDC WD3200AAKS-75B3A0|45|C|"
        #         "|/dev/sde|WDC WD3200AAKS-75B3A0|43|C|"
        #         "|/dev/sdf|???|ERR|*|"
        #         "|/dev/sdg|HGST HTS541010A9E680|SLP|*|"
        #         "|/dev/sdh|HGST HTS541010A9E680|UNK|*|")
        data = self.fetch()

        # Exit if no data
        if data == "":
            return

        # Safety check to avoid malformed data
        # Considering the size of "|/dev/sda||0||" as the minimum
        if len(data) < 14:
            data = self.cache if self.cache else self.fetch()
        self.cache = data

        try:
            fields = data.split(b'|')
        except TypeError:
            fields = ""
        devices = (len(fields) - 1) // 5
        for item in range(devices):
            offset = item * 5
            hddtemp_current = {}
            device = os.path.basename(nativestr(fields[offset + 1]))
            temperature = fields[offset + 3]
            unit = nativestr(fields[offset + 4])
            hddtemp_current['label'] = device
            try:
                hddtemp_current['value'] = float(temperature)
            except ValueError:
                # Temperature could be 'ERR', 'SLP' or 'UNK' (see issue #824)
                # Improper bytes/unicode in glances_hddtemp.py (see issue #887)
                hddtemp_current['value'] = nativestr(temperature)
            hddtemp_current['unit'] = unit
            self.hddtemp_list.append(hddtemp_current)

    def fetch(self):
        """Fetch the data from hddtemp daemon."""
        # Taking care of sudden deaths/stops of hddtemp daemon
        try:
            sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sck.connect((self.host, self.port))
            data = b''
            while True:
                received = sck.recv(4096)
                if not received:
                    break
                data += received
        except Exception as e:
            logger.debug(f"Cannot connect to an HDDtemp server ({self.host}:{self.port} => {e})")
            logger.debug("Disable the HDDtemp module. Use the --disable-hddtemp to hide the previous message.")
            if self.args is not None:
                self.args.disable_hddtemp = True
            data = ""
        finally:
            sck.close()
            if data != "":
                logger.debug(f"Received data from the HDDtemp server: {data}")

        return data

    def get(self):
        """Get HDDs list."""
        self.__update__()
        return self.hddtemp_list
