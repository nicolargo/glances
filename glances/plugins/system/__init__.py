#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""System plugin."""

import builtins
import os
import platform
import re

from glances.globals import iteritems
from glances.logger import logger
from glances.plugins.plugin.model import GlancesPluginModel

# {
#   "os_name": "Linux",
#   "hostname": "XPS13-9333",
#   "platform": "64bit",
#   "linux_distro": "Ubuntu 22.04",
#   "os_version": "5.15.0-88-generic",
#   "hr_name": "Ubuntu 22.04 64bit"
# }
# Fields description
# description: human readable description
# short_name: shortname to use un UI
# unit: unit type
# rate: is it a rate ? If yes, // by time_since_update when displayed,
# min_symbol: Auto unit should be used if value > than 1 'X' (K, M, G)...
fields_description = {
    'os_name': {
        'description': 'Operating system name',
    },
    'hostname': {
        'description': 'Hostname',
    },
    'platform': {
        'description': 'Platform (32 or 64 bits)',
    },
    'linux_distro': {
        'description': 'Linux distribution',
    },
    'os_version': {
        'description': 'Operating system version',
    },
    'hr_name': {
        'description': 'Human readable operating system name',
    },
}

# SNMP OID
snmp_oid = {
    'default': {'hostname': '1.3.6.1.2.1.1.5.0', 'system_name': '1.3.6.1.2.1.1.1.0'},
    'netapp': {
        'hostname': '1.3.6.1.2.1.1.5.0',
        'system_name': '1.3.6.1.2.1.1.1.0',
        'platform': '1.3.6.1.4.1.789.1.1.5.0',
    },
}

# SNMP to human read
# Dict (key: OS short name) of dict (reg exp OID to human)
# Windows:
# http://msdn.microsoft.com/en-us/library/windows/desktop/ms724832%28v=vs.85%29.aspx
snmp_to_human = {
    'windows': {
        'Windows Version 10.0': 'Windows 10|11 or Server 2016|2019|2022',
        'Windows Version 6.3': 'Windows 8.1 or Server 2012R2',
        'Windows Version 6.2': 'Windows 8 or Server 2012',
        'Windows Version 6.1': 'Windows 7 or Server 2008R2',
        'Windows Version 6.0': 'Windows Vista or Server 2008',
        'Windows Version 5.2': 'Windows XP 64bits or 2003 server',
        'Windows Version 5.1': 'Windows XP',
        'Windows Version 5.0': 'Windows 2000',
    }
}


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
        with builtins.open(os.path.join('/etc', 'os-release')) as f:
            for line in f:
                for key in keys:
                    if line.startswith(key):
                        ashtray[key] = re.sub(r'^"|"$', '', line.strip().split('=')[1])
    except OSError:
        return pretty_name

    if ashtray:
        if 'NAME' in ashtray:
            pretty_name = ashtray['NAME']
        if 'VERSION_ID' in ashtray:
            pretty_name += ' {}'.format(ashtray['VERSION_ID'])

    return pretty_name


class PluginModel(GlancesPluginModel):
    """Glances' host/system plugin.

    stats is a dict
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(args=args, config=config, fields_description=fields_description)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Set default rate to 60 seconds
        if self.get_refresh():
            self.set_refresh(60)

        # Get the default message (if defined)
        self.system_info_msg = config.get_value('system', 'system_info_msg') if config else None

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update the host/system info using the input method.

        :return: the stats dict
        """
        # Init new stats
        stats = self.get_init_value()

        if self.input_method == 'local':
            # Update stats using the standard system lib
            stats['os_name'] = platform.system()
            stats['hostname'] = platform.node()
            stats['platform'] = platform.architecture()[0]
            if stats['os_name'] == "Linux":
                try:
                    linux_distro = platform.linux_distribution()
                except AttributeError:
                    stats['linux_distro'] = _linux_os_release()
                else:
                    if linux_distro[0] == '':
                        stats['linux_distro'] = _linux_os_release()
                    else:
                        stats['linux_distro'] = ' '.join(linux_distro[:2])
                stats['os_version'] = platform.release()
            elif stats['os_name'].endswith('BSD') or stats['os_name'] == 'SunOS':
                stats['os_version'] = platform.release()
            elif stats['os_name'] == "Darwin":
                stats['os_version'] = platform.mac_ver()[0]
            elif stats['os_name'] == "Windows":
                os_version = platform.win32_ver()
                stats['os_version'] = ' '.join(os_version[::2])
                # if the python version is 32 bit perhaps the windows operating
                # system is 64bit
                if stats['platform'] == '32bit' and 'PROCESSOR_ARCHITEW6432' in os.environ:
                    stats['platform'] = '64bit'
            else:
                stats['os_version'] = ""

            # Add human readable name
            if self.system_info_msg:
                try:
                    stats['hr_name'] = self.system_info_msg.format(**stats)
                except KeyError as e:
                    logger.debug(f'Error in system_info_msg ({e})')
                    stats['hr_name'] = '{os_name} {os_version} {platform}'.format(**stats)
            elif stats['os_name'] == "Linux":
                stats['hr_name'] = '{linux_distro} {platform} / {os_name} {os_version}'.format(**stats)
            else:
                stats['hr_name'] = '{os_name} {os_version} {platform}'.format(**stats)

        elif self.input_method == 'snmp':
            # Update stats using SNMP
            try:
                stats = self.get_stats_snmp(snmp_oid=snmp_oid[self.short_system_name])
            except KeyError:
                stats = self.get_stats_snmp(snmp_oid=snmp_oid['default'])
            # Default behavior: display all the information
            stats['os_name'] = stats['system_name']
            # Windows OS tips
            if self.short_system_name == 'windows':
                for r, v in iteritems(snmp_to_human['windows']):
                    if re.search(r, stats['system_name']):
                        stats['os_name'] = v
                        break
            # Add human readable name
            stats['hr_name'] = stats['os_name']

        # Update the stats
        self.stats = stats

        return self.stats

    def msg_curse(self, args=None, max_width=None):
        """Return the string to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and plugin not disabled
        if not self.stats or self.is_disabled():
            return ret

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
        msg = ' ' + self.stats['hr_name']
        ret.append(self.curse_add_line(msg, optional=True))

        # Return the message with decoration
        return ret
