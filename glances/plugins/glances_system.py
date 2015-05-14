# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2015 Nicolargo <nicolas@nicolargo.com>
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

"""System plugin."""

# Import system libs
import os
import platform
import re

# Import Glances libs
from glances.plugins.glances_plugin import GlancesPlugin

# SNMP OID
snmp_oid = {'default': {'hostname': '1.3.6.1.2.1.1.5.0',
                        'system_name': '1.3.6.1.2.1.1.1.0'},
            'netapp': {'hostname': '1.3.6.1.2.1.1.5.0',
                       'system_name': '1.3.6.1.2.1.1.1.0',
                       'platform': '1.3.6.1.4.1.789.1.1.5.0'}}

# SNMP to human read
# Dict (key: OS short name) of dict (reg exp OID to human)
# Windows:
# http://msdn.microsoft.com/en-us/library/windows/desktop/ms724832%28v=vs.85%29.aspx
snmp_to_human = {'windows': {'Windows Version 6.3': 'Windows 8.1 or Server 2012R2',
                             'Windows Version 6.2': 'Windows 8 or Server 2012',
                             'Windows Version 6.1': 'Windows 7 or Server 2008R2',
                             'Windows Version 6.0': 'Windows Vista or Server 2008',
                             'Windows Version 5.2': 'Windows XP 64bits or 2003 server',
                             'Windows Version 5.1': 'Windows XP',
                             'Windows Version 5.0': 'Windows 2000'}}


def _linux_os_release():
    """Try to determine the name of a Linux distribution.

    This function checks for the /etc/os-release file.
    It takes the name from the 'NAME' field and the version from 'VERSION_ID'.
    An empty string is returned if the above values cannot be determined.
    """
    pretty_name = ''
    ashtray = {}
    keys = ['NAME', 'VERSION_ID']
    try:
        with open(os.path.join('/etc', 'os-release')) as f:
            for line in f:
                for key in keys:
                    if line.startswith(key):
                        ashtray[key] = line.strip().split('=')[1][1:-1]
    except (OSError, IOError):
        return pretty_name

    if ashtray:
        if 'NAME' in ashtray:
            pretty_name = ashtray['NAME']
        if 'VERSION_ID' in ashtray:
            pretty_name += ' {0}'.format(ashtray['VERSION_ID'])

    return pretty_name


class Plugin(GlancesPlugin):

    """Glances' host/system plugin.

    stats is a dict
    """

    def __init__(self, args=None):
        """Init the plugin."""
        GlancesPlugin.__init__(self, args=args)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init the stats
        self.reset()

    def reset(self):
        """Reset/init the stats."""
        self.stats = {}

    def update(self):
        """Update the host/system info using the input method.

        Return the stats (dict)
        """
        # Reset stats
        self.reset()

        if self.input_method == 'local':
            # Update stats using the standard system lib
            self.stats['os_name'] = platform.system()
            self.stats['hostname'] = platform.node()
            self.stats['platform'] = platform.architecture()[0]
            if self.stats['os_name'] == "Linux":
                linux_distro = platform.linux_distribution()
                if linux_distro[0] == '':
                    self.stats['linux_distro'] = _linux_os_release()
                else:
                    self.stats['linux_distro'] = ' '.join(linux_distro[:2])
                self.stats['os_version'] = platform.release()
            elif self.stats['os_name'] == "FreeBSD":
                self.stats['os_version'] = platform.release()
            elif self.stats['os_name'] == "Darwin":
                self.stats['os_version'] = platform.mac_ver()[0]
            elif self.stats['os_name'] == "Windows":
                os_version = platform.win32_ver()
                self.stats['os_version'] = ' '.join(os_version[::2])
                # if the python version is 32 bit perhaps the windows operating
                # system is 64bit
                if self.stats['platform'] == '32bit' and 'PROCESSOR_ARCHITEW6432' in os.environ:
                    self.stats['platform'] = '64bit'
            else:
                self.stats['os_version'] = ""
            # Add human readable name
            if self.stats['os_name'] == "Linux":
                self.stats['hr_name'] = self.stats['linux_distro']
            else:
                self.stats['hr_name'] = '{0} {1}'.format(
                    self.stats['os_name'], self.stats['os_version'])
            self.stats['hr_name'] += ' {0}'.format(self.stats['platform'])

        elif self.input_method == 'snmp':
            # Update stats using SNMP
            try:
                self.stats = self.get_stats_snmp(
                    snmp_oid=snmp_oid[self.short_system_name])
            except KeyError:
                self.stats = self.get_stats_snmp(snmp_oid=snmp_oid['default'])
            # Default behavor: display all the information
            self.stats['os_name'] = self.stats['system_name']
            # Windows OS tips
            if self.short_system_name == 'windows':
                try:
                    iteritems = snmp_to_human['windows'].iteritems()
                except AttributeError:
                    iteritems = snmp_to_human['windows'].items()
                for r, v in iteritems:
                    if re.search(r, self.stats['system_name']):
                        self.stats['os_name'] = v
                        break
            # Add human readable name
            self.stats['hr_name'] = self.stats['os_name']

        return self.stats

    def msg_curse(self, args=None):
        """Return the string to display in the curse interface."""
        # Init the return message
        ret = []

        # Build the string message
        if args.client:
            # Client mode
            if args.cs_status.lower() == "connected":
                msg = 'Connected to '
                ret.append(self.curse_add_line(msg, 'OK'))
            elif args.cs_status.lower() == "snmp":
                msg = 'SNMP from '
                ret.append(self.curse_add_line(msg, 'OK'))
            elif args.cs_status.lower() == "disconnected":
                msg = 'Disconnected from '
                ret.append(self.curse_add_line(msg, 'CRITICAL'))

        # Hostname is mandatory
        msg = self.stats['hostname']
        ret.append(self.curse_add_line(msg, "TITLE"))
        # System info
        if self.stats['os_name'] == "Linux" and self.stats['linux_distro']:
            msg = ' ({0} {1} / {2} {3})'.format(self.stats['linux_distro'],
                                                self.stats['platform'],
                                                self.stats['os_name'],
                                                self.stats['os_version'])
        else:
            try:
                msg = ' ({0} {1} {2})'.format(self.stats['os_name'],
                                              self.stats['os_version'],
                                              self.stats['platform'])
            except Exception:
                msg = ' ({0})'.format(self.stats['os_name'])
        ret.append(self.curse_add_line(msg, optional=True))

        # Return the message with decoration
        return ret
