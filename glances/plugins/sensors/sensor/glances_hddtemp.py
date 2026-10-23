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


class GlancesGrabHDDTemp:
    """Get hddtemp stats using a socket connection."""

    # Seconds to connect and to wait for each read; bytes kept at most.
    TIMEOUT = 2.0
    MAX_BYTES = 64 * 1024

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
        # Taking care of sudden deaths/stops of hddtemp daemon.
        # A time limit and a size cap: the port is unprivileged, so when no
        # daemon runs, a local user can take it and would otherwise freeze the
        # whole sensors collection or grow this process (security audit
        # 2026-10-17, A5).
        sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sck.settimeout(self.TIMEOUT)
        try:
            sck.connect((self.host, self.port))
            data = b''
            while len(data) < self.MAX_BYTES:
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
