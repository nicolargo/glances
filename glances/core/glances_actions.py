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

    def run(self, commands):
        """Run the commands (in background)
        - commands: a list of command line"""

        for cmd in commands:
            logger.info("Action triggered: {0}".format(cmd))
            splitted_cmd = cmd.split()
            Popen(splitted_cmd)
