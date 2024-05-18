#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""
Thresholds classes: OK, CAREFUL, WARNING, CRITICAL
"""

import sys
from functools import total_ordering


class GlancesThresholds:
    """Class to manage thresholds dict for all Glances plugins:

    key: Glances stats (example: cpu_user)
    value: Threshold instance
    """

    threshold_list = ['OK', 'CAREFUL', 'WARNING', 'CRITICAL']

    def __init__(self):
        self.current_module = sys.modules[__name__]
        self._thresholds = {}

    def get(self, stat_name=None):
        """Return the threshold dict.
        If stat_name is None, return the threshold for all plugins (dict of Threshold*)
        Else return the Threshold* instance for the given plugin
        """
        if stat_name is None:
            return self._thresholds

        if stat_name in self._thresholds:
            return self._thresholds[stat_name]
        return {}

    def add(self, stat_name, threshold_description):
        """Add a new threshold to the dict (key = stat_name)"""
        if threshold_description not in self.threshold_list:
            return False

        self._thresholds[stat_name] = getattr(
            self.current_module, 'GlancesThreshold' + threshold_description.capitalize()
        )()
        return True


# Global variable uses to share thresholds between Glances components
glances_thresholds = GlancesThresholds()


@total_ordering
class _GlancesThreshold:
    """Father class for all other Thresholds"""

    def description(self):
        return self._threshold['description']

    def value(self):
        return self._threshold['value']

    def __repr__(self):
        return str(self._threshold)

    def __str__(self):
        return self.description()

    def __lt__(self, other):
        return self.value() < other.value()

    def __eq__(self, other):
        return self.value() == other.value()


class GlancesThresholdOk(_GlancesThreshold):
    """Ok Threshold class"""

    _threshold = {'description': 'OK', 'value': 0}


class GlancesThresholdCareful(_GlancesThreshold):
    """Careful Threshold class"""

    _threshold = {'description': 'CAREFUL', 'value': 1}


class GlancesThresholdWarning(_GlancesThreshold):
    """Warning Threshold class"""

    _threshold = {'description': 'WARNING', 'value': 2}


class GlancesThresholdCritical(_GlancesThreshold):
    """Warning Threshold class"""

    _threshold = {'description': 'CRITICAL', 'value': 3}
