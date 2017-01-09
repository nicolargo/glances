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

"""Manage the Glances standalone session."""

import sched
import time

from glances.globals import WINDOWS
from glances.logger import logger
from glances.processes import glances_processes
from glances.stats import GlancesStats
from glances.outputs.glances_curses import GlancesCursesStandalone
from glances.outdated import Outdated


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

        if (not WINDOWS) and args.no_kernel_threads:
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
            self.screen = GlancesCursesStandalone(config=config, args=args)

        # Check the latest Glances version
        self.outdated = Outdated(config=config, args=args)

        # Create the schedule instance
        self.schedule = sched.scheduler(
            timefunc=time.time, delayfunc=time.sleep)

    @property
    def quiet(self):
        return self._quiet

    def __serve_forever(self):
        """Main loop for the CLI."""
        # Reschedule the function inside itself
        self.schedule.enter(self.refresh_time, priority=0,
                            action=self.__serve_forever, argument=())

        # Update system informations
        self.stats.update()

        # Update the screen
        if not self.quiet:
            self.screen.update(self.stats)

        # Export stats using export modules
        self.stats.export(self.stats)

    def serve_forever(self):
        """Wrapper to the serve_forever function.

        This function will restore the terminal to a sane state
        before re-raising the exception and generating a traceback.
        """
        self.__serve_forever()
        try:
            self.schedule.run()
        finally:
            self.end()

    def end(self):
        """End of the standalone CLI."""
        if not self.quiet:
            self.screen.end()

        # Exit from export modules
        self.stats.end()

        # Check Glances version versus Pypi one
        if self.outdated.is_outdated():
            print("You are using Glances version {}, however version {} is available.".format(
                self.outdated.installed_version(), self.outdated.latest_version()))
            print("You should consider upgrading using: pip install --upgrade glances")
