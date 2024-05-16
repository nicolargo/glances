#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Attribute class."""

from datetime import datetime


class GlancesAttribute:
    def __init__(self, name, description='', history_max_size=None):
        """Init the attribute

        :param name: Attribute name (string)
        :param description: Attribute human reading description (string)
        :param history_max_size: Maximum size of the history list (default is no limit)

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
        """Add a value in the history"""
        if self._history_max_size:
            if self.history_len() >= self._history_max_size:
                self._history.pop(0)
            self._history.append(value)

    def history_size(self):
        """Return the history size (maximum number of value in the history)"""
        return len(self._history)

    def history_len(self):
        """Return the current history length"""
        return len(self._history)

    def history_value(self, pos=1):
        """Return the value in position pos in the history.

        Default is to return the latest value added to the history.
        """
        return self._history[-pos]

    def history_raw(self, nb=0):
        """Return the history in ISO JSON format"""
        return self._history[-nb:]

    def history_json(self, nb=0):
        """Return the history in ISO JSON format"""
        return [(i[0].isoformat(), i[1]) for i in self._history[-nb:]]

    def history_mean(self, nb=5):
        """Return the mean on the <nb> values in the history."""
        _, v = zip(*self._history)
        return sum(v[-nb:]) / float(v[-1] - v[-nb])
