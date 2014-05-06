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

import psutil

from glances.plugins.glances_plugin import GlancesPlugin

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
fs_oid = { 'mnt_point': '1.3.6.1.4.1.2021.9.1.2',
           'device_name': '1.3.6.1.4.1.2021.9.1.3',
            'size': '1.3.6.1.4.1.2021.9.1.6',
            'used': '1.3.6.1.4.1.2021.9.1.8',
            # 'avail': '1.3.6.1.4.1.2021.9.1.7',
            'percent': '1.3.6.1.4.1.2021.9.1.9'}


class Plugin(GlancesPlugin):
    """
    Glances's File System (fs) Plugin

    stats is a list
    """

    def __init__(self):
        GlancesPlugin.__init__(self)

        # We want to display the stat in the curse interface
        self.display_curse = True
        # Set the message position
        # It is NOT the curse position but the Glances column/line
        # Enter -1 to right align
        self.column_curse = 0
        # Enter -1 to diplay bottom
        self.line_curse = 4

        # Init the stats
        self.reset()        

    def reset(self):
        """
        Reset/init the stats
        """
        self.stats = []

    def update(self, input='local'):
        """
        Update the FS stats using the input method
        Input method could be: local (mandatory) or snmp (optionnal)
        """

        # Reset the list
        self.reset()

        if input == 'local':
            # Update stats using the standard system lib

            # Grab the stats using the PsUtil disk_partitions
            # If 'all'=False return physical devices only (e.g. hard disks, cd-rom drives, USB keys)
            # and ignore all others (e.g. memory partitions such as /dev/shm)
            try:
                fs_stat = psutil.disk_partitions(all=False)
            except UnicodeDecodeError:
                return self.stats

            # Loop over fs
            for fs in range(len(fs_stat)):
                fs_current = {}
                fs_current['device_name'] = fs_stat[fs].device
                fs_current['fs_type'] = fs_stat[fs].fstype
                fs_current['mnt_point'] = fs_stat[fs].mountpoint
                # Grab the disk usage
                try:
                    fs_usage = psutil.disk_usage(fs_current['mnt_point'])
                except OSError:
                    # Correct issue #346
                    # Disk is ejected during the command
                    continue
                fs_current['size'] = fs_usage.total
                fs_current['used'] = fs_usage.used
                # fs_current['avail'] = fs_usage.free
                fs_current['percent'] = fs_usage.percent
                self.stats.append(fs_current)

        elif input == 'snmp':
            # Update stats using SNMP

            # Loop over disks
            diskIndex = 1
            while (diskIndex < 1024):
                # Add disk index to the fs OID
                snmp_oid = dict((k, v + '.' + str(diskIndex)) for (k, v) in fs_oid.items())
                fs_current = self.set_stats_snmp(snmp_oid=snmp_oid)
                if str(fs_current['mnt_point']) == '':
                    break
                # Size returned by SNMP is in kilobyte, convert it in byte
                fs_current['size'] = int(fs_current['size']) * 1024
                fs_current['used'] = int(fs_current['used']) * 1024
                # fs_current['avail'] = int(fs_current['avail'])                
                self.stats.append(fs_current)
                diskIndex += 1

        return self.stats

    def msg_curse(self, args=None):
        """
        Return the dict to display in the curse interface
        """
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if self.stats == [] or args.disable_fs:
            return ret

        # Build the string message
        # Header
        msg = "{0:9}".format(_("FILE SYS"))
        ret.append(self.curse_add_line(msg, "TITLE"))
        msg = "{0:>7}".format(_("Used"))
        ret.append(self.curse_add_line(msg))
        msg = "{0:>7}".format(_("Total"))
        ret.append(self.curse_add_line(msg))

        # Disk list (sorted by name)
        for i in sorted(self.stats, key=lambda fs: fs['mnt_point']):
            # New line
            ret.append(self.curse_new_line())
            if (len(i['mnt_point']) + len(i['device_name'].split('/')[-1])) <= 6:
                # If possible concatenate mode info... Glances touch inside :)
                mnt_point = i['mnt_point'] + ' (' + i['device_name'].split('/')[-1] + ')'
            elif len(i['mnt_point']) > 9:
                # Cut mount point name if it is too long
                mnt_point = '_' + i['mnt_point'][-8:]
            else:
                mnt_point = i['mnt_point']
            msg = "{0:9}".format(mnt_point)
            ret.append(self.curse_add_line(msg))
            msg = "{0:>7}".format(self.auto_unit(i['used']))
            ret.append(self.curse_add_line(msg, self.get_alert(i['used'], max=i['size'])))
            msg = "{0:>7}".format(self.auto_unit(i['size']))
            ret.append(self.curse_add_line(msg))

        return ret
