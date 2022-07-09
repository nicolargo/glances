# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

r"""
Default AMP
=========

Monitor a process by executing a command line. This is the default AMP's behavior
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

from glances.globals import u, to_ascii
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
            self.set_result(
                'CPU: {:.1f}% | MEM: {:.1f}%'.format(
                    sum([p['cpu_percent'] for p in process_list]), sum([p['memory_percent'] for p in process_list])
                )
            )
            return self.result()
        # Run command(s)
        # Comma separated commands can be executed
        try:
            msg = ''
            for cmd in res.split(';'):
                msg += u(check_output(cmd.split(), stderr=STDOUT))
            self.set_result(to_ascii(msg.rstrip()))
        except CalledProcessError as e:
            self.set_result(e.output)
        return self.result()
