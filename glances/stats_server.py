#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""The stats server manager."""

import collections

from glances.logger import logger
from glances.stats import GlancesStats


class GlancesStatsServer(GlancesStats):
    """This class stores, updates and gives stats for the server."""

    def __init__(self, config=None, args=None):
        # Init the stats
        super().__init__(config=config, args=args)

        # Init the all_stats dict used by the server
        # all_stats is a dict of dicts filled by the server
        self.all_stats = collections.defaultdict(dict)

        # In the update method, disable extended process stats
        logger.info("Disable extended processes stats in server mode")

    def update(self, input_stats=None):
        """Update the stats."""
        input_stats = input_stats or {}

        # Force update of all the stats
        super().update()

        # Disable the extended processes stats because it cause an high CPU load
        self._plugins['processcount'].disable_extended()

        # Build all_stats variable (concatenation of all the stats)
        self.all_stats = self._set_stats(input_stats)

    def _set_stats(self, input_stats):
        """Set the stats to the input_stats one."""
        # Build the all_stats with the get_raw() method of the plugins
        return {p: self._plugins[p].get_raw() for p in self._plugins if self._plugins[p].is_enabled()}

    def getAll(self):
        """Return the stats as a list."""
        return self.all_stats
