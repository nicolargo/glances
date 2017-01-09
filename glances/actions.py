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

"""Manage on alert actions."""

from subprocess import Popen

from glances.logger import logger
from glances.timer import Timer

try:
    import pystache
except ImportError:
    logger.debug("Pystache library not found (action scripts won't work)")
    pystache_tag = False
else:
    pystache_tag = True


class GlancesActions(object):

    """This class manage action if an alert is reached."""

    def __init__(self, args=None):
        """Init GlancesActions class."""
        # Dict with the criticity status
        # - key: stat_name
        # - value: criticity
        # Goal: avoid to execute the same command twice
        self.status = {}

        # Add a timer to avoid any trigger when Glances is started (issue#732)
        # Action can be triggered after refresh * 2 seconds
        if hasattr(args, 'time'):
            self.start_timer = Timer(args.time * 2)
        else:
            self.start_timer = Timer(3)

    def get(self, stat_name):
        """Get the stat_name criticity."""
        try:
            return self.status[stat_name]
        except KeyError:
            return None

    def set(self, stat_name, criticity):
        """Set the stat_name to criticity."""
        self.status[stat_name] = criticity

    def run(self, stat_name, criticity, commands, mustache_dict=None):
        """Run the commands (in background).

        - stats_name: plugin_name (+ header)
        - criticity: criticity of the trigger
        - commands: a list of command line with optional {{mustache}}
        - mustache_dict: Plugin stats (can be use within {{mustache}})

        Return True if the commands have been ran.
        """
        if self.get(stat_name) == criticity or not self.start_timer.finished():
            # Action already executed => Exit
            return False

        logger.debug("Run action {} for {} ({}) with stats {}".format(
            commands, stat_name, criticity, mustache_dict))

        # Run all actions in background
        for cmd in commands:
            # Replace {{arg}} by the dict one (Thk to {Mustache})
            if pystache_tag:
                cmd_full = pystache.render(cmd, mustache_dict)
            else:
                cmd_full = cmd
            # Execute the action
            logger.info("Action triggered for {} ({}): {}".format(stat_name, criticity, cmd_full))
            logger.debug("Stats value for the trigger: {}".format(mustache_dict))
            try:
                Popen(cmd_full, shell=True)
            except OSError as e:
                logger.error("Can't execute the action ({})".format(e))

        self.set(stat_name, criticity)

        return True
