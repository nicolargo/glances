#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Virtual memory plugin."""

import psutil

from glances.plugins.plugin.model import GlancesPluginModel

# Fields description
fields_description = {
    'total': {'description': 'Total physical memory available.', 'unit': 'bytes', 'min_symbol': 'K'},
    'available': {
        'description': 'The actual amount of available memory that can be given instantly \
to processes that request more memory in bytes; this is calculated by summing \
different memory values depending on the platform (e.g. free + buffers + cached on Linux) \
and it is supposed to be used to monitor actual memory usage in a cross platform fashion.',
        'unit': 'bytes',
        'min_symbol': 'K',
    },
    'percent': {
        'description': 'The percentage usage calculated as (total - available) / total * 100.',
        'unit': 'percent',
    },
    'used': {
        'description': 'Memory used, calculated differently depending on the platform and \
designed for informational purposes only.',
        'unit': 'bytes',
        'min_symbol': 'K',
    },
    'free': {
        'description': 'Memory not being used at all (zeroed) that is readily available; \
note that this doesn\'t reflect the actual memory available (use \'available\' instead).',
        'unit': 'bytes',
        'min_symbol': 'K',
    },
    'active': {
        'description': '*(UNIX)*: memory currently in use or very recently used, and so it is in RAM.',
        'unit': 'bytes',
        'min_symbol': 'K',
    },
    'inactive': {
        'description': '*(UNIX)*: memory that is marked as not used.',
        'unit': 'bytes',
        'min_symbol': 'K',
        'short_name': 'inacti',
    },
    'buffers': {
        'description': '*(Linux, BSD)*: cache for things like file system metadata.',
        'unit': 'bytes',
        'min_symbol': 'K',
        'short_name': 'buffer',
    },
    'cached': {'description': '*(Linux, BSD)*: cache for various things.', 'unit': 'bytes', 'min_symbol': 'K'},
    'wired': {
        'description': '*(BSD, macOS)*: memory that is marked to always stay in RAM. It is never moved to disk.',
        'unit': 'bytes',
        'min_symbol': 'K',
    },
    'shared': {
        'description': '*(BSD)*: memory that may be simultaneously accessed by multiple processes.',
        'unit': 'bytes',
        'min_symbol': 'K',
    },
}

# SNMP OID
# Total RAM in machine: .1.3.6.1.4.1.2021.4.5.0
# Total RAM used: .1.3.6.1.4.1.2021.4.6.0
# Total RAM Free: .1.3.6.1.4.1.2021.4.11.0
# Total RAM Shared: .1.3.6.1.4.1.2021.4.13.0
# Total RAM Buffered: .1.3.6.1.4.1.2021.4.14.0
# Total Cached Memory: .1.3.6.1.4.1.2021.4.15.0
# Note: For Windows, stats are in the FS table
snmp_oid = {
    'default': {
        'total': '1.3.6.1.4.1.2021.4.5.0',
        'free': '1.3.6.1.4.1.2021.4.11.0',
        'shared': '1.3.6.1.4.1.2021.4.13.0',
        'buffers': '1.3.6.1.4.1.2021.4.14.0',
        'cached': '1.3.6.1.4.1.2021.4.15.0',
    },
    'windows': {
        'mnt_point': '1.3.6.1.2.1.25.2.3.1.3',
        'alloc_unit': '1.3.6.1.2.1.25.2.3.1.4',
        'size': '1.3.6.1.2.1.25.2.3.1.5',
        'used': '1.3.6.1.2.1.25.2.3.1.6',
    },
    'esxi': {
        'mnt_point': '1.3.6.1.2.1.25.2.3.1.3',
        'alloc_unit': '1.3.6.1.2.1.25.2.3.1.4',
        'size': '1.3.6.1.2.1.25.2.3.1.5',
        'used': '1.3.6.1.2.1.25.2.3.1.6',
    },
}

# Define the history items list
# All items in this list will be historised if the --enable-history tag is set
items_history_list = [{'name': 'percent', 'description': 'RAM memory usage', 'y_unit': '%'}]


