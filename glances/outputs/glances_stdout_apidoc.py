#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Fields description interface class."""

import json
import time
from pprint import pformat

from glances import __apiversion__
from glances.globals import iteritems
from glances.logger import logger

API_URL = f"http://localhost:61208/api/{__apiversion__}"

APIDOC_HEADER = f"""\
.. _api:

API (Restfull/JSON) documentation
=================================

This documentation describes the Glances API version {__apiversion__} (Restfull/JSON) interface.

For Glances version 3, please have a look on:
``https://github.com/nicolargo/glances/blob/support/glancesv3/docs/api.rst``

Run the Glances API server
--------------------------

The Glances Restfull/API server could be ran using the following command line:

.. code-block:: bash

    # glances -w --disable-webui

It is also ran automatically when Glances is started in Web server mode (-w).

If you want to enable the Glances Central Browser, use:

.. code-block:: bash

    # glances -w --browser --disable-webui

API URL
-------

The default root API URL is ``http://localhost:61208/api/{__apiversion__}``.

The bind address and port could be changed using the ``--bind`` and ``--port`` command line options.

It is also possible to define an URL prefix using the ``url_prefix`` option from the [outputs] section
of the Glances configuration file.

Note: The url_prefix should always end with a slash (``/``).

For example:

.. code-block:: ini
    [outputs]
    url_prefix = /glances/

will change the root API URL to ``http://localhost:61208/glances/api/{__apiversion__}`` and the Web UI URL to
``http://localhost:61208/glances/``

API documentation URL
---------------------

The API documentation is embeded in the server and available at the following URL:
``http://localhost:61208/docs#/``.

WebUI refresh
-------------

It is possible to change the Web UI refresh rate (default is 2 seconds) using the following option in the URL:
``http://localhost:61208/?refresh=5``

"""


def indent_stat(stat, indent='    '):
    # Indent stats to pretty print it
    if isinstance(stat, list) and len(stat) > 1 and isinstance(stat[0], dict):
        # Only display two first items
        return indent + pformat(stat[0:2]).replace('\n', '\n' + indent).replace("'", '"')
    return indent + pformat(stat).replace('\n', '\n' + indent).replace("'", '"')


def print_api_status():
    sub_title = 'GET API status'
    print(sub_title)
    print('-' * len(sub_title))
    print('')
    print('This entry point should be used to check the API status.')
    print('It will the Glances version and a 200 return code if everything is OK.')
    print('')
    print('Get the Rest API status::')
    print('')
    print(f'    # curl -I {API_URL}/status')
    print(indent_stat('HTTP/1.0 200 OK'))
    print('')


def print_plugins_list(stat):
    sub_title = 'GET plugins list'
    print(sub_title)
    print('-' * len(sub_title))
    print('')
    print('Get the plugins list::')
    print('')
    print(f'    # curl {API_URL}/pluginslist')
    print(indent_stat(stat))
    print('')


def print_plugin_stats(plugin, stat):
    sub_title = f'GET {plugin}'
    print(sub_title)
    print('-' * len(sub_title))
    print('')

    print('Get plugin stats::')
    print('')
    print(f'    # curl {API_URL}/{plugin}')
    print(indent_stat(json.loads(stat.get_stats())))
    print('')


def print_plugin_description(plugin, stat):
    if stat.fields_description:
        # For each plugins with a description
        print('Fields descriptions:')
        print('')
        time_since_update = False
        for field, description in iteritems(stat.fields_description):
            print(
                '* **{}**: {} (unit is *{}*)'.format(
                    field,
                    (
                        description['description'][:-1]
                        if description['description'].endswith('.')
                        else description['description']
                    ),
                    description['unit'] if 'unit' in description else 'None',
                )
            )
            if 'rate' in description and description['rate']:
                time_since_update = True
                print(
                    '* **{}**: {} (unit is *{}* per second)'.format(
                        field + '_rate_per_sec',
                        (
                            description['description'][:-1]
                            if description['description'].endswith('.')
                            else description['description']
                        )
                        + ' per second',
                        description['unit'] if 'unit' in description else 'None',
                    )
                )
                print(
                    '* **{}**: {} (unit is *{}*)'.format(
                        field + '_gauge',
                        (
                            description['description'][:-1]
                            if description['description'].endswith('.')
                            else description['description']
                        )
                        + ' (cumulative)',
                        description['unit'] if 'unit' in description else 'None',
                    )
                )

        if time_since_update:
            print(
                '* **{}**: {} (unit is *{}*)'.format(
                    'time_since_update', 'Number of seconds since last update', 'seconds'
                )
            )

        print('')
    else:
        logger.error(f'No fields_description variable defined for plugin {plugin}')


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
        print(f'    # curl {API_URL}/{plugin}/{item}')
        print(indent_stat(stat_item))
        print('')
    if item and value and stat.get_stats_value(item, value):
        print('Get a specific item when field matches the given value::')
        print('')
        print(f'    # curl {API_URL}/{plugin}/{item}/value/{value}')
        print(indent_stat(json.loads(stat.get_stats_value(item, value))))
        print('')


