#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

from glances import __version__ as glances_version
from glances.globals import auto_unit, weak_lru_cache
from glances.main import GlancesMain
from glances.outputs.glances_bars import Bar
from glances.processes import sort_stats
from glances.stats import GlancesStats

plugin_dependencies_tree = {
    'processlist': ['processcount'],
}


class GlancesAPI:
    ttl = 2.0  # Default cache TTL in seconds

    def __init__(self, config=None, args=None, args_begin_at=1):
        self.__version__ = glances_version.split('.')[0]  # Get the major version

        core = GlancesMain(args_begin_at)
        self.args = args if args is not None else core.get_args()
        self.config = config if config is not None else core.get_config()
        self._stats = GlancesStats(config=self.config, args=self.args)

        # Set the cache TTL for the API
        self.ttl = self.args.time if self.args.time is not None else self.ttl

        # Init the stats of all plugins in order to ensure that rate are computed
        self._stats.update()

    @weak_lru_cache(maxsize=1, ttl=ttl)
    def __getattr__(self, item):
        """Fallback to the stats object for any missing attributes."""
        if item in self._stats.getPluginsList():
            if item in plugin_dependencies_tree:
                # Ensure dependencies are updated before accessing the plugin
                for dependency in plugin_dependencies_tree[item]:
                    self._stats.get_plugin(dependency).update()
            # Update the plugin stats
            self._stats.get_plugin(item).update()
            return self._stats.get_plugin(item)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{item}'")

    def plugins(self):
        """Return the list of available plugins."""
        return self._stats.getPluginsList()

    def auto_unit(self, number, low_precision=False, min_symbol='K', none_symbol='-'):
        """
        Converts a numeric value into a human-readable string with appropriate units.

        Args:
            number (float or int): The numeric value to be converted.
            low_precision (bool, optional): If True, use lower precision for the output. Defaults to False.
            min_symbol (str, optional): The minimum unit symbol to use (e.g., 'K' for kilo). Defaults to 'K'.
            none_symbol (str, optional): The symbol to display if the number is None. Defaults to '-'.

        Returns:
            str: A human-readable string representation of the number with units.
        """
        return auto_unit(number, low_precision, min_symbol, none_symbol)

    def bar(self, value, size=18, bar_char='■', empty_char='□', pre_char='', post_char=''):
        """
        Generate a progress bar representation for a given value.

        Args:
            value (float): The percentage value to represent in the bar (typically between 0 and 100).
            size (int, optional): The total length of the bar in characters. Defaults to 18.
            bar_char (str, optional): The character used to represent the filled portion of the bar. Defaults to '■'.
            empty_char (str, optional): The character used to represent the empty portion of the bar. Defaults to '□'.
            pre_char (str, optional): A string to prepend to the bar. Defaults to ''.
            post_char (str, optional): A string to append to the bar. Defaults to ''.

        Returns:
            str: A string representing the progress bar.
        """
        b = Bar(
            size, bar_char=bar_char, empty_char=empty_char, pre_char=pre_char, post_char=post_char, display_value=False
        )
        b.percent = value
        return b.get()

    def top_process(self, limit=3, sorted_by='cpu_percent', sorted_by_secondary='memory_percent'):
        """
        Returns a list of the top processes sorted by specified criteria.

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
        """
        # Exclude glances process from the top list
        # because in fetch mode, Glances generate a CPU load
        all_but_glances = [
            p
            for p in self._stats.get_plugin('processlist').get_raw()
            if p['cmdline'] and 'glances' not in (p['cmdline'] or ())
        ]
        return sort_stats(all_but_glances, sorted_by=sorted_by, sorted_by_secondary=sorted_by_secondary)[:limit]
