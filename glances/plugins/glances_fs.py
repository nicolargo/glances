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

"""File system plugin."""

import operator

from glances.plugins.glances_plugin import GlancesPlugin

import psutil


# SNMP OID
# The snmpd.conf needs to be edited.
# Add the following to enable it on all disk
# ...
# includeAllDisks 10%
# ...
# The OIDs are as follows (for the first disk)
# Path where the disk is mounted: .1.3.6.1.4.1.2021.9.1.2.1
# Path of the device for the partition: .1.3.6.1.4.1.2021.9.1.3.1
# Total size of the disk/partion (kBytes): .1.3.6.1.4.1.2021.9.1.6.1
# Available space on the disk: .1.3.6.1.4.1.2021.9.1.7.1
# Used space on the disk: .1.3.6.1.4.1.2021.9.1.8.1
# Percentage of space used on disk: .1.3.6.1.4.1.2021.9.1.9.1
# Percentage of inodes used on disk: .1.3.6.1.4.1.2021.9.1.10.1
snmp_oid = {'default': {'mnt_point': '1.3.6.1.4.1.2021.9.1.2',
                        'device_name': '1.3.6.1.4.1.2021.9.1.3',
                        'size': '1.3.6.1.4.1.2021.9.1.6',
                        'used': '1.3.6.1.4.1.2021.9.1.8',
                        'percent': '1.3.6.1.4.1.2021.9.1.9'},
            'windows': {'mnt_point': '1.3.6.1.2.1.25.2.3.1.3',
                        'alloc_unit': '1.3.6.1.2.1.25.2.3.1.4',
                        'size': '1.3.6.1.2.1.25.2.3.1.5',
                        'used': '1.3.6.1.2.1.25.2.3.1.6'},
            'netapp': {'mnt_point': '1.3.6.1.4.1.789.1.5.4.1.2',
                       'device_name': '1.3.6.1.4.1.789.1.5.4.1.10',
                       'size': '1.3.6.1.4.1.789.1.5.4.1.3',
                       'used': '1.3.6.1.4.1.789.1.5.4.1.4',
                       'percent': '1.3.6.1.4.1.789.1.5.4.1.6'}}
snmp_oid['esxi'] = snmp_oid['windows']

# Define the history items list
# All items in this list will be historised if the --enable-history tag is set
# 'color' define the graph color in #RGB format
items_history_list = [{'name': 'percent', 'color': '#00FF00'}]


