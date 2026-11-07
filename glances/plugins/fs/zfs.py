#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

# zfs_enable() and zfs_stats() (ARC stats) are used by the MEM plugin (see #3979).
# zfs_pools() and zfs_datasets() require OpenZFS >= 2.3 JSON output and are not
# consumed by any plugin yet.

import json
import os
import re
import subprocess  # nosec B404
from functools import lru_cache

from glances.logger import logger

# JSON output for the zfs/zpool commands is available since OpenZFS 2.3
ZFS_JSON_MIN_VERSION = (2, 3)
# Hard timeout to avoid blocking commands hanging the process
ZFS_COMMAND_TIMEOUT = 5


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


def _run_zfs_command(args, timeout=ZFS_COMMAND_TIMEOUT):
    """Run a zfs/zpool command and return its stdout, or None on failure."""
    try:
        # args is always a fixed list built from constants, never shell=True.
        result = subprocess.run(  # nosec B603
            args, capture_output=True, text=True, timeout=timeout
        )
    except Exception as e:
        logger.debug(f"Cannot run ZFS command {' '.join(args)}: {e}")
        return None
    if result.returncode != 0:
        logger.debug(f"ZFS command {' '.join(args)} failed: {result.stderr.strip()}")
        return None
    return result.stdout


def _zfs_version():
    """Return the installed ZFS version as a (major, minor) tuple, or None."""
    output = _run_zfs_command(['zfs', '--version'])
    if output is None:
        return None
    match = re.search(r'zfs-(\d+)\.(\d+)', output)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


@lru_cache(maxsize=1)
def zfs_json_supported():
    """Check if the installed ZFS version supports JSON output (>= 2.3)."""
    version = _zfs_version()
    return version is not None and version >= ZFS_JSON_MIN_VERSION


def _zfs_json(args):
    """Run a JSON zfs/zpool command and return the parsed output, or {}."""
    if not zfs_json_supported():
        return {}
    output = _run_zfs_command(args)
    if output is None:
        return {}
    try:
        return json.loads(output)
    except (TypeError, ValueError) as e:
        logger.debug(f"Cannot parse ZFS JSON output from {' '.join(args)}: {e}")
        return {}


def zfs_pools():
    """Get ZFS pools status, keyed by pool GUID.

    Return an empty dict if the installed ZFS version does not support
    JSON output (< 2.3) or if the command fails.
    """
    data = _zfs_json(['zpool', 'status', '-j', '--json-int', '--json-pool-key-guid'])
    return data.get('pools', {}) if isinstance(data, dict) else {}


def zfs_pools_list():
    """Get ZFS pools properties, keyed by pool GUID.

    Return an empty dict if the installed ZFS version does not support
    JSON output (< 2.3) or if the command fails.
    """
    data = _zfs_json(['zpool', 'list', '-j', '--json-int', '--json-pool-key-guid'])
    return data.get('pools', {}) if isinstance(data, dict) else {}


def zfs_datasets():
    """Get ZFS datasets stats, keyed by dataset name.

    Return an empty dict if the installed ZFS version does not support
    JSON output (< 2.3) or if the command fails.
    """
    data = _zfs_json(
        [
            'zfs',
            'list',
            '-j',
            '--json-int',
            '-t',
            'filesystem,volume',
            '-o',
            'name,type,used,available,referenced,mountpoint',
        ]
    )
    return data.get('datasets', {}) if isinstance(data, dict) else {}
