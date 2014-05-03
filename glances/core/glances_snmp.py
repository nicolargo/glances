# -*- coding: utf-8 -*-
#
# This file is part of Glances.
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

import sys

try:
    from pysnmp.entity.rfc3413.oneliner import cmdgen
except ImportError, e:
    print("Error importing PySNMP lib: %s" % e)
    print("Install using pip: # pip install pysnmp")
    sys.exit(2)


class GlancesSNMPClient(object):
    """ SNMP client class (based on PySNMP) """
    
    def __init__(self, host = "localhost",
                       port = 161,
                       community = "public",
                       version = "SNMPv2-MIB"):
        super(GlancesSNMPClient, self).__init__()
        self.cmdGen = cmdgen.CommandGenerator()
        self.host = host
        self.port = port
        self.community = community
        self.version = version

    def __result__(self, errorIndication, errorStatus, errorIndex, varBinds):
        ret = {}
        if not (errorIndication or errorStatus):
            for name, val in varBinds:
                if (str(val) == ''):
                    ret[name.prettyPrint()] = ''
                else:
                    ret[name.prettyPrint()] = val.prettyPrint()
        return ret

    def get_by_oid(self, *oid):
        errorIndication, errorStatus, errorIndex, varBinds = self.cmdGen.getCmd(
            cmdgen.CommunityData(self.community),
            cmdgen.UdpTransportTarget((self.host, self.port)),
            *oid
        )
        return self.__result__(errorIndication, errorStatus, errorIndex, varBinds)
