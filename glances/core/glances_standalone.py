# -*- coding: utf-8 -*-
#
# This file is part of Glances.
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

"""Manage the Glances standalone session."""

# Import Glances libs
from glances.core.glances_globals import logger
from glances.core.glances_stats import GlancesStats
from glances.outputs.glances_curses import GlancesCurses
from glances.core.glances_globals import glances_processes


class GlancesStandalone(object):

    """This class creates and manages the Glances standalone session."""

    def __init__(self, config=None, args=None):
        # Init stats
        self.stats = GlancesStats(config=config, args=args)

        # If configured, set the maximum processes number to display
        try:
            max_processes = int(self.stats.get_plugin('processlist').get_conf_value('max_processes'))
            logger.debug(_("Limit maximum displayed processes to %s") % max_processes)
        except:
            max_processes = None
            logger.warning(_("Maximum displayed processes is not configured (high CPU consumption)"))
        glances_processes.set_max_processes(max_processes)

        # Initial system informations update
        self.stats.update()

        # Init CSV output
        if args.output_csv is not None:
            from glances.outputs.glances_csv import GlancesCSV

            self.csvoutput = GlancesCSV(args=args)
            self.csv_tag = True
        else:
            self.csv_tag = False

        # Init screen
        self.screen = GlancesCurses(args=args)

    def serve_forever(self):
        """Main loop for the CLI."""
        while True:
            # Update system informations
            self.stats.update()

            # Update the screen
            self.screen.update(self.stats)

            # Update the CSV output
            if self.csv_tag:
                self.csvoutput.update(self.stats)

    def end(self):
        """End of the CLI."""
        self.screen.end()

        # Close the CSV file
        if self.csv_tag:
            self.csvoutput.exit()
