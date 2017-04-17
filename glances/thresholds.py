# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2017 Nicolargo <nicolas@nicolargo.com>
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

"""
Thresholds classes: OK, CAREFUL, WARNING, CRITICAL
"""


class _GlancesThreshold(object):

    """Father class for all other Thresholds"""

    def description(self):
        return self._threshold['description']

    def value(self):
        return self._threshold['value']

    def __repr__(self):
        return self._threshold

    def __str__(self):
        return self.description()

    def __cmp__(self, other):
        """Override the default comparaison behavior"""
        return self.value().__cmp__(other.value())


class GlancesThresholdOk(_GlancesThreshold):

    """Ok Threshold class"""

    _threshold = {'description': 'OK',
                  'value': 0}


class GlancesThresholdCareful(_GlancesThreshold):

    """Careful Threshold class"""

    _threshold = {'description': 'CAREFUL',
                  'value': 1}


class GlancesThresholdWarning(_GlancesThreshold):

    """Warning Threshold class"""

    _threshold = {'description': 'WARNING',
                  'value': 2}


class GlancesThresholdCritical(_GlancesThreshold):

    """Warning Threshold class"""

    _threshold = {'description': 'CRITICAL',
                  'value': 3}
