#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage bars for Glances output."""

from math import modf


class Bar:
    """Manage bar (progression or status).

    import sys
    import time
    b = Bar(10)
    for p in range(0, 100):
        b.percent = p
        print("\r%s" % b),
        time.sleep(0.1)
        sys.stdout.flush()
    """

    def __init__(
        self,
        size,
        bar_char='|',
        empty_char=' ',
        pre_char='[',
        post_char=']',
        unit_char='%',
        display_value=True,
        min_value=0,
        max_value=100,
    ):
        """Init a bar (used in Quicllook plugin)

        Args:
            size (_type_): Bar size
            bar_char (str, optional): Bar character. Defaults to '|'.
            empty_char (str, optional): Empty character. Defaults to ' '.
            pre_char (str, optional): Display this char before the bar. Defaults to '['.
            post_char (str, optional): Display this char after the bar. Defaults to ']'.
            unit_char (str, optional): Unit char to be displayed. Defaults to '%'.
            display_value (bool, optional): Do i need to display the value. Defaults to True.
            min_value (int, optional): Minimum value. Defaults to 0.
            max_value (int, optional): Maximum value (percent can be higher). Defaults to 100.
        """
        # Build curses_bars
        self.__curses_bars = [empty_char] * 5 + [bar_char] * 5
        # Bar size
        self.__size = size
        # Bar current percent
        self.__percent = 0
        # Min and max value
        self.min_value = min_value
        self.max_value = max_value
        # Char used for the decoration
        self.__pre_char = pre_char
        self.__post_char = post_char
        self.__empty_char = empty_char
        self.__unit_char = unit_char
        # Value should be displayed ?
        self.__display_value = display_value

    @property
    def size(self, with_decoration=False):
        # Return the bar size, with or without decoration
        if with_decoration:
            return self.__size
        if self.__display_value:
            return self.__size - 6
        return None

    @property
    def percent(self):
        return self.__percent

    @percent.setter
    def percent(self, value):
        if value < self.min_value:
            value = self.min_value
        self.__percent = value

    @property
    def pre_char(self):
        return self.__pre_char

    @property
    def post_char(self):
        return self.__post_char

    def get(self, overlay: str = None):
        """Return the bars."""
        value = self.max_value if self.percent > self.max_value else self.percent

        # Build the bar
        frac, whole = modf(self.size * value / 100.0)
        ret = self.__curses_bars[8] * int(whole)
        if frac > 0:
            ret += self.__curses_bars[int(frac * 8)]
            whole += 1
        ret += self.__empty_char * int(self.size - whole)

        # Add the value
        if self.__display_value:
            if self.percent >= self.max_value:
                ret = '{} {}{:3.0f}{}'.format(
                    ret, '>' if self.percent > self.max_value else ' ', self.max_value, self.__unit_char
                )
            else:
                ret = f'{ret}{self.percent:5.1f}{self.__unit_char}'

        # Add overlay
        if overlay and len(overlay) < len(ret) - 6:
            ret = overlay + ret[len(overlay) :]

        return ret

    def __str__(self):
        """Return the bars."""
        return self.get()
