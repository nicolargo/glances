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

"""Manage on alert actions."""

# Import system lib
from subprocess import Popen

# Import Glances lib
from glances.core.glances_logging import logger


class GlancesActions(object):

    """This class manage action if an alert is reached"""

    def __init__(self):
        """Init GlancesActions class"""

        # Dict with the criticity status
        # - key: stat_name
        # - value: criticity
        # Goal: avoid to execute the same command twice
        self.status = {}

    def get(self, stat_name):
        """Get the stat_name criticity"""
        try:
            return self.status[stat_name]
        except KeyError:
            return None

    def set(self, stat_name, criticity):
        """Set the stat_name to criticity"""
        self.status[stat_name] = criticity

    def run(self, stat_name, criticity, commands):
        """Run the commands (in background)
        - stats_name: plugin_name (+ header)
        - criticity: criticity of the trigger
        - commands: a list of command line

        Return True if the commands have been ran"""

        if self.get(stat_name) == criticity:
            # Action already executed => Exit
            return False

        # Ran all actions in background
        for cmd in commands:
            logger.info("Action triggered for {0} ({1}): {2}".format(stat_name, criticity, cmd))
            splitted_cmd = cmd.split()
            Popen(splitted_cmd)

        self.set(stat_name, criticity)

        return True