class Plugin(GlancesPlugin):

    """Glances file system plugin.

    stats is a list
    """

    def __init__(self, args=None):
        """Init the plugin."""
        GlancesPlugin.__init__(
            self, args=args, items_history_list=items_history_list)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init the stats
        self.reset()

    def get_key(self):
        """Return the key of the list."""
        return 'mnt_point'

    def reset(self):
        """Reset/init the stats."""
        self.stats = []

    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update the FS stats using the input method."""
        # Reset the list
        self.reset()

        if self.input_method == 'local':
            # Update stats using the standard system lib

            # Grab the stats using the PsUtil disk_partitions
            # If 'all'=False return physical devices only (e.g. hard disks, cd-rom drives, USB keys)
            # and ignore all others (e.g. memory partitions such as /dev/shm)
            try:
                fs_stat = psutil.disk_partitions(all=False)
            except UnicodeDecodeError:
                return self.stats

            # Optionnal hack to allow logicals mounts points (issue #448)
            # Ex: Had to put 'allow=zfs' in the [fs] section of the conf file
            #     to allow zfs monitoring
            for fstype in self.get_conf_value('allow'):
                try:
                    fs_stat += [f for f in psutil.disk_partitions(all=True) if f.fstype.find(fstype) >= 0]
                except UnicodeDecodeError:
                    return self.stats

            # Loop over fs
            for fs in fs_stat:
                # Grab the disk usage
                try:
                    fs_usage = psutil.disk_usage(fs.mountpoint)
                except OSError:
                    # Correct issue #346
                    # Disk is ejected during the command
                    continue
                fs_current = {
                    'device_name': fs.device,
                    'fs_type': fs.fstype,
                    'mnt_point': fs.mountpoint,
                    'size': fs_usage.total,
                    'used': fs_usage.used,
                    'free': fs_usage.free,
                    'percent': fs_usage.percent,
                    'key': self.get_key()}
                self.stats.append(fs_current)

        elif self.input_method == 'snmp':
            # Update stats using SNMP

            # SNMP bulk command to get all file system in one shot
            try:
                fs_stat = self.get_stats_snmp(snmp_oid=snmp_oid[self.short_system_name],
                                              bulk=True)
            except KeyError:
                fs_stat = self.get_stats_snmp(snmp_oid=snmp_oid['default'],
                                              bulk=True)

            # Loop over fs
            if self.short_system_name in ('windows', 'esxi'):
                # Windows or ESXi tips
                for fs in fs_stat:
                    # Memory stats are grabbed in the same OID table (ignore it)
                    if fs == 'Virtual Memory' or fs == 'Physical Memory' or fs == 'Real Memory':
                        continue
                    size = int(fs_stat[fs]['size']) * int(fs_stat[fs]['alloc_unit'])
                    used = int(fs_stat[fs]['used']) * int(fs_stat[fs]['alloc_unit'])
                    percent = float(used * 100 / size)
                    fs_current = {
                        'device_name': '',
                        'mnt_point': fs.partition(' ')[0],
                        'size': size,
                        'used': used,
                        'percent': percent,
                        'key': self.get_key()}
                    self.stats.append(fs_current)
            else:
                # Default behavior
                for fs in fs_stat:
                    fs_current = {
                        'device_name': fs_stat[fs]['device_name'],
                        'mnt_point': fs,
                        'size': int(fs_stat[fs]['size']) * 1024,
                        'used': int(fs_stat[fs]['used']) * 1024,
                        'percent': float(fs_stat[fs]['percent']),
                        'key': self.get_key()}
                    self.stats.append(fs_current)

        # Update the history list
        self.update_stats_history('mnt_point')

        # Update the view
        self.update_views()

        return self.stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        GlancesPlugin.update_views(self)

        # Add specifics informations
        # Alert
        for i in self.stats:
            self.views[i[self.get_key()]]['used']['decoration'] = self.get_alert(
                i['used'], maximum=i['size'], header=i['mnt_point'])

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or args.disable_fs:
            return ret

        # Max size for the fsname name
        if max_width is not None and max_width >= 23:
            # Interface size name = max_width - space for interfaces bitrate
            fsname_max_width = max_width - 14
        else:
            fsname_max_width = 9

        # Build the string message
        # Header
        msg = '{0:{width}}'.format('FILE SYS', width=fsname_max_width)
        ret.append(self.curse_add_line(msg, "TITLE"))
        if args.fs_free_space:
            msg = '{0:>7}'.format('Free')
        else:
            msg = '{0:>7}'.format('Used')
        ret.append(self.curse_add_line(msg))
        msg = '{0:>7}'.format('Total')
        ret.append(self.curse_add_line(msg))

        # Disk list (sorted by name)
        for i in sorted(self.stats, key=operator.itemgetter(self.get_key())):
            # New line
            ret.append(self.curse_new_line())
            if i['device_name'] == '' or i['device_name'] == 'none':
                mnt_point = i['mnt_point'][-fsname_max_width + 1:]
            elif len(i['mnt_point']) + len(i['device_name'].split('/')[-1]) <= fsname_max_width - 3:
                # If possible concatenate mode info... Glances touch inside :)
                mnt_point = i['mnt_point'] + \
                    ' (' + i['device_name'].split('/')[-1] + ')'
            elif len(i['mnt_point']) > fsname_max_width:
                # Cut mount point name if it is too long
                mnt_point = '_' + i['mnt_point'][-fsname_max_width + 1:]
            else:
                mnt_point = i['mnt_point']
            msg = '{0:{width}}'.format(mnt_point, width=fsname_max_width)
            ret.append(self.curse_add_line(msg))
            if args.fs_free_space:
                msg = '{0:>7}'.format(self.auto_unit(i['free']))
            else:
                msg = '{0:>7}'.format(self.auto_unit(i['used']))
            ret.append(self.curse_add_line(msg, self.get_views(item=i[self.get_key()],
                                                               key='used',
                                                               option='decoration')))
            msg = '{0:>7}'.format(self.auto_unit(i['size']))
            ret.append(self.curse_add_line(msg))

        return ret
