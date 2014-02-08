#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances - An eye on your system
#
# Copyright (C) 2014 Nicolargo <nicolas@nicolargo.com>
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

import json
from time import time

# Global list to manage the elapsed time
last_update_times = {}


def getTimeSinceLastUpdate(IOType):
    global last_update_times
    # assert(IOType in ['net', 'disk', 'process_disk'])
    current_time = time()
    last_time = last_update_times.get(IOType)
    if not last_time:
        time_since_update = 1
    else:
        time_since_update = current_time - last_time
    last_update_times[IOType] = current_time
    return time_since_update


class GlancesPlugin(object):
    """
    Main class for Glances' plugin
    """

    def __init__(self):
        # Init the stat list
        self.stats = None
    

    def __repr__(self):
        # Return the raw stats
        return self.stats
        

    def __str__(self):
        # Return the human-readable stats
        return str(self.stats)


    def get_raw(self):
        # Return the stats object
        return self.stats


    def get_stats(self):
        # Return the stats object in JSON format for the RPC API
        return json.dumps(self.stats)


    def msg_curse(self):
        """
        Return default string to display in the curse interface
        """
        return [ self.curse_add_line(str(self.stats)) ]


    def get_curse(self):
        # Return a dict with all the information needed to display the stat
        # key     | description
        #----------------------------
        # display | Display the stat (True or False)
        # msgdict | Message to display (list of dict [{ 'msg': msg, 'decoration': decoration } ... ])
        # column  | column number
        # line    | Line number

        display_curse = False
        column_curse = -1
        line_curse = -1

        if (hasattr(self, 'display_curse')):
            display_curse = self.display_curse
        if (hasattr(self, 'column_curse')):
            column_curse = self.column_curse
        if (hasattr(self, 'line_curse')):
            line_curse = self.line_curse

        return { 'display': display_curse,
                 'msgdict': self.msg_curse(),
                 'column': column_curse,
                 'line': line_curse }


    def curse_add_line(self, msg, decoration="NORMAL"):
        """
        Return a dict with: { 'msg': msg, 'decoration': decoration }
        with:
            msg: string
            decoration: NORMAL (no decoration), UNDERLINE, BOLD, REVERSE
        """ 

        return { 'msg': msg, 'decoration': decoration }


    def curse_new_line(self):
        """
        Go to a new line
        """ 

        return self.curse_add_line('\n')
