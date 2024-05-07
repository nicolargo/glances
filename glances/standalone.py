# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage the Glances standalone session."""

import sys
import time

from glances.logger import logger

from glances.globals import WINDOWS
from glances.processes import glances_processes
from glances.stats import GlancesStats
from glances.outputs.glances_curses import GlancesCursesStandalone
from glances.outputs.glances_stdout import GlancesStdout
from glances.outputs.glances_stdout_json import GlancesStdoutJson
from glances.outputs.glances_stdout_csv import GlancesStdoutCsv
from glances.outputs.glances_stdout_issue import GlancesStdoutIssue
from glances.outputs.glances_stdout_apidoc import GlancesStdoutApiDoc
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

        # The args is needed to get the selected process in the process list (Curses mode)
        glances_processes.set_args(args)

        # If process extended stats is disabled by user
        if not args.enable_process_extended:
            logger.debug("Extended stats for top process are disabled")
            glances_processes.disable_extended()
        else:
            logger.debug("Extended stats for top process are enabled")
            glances_processes.enable_extended()

        # Manage optional process filter
        if args.process_filter is not None:
            logger.info("Process filter is set to: {}".format(args.process_filter))
            glances_processes.process_filter = args.process_filter

        if (args.export or args.stdout) and args.export_process_filter is not None:
            logger.info("Export process filter is set to: {}".format(args.export_process_filter))
            glances_processes.export_process_filter = args.export_process_filter

        if (not WINDOWS) and args.no_kernel_threads:
            # Ignore kernel threads in process list
            glances_processes.disable_kernel_threads()

        # Initial system information update
        start_duration.reset()
        self.stats.update()
        logger.debug("First stats update duration: {} seconds".format(start_duration.get()))

        if self.quiet:
            logger.info("Quiet mode is ON, nothing will be displayed")
            # In quiet mode, nothing is displayed
            glances_processes.max_processes = 0
        elif args.stdout_issue:
            logger.info("Issue mode is ON")
            # Init screen
            self.screen = GlancesStdoutIssue(config=config, args=args)
        elif args.stdout_apidoc:
            logger.info("Fields descriptions mode is ON")
            # Init screen
            self.screen = GlancesStdoutApiDoc(config=config, args=args)
        elif args.stdout:
            logger.info("Stdout mode is ON, following stats will be displayed: {}".format(args.stdout))
            # Init screen
            self.screen = GlancesStdout(config=config, args=args)
        elif args.stdout_json:
            logger.info("Stdout JSON mode is ON, following stats will be displayed: {}".format(args.stdout_json))
            # Init screen
            self.screen = GlancesStdoutJson(config=config, args=args)
        elif args.stdout_csv:
            logger.info("Stdout CSV mode is ON, following stats will be displayed: {}".format(args.stdout_csv))
            # Init screen
            self.screen = GlancesStdoutCsv(config=config, args=args)
        else:
            # Default number of processes to displayed is set to 50
            glances_processes.max_processes = 50

            # Init screen
            self.screen = GlancesCursesStandalone(config=config, args=args)

            # If an error occur during the screen init, continue if export option is set
            # It is done in the screen.init function
            self._quiet = args.quiet

        # Check the latest Glances version
        self.outdated = Outdated(config=config, args=args)

    @property
    def quiet(self):
        return self._quiet

    def display_modules_list(self):
        """Display modules list"""
        print("Plugins list: {}".format(', '.join(sorted(self.stats.getPluginsList(enable=False)))))
        print("Exporters list: {}".format(', '.join(sorted(self.stats.getExportsList(enable=False)))))

    def serve_issue(self):
        """Special mode for the --issue option

        Update is done in the screen.update function
        """
        ret = not self.screen.update(self.stats)
        self.end()
        return ret

    def __serve_once(self):
        """Main loop for the CLI.

        :return: True if we should continue (no exit key has been pressed)
        """
        # Update stats
        # Start a counter used to compute the time needed
        counter = Counter()
        self.stats.update()
        logger.debug('Stats updated duration: {} seconds'.format(counter.get()))

        # Patch for issue1326 to avoid < 0 refresh
        adapted_refresh = (self.refresh_time - counter.get()) if (self.refresh_time - counter.get()) > 0 else 0

        # Display stats
        # and wait refresh_time - counter
        if not self.quiet:
            # The update function return True if an exit key 'q' or 'ESC'
            # has been pressed.
            counter_display = Counter()
            ret = not self.screen.update(self.stats, duration=adapted_refresh)
            logger.debug('Stats display duration: {} seconds'.format(counter_display.get() - adapted_refresh))
        else:
            # Nothing is displayed
            # Break should be done via a signal (CTRL-C)
            time.sleep(adapted_refresh)
            ret = True

        # Export stats
        # Start a counter used to compute the time needed
        counter_export = Counter()
        self.stats.export(self.stats)
        logger.debug('Stats exported duration: {} seconds'.format(counter_export.get()))

        return ret

    def serve_n(self, n=1):
        """Serve n time."""
        for _ in range(n):
            if not self.__serve_once():
                break
        # self.end()

    def serve_forever(self):
        """Wrapper to the serve_forever function."""
        if self.args.stop_after:
            self.serve_n(self.args.stop_after)
        else:
            while self.__serve_once():
                pass
        # self.end()

    def end(self):
        """End of the standalone CLI."""
        if not self.quiet:
            self.screen.end()

        # Exit from export modules
        self.stats.end()

        # Check Glances version versus PyPI one
        if self.outdated.is_outdated():
            print(
                "You are using Glances version {}, however version {} is available.".format(
                    self.outdated.installed_version(), self.outdated.latest_version()
                )
            )
            print("You should consider upgrading using: pip install --upgrade glances")
            print("Disable this warning temporarily using: glances --disable-check-update")
            print(
                "To disable it permanently, refer config reference at "
                "https://glances.readthedocs.io/en/latest/config.html#syntax"
            )
