# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Stdout interface class."""

import time

from glances.logger import logger
from glances.globals import printandflush


class GlancesStdout(object):

    """This class manages the Stdout display."""

    def __init__(self, config=None, args=None):
        # Init
        self.config = config
        self.args = args

        # Build the list of plugin and/or plugin.attribute to display
        self.plugins_list = self.build_list()

    def build_list(self):
        """Return a list of tuples taken from self.args.stdout

        :return: A list of tuples. Example -[(plugin, attribute), ... ]
        """
        ret = []
        for p in self.args.stdout.split(','):
            if '.' in p:
                p, a = p.split('.')
            else:
                a = None
            ret.append((p, a))
        return ret

    def end(self):
        pass

    def update(self, stats, duration=3):
        """Display stats to stdout.

        Refresh every duration second.
        """
        for plugin, attribute in self.plugins_list:
            # Check if the plugin exist and is enable
            if plugin in stats.getPluginsList() and stats.get_plugin(plugin).is_enabled():
                stat = stats.get_plugin(plugin).get_export()
            else:
                continue
            # Display stats
            if attribute is not None:
                # With attribute
                try:
                    printandflush("{}.{}: {}".format(plugin, attribute, stat[attribute]))
                except KeyError as err:
                    logger.error("Can not display stat {}.{} ({})".format(plugin, attribute, err))
            else:
                # Without attribute
                printandflush("{}: {}".format(plugin, stat))

        # Wait until next refresh
        if duration > 0:
            time.sleep(duration)
