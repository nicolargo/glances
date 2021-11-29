# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2021 Nicolargo <nicolas@nicolargo.com>
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

from glances.logger import logger
from glances.timer import Timer
from glances.secure import secure_popen

try:
    import chevron
except ImportError:
    logger.debug("Chevron library not found (action scripts won't work)")
    chevron_tag = False
else:
    chevron_tag = True


class GlancesActions(object):

    """This class manage action if an alert is reached."""

    def __init__(self, args=None):
        """Init GlancesActions class."""
        # Dict with the criticality status
        # - key: stat_name
        # - value: criticality
        # Goal: avoid to execute the same command twice
        self.status = {}

        # Add a timer to avoid any trigger when Glances is started (issue#732)
        # Action can be triggered after refresh * 2 seconds
        if hasattr(args, 'time'):
            self.start_timer = Timer(args.time * 2)
        else:
            self.start_timer = Timer(3)

    def get(self, stat_name):
        """Get the stat_name criticality."""
        try:
            return self.status[stat_name]
        except KeyError:
            return None

    def set(self, stat_name, criticality):
        """Set the stat_name to criticality."""
        self.status[stat_name] = criticality

    def run(self, stat_name, criticality, commands, repeat, mustache_dict=None):
        """Run the commands (in background).

        :param stat_name: plugin_name (+ header)
        :param criticality: criticality of the trigger
        :param commands: a list of command line with optional {{mustache}}
        :param repeat: If True, then repeat the action
        :param  mustache_dict: Plugin stats (can be use within {{mustache}})

        :return: True if the commands have been ran.
        """
        if (self.get(stat_name) == criticality and not repeat) or not self.start_timer.finished():
            # Action already executed => Exit
            return False

        logger.debug(
            "{} action {} for {} ({}) with stats {}".format(
                "Repeat" if repeat else "Run", commands, stat_name, criticality, mustache_dict
            )
        )

        # Run all actions in background
        for cmd in commands:
            # Replace {{arg}} by the dict one (Thk to {Mustache})
            if chevron_tag:
                cmd_full = chevron.render(cmd, mustache_dict)
            else:
                cmd_full = cmd
            # Execute the action
            logger.info("Action triggered for {} ({}): {}".format(stat_name, criticality, cmd_full))
            try:
                ret = secure_popen(cmd_full)
            except OSError as e:
                logger.error("Action error for {} ({}): {}".format(stat_name, criticality, e))
            else:
                logger.debug("Action result for {} ({}): {}".format(stat_name, criticality, ret))

        self.set(stat_name, criticality)

        return True
