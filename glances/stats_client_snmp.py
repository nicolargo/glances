# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2016 Nicolargo <nicolas@nicolargo.com>
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

"""The stats manager."""

import re

from glances.stats import GlancesStats
from glances.compat import iteritems
from glances.logger import logger

# SNMP OID regexp pattern to short system name dict
oid_to_short_system_name = {'.*Linux.*': 'linux',
                            '.*Darwin.*': 'mac',
                            '.*BSD.*': 'bsd',
                            '.*Windows.*': 'windows',
                            '.*Cisco.*': 'cisco',
                            '.*VMware ESXi.*': 'esxi',
                            '.*NetApp.*': 'netapp'}


class GlancesStatsClientSNMP(GlancesStats):

    """This class stores, updates and gives stats for the SNMP client."""

    def __init__(self, config=None, args=None):
        super(GlancesStatsClientSNMP, self).__init__()

        # Init the configuration
        self.config = config

        # Init the arguments
        self.args = args

        # OS name is used because OID is differents between system
        self.os_name = None

        # Load plugins and export modules
        self.load_plugins_and_exports(self.args)

    def check_snmp(self):
        """Chek if SNMP is available on the server."""
        # Import the SNMP client class
        from glances.snmp import GlancesSNMPClient

        # Create an instance of the SNMP client
        clientsnmp = GlancesSNMPClient(host=self.args.client,
                                       port=self.args.snmp_port,
                                       version=self.args.snmp_version,
                                       community=self.args.snmp_community,
                                       user=self.args.snmp_user,
                                       auth=self.args.snmp_auth)

        # If we cannot grab the hostname, then exit...
        ret = clientsnmp.get_by_oid("1.3.6.1.2.1.1.5.0") != {}
        if ret:
            # Get the OS name (need to grab the good OID...)
            oid_os_name = clientsnmp.get_by_oid("1.3.6.1.2.1.1.1.0")
            try:
                self.system_name = self.get_system_name(oid_os_name['1.3.6.1.2.1.1.1.0'])
                logger.info("SNMP system name detected: {0}".format(self.system_name))
            except KeyError:
                self.system_name = None
                logger.warning("Cannot detect SNMP system name")

        return ret

    def get_system_name(self, oid_system_name):
        """Get the short os name from the OS name OID string."""
        short_system_name = None

        if oid_system_name == '':
            return short_system_name

        # Find the short name in the oid_to_short_os_name dict
        for r, v in iteritems(oid_to_short_system_name):
            if re.search(r, oid_system_name):
                short_system_name = v
                break

        return short_system_name

    def update(self):
        """Update the stats using SNMP."""
        # For each plugins, call the update method
        for p in self._plugins:
            # Set the input method to SNMP
            self._plugins[p].input_method = 'snmp'
            self._plugins[p].short_system_name = self.system_name
            try:
                self._plugins[p].update()
            except Exception as e:
                logger.error("Update {0} failed: {1}".format(p, e))
