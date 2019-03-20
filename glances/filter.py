# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2019 Nicolargo <nicolas@nicolargo.com>
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
    >>> f.key
    None
    >>> f.filter = 'user:nicolargo'
    >>> f.filter
    'nicolargo'
    >>> f.key
    'user'
    >>> f.filter = 'username:.*nico.*'
    >>> f.filter
    '.*nico.*'
    >>> f.key
    'username'
    """

    def __init__(self):
        # Filter entered by the user (string)
        self._filter_input = None
        # Filter to apply
        self._filter = None
        # Filter regular expression
        self._filter_re = None
        # Dict key where the filter should be applied
        # Default is None: search on command line and process name
        self._filter_key = None

    @property
    def filter_input(self):
        """Return the filter given by the user (as a sting)"""
        return self._filter_input

    @property
    def filter(self):
        """Return the current filter to be applied"""
        return self._filter

    @filter.setter
    def filter(self, value):
        """Set the filter (as a sting) and compute the regular expression
        A filter could be one of the following:
        - python > Process name of cmd start with python
        - .*python.* > Process name of cmd contain python
        - username:nicolargo > Process of nicolargo user
        """
        self._filter_input = value
        if value is None:
            self._filter = None
            self._filter_key = None
        else:
            new_filter = value.split(':')
            if len(new_filter) == 1:
                self._filter = new_filter[0]
                self._filter_key = None
            else:
                self._filter = new_filter[1]
                self._filter_key = new_filter[0]

        self._filter_re = None
        if self.filter is not None:
            logger.info("Set filter to {} on key {}".format(self.filter, self.filter_key))
            # Compute the regular expression
            try:
                self._filter_re = re.compile(self.filter)
                logger.debug("Filter regex compilation OK: {}".format(self.filter))
            except Exception as e:
                logger.error("Cannot compile filter regex: {} ({})".format(self.filter, e))
                self._filter = None
                self._filter_re = None
                self._filter_key = None

    @property
    def filter_re(self):
        """Return the filter regular expression"""
        return self._filter_re

    @property
    def filter_key(self):
        """key where the filter should be applied"""
        return self._filter_key

    def is_filtered(self, process):
        """Return True if the process item match the current filter
        The proces item is a dict.
        """
        if self.filter is None:
            # No filter => Not filtered
            return False

        if self.filter_key is None:
            # Apply filter on command line and process name
            return self._is_process_filtered(process, key='name') or \
                self._is_process_filtered(process, key='cmdline')
        else:
            # Apply filter on <key>
            return self._is_process_filtered(process)

    def _is_process_filtered(self, process, key=None):
        """Return True if the process[key] should be filtered according to the current filter"""
        if key is None:
            key = self.filter_key
        try:
            # If the item process[key] is a list, convert it to a string
            # in order to match it with the current regular expression
            if isinstance(process[key], list):
                value = ' '.join(process[key])
            else:
                value = process[key]
        except KeyError:
            # If the key did not exist
            return False
        try:
            return self._filter_re.match(value) is None
        except (AttributeError, TypeError):
            # AttributeError
            # Filter processes crashs with a bad regular expression pattern (issue #665)
            # TypeError
            # Filter processes crashs if value is None (issue #1105)
            return False
