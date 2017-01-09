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

"""Attribute class."""

from datetime import datetime


class GlancesAttribute(object):

    def __init__(self, name, description='', history_max_size=None):
        """Init the attribute
        name: Attribute name (string)
        description: Attribute human reading description (string)
        history_max_size: Maximum size of the history list (default is no limit)

        History is stored as a list for tuple: [(date, value), ...]
        """
        self._name = name
        self._description = description
        self._value = None
        self._history_max_size = history_max_size
        self._history = []

    def __repr__(self):
        return self.value

    def __str__(self):
        return str(self.value)

    """
    Properties for the attribute name
    """
    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name):
        self._name = new_name

    """
    Properties for the attribute description
    """
    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, new_description):
        self._description = new_description

    """
    Properties for the attribute value
    """
    @property
    def value(self):
        if self.history_len() > 0:
            return (self._value[1] - self.history_value()[1]) / (self._value[0] - self.history_value()[0])
        else:
            return None

    @value.setter
    def value(self, new_value):
        """Set a value.
        Value is a tuple: (<timestamp>, <new_value>)
        """
        self._value = (datetime.now(), new_value)
        self.history_add(self._value)

    """
    Properties for the attribute history
    """
    @property
    def history(self):
        return self._history

    @history.setter
    def history(self, new_history):
        self._history = new_history

    @history.deleter
    def history(self):
        del self._history

    def history_reset(self):
        self._history = []

    def history_add(self, value):
        """Add a value in the history
        """
        if self._history_max_size is None or self.history_len() < self._history_max_size:
            self._history.append(value)
        else:
            self._history = self._history[1:] + [value]

    def history_size(self):
        """Return the history size (maximum nuber of value in the history)
        """
        return len(self._history)

    def history_len(self):
        """Return the current history lenght
        """
        return len(self._history)

    def history_value(self, pos=1):
        """Return the value in position pos in the history.
        Default is to return the latest value added to the history.
        """
        return self._history[-pos]

    def history_json(self, nb=0):
        """Return the history of last nb items (0 for all) In ISO JSON format"""
        return [(i[0].isoformat(), i[1]) for i in self._history[-nb:]]

    def history_mean(self, nb=5):
        """Return the mean on the <nb> values in the history.
        """
        _, v = zip(*self._history)
        return sum(v[-nb:]) / float(v[-1] - v[-nb])
