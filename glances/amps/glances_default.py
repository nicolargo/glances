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

r"""
Default AMP
=========

Monitor a process by executing a command line. This is the default AMP's behavor
if no AMP script is found.

Configuration file example
--------------------------

[amp_foo]
enable=true
regex=\/usr\/bin\/foo
refresh=10
one_line=false
command=foo status
"""

from subprocess import check_output, STDOUT, CalledProcessError

from glances.compat import u, to_ascii
from glances.logger import logger
from glances.amps.glances_amp import GlancesAmp


class Amp(GlancesAmp):
    """Glances' Default AMP."""

    NAME = ''
    VERSION = '1.1'
    DESCRIPTION = ''
    AUTHOR = 'Nicolargo'
    EMAIL = 'contact@nicolargo.com'

    def __init__(self, name=None, args=None):
        """Init the AMP."""
        self.NAME = name.capitalize()
        super(Amp, self).__init__(name=name, args=args)

    def update(self, process_list):
        """Update the AMP"""
        # Get the systemctl status
        logger.debug('{}: Update AMP stats using command {}'.format(self.NAME, self.get('service_cmd')))
        # Get command to execute
        try:
            res = self.get('command')
        except OSError as e:
            logger.debug('{}: Error while executing command ({})'.format(self.NAME, e))
            return self.result()
        # No command found, use default message
        if res is None:
            # Set the default message if command return None
            # Default sum of CPU and MEM for the matching regex
            self.set_result('CPU: {:.1f}% | MEM: {:.1f}%'.format(
                sum([p['cpu_percent'] for p in process_list]),
                sum([p['memory_percent'] for p in process_list])))
            return self.result()
        # Run command(s)
        # Comman separated commands can be executed
        try:
            msg = ''
            for cmd in res.split(';'):
                msg += u(check_output(cmd.split(), stderr=STDOUT))
            self.set_result(to_ascii(msg.rstrip()))
        except CalledProcessError as e:
            self.set_result(e.output)
        return self.result()
