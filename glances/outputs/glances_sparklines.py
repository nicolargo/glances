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

"""Manage sparklines for Glances output."""

from __future__ import unicode_literals
from __future__ import division
import sys
from math import modf
from glances.logger import logger
from glances.compat import nativestr

sparklines_module = True

try:
    from sparklines import sparklines
except ImportError as e:
    logger.warning("Sparklines module not found ({})".format(e))
    sparklines_module = False

try:
    '┌┬┐╔╦╗╒╤╕╓╥╖│║─═├┼┤╠╬╣╞╪╡╟╫╢└┴┘╚╩╝╘╧╛╙╨╜'.encode(sys.stdout.encoding)
except (UnicodeEncodeError, TypeError) as e:
    logger.warning("UTF-8 is mandatory for sparklines ({})".format(e))
    sparklines_module = False


class Sparkline(object):

    r"""Manage sparklines (see https://pypi.org/project/sparklines/)."""

    def __init__(self, size, pre_char='[', post_char=']', empty_char=' ', with_text=True):
        # If the sparklines python module available ?
        self.__available = sparklines_module
        # Sparkline size
        self.__size = size
        # Sparkline current percents list
        self.__percent = []
        # Char used for the decoration
        self.__pre_char = pre_char
        self.__post_char = post_char
        self.__empty_char = empty_char
        self.__with_text = with_text

    @property
    def available(self):
        return self.__available

    @property
    def size(self, with_decoration=False):
        # Return the sparkine size, with or without decoration
        if with_decoration:
            return self.__size
        if self.__with_text:
            return self.__size - 6

    @property
    def percents(self):
        return self.__percent

    @percents.setter
    def percents(self, value):
        self.__percent = value

    @property
    def pre_char(self):
        return self.__pre_char

    @property
    def post_char(self):
        return self.__post_char

    def get(self):
        """Return the sparkline."""
        ret = sparklines(self.percents)[0]
        if self.__with_text:
            percents_without_none = [x for x in self.percents if x is not None]
            if len(percents_without_none) > 0:
                ret = '{}{:5.1f}%'.format(ret, percents_without_none[-1])
        return nativestr(ret)

    def __str__(self):
        """Return the sparkline."""
        return self.get()
