#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""StdoutCsv interface class."""

import time

from glances.globals import printandflush


class GlancesStdoutCsv:
    """This class manages the StdoutCsv display."""

    separator = ','
    na = 'N/A'

    def __init__(self, config=None, args=None):
        # Init
        self.config = config
        self.args = args

        # Display the header only on the first line
        self.header = True

        # Remember, per plugin, the ordered list of list-item keys (e.g. network
        # interface names) captured when the header was built. Data rows are then
        # aligned to this fixed schema: absent items are filled with N/A and items
        # that appear after export start are omitted (they have no header column).
        self.list_keys = {}

        # Number of fields per list item for each plugin, captured at header time,
        # so a missing interface can be padded with the right number of N/A cells.
        self.header_field_counts = {}

        # Build the list of plugin and/or plugin.attribute to display
        self.plugins_list = self.build_list()

    def build_list(self):
        """Return a list of tuples taken from self.args.stdout

        :return: A list of tuples. Example -[(plugin, attribute), ... ]
        """
        ret = []
        for p in self.args.stdout_csv.split(','):
            if '.' in p:
                p, a = p.split('.')
            else:
                a = None
            ret.append((p, a))
        return ret

    def end(self):
        pass

    def build_header(self, plugin, attribute, stat):
        """Build and return the header line"""
        line = ''

        if attribute is not None:
            line += f'{plugin}.{attribute}{self.separator}'
        else:
            if isinstance(stat, dict):
                for k in stat:
                    line += f'{plugin}.{str(k)}{self.separator}'
            elif isinstance(stat, list):
                keys_order = []
                for i in stat:
                    if isinstance(i, dict) and 'key' in i:
                        keys_order.append(str(i[i['key']]))
                        for k in i:
                            line += '{}.{}.{}{}'.format(plugin, str(i[i['key']]), str(k), self.separator)
                # Lock the interface schema (ordered identities + their fields)
                self.list_keys[plugin] = keys_order
                for i in stat:
                    if isinstance(i, dict) and 'key' in i:
                        self.header_field_counts[plugin] = len(i)
                        break
            else:
                line += f'{plugin}{self.separator}'

        return line

    def build_data(self, plugin, attribute, stat):
        """Build and return the data line"""
        line = ''

        if attribute is not None:
            line += f'{str(stat.get(attribute, self.na))}{self.separator}'
        else:
            if isinstance(stat, dict):
                for v in stat.values():
                    line += f'{str(v)}{self.separator}'
            elif isinstance(stat, list):
                # Index current items by their identity value
                current = {}
                for i in stat:
                    if isinstance(i, dict) and 'key' in i:
                        ident = str(i[i['key']])
                        current[ident] = i
                # Emit one block per identity locked in at header time.
                # Absent identities are filled with N/A; identities that appeared
                # after the header was built are omitted (no column exists).
                for ident in self.list_keys.get(plugin, []):
                    if ident in current:
                        for v in current[ident].values():
                            line += f'{str(v)}{self.separator}'
                    else:
                        # Fill with N/A using the header's field count for this plugin.
                        n_fields = self.header_field_counts.get(plugin, 0)
                        line += (f'{self.na}{self.separator}') * n_fields
            else:
                line += f'{str(stat)}{self.separator}'

        return line

    def update(self, stats, duration=3, cs_status=None, return_to_browser=False):
        """Display stats to stdout.

        Refresh every duration second.
        """
        # Build the stats list
        line = ''
        for plugin, attribute in self.plugins_list:
            # Check if the plugin exist and is enable
            if plugin in stats.getPluginsList() and stats.get_plugin(plugin).is_enabled():
                stat = stats.get_plugin(plugin).get_export()
            else:
                continue

            # Build the line to display (header or data)
            if self.header:
                line += self.build_header(plugin, attribute, stat)
            else:
                line += self.build_data(plugin, attribute, stat)

        # Display the line (without the last 'separator')
        printandflush(line[:-1])

        # Display header one time
        self.header = False

        # Wait until next refresh
        if duration > 0:
            time.sleep(duration)
