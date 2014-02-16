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

from glances_plugin import GlancesPlugin, getTimeSinceLastUpdate

class Plugin(GlancesPlugin):
    """
    Glances's HDD temperature sensors Plugin

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
        Update Sensors stats
        """

        self.stats = self.glancesgrabhddtemp.get()


class glancesGrabHDDTemp:
    """
    Get hddtemp stats using a socket connection
    """
    cache = ""
    address = "127.0.0.1"
    port = 7634

    def __init__(self):
        """
        Init hddtemp stats
        """
        try:
            sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sck.connect((self.address, self.port))
            sck.close()
        except Exception:
            self.initok = False
        else:
            self.initok = True

    def __update__(self):
        """
        Update the stats
        """
        # Reset the list
        self.hddtemp_list = []

        if self.initok:
            data = ""
            # Taking care of sudden deaths/stops of hddtemp daemon
            try:
                sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sck.connect((self.address, self.port))
                data = sck.recv(4096)
                sck.close()
            except Exception:
                hddtemp_current = {}
                hddtemp_current['label'] = "hddtemp is gone"
                hddtemp_current['value'] = 0
                self.hddtemp_list.append(hddtemp_current)
                return
            else:
                # Considering the size of "|/dev/sda||0||" as the minimum
                if len(data) < 14:
                    if len(self.cache) == 0:
                        data = "|hddtemp error||0||"
                    else:
                        data = self.cache
                self.cache = data
                fields = data.decode('utf-8').split("|")
                devices = (len(fields) - 1) // 5
                for i in range(0, devices):
                    offset = i * 5
                    hddtemp_current = {}
                    temperature = fields[offset + 3]
                    if temperature == "ERR":
                        hddtemp_current['label'] = _("hddtemp error")
                        hddtemp_current['value'] = 0
                    elif temperature == "SLP":
                        hddtemp_current['label'] = fields[offset + 1].split("/")[-1] + " is sleeping"
                        hddtemp_current['value'] = 0
                    elif temperature == "UNK":
                        hddtemp_current['label'] = fields[offset + 1].split("/")[-1] + " is unknown"
                        hddtemp_current['value'] = 0
                    else:
                        hddtemp_current['label'] = fields[offset + 1].split("/")[-1]
                        try:
                            hddtemp_current['value'] = int(temperature)
                        except TypeError:
                            hddtemp_current['label'] = fields[offset + 1].split("/")[-1] + " is unknown"
                            hddtemp_current['value'] = 0
                    self.hddtemp_list.append(hddtemp_current)

    def get(self):
        self.__update__()
        return self.hddtemp_list
