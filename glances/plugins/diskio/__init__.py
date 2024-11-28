#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Disk I/O plugin."""

import psutil

from glances.globals import nativestr
from glances.logger import logger
from glances.plugins.plugin.model import GlancesPluginModel

# Fields description
# description: human readable description
# short_name: shortname to use un UI
# unit: unit type
# rate: if True then compute and add *_gauge and *_rate_per_is fields
# min_symbol: Auto unit should be used if value > than 1 'X' (K, M, G)...
fields_description = {
    'disk_name': {'description': 'Disk name.'},
    'read_count': {
        'description': 'Number of reads.',
        'rate': True,
        'unit': 'number',
    },
    'write_count': {
        'description': 'Number of writes.',
        'rate': True,
        'unit': 'number',
    },
    'read_bytes': {
        'description': 'Number of bytes read.',
        'rate': True,
        'unit': 'byte',
    },
    'write_bytes': {
        'description': 'Number of bytes written.',
        'rate': True,
        'unit': 'byte',
    },
}

# Define the history items list
items_history_list = [
    {'name': 'read_bytes_rate_per_sec', 'description': 'Bytes read per second', 'y_unit': 'B/s'},
    {'name': 'write_bytes_rate_per_sec', 'description': 'Bytes write per second', 'y_unit': 'B/s'},
]


class PluginModel(GlancesPluginModel):
    """Glances disks I/O plugin.

    stats is a list
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(
            args=args,
            config=config,
            items_history_list=items_history_list,
            stats_init_value=[],
            fields_description=fields_description,
        )

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Hide stats if it has never been != 0
        if config is not None:
            self.hide_zero = config.get_bool_value(self.plugin_name, 'hide_zero', default=False)
            self.hide_threshold_bytes = config.get_int_value(self.plugin_name, 'hide_threshold_bytes', default=0)
        else:
            self.hide_zero = False
            self.hide_threshold_bytes = 0
        self.hide_zero_fields = ['read_bytes_rate_per_sec', 'write_bytes_rate_per_sec']

        # Force a first update because we need two updates to have the first stat
        self.update()
        self.refresh_timer.set(0)

    def get_key(self):
        """Return the key of the list."""
        return 'disk_name'

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update disk I/O stats using the input method."""
        # Update the stats
        if self.input_method == 'local':
            stats = self.update_local()
        else:
            stats = self.get_init_value()

        # Update the stats
        self.stats = stats

        return self.stats

    @GlancesPluginModel._manage_rate
    def update_local(self):
        stats = self.get_init_value()

        try:
            diskio = psutil.disk_io_counters(perdisk=True)
        except Exception:
            return stats

        for disk_name, disk_stat in diskio.items():
            # By default, RamFS is not displayed (issue #714)
            if self.args is not None and not self.args.diskio_show_ramfs and disk_name.startswith('ram'):
                continue

            # Shall we display the stats ?
            if not self.is_display(disk_name):
                continue

            # Filter stats to keep only the fields we want (define in fields_description)
            # It will also convert psutil objects to a standard Python dict
            stat = self.filter_stats(disk_stat)

            # Add the key
            stat['key'] = self.get_key()

            # Add disk name
            stat['disk_name'] = disk_name

            # Add alias if exist (define in the configuration file)
            if self.has_alias(disk_name) is not None:
                stat['alias'] = self.has_alias(disk_name)

            stats.append(stat)

        return stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super().update_views()

        # Add specifics information
        # Alert
        for i in self.get_raw():
            # Skip alert if no timespan to measure
            if 'read_bytes_rate_per_sec' not in i or 'write_bytes_rate_per_sec' not in i:
                continue

            disk_real_name = i['disk_name']
            alert_rx = self.get_alert(i['read_bytes'], header=disk_real_name + '_rx')
            alert_tx = self.get_alert(i['write_bytes'], header=disk_real_name + '_tx')
            self.views[i[self.get_key()]]['read_bytes']['decoration'] = alert_rx
            self.views[i[self.get_key()]]['read_bytes_rate_per_sec']['decoration'] = alert_rx
            self.views[i[self.get_key()]]['write_bytes']['decoration'] = alert_tx
            self.views[i[self.get_key()]]['write_bytes_rate_per_sec']['decoration'] = alert_tx

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or self.is_disabled():
            return ret

        # Max size for the interface name
        if max_width:
            name_max_width = max_width - 13
        else:
            # No max_width defined, return an empty curse message
            logger.debug(f"No max_width defined for the {self.plugin_name} plugin, it will not be displayed.")
            return ret

        # Header
        msg = '{:{width}}'.format('DISK I/O', width=name_max_width)
        ret.append(self.curse_add_line(msg, "TITLE"))
        if args.diskio_iops:
            msg = '{:>8}'.format('IOR/s')
            ret.append(self.curse_add_line(msg))
            msg = '{:>7}'.format('IOW/s')
            ret.append(self.curse_add_line(msg))
        else:
            msg = '{:>8}'.format('R/s')
            ret.append(self.curse_add_line(msg))
            msg = '{:>7}'.format('W/s')
            ret.append(self.curse_add_line(msg))
        # Disk list (sorted by name)
        for i in self.sorted_stats():
            # Hide stats if never be different from 0 (issue #1787)
            if all(self.get_views(item=i[self.get_key()], key=f, option='hidden') for f in self.hide_zero_fields):
                continue
            # Is there an alias for the disk name ?
            disk_name = i['alias'] if 'alias' in i else i['disk_name']
            # New line
            ret.append(self.curse_new_line())
            if len(disk_name) > name_max_width:
                # Cut disk name if it is too long
                disk_name = disk_name[:name_max_width] + '_'
            msg = '{:{width}}'.format(nativestr(disk_name), width=name_max_width + 1)
            ret.append(self.curse_add_line(msg))
            if args.diskio_iops:
                # count
                txps = self.auto_unit(i.get('read_count_rate_per_sec', None))
                rxps = self.auto_unit(i.get('write_count_rate_per_sec', None))
                msg = f'{txps:>7}'
                ret.append(
                    self.curse_add_line(
                        msg, self.get_views(item=i[self.get_key()], key='read_count', option='decoration')
                    )
                )
                msg = f'{rxps:>7}'
                ret.append(
                    self.curse_add_line(
                        msg, self.get_views(item=i[self.get_key()], key='write_count', option='decoration')
                    )
                )
            else:
                # Bitrate
                txps = self.auto_unit(i.get('read_bytes_rate_per_sec', None))
                rxps = self.auto_unit(i.get('write_bytes_rate_per_sec', None))
                msg = f'{txps:>7}'
                ret.append(
                    self.curse_add_line(
                        msg, self.get_views(item=i[self.get_key()], key='read_bytes', option='decoration')
                    )
                )
                msg = f'{rxps:>7}'
                ret.append(
                    self.curse_add_line(
                        msg, self.get_views(item=i[self.get_key()], key='write_bytes', option='decoration')
                    )
                )

        return ret
