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
    printtab('>>> gl.mem["used"]')
    printtab(f'{gl.mem["used"]}')
    printtab('>>> gl.auto_unit(gl.mem["used"])')
    printtab(f'{gl.auto_unit(gl.mem["used"])}')
    print('')
    print('If the stats return a list of items (like network interfaces or processes), you can')
    print('access them by their name:')
    print('')
    print('.. code-block:: python')
    print('')
    printtab('>>> gl.network.keys()')
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
    printtab(f'>>> type(gl.{plugin})')
    printtab(f'{type(stats_obj)}')
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
    for plugin in [p for p in gl.plugins() if p not in ['help', 'programlist']]:
        print_plugin(gl, plugin)


def print_auto_unit(gl):
    sub_title = 'Use auto_unit to display a human-readable string with the unit'
    print(sub_title)
    print('-' * len(sub_title))
    print('')
    print('Use auto_unit() function to generate a human-readable string with the unit:')
    print('')
    print('.. code-block:: python')
    print('')
    printtab('>>> gl.mem["used"]')
    printtab(f'{gl.mem["used"]}')
    print('')
    printtab('>>> gl.auto_unit(gl.mem["used"])')
    printtab(f'{gl.auto_unit(gl.mem["used"])}')
    print('')
    print("""
Args:

    number (float or int): The numeric value to be converted.

    low_precision (bool, optional): If True, use lower precision for the output. Defaults to False.

    min_symbol (str, optional): The minimum unit symbol to use (e.g., 'K' for kilo). Defaults to 'K'.

    none_symbol (str, optional): The symbol to display if the number is None. Defaults to '-'.

Returns:

    str: A human-readable string representation of the number with units.

""")


def print_bar(gl):
    sub_title = 'Use to display stat as a bar'
    print(sub_title)
    print('-' * len(sub_title))
    print('')
    print('Use bar() function to generate a bar:')
    print('')
    print('.. code-block:: python')
    print('')
    printtab('>>> gl.bar(gl.mem["percent"])')
    printtab(f'{gl.bar(gl.mem["percent"])}')
    print('')
    print("""
Args:

    value (float): The percentage value to represent in the bar (typically between 0 and 100).

    size (int, optional): The total length of the bar in characters. Defaults to 18.

    bar_char (str, optional): The character used to represent the filled portion of the bar. Defaults to '■'.

    empty_char (str, optional): The character used to represent the empty portion of the bar. Defaults to '□'.

    pre_char (str, optional): A string to prepend to the bar. Defaults to ''.

    post_char (str, optional): A string to append to the bar. Defaults to ''.

Returns:

    str: A string representing the progress bar.

""")


def print_top_process(gl):
    sub_title = 'Use to display top process list'
    print(sub_title)
    print('-' * len(sub_title))
    print('')
    print('Use top_process() function to generate a list of top processes sorted by CPU or MEM usage:')
    print('')
    print('.. code-block:: python')
    print('')
    printtab('>>> gl.top_process()')
    printtab(f'{gl.top_process()}')
    print('')
    print("""
Args:

    limit (int, optional): The maximum number of top processes to return. Defaults to 3.

    sorted_by (str, optional): The primary key to sort processes by (e.g., 'cpu_percent').
                                Defaults to 'cpu_percent'.

    sorted_by_secondary (str, optional): The secondary key to sort processes by if primary keys are equal
                                            (e.g., 'memory_percent'). Defaults to 'memory_percent'.

Returns:

    list: A list of dictionaries representing the top processes, excluding those with 'glances' in their
            command line.

Note:

    The 'glances' process is excluded from the returned list to avoid self-generated CPU load affecting
    the results.

""")


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

        # Others helpers
        print_auto_unit(self.gl)
        print_bar(self.gl)
        print_top_process(self.gl)

        # Return True to exit directly (no refresh)
        return True
