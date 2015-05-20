# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2015 Nicolargo <nicolas@nicolargo.com>
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

from time import sleep

# Import Glances libs
from glances.core.glances_globals import is_windows
from glances.core.glances_logging import logger
from glances.core.glances_processes import glances_processes
from glances.core.glances_stats import GlancesStats
from glances.outputs.glances_curses import GlancesCursesStandalone


class GlancesStandalone(object):

    """This class creates and manages the Glances standalone session."""

    def __init__(self, config=None, args=None):
        # Quiet mode
        self._quiet = args.quiet
        self.refresh_time = args.time

        # Init stats
        self.stats = GlancesStats(config=config, args=args)

        # If process extended stats is disabled by user
        if not args.enable_process_extended:
            logger.debug("Extended stats for top process are disabled")
            glances_processes.disable_extended()
        else:
            logger.debug("Extended stats for top process are enabled")
            glances_processes.enable_extended()

        # Manage optionnal process filter
        if args.process_filter is not None:
            glances_processes.process_filter = args.process_filter

        if (not is_windows) and args.no_kernel_threads:
            # Ignore kernel threads in process list
            glances_processes.disable_kernel_threads()

        try:
            if args.process_tree:
                # Enable process tree view
                glances_processes.enable_tree()
        except AttributeError:
            pass

        # Initial system informations update
        self.stats.update()

        if self.quiet:
            logger.info("Quiet mode is ON: Nothing will be displayed")
            # In quiet mode, nothing is displayed
            glances_processes.max_processes = 0
        else:
            # Default number of processes to displayed is set to 50
            glances_processes.max_processes = 50

            # Init screen
            self.screen = GlancesCursesStandalone(args=args)

    @property
    def quiet(self):
        return self._quiet

    def __serve_forever(self):
        """Main loop for the CLI."""
        while True:
            # Update system informations
            self.stats.update()

            if not self.quiet:
                # Update the screen
                self.screen.update(self.stats)
            else:
                # Wait...
                sleep(self.refresh_time)

            # Export stats using export modules
            self.stats.export(self.stats)

    def serve_forever(self):
        """Wrapper to the serve_forever function.

        This function will restore the terminal to a sane state
        before re-raising the exception and generating a traceback.
        """
        try:
            return self.__serve_forever()
        finally:
            self.end()

    def end(self):
        """End of the standalone CLI."""
        if not self.quiet:
            self.screen.end()

        # Exit from export modules
        self.stats.end()
