#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage stats history"""

from glances.attribute import GlancesAttribute


class GlancesHistory:
    """This class manage a dict of GlancesAttribute
    - key: stats name
    - value: GlancesAttribute"""

    def __init__(self):
        """
        items_history_list: list of stats to historized (define inside plugins)
        """
        self.stats_history = {}

    def add(self, key, value, description='', history_max_size=None):
        """Add an new item (key, value) to the current history."""
        if key not in self.stats_history:
            self.stats_history[key] = GlancesAttribute(key, description=description, history_max_size=history_max_size)
        self.stats_history[key].value = value

    def reset(self):
        """Reset all the stats history"""
        for a in self.stats_history:
            self.stats_history[a].history_reset()

    def get(self, nb=0):
        """Get the history as a dict of list"""
        return {i: self.stats_history[i].history_raw(nb=nb) for i in self.stats_history}

    def get_json(self, nb=0):
        """Get the history as a dict of list (with list JSON compliant)"""
        return {i: self.stats_history[i].history_json(nb=nb) for i in self.stats_history}
