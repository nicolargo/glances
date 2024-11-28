#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage sparklines for Glances output."""

import sys

from glances.globals import nativestr
from glances.logger import logger

sparklines_module = True

try:
    from sparklines import sparklines
except ImportError as e:
    logger.warning(f"Sparklines module not found ({e})")
    sparklines_module = False

try:
    '┌┬┐╔╦╗╒╤╕╓╥╖│║─═├┼┤╠╬╣╞╪╡╟╫╢└┴┘╚╩╝╘╧╛╙╨╜'.encode(sys.stdout.encoding)
except (UnicodeEncodeError, TypeError) as e:
    logger.warning(f"UTF-8 is mandatory for sparklines ({e})")
    sparklines_module = False


class Sparkline:
    """Manage sparklines (see https://pypi.org/project/sparklines/)."""

    def __init__(self, size, pre_char='[', post_char=']', unit_char='%', display_value=True):
        # If the sparklines python module available ?
        self.__available = sparklines_module
        # Sparkline size
        self.__size = size
        # Sparkline current percents list
        self.__percent = []
        # Char used for the decoration
        self.__pre_char = pre_char
        self.__post_char = post_char
        self.__unit_char = unit_char
        # Value should be displayed ?
        self.__display_value = display_value

    @property
    def available(self):
        return self.__available

    @property
    def size(self, with_decoration=False):
        # Return the sparkline size, with or without decoration
        if with_decoration:
            return self.__size
        if self.__display_value:
            return self.__size - 6
        return None

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

    def get(self, overwrite=''):
        """Return the sparkline."""
        ret = sparklines(self.percents, minimum=0, maximum=100)[0]
        if self.__display_value:
            percents_without_none = [x for x in self.percents if x is not None]
            if percents_without_none:
                ret = f'{ret}{percents_without_none[-1]:5.1f}{self.__unit_char}'
        ret = nativestr(ret)
        if overwrite and len(overwrite) < len(ret) - 6:
            ret = overwrite + ret[len(overwrite) :]
        return ret

    def __str__(self):
        """Return the sparkline."""
        return self.get()
