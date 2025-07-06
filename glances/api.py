#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

from glances import __version__ as glances_version
from glances.main import GlancesMain
from glances.stats import GlancesStats


class GlancesAPI:
    def __init__(self):
        self.__version__ = glances_version.split('.')[0]  # Get the major version

        core = GlancesMain(args_begin_at=2)
        self._stats = GlancesStats(config=core.get_config(), args=core.get_args())

        for p in self._stats.getPluginsList():
            plugin = self._stats.get_plugin(p)
            if plugin is not None:
                setattr(self, p, plugin)
