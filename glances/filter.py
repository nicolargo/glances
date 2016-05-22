# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2016 Nicolargo <nicolas@nicolargo.com>
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

import re

from glances.logger import logger


class GlancesFilter(object):

    """Allow Glances to filter processes

    >>> f = GlancesFilter()
    >>> f.filter = '.*python.*'
    >>> f.filter
    '.*python.*'
    """

    def __init__(self):
        # Filter entered by the user (string)
        self._filter = None
        # Filter regular expression
        self._filter_re = None

    @property
    def filter(self):
        """Return the filter (as a sting)"""
        return self._filter

    @filter.setter
    def filter(self, value):
        """Set the filter (as a sting) and compute the regular expression"""
        self._filter = value
        self._filter_re = None

        if self.filter is not None:
            logger.info("Set filter to {0}".format(self.filter))
            # Compute the regular expression
            try:
                self._filter_re = re.compile(self.filter)
                logger.debug("Filter regex compilation OK: {0}".format(self.filter))
            except Exception as e:
                logger.error("Cannot compile filter regex: {0} ({1})".format(self.filter, e))

    @property
    def filter_re(self):
        """Return the filter regular expression"""
        return self._filter_re

    def is_filtered(self, process, key='cmdline'):
        """Return True if the process item match the current filter
        The proces item is a dict.
        The filter will be applyed on the process[key] (command line by default)
        """
        if self.filter is None:
            # No filter => Not filtered
            return False
        try:
            return self._filter_re.match(' '.join(process[key])) is None
        except AttributeError:
            #  Filter processes crashs with a bad regular expression pattern (issue #665)
            return False
