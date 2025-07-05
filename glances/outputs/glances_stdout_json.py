#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Stdout interface class."""

import time

from glances.globals import printandflush


class GlancesStdoutJson:
    """This class manages the Stdout JSON display."""

    def __init__(self, config=None, args=None):
        # Init
        self.config = config
        self.args = args

        # Build the list of plugin to display
        self.plugins_list = self.build_list()

    def build_list(self):
        """Return a list of tuples taken from self.args.stdout_json

        :return: A list of tuples. Example -[(plugin, attribute), ... ]
        """
        return self.args.stdout_json.split(',')

    def end(self):
        pass

    def update(self, stats, duration=3, cs_status=None, return_to_browser=False):
        """Display stats in JSON format to stdout.

        Refresh every duration second.
        """
        all_in_json = '{'
        plugins_list_json = []
        for plugin in self.plugins_list:
            # Check if the plugin exist and is enable
            if plugin in stats.getPluginsList() and stats.get_plugin(plugin).is_enabled():
                plugins_list_json.append(f'"{plugin}": {stats.get_plugin(plugin).get_json().decode("utf-8")}')
            else:
                continue
        # Join all plugins in a single JSON object
        all_in_json += ', '.join(plugins_list_json)
        all_in_json += '}'

        # Display stats
        printandflush(all_in_json)

        # Wait until next refresh
        if duration > 0:
            time.sleep(duration)
