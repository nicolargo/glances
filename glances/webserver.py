#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances Restful/API and Web based interface."""

from glances.globals import WINDOWS
from glances.outputs.glances_restful_api import GlancesRestfulApi
from glances.processes import glances_processes
from glances.stats import GlancesStats


class GlancesWebServer:
    """This class creates and manages the Glances Web server session."""

    def __init__(self, config=None, args=None):
        # Init stats
        self.stats = GlancesStats(config, args)

        if not WINDOWS and args.no_kernel_threads:
            # Ignore kernel threads in process list
            glances_processes.disable_kernel_threads()

        # Set the args for the glances_processes instance
        glances_processes.set_args(args)

        # Initial system information update
        self.stats.update()

        # Init the Web server
        self.web = GlancesRestfulApi(config=config, args=args)

    def serve_forever(self):
        """Main loop for the Web server."""
        self.web.start(self.stats)

    def end(self):
        """End of the Web server."""
        self.web.end()
        self.stats.end()
