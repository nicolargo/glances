#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

from glances import __version__ as glances_version
from glances.globals import weak_lru_cache
from glances.main import GlancesMain
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
