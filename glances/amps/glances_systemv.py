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
SystemV AMP
===========

Monitor the state of the Syste V init system and service.

How to read the stats
---------------------

Running: Number of running services.
Stopped: Number of stopped services.
Upstart: Number of service managed by Upstart.

Source reference: http://askubuntu.com/questions/407075/how-to-read-service-status-all-results

Configuration file example
--------------------------

[amp_systemv]
# Systemv
enable=true
regex=\/sbin\/init
refresh=60
one_line=true
service_cmd=/usr/bin/service --status-all
"""

from subprocess import check_output, STDOUT

from glances.logger import logger
from glances.compat import iteritems
from glances.amps.glances_amp import GlancesAmp


class Amp(GlancesAmp):
    """Glances' Systemd AMP."""

    NAME = 'SystemV'
    VERSION = '1.0'
    DESCRIPTION = 'Get services list from service (initd)'
    AUTHOR = 'Nicolargo'
    EMAIL = 'contact@nicolargo.com'

    # def __init__(self, args=None):
    #     """Init the AMP."""
    #     super(Amp, self).__init__(args=args)

    def update(self, process_list):
        """Update the AMP"""
        # Get the systemctl status
        logger.debug('{}: Update stats using service {}'.format(self.NAME, self.get('service_cmd')))
        try:
            res = check_output(self.get('service_cmd').split(), stderr=STDOUT).decode('utf-8')
        except OSError as e:
            logger.debug('{}: Error while executing service ({})'.format(self.NAME, e))
        else:
            status = {'running': 0, 'stopped': 0, 'upstart': 0}
            # For each line
            for r in res.split('\n'):
                # Split per space .*
                l = r.split()
                if len(l) < 4:
                    continue
                if l[1] == '+':
                    status['running'] += 1
                elif l[1] == '-':
                    status['stopped'] += 1
                elif l[1] == '?':
                    status['upstart'] += 1
            # Build the output (string) message
            output = 'Services\n'
            for k, v in iteritems(status):
                output += '{}: {}\n'.format(k, v)
            self.set_result(output, separator=' ')

        return self.result()