def print_all():
    sub_title = 'GET all stats'
    print(sub_title)
    print('-' * len(sub_title))
    print('')
    print('Get all Glances stats::')
    print('')
    print(f'    # curl {API_URL}/all')
    print('    Return a very big dictionary (avoid using this request, performances will be poor)...')
    print('')


def print_top(stats):
    time.sleep(1)
    stats.update()
    sub_title = 'GET top n items of a specific plugin'
    print(sub_title)
    print('-' * len(sub_title))
    print('')
    print('Get top 2 processes of the processlist plugin::')
    print('')
    print(f'    # curl {API_URL}/processlist/top/2')
    print(indent_stat(stats.get_plugin('processlist').get_export()[:2]))
    print('')
    print('Note: Only work for plugin with a list of items')
    print('')


def print_fields_info(stats):
    sub_title = 'GET item description'
    print(sub_title)
    print('-' * len(sub_title))
    print('Get item description (human readable) for a specific plugin/item::')
    print('')
    print(f'    # curl {API_URL}/diskio/read_bytes/description')
    print(indent_stat(stats.get_plugin('diskio').get_item_info('read_bytes', 'description')))
    print('')
    print('Note: the description is defined in the fields_description variable of the plugin.')
    print('')
    sub_title = 'GET item unit'
    print(sub_title)
    print('-' * len(sub_title))
    print('Get item unit for a specific plugin/item::')
    print('')
    print(f'    # curl {API_URL}/diskio/read_bytes/unit')
    print(indent_stat(stats.get_plugin('diskio').get_item_info('read_bytes', 'unit')))
    print('')
    print('Note: the description is defined in the fields_description variable of the plugin.')
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
    print(f'    # curl {API_URL}/cpu/history')
    print(indent_stat(json.loads(stats.get_plugin('cpu').get_stats_history(nb=3))))
    print('')
    print('Limit history to last 2 values::')
    print('')
    print(f'    # curl {API_URL}/cpu/history/2')
    print(indent_stat(json.loads(stats.get_plugin('cpu').get_stats_history(nb=2))))
    print('')
    print('History for a specific field::')
    print('')
    print(f'    # curl {API_URL}/cpu/system/history')
    print(indent_stat(json.loads(stats.get_plugin('cpu').get_stats_history('system'))))
    print('')
    print('Limit history for a specific field to last 2 values::')
    print('')
    print(f'    # curl {API_URL}/cpu/system/history')
    print(indent_stat(json.loads(stats.get_plugin('cpu').get_stats_history('system', nb=2))))
    print('')


def print_limits(stats):
    sub_title = 'GET limits (used for thresholds)'
    print(sub_title)
    print('-' * len(sub_title))
    print('')
    print('All limits/thresholds::')
    print('')
    print(f'    # curl {API_URL}/all/limits')
    print(indent_stat(stats.getAllLimitsAsDict()))
    print('')
    print('Limits/thresholds for the cpu plugin::')
    print('')
    print(f'    # curl {API_URL}/cpu/limits')
    print(indent_stat(stats.get_plugin('cpu').limits))
    print('')


def print_plugin_post_events():
    sub_title = 'POST clear events'
    print(sub_title)
    print('-' * len(sub_title))
    print('')
    print('Clear all alarms from the list::')
    print('')
    print(f'    # curl -H "Content-Type: application/json" -X POST {API_URL}/events/clear/all')
    print('')
    print('Clear warning alarms from the list::')
    print('')
    print(f'    # curl -H "Content-Type: application/json" -X POST {API_URL}/events/clear/warning')
    print('')


class GlancesStdoutApiDoc:
    """This class manages the fields description display."""

    def __init__(self, config=None, args=None):
        # Init
        self.config = config
        self.args = args

    def end(self):
        pass

    def update(self, stats, duration=1):
        """Display issue"""

        # Display header
        print(APIDOC_HEADER)

        # Display API status
        print_api_status()

        # Display plugins list
        print_plugins_list(sorted(stats._plugins))

        # Loop over plugins
        for plugin in sorted(stats._plugins):
            stat = stats.get_plugin(plugin)
            print_plugin_stats(plugin, stat)
            print_plugin_description(plugin, stat)
            if plugin == 'alert':
                print_plugin_post_events()

            stat_export = stat.get_export()
            if stat_export is None or stat_export == [] or stat_export == {}:
                continue
            print_plugin_item_value(plugin, stat, stat_export)

        # Get all stats
        print_all()

        # Get top stats (only for plugins with a list of items)
        # Example for processlist plugin: get top 2 processes
        print_top(stats)

        # Fields description
        print_fields_info(stats)

        # History
        print_history(stats)

        # Limits
        print_limits(stats)

        # Return True to exit directly (no refresh)
        return True
