#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Textual interface class."""

from glances.outputs.tui.app import GlancesTuiApp


class GlancesTextualStandalone:
    """This class manages the Textual user interface."""

    def __init__(self, stats=None, config=None, args=None):
        # Init config
        self.config = config

        # Init args
        self.args = args

        # Init stats
        self.stats = stats

        # Init the textual App
        self.app = self.init_app()

    def init_app(self):
        """Init the Textual app."""
        return GlancesTuiApp(stats=self.stats, config=self.config, args=self.args)

    def start(self):
        """Start the Textual app."""
        self.app.run()

    def end(self):
        """End the Textual app."""
        # TODO: check what is done in this function
        # Is it realy usefull ?
        self.app.exit()
