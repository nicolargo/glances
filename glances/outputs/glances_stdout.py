#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Stdout interface class."""

import time

from glances.globals import printandflush
from glances.logger import logger


class GlancesStdout:
    """This class manages the Stdout display."""

    def __init__(self, config=None, args=None):
        # Init
        self.config = config
        self.args = args

        # Build the list of plugin and/or plugin.attribute to display
        self.plugins_list = self.build_list()

    def build_list(self):
        """Return a list of tuples taken from self.args.stdout

        :return: A list of tuples. Example [(plugin, key, attribute), ... ]
        """
        ret = []
        for p in self.args.stdout.split(','):
            pka = p.split('.')
            if len(pka) == 1:
                # Only plugin name is provided
                new = (pka[0], None, None)
            elif len(pka) == 2:
                # Plugin name and attribute is provided
                new = (pka[0], None, pka[1])
            elif len(pka) == 3:
                # Plugin name, key and attribute are provided
                new = (pka[0], pka[1], pka[2])
            ret.append(new)
        return ret

    def end(self):
        pass

    def update(self, stats, duration=3):
        """Display stats to stdout.

        Refresh every duration second.
        """
        for plugin, key, attribute in self.plugins_list:
            # Check if the plugin exist and is enable
            if plugin in stats.getPluginsList() and stats.get_plugin(plugin).is_enabled():
                stat = stats.get_plugin(plugin).get_export()
            else:
                continue
            # Display stats
            if attribute is not None:
                # With attribute
                if isinstance(stat, dict):
                    try:
                        printandflush(f"{plugin}.{attribute}: {stat[attribute]}")
                    except KeyError as err:
                        logger.error(f"Can not display stat {plugin}.{attribute} ({err})")
                elif isinstance(stat, list):
                    for i in stat:
                        if key is None:
                            i_key = i[i['key']]
                        elif str(key) == str(i[i['key']]):
                            i_key = key
                        else:
                            continue
                        try:
                            printandflush(f"{plugin}.{i_key}.{attribute}: {i[attribute]}")
                        except KeyError as err:
                            logger.error(f"Can not display stat {plugin}.{attribute} ({err})")
            else:
                # Without attribute
                printandflush(f"{plugin}: {stat}")

        # Wait until next refresh
        if duration > 0:
            time.sleep(duration)
