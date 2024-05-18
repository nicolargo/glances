#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

import re

from glances.logger import logger


class GlancesFilterList:
    """Manage a lis of GlancesFilter objects

    >>> fl = GlancesFilterList()
    >>> fl.filter = '.*python.*,user:nicolargo'
    >>> fl.is_filtered({'name': 'python is in the place'})
    True
    >>> fl.is_filtered({'name': 'snake is in the place'})
    False
    >>> fl.is_filtered({'name': 'snake is in the place', 'username': 'nicolargo'})
    True
    >>> fl.is_filtered({'name': 'snake is in the place', 'username': 'notme'})
    False
    """

    def __init__(self):
        self._filter = []

    @property
    def filter(self):
        """Return the current filter to be applied"""
        return self._filter

    @filter.setter
    def filter(self, value):
        """Add a comma separated list of filters"""
        for f in value.split(','):
            self._add_filter(f)

    def _add_filter(self, filter_input):
        """Add a filter"""
        f = GlancesFilter()
        f.filter = filter_input
        self._filter.append(f)

    def is_filtered(self, process):
        """Return True if the process is filtered by at least one filter"""
        for f in self._filter:
            if f.is_filtered(process):
                return True
        return False


class GlancesFilter:
    """Allow Glances to filter processes

    >>> f = GlancesFilter()
    >>> f.filter = '.*python.*'
    >>> f.filter
    '.*python.*'
    >>> f.filter_key
    None
    >>> f.filter = 'username:nicolargo'
    >>> f.filter
    'nicolargo'
    >>> f.filter_key
    'username'
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
        """Return the filter given by the user (as a string)"""
        return self._filter_input

    @property
    def filter(self):
        """Return the current filter to be applied"""
        return self._filter

    @filter.setter
    def filter(self, value):
        """Set the filter (as a string) and compute the regular expression

        A filter could be one of the following:
        - python > Process name start with python
        - .*python.* > Process name contain python
        - user:nicolargo > Process belong to nicolargo user
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
            logger.debug(
                "Set filter to {} on {}".format(self.filter, self.filter_key if self.filter_key else 'name or cmdline')
            )
            # Compute the regular expression
            try:
                self._filter_re = re.compile(self.filter)
                logger.debug(f"Filter regex compilation OK: {self.filter}")
            except Exception as e:
                logger.error(f"Cannot compile filter regex: {self.filter} ({e})")
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

        :param process: A dict corresponding to the process item.
        """
        if self.filter is None:
            # No filter => Not filtered
            return False

        if self.filter_key is None:
            # Apply filter on command line and process name
            return self._is_process_filtered(process, key='name') or self._is_process_filtered(process, key='cmdline')

        # Apply filter on <key>
        return self._is_process_filtered(process)

    def _is_process_filtered(self, process, key=None):
        """Return True if the process[key] should be filtered according to the current filter"""
        if key is None:
            key = self.filter_key
        try:
            # If the item process[key] is a list, convert it to a string
            # in order to match it with the current regular expression
            if isinstance(process[key], list) and key == 'cmdline' and len(process[key]) > 0:
                value = process[key][0]
            elif isinstance(process[key], list):
                value = ' '.join(process[key])
            else:
                value = process[key]
        except KeyError:
            # If the key did not exist
            return False
        try:
            return self._filter_re.fullmatch(value) is not None
        except (AttributeError, TypeError):
            # AttributeError -  Filter processes crashes with a bad regular expression pattern (issue #665)
            # TypeError - Filter processes crashes if value is None (issue #1105)
            return False
