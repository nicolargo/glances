# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2021 Nicolargo <nicolas@nicolargo.com>
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

"""Fields description interface class."""

from pprint import pformat
import json
import time

from glances.logger import logger
from glances.compat import iteritems

API_URL = "http://localhost:61208/api/3"

APIDOC_HEADER = """\
.. _api:

API (Restfull/JSON) documentation
=================================

The Glances Restfull/API server could be ran using the following command line:

.. code-block:: bash

    # glances -w --disable-webui

Note: Change request URL api/3 by api/2 if you use Glances 2.x.
"""


def indent_stat(stat, indent='    '):
    # Indent stats to pretty print it
    if isinstance(stat, list) and len(stat) > 1 and isinstance(stat[0], dict):
        # Only display two first items
        return indent + pformat(stat[0:2]).replace('\n', '\n' + indent)
    else:
        return indent + pformat(stat).replace('\n', '\n' + indent)


def print_plugins_list(stat):
    sub_title = 'GET plugins list'
    print(sub_title)
    print('-' * len(sub_title))
    print('')
    print('Get the plugins list::')
    print('')
    print('    # curl {}/pluginslist'.format(API_URL))
    print(indent_stat(stat))
    print('')


def print_plugin_export(plugin, stat_export):
    sub_title = 'GET {}'.format(plugin)
    print(sub_title)
    print('-' * len(sub_title))
    print('')

    print('Get plugin stats::')
    print('')
    print('    # curl {}/{}'.format(API_URL, plugin))
    print(indent_stat(stat_export))
    print('')


def print_plugin_description(plugin, stat):
    if stat.fields_description:
        # For each plugins with a description
        print('Fields descriptions:')
        print('')
        for field, description in iteritems(stat.fields_description):
            print('* **{}**: {} (unit is *{}*)'.format(field,
                    description['description'][:-1] if description['description'].endswith('.') else description['description'],
                    description['unit']))
        print('')
    else:
        logger.error('No fields_description variable defined for plugin {}'.format(plugin))


def print_plugin_item_value(plugin, stat, stat_export):
    item = None
    value = None
    if isinstance(stat_export, dict):
        item = list(stat_export.keys())[0]
        value = None
    elif isinstance(stat_export, list) and len(stat_export) > 0 and isinstance(stat_export[0], dict):
        if 'key' in stat_export[0]:
            item = stat_export[0]['key']
        else:
            item = list(stat_export[0].keys())[0]
    if item and stat.get_stats_item(item):
        stat_item = json.loads(stat.get_stats_item(item))
        if isinstance(stat_item[item], list):
            value = stat_item[item][0]
        else:
            value = stat_item[item]
        print('Get a specific field::')
        print('')
        print('    # curl {}/{}/{}'.format(API_URL, plugin, item))
        print(indent_stat(stat_item))
        print('')
    if item and value and stat.get_stats_value(item, value):
        print('Get a specific item when field matchs the given value::')
        print('')
        print('    # curl {}/{}/{}/{}'.format(API_URL, plugin, item, value))
        print(indent_stat(json.loads(stat.get_stats_value(item, value))))
        print('')


def print_all():
    sub_title = 'GET all stats'
    print(sub_title)
    print('-' * len(sub_title))
    print('')
    print('Get all Glances stats::')
    print('')
    print('    # curl {}/all'.format(API_URL))
    print('    Return a very big dictionnary (avoid using this request, performances will be poor)...')
    print('')


def print_history(stats):
    time.sleep(1)
    stats.update()
    time.sleep(1)
    stats.update()
    sub_title = 'GET stats history'
    print(sub_title)
    print('-' * len(sub_title))
    print('')
    print('History of a plugin::')
    print('')
    print('    # curl {}/cpu/history'.format(API_URL))
    print(indent_stat(json.loads(stats.get_plugin('cpu').get_stats_history(nb=3))))
    print('')
    print('Limit history to last 2 values::')
    print('')
    print('    # curl {}/cpu/history/2'.format(API_URL))
    print(indent_stat(json.loads(stats.get_plugin('cpu').get_stats_history(nb=2))))
    print('')
    print('History for a specific field::')
    print('')
    print('    # curl {}/cpu/system/history'.format(API_URL))
    print(indent_stat(json.loads(stats.get_plugin('cpu').get_stats_history('system'))))
    print('')
    print('Limit history for a specific field to last 2 values::')
    print('')
    print('    # curl {}/cpu/system/history'.format(API_URL))
    print(indent_stat(json.loads(stats.get_plugin('cpu').get_stats_history('system', nb=2))))
    print('')


def print_limits(stats):
    sub_title = 'GET limits (used for thresholds)'
    print(sub_title)
    print('-' * len(sub_title))
    print('')
    print('All limits/thresholds::')
    print('')
    print('    # curl {}/all/limits'.format(API_URL))
    print(indent_stat(stats.getAllLimitsAsDict()))
    print('')
    print('Limits/thresholds for the cpu plugin::')
    print('')
    print('    # curl {}/cpu/limits'.format(API_URL))
    print(indent_stat(stats.get_plugin('cpu').limits))
    print('')


class GlancesStdoutApiDoc(object):

    """
    This class manages the fields description display.
    """

    def __init__(self, config=None, args=None):
        # Init
        self.config = config
        self.args = args

    def end(self):
        pass

    def update(self,
               stats,
               duration=1):
        """Display issue
        """

        # Display header
        print(APIDOC_HEADER)

        # Display plugins list
        print_plugins_list(sorted(stats._plugins))

        # Loop over plugins
        for plugin in sorted(stats._plugins):
            stat = stats.get_plugin(plugin)
            stat_export = stat.get_export()
            if stat_export is None or stat_export == [] or stat_export == {}:
                continue
            print_plugin_export(plugin, stat_export)
            print_plugin_description(plugin, stat)
            print_plugin_item_value(plugin, stat, stat_export)

        # Get all stats
        print_all()

        # History
        print_history(stats)

        # Limits
        print_limits(stats)

        # Return True to exit directly (no refresh)
        return True
