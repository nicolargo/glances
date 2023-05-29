# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2023 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances Data Item class."""

import time

from dataclasses import dataclass


class GlancesDataUnit:

    PERCENT = '%'
    BIT = 'b'
    BYTE = 'B'
    CORE = 'C'
    TEMPERATURE = '°'


@dataclass
class GlancesDataItem:
    """Class for a Glances Data item."""

    description: str = None
    name: str = None
    short_name: str = None
    rate: bool = False
    value: float = None
    _previous_value: float = None
    unit: str = None
    min_symbol: str = None
    last_update: float = None

    def __post_init__(self):
        """Init the GlancesItem object."""
        # Init the last update time
        pass

    def update(self, value: float):
        """Update the value."""
        if self.rate:
            # Compute the rate
            if self._previous_value is None:
                self._previous_value = value
            else:
                self.value = (value - self._previous_value) / (time.time() - self.last_update)
        else:
            # Store the value
            self.value = value
        self.last_update = time.time()

    def dict(self):
        """Return a dict of the object.
        Intersting topic: https://stackoverflow.com/questions/72604922/how-to-convert-python-dataclass-to-dictionary-of-string-literal
        """
        return self.__dict__
