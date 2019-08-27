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

"""Manage the Glances standalone session."""

import sys
import time

from glances.globals import WINDOWS
from glances.logger import logger
from glances.processes import glances_processes
from glances.stats import GlancesStats
from glances.outputs.glances_curses import GlancesCursesStandalone
from glances.outputs.glances_stdout import GlancesStdout
from glances.outputs.glances_stdout_csv import GlancesStdoutCsv
from glances.outdated import Outdated
from glances.timer import Counter


class GlancesStandalone(object):

    """This class creates and manages the Glances standalone session."""

    def __init__(self, config=None, args=None):
        self.config = config
        self.args = args

        # Quiet mode
        self._quiet = args.quiet
        self.refresh_time = args.time

        # Init stats
        start_duration = Counter()
        start_duration.reset()
        self.stats = GlancesStats(config=config, args=args)
        logger.debug("Plugins initialisation duration: {} seconds".format(start_duration.get()))

        # Modules (plugins and exporters) are loaded at this point
        # Glances can display the list if asked...
        if args.modules_list:
            self.display_modules_list()
            sys.exit(0)

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

        # Initial system informations update
        start_duration.reset()
        self.stats.update()
        logger.debug("First stats update duration: {} seconds".format(start_duration.get()))

        if self.quiet:
            logger.info("Quiet mode is ON, nothing will be displayed")
            # In quiet mode, nothing is displayed
            glances_processes.max_processes = 0
        elif args.stdout:
            logger.info("Stdout mode is ON, following stats will be displayed: {}".format(args.stdout))
            # Init screen
            self.screen = GlancesStdout(config=config, args=args)
        elif args.stdout_csv:
            logger.info("Stdout CSV mode is ON, following stats will be displayed: {}".format(args.stdout))
            # Init screen
            self.screen = GlancesStdoutCsv(config=config, args=args)
        else:
            # Default number of processes to displayed is set to 50
            glances_processes.max_processes = 50

            # Init screen
            self.screen = GlancesCursesStandalone(config=config, args=args)

        # Check the latest Glances version
        self.outdated = Outdated(config=config, args=args)

    @property
    def quiet(self):
        return self._quiet

    def display_modules_list(self):
        """Display modules list"""
        print("Plugins list: {}".format(
            ', '.join(sorted(self.stats.getPluginsList(enable=False)))))
        print("Exporters list: {}".format(
            ', '.join(sorted(self.stats.getExportsList(enable=False)))))

    def __serve_forever(self):
        """Main loop for the CLI.

        return True if we should continue (no exit key has been pressed)
        """
        # Start a counter used to compute the time needed for
        # update and export the stats
        counter = Counter()

        # Update stats
        self.stats.update()
        logger.debug('Stats updated duration: {} seconds'.format(counter.get()))

        # Export stats
        counter_export = Counter()
        self.stats.export(self.stats)
        logger.debug('Stats exported duration: {} seconds'.format(counter_export.get()))

        # Patch for issue1326 to avoid < 0 refresh
        adapted_refresh = self.refresh_time - counter.get()
        adapted_refresh = adapted_refresh if adapted_refresh > 0 else 0

        # Display stats
        # and wait refresh_time - counter
        if not self.quiet:
            # The update function return True if an exit key 'q' or 'ESC'
            # has been pressed.
            ret = not self.screen.update(self.stats, duration=adapted_refresh)
        else:
            # Nothing is displayed
            # Break should be done via a signal (CTRL-C)
            time.sleep(adapted_refresh)
            ret = True

        return ret

    def serve_forever(self):
        """Wrapper to the serve_forever function."""
        loop = True
        while loop:
            loop = self.__serve_forever()
        self.end()

    def end(self):
        """End of the standalone CLI."""
        if not self.quiet:
            self.screen.end()

        # Exit from export modules
        self.stats.end()

        # Check Glances version versus PyPI one
        if self.outdated.is_outdated():
            print("You are using Glances version {}, however version {} is available.".format(
                self.outdated.installed_version(), self.outdated.latest_version()))
            print("You should consider upgrading using: pip install --upgrade glances")
