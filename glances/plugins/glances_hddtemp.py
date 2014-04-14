#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances - An eye on your system
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

# Import system libs
import socket

# Import Glances libs
from glances.plugins.glances_plugin import GlancesPlugin


class Plugin(GlancesPlugin):
    """
    Glances' HDD temperature sensors plugin

    stats is a list
    """
    def __init__(self):
        GlancesPlugin.__init__(self)

        # Init the sensor class
        self.glancesgrabhddtemp = glancesGrabHDDTemp()

        # We do not want to display the stat in a dedicated area
        # The HDD temp is displayed within the sensors plugin
        self.display_curse = False

    def update(self):
        """
        Update HDD stats
        """
        self.stats = self.glancesgrabhddtemp.get()


class glancesGrabHDDTemp:
    """
    Get hddtemp stats using a socket connection
    """
    def __init__(self, host="127.0.0.1", port=7634):
        """
        Init hddtemp stats
        """
        self.host = host
        self.port = port
        self.cache = ""
        self.hddtemp_list = []

    def __update__(self):
        """
        Update the stats
        """
        # Reset the list
        self.hddtemp_list = []

        # Fetch the data
        data = self.fetch()

        # Exit if no data
        if data == "":
            return

        # Safety check to avoid malformed data
        # Considering the size of "|/dev/sda||0||" as the minimum
        if len(data) < 14:
            data = self.cache if len(self.cache) > 0 else self.fetch()
        self.cache = data

        try:
            fields = data.split(b'|')
        except TypeError:
            fields = ""
        devices = (len(fields) - 1) // 5
        for item in range(devices):
            offset = item * 5
            hddtemp_current = {}
            device = fields[offset + 1].split(b'/dev/')[-1]
            temperature = fields[offset + 3]
            hddtemp_current['label'] = device.decode('utf-8')
            hddtemp_current['value'] = temperature.decode('utf-8')
            self.hddtemp_list.append(hddtemp_current)

    def fetch(self):
        """
        Fetch the data from hddtemp daemon
        """
        # Taking care of sudden deaths/stops of hddtemp daemon
        try:
            sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sck.connect((self.host, self.port))
            data = sck.recv(4096)
            sck.close()
        except socket.error:
            data = ""

        return data

    def get(self):
        self.__update__()
        return self.hddtemp_list
