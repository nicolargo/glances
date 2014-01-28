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

from psutil import disk_partitions, disk_usage
from glances_plugin import GlancesPlugin


class Plugin(GlancesPlugin):
    """
    Glances's File System (fs) Plugin

    stats is a list
    """

    def __init__(self):
        GlancesPlugin.__init__(self)

        # Init the FS class
        self.glancesgrabfs = glancesGrabFs()


    def update(self):
        """
        Update  stats
        """

        self.stats = self.glancesgrabfs.get()


    def get_stats(self):
        # Return the stats object for the RPC API
        # !!! Sort it by mount name (why do it here ? Better in client side ?)
        self.stats = sorted(self.stats, key=lambda network: network['mnt_point'])
        return GlancesPlugin.get_stats(self)


class glancesGrabFs:
    """
    Get FS stats
    """

    def __init__(self):
        """
        Init FS stats
        """
        # Ignore the following FS name
        self.ignore_fsname = ('', 'cgroup', 'fusectl', 'gvfs-fuse-daemon',
                              'gvfsd-fuse', 'none')

        # Ignore the following FS type
        self.ignore_fstype = ('autofs', 'binfmt_misc', 'configfs', 'debugfs',
                              'devfs', 'devpts', 'devtmpfs', 'hugetlbfs',
                              'iso9660', 'linprocfs', 'mqueue', 'none',
                              'proc', 'procfs', 'pstore', 'rootfs',
                              'securityfs', 'sysfs', 'usbfs')

        # ignore FS by mount point
        self.ignore_mntpoint = ('', '/dev/shm', '/lib/init/rw', '/sys/fs/cgroup')

    def __update__(self):
        """
        Update the stats
        """
        # Reset the list
        self.fs_list = []

        # Open the current mounted FS
        fs_stat = disk_partitions(all=True)
        for fs in range(len(fs_stat)):
            fs_current = {}
            fs_current['device_name'] = fs_stat[fs].device
            if fs_current['device_name'] in self.ignore_fsname:
                continue
            fs_current['fs_type'] = fs_stat[fs].fstype
            if fs_current['fs_type'] in self.ignore_fstype:
                continue
            fs_current['mnt_point'] = fs_stat[fs].mountpoint
            if fs_current['mnt_point'] in self.ignore_mntpoint:
                continue
            try:
                fs_usage = disk_usage(fs_current['mnt_point'])
            except Exception:
                continue
            fs_current['size'] = fs_usage.total
            fs_current['used'] = fs_usage.used
            fs_current['avail'] = fs_usage.free
            self.fs_list.append(fs_current)

    def get(self):
        self.__update__()
        return self.fs_list
