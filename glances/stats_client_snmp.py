#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""The stats manager."""

import re

from glances.globals import iteritems
from glances.logger import logger
from glances.stats import GlancesStats

# SNMP OID regexp pattern to short system name dict
oid_to_short_system_name = {
    '.*Linux.*': 'linux',
    '.*Darwin.*': 'mac',
    '.*BSD.*': 'bsd',
    '.*Windows.*': 'windows',
    '.*Cisco.*': 'cisco',
    '.*VMware ESXi.*': 'esxi',
    '.*NetApp.*': 'netapp',
}


class GlancesStatsClientSNMP(GlancesStats):
    """This class stores, updates and gives stats for the SNMP client."""

    def __init__(self, config=None, args=None):
        super().__init__()

        # Init the configuration
        self.config = config

        # Init the arguments
        self.args = args

        # OS name is used because OID is different between system
        self.os_name = None

        # Load AMPs, plugins and exports modules
        self.load_modules(self.args)

    def check_snmp(self):
        """Check if SNMP is available on the server."""
        # Import the SNMP client class
        from glances.snmp import GlancesSNMPClient

        # Create an instance of the SNMP client
        snmp_client = GlancesSNMPClient(
            host=self.args.client,
            port=self.args.snmp_port,
            version=self.args.snmp_version,
            community=self.args.snmp_community,
            user=self.args.snmp_user,
            auth=self.args.snmp_auth,
        )

        # If we cannot grab the hostname, then exit...
        ret = snmp_client.get_by_oid("1.3.6.1.2.1.1.5.0") != {}
        if ret:
            # Get the OS name (need to grab the good OID...)
            oid_os_name = snmp_client.get_by_oid("1.3.6.1.2.1.1.1.0")
            try:
                self.system_name = self.get_system_name(oid_os_name['1.3.6.1.2.1.1.1.0'])
                logger.info(f"SNMP system name detected: {self.system_name}")
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
            if self._plugins[p].is_disabled():
                # If current plugin is disable
                # then continue to next plugin
                continue

            # Set the input method to SNMP
            self._plugins[p].input_method = 'snmp'
            self._plugins[p].short_system_name = self.system_name

            # Update the stats...
            try:
                self._plugins[p].update()
            except Exception as e:
                logger.error(f"Update {p} failed: {e}")
            else:
                # ... the history
                self._plugins[p].update_stats_history()
                # ... and the views
                self._plugins[p].update_views()
