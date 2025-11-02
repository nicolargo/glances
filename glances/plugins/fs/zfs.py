#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

# For the moment, thoses functions are only used in the MEM plugin (see #3979)

import os

from glances.logger import logger


def zfs_enable(zfs_stats_path='/proc/spl/kstat/zfs'):
    """Check if ZFS is enabled on this system."""
    return os.path.isdir(zfs_stats_path)


def zfs_stats(zfs_stats_files=['/proc/spl/kstat/zfs/arcstats']):
    """Get ZFS stats from /proc/spl/kstat/zfs files."""
    stats = {}
    for zfs_stats_file in zfs_stats_files:
        try:
            with open(zfs_stats_file) as f:
                lines = f.readlines()
            namespace = os.path.basename(zfs_stats_file)
            for line in lines[2:]:  # Skip the first two header lines
                parts = line.split()
                stats[namespace + '.' + parts[0]] = int(parts[2])
        except Exception as e:
            logger.error(f"Error reading ZFS stats in {zfs_stats_file}: {e}")
    return stats
