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

# Import system libs
import sys
import socket
import json

# Import Glances libs
from ..core.glances_limits import glancesLimits
from ..core.glances_monitor_list import monitorList
from ..core.glances_stats import GlancesStats
from ..outputs.glances_curses import glancesCurses


class GlancesStandalone():
    """
    This class creates and manages the Glances standalone session
    """

    def __init__(self, 
                 config=None,
                 refresh_time=3,
                 use_bold=True):
        # Init the limits
        self.limits = glancesLimits(config)

        # Init the monitoring list
        self.monitors = monitorList(config)

        # Init stats
        self.stats = GlancesStats(config)

        # Initial update
        self.stats.update()

        self.refresh_time = refresh_time

        # Init HTML output
        # !!! TODO
        # if html_tag:
        #     htmloutput = glancesHtml(html_path=output_folder,
        #                              refresh_time=refresh_time)

        # Init CSV output
        # !!! TODO
        # if csv_tag:
        #     csvoutput = glancesCsv(cvsfile=output_file,
        #                            refresh_time=refresh_time)

        # Init screen
        # !!! TODO
        # !!! Is refresh_time mandatory for this class ?
        self.screen = glancesCurses(refresh_time=refresh_time,
                                    use_bold=use_bold)


    def serve_forever(self):
        while True:
            # Update system informations
            self.stats.update()

            # Update the screen
            self.screen.update(self.stats)

            # Update the HTML output
            # !!! TODO
            # if html_tag:
            #     htmloutput.update(stats)

            # Update the CSV output
            # !!! TODO
            # if csv_tag:
            #     csvoutput.update(stats)