class PluginModel(GlancesPluginModel):
    """Glances' memory plugin.

    stats is a dict
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(
            args=args, config=config, items_history_list=items_history_list, fields_description=fields_description
        )

        # We want to display the stat in the curse interface
        self.display_curse = True

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update RAM memory stats using the input method."""
        # Init new stats
        stats = self.get_init_value()

        if self.input_method == 'local':
            # Update stats using the standard system lib
            # Grab MEM using the psutil virtual_memory method
            vm_stats = psutil.virtual_memory()

            # Get all the memory stats (copy/paste of the psutil documentation)
            # total: total physical memory available.
            # available: the actual amount of available memory that can be given instantly
            # to processes that request more memory in bytes; this is calculated by summing
            # different memory values depending on the platform (e.g. free + buffers + cached on Linux)
            # and it is supposed to be used to monitor actual memory usage in a cross platform fashion.
            # percent: the percentage usage calculated as (total - available) / total * 100.
            # used: memory used, calculated differently depending on the platform and designed for informational
            # purposes only.
            # free: memory not being used at all (zeroed) that is readily available; note that this doesn't
            # reflect the actual memory available (use ‘available’ instead).
            # Platform-specific fields:
            # active: (UNIX): memory currently in use or very recently used, and so it is in RAM.
            # inactive: (UNIX): memory that is marked as not used.
            # buffers: (Linux, BSD): cache for things like file system metadata.
            # cached: (Linux, BSD): cache for various things.
            # wired: (BSD, macOS): memory that is marked to always stay in RAM. It is never moved to disk.
            # shared: (BSD): memory that may be simultaneously accessed by multiple processes.
            self.reset()
            for mem in [
                'total',
                'available',
                'percent',
                'used',
                'free',
                'active',
                'inactive',
                'buffers',
                'cached',
                'wired',
                'shared',
            ]:
                if hasattr(vm_stats, mem):
                    stats[mem] = getattr(vm_stats, mem)

            # Use the 'free'/htop calculation
            # free=available+buffer+cached
            stats['free'] = stats['available']
            if hasattr(stats, 'buffers'):
                stats['free'] += stats['buffers']
            if hasattr(stats, 'cached'):
                stats['free'] += stats['cached']
            # used=total-free
            stats['used'] = stats['total'] - stats['free']
        elif self.input_method == 'snmp':
            # Update stats using SNMP
            if self.short_system_name in ('windows', 'esxi'):
                # Mem stats for Windows|Vmware Esxi are stored in the FS table
                try:
                    fs_stat = self.get_stats_snmp(snmp_oid=snmp_oid[self.short_system_name], bulk=True)
                except KeyError:
                    self.reset()
                else:
                    for fs in fs_stat:
                        # The Physical Memory (Windows) or Real Memory (VMware)
                        # gives statistics on RAM usage and availability.
                        if fs in ('Physical Memory', 'Real Memory'):
                            stats['total'] = int(fs_stat[fs]['size']) * int(fs_stat[fs]['alloc_unit'])
                            stats['used'] = int(fs_stat[fs]['used']) * int(fs_stat[fs]['alloc_unit'])
                            stats['percent'] = float(stats['used'] * 100 / stats['total'])
                            stats['free'] = stats['total'] - stats['used']
                            break
            else:
                # Default behavior for others OS
                stats = self.get_stats_snmp(snmp_oid=snmp_oid['default'])

                if stats['total'] == '':
                    self.reset()
                    return self.stats

                for k in stats:
                    stats[k] = int(stats[k]) * 1024

                # used=total-free
                stats['used'] = stats['total'] - stats['free']

                # percent: the percentage usage calculated as (total - available) / total * 100.
                stats['percent'] = float((stats['total'] - stats['free']) / stats['total'] * 100)

        # Update the stats
        self.stats = stats

        return self.stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super().update_views()

        # Add specifics information
        # Alert and log
        self.views['percent']['decoration'] = self.get_alert_log(self.stats['used'], maximum=self.stats['total'])
        # Optional
        for key in ['active', 'inactive', 'buffers', 'cached']:
            if key in self.stats:
                self.views[key]['optional'] = True

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and plugin not disabled
        if not self.stats or self.is_disabled():
            return ret

        # First line
        # total% + active
        msg = '{}'.format('MEM')
        ret.append(self.curse_add_line(msg, "TITLE"))
        msg = ' {:2}'.format(self.trend_msg(self.get_trend('percent')))
        ret.append(self.curse_add_line(msg))
        # Percent memory usage
        msg = '{:>7.1%}'.format(self.stats['percent'] / 100)
        ret.append(self.curse_add_line(msg, self.get_views(key='percent', option='decoration')))
        # Active memory usage
        ret.extend(self.curse_add_stat('active', width=16, header='  '))

        # Second line
        # total + inactive
        ret.append(self.curse_new_line())
        # Total memory usage
        ret.extend(self.curse_add_stat('total', width=15))
        # Inactive memory usage
        ret.extend(self.curse_add_stat('inactive', width=16, header='  '))

        # Third line
        # used + buffers
        ret.append(self.curse_new_line())
        # Used memory usage
        ret.extend(self.curse_add_stat('used', width=15))
        # Buffers memory usage
        ret.extend(self.curse_add_stat('buffers', width=16, header='  '))

        # Fourth line
        # free + cached
        ret.append(self.curse_new_line())
        # Free memory usage
        ret.extend(self.curse_add_stat('free', width=15))
        # Cached memory usage
        ret.extend(self.curse_add_stat('cached', width=16, header='  '))

        return ret
