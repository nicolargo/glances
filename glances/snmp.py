#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

import sys

from glances.logger import logger

# Import mandatory PySNMP lib
try:
    from pysnmp.entity.rfc3413.oneliner import cmdgen
except ImportError:
    logger.critical("PySNMP library not found. To install it: pip install pysnmp")
    sys.exit(2)


class GlancesSNMPClient:
    """SNMP client class (based on pysnmp library)."""

    def __init__(self, host='localhost', port=161, version='2c', community='public', user='private', auth=''):
        super().__init__()
        self.cmdGen = cmdgen.CommandGenerator()

        self.version = version

        self.host = host
        self.port = port

        self.community = community
        self.user = user
        self.auth = auth

    def __buid_result(self, varBinds):
        """Build the results."""
        ret = {}
        for name, val in varBinds:
            if str(val) == '':
                ret[str(name)] = ''
            else:
                ret[str(name)] = val.prettyPrint()
        return ret

    def __get_result__(self, errorIndication, errorStatus, errorIndex, varBinds):
        """Put results in table."""
        ret = {}
        if not errorIndication or not errorStatus:
            ret = self.__buid_result(varBinds)
        return ret

    def get_by_oid(self, *oid):
        """SNMP simple request (list of OID).

        One request per OID list.

        :param oid: oid list
        :return: a dict
        """
        if self.version == '3':
            errorIndication, errorStatus, errorIndex, varBinds = self.cmdGen.getCmd(
                cmdgen.UsmUserData(self.user, self.auth), cmdgen.UdpTransportTarget((self.host, self.port)), *oid
            )
        else:
            errorIndication, errorStatus, errorIndex, varBinds = self.cmdGen.getCmd(
                cmdgen.CommunityData(self.community), cmdgen.UdpTransportTarget((self.host, self.port)), *oid
            )
        return self.__get_result__(errorIndication, errorStatus, errorIndex, varBinds)

    def __bulk_result__(self, errorIndication, errorStatus, errorIndex, varBindTable):
        ret = []
        if not errorIndication or not errorStatus:
            for varBindTableRow in varBindTable:
                ret.append(self.__buid_result(varBindTableRow))
        return ret

    def getbulk_by_oid(self, non_repeaters, max_repetitions, *oid):
        """SNMP getbulk request.

        In contrast to snmpwalk, this information will typically be gathered in
        a single transaction with the agent, rather than one transaction per
        variable found.

        * non_repeaters: This specifies the number of supplied variables that
          should not be iterated over.
        * max_repetitions: This specifies the maximum number of iterations over
          the repeating variables.
        * oid: oid list
        > Return a list of dicts
        """
        if self.version.startswith('3'):
            errorIndication, errorStatus, errorIndex, varBinds = self.cmdGen.getCmd(
                cmdgen.UsmUserData(self.user, self.auth),
                cmdgen.UdpTransportTarget((self.host, self.port)),
                non_repeaters,
                max_repetitions,
                *oid,
            )
        if self.version.startswith('2'):
            errorIndication, errorStatus, errorIndex, varBindTable = self.cmdGen.bulkCmd(
                cmdgen.CommunityData(self.community),
                cmdgen.UdpTransportTarget((self.host, self.port)),
                non_repeaters,
                max_repetitions,
                *oid,
            )
        else:
            # Bulk request are not available with SNMP version 1
            return []
        return self.__bulk_result__(errorIndication, errorStatus, errorIndex, varBindTable)
