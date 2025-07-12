#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Generate Glances Python API documentation."""

from pprint import pformat

from glances import api

APIDOC_HEADER = """\
.. _api:

Python API documentation
========================

This documentation describes the Glances Python API.

Note: This API is only available in Glances 4.4.0 or higher.

"""


def printtab(s, indent='    '):
    print(indent + s.replace('\n', '\n' + indent))


def print_tldr(gl):
    """Print the TL;DR section of the API documentation."""
    sub_title = 'TL;DR'
    print(sub_title)
    print('-' * len(sub_title))
    print('')
    print('You can access the Glances API by importing the `glances.api` module and creating an')
    print('instance of the `GlancesAPI` class. This instance provides access to all Glances plugins')
    print('and their fields. For example, to access the CPU plugin and its total field, you can')
    print('use the following code:')
    print('')
    print('.. code-block:: python')
    print('')
    printtab('>>> from glances import api')
    printtab('>>> gl = api.GlancesAPI()')
    printtab('>>> gl.cpu')
    printtab(f'{pformat(gl.cpu.stats)}')
    printtab('>>> gl.cpu["total"]')
    printtab(f'{gl.cpu["total"]}')
    print('')
    print('If the stats return a list of items (like network interfaces or processes), you can')
    print('access them by their name:')
    print('')
    print('.. code-block:: python')
    print('')
    printtab(f'{gl.network.keys()}')
    printtab(f'>>> gl.network["{gl.network.keys()[0]}"]')
    printtab(f'{pformat(gl.network[gl.network.keys()[0]])}')
    print('')


def print_init_api(gl):
    sub_title = 'Init Glances Python API'
    print(sub_title)
    print('-' * len(sub_title))
    print('')
    print('Init the Glances API:')
    print('')
    print('.. code-block:: python')
    print('')
    printtab('>>> from glances import api')
    printtab('>>> gl = api.GlancesAPI()')
    print('')


def print_plugins_list(gl):
    sub_title = 'Get Glances plugins list'
    print(sub_title)
    print('-' * len(sub_title))
    print('')
    print('Get the plugins list:')
    print('')
    print('.. code-block:: python')
    print('')
    printtab('>>> gl.plugins()')
    printtab(f'{gl.plugins()}')
    print('```')
    print('')


def print_plugin(gl, plugin):
    """Print the details of a single plugin."""
    sub_title = f'Glances {plugin}'
    print(sub_title)
    print('-' * len(sub_title))
    print('')

    stats_obj = gl.__getattr__(plugin)

    print(f'{plugin.capitalize()} stats:')
    print('')
    print('.. code-block:: python')
    print('')
    printtab(f'>>> gl.{plugin}')
    printtab(f'Return a {type(stats_obj)} object')
    if len(stats_obj.keys()) > 0 and isinstance(stats_obj[stats_obj.keys()[0]], dict):
        printtab(f'>>> gl.{plugin}')
        printtab(f'Return a dict of dict with key=<{stats_obj[stats_obj.keys()[0]]["key"]}>')
        printtab(f'>>> gl.{plugin}.keys()')
        printtab(f'{stats_obj.keys()}')
        printtab(f'>>> gl.{plugin}["{stats_obj.keys()[0]}"]')
        printtab(f'{pformat(stats_obj[stats_obj.keys()[0]])}')
    else:
        printtab(f'>>> gl.{plugin}')
        printtab(f'{pformat(stats_obj.stats)}')
        if len(stats_obj.keys()) > 0:
            printtab(f'>>> gl.{plugin}.keys()')
            printtab(f'{stats_obj.keys()}')
            printtab(f'>>> gl.{plugin}["{stats_obj.keys()[0]}"]')
            printtab(f'{pformat(stats_obj[stats_obj.keys()[0]])}')
    print('')

    if stats_obj.fields_description is not None:
        print(f'{plugin.capitalize()} fields description:')
        print('')
        for field, description in stats_obj.fields_description.items():
            print(f'* {field}: {description["description"]}')
        print('')

    print(f'{plugin.capitalize()} limits:')
    print('')
    print('.. code-block:: python')
    print('')
    printtab(f'>>> gl.{plugin}.limits')
    printtab(f'{pformat(gl.__getattr__(plugin).limits)}')
    print('')


def print_plugins(gl):
    """Print the details of all plugins."""
    for plugin in gl.plugins():
        print_plugin(gl, plugin)


class GlancesStdoutApiDoc:
    """This class manages the fields description display."""

    def __init__(self, config=None, args=None):
        # Init
        self.gl = api.GlancesAPI()

    def end(self):
        pass

    def update(self, stats, duration=1):
        """Display issue"""

        # Display header
        print(APIDOC_HEADER)

        # Display TL;DR section
        print_tldr(self.gl)

        # Init the API
        print_init_api(self.gl)

        # Display plugins list
        print_plugins_list(self.gl)

        # Loop over plugins
        print_plugins(self.gl)

        # Return True to exit directly (no refresh)
        return True
