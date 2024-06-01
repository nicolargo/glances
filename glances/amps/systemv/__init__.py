#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

r"""
SystemV AMP
===========

Monitor the state of the System V init system and service.

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

from glances.amps.amp import GlancesAmp
from glances.globals import iteritems
from glances.logger import logger
from glances.secure import secure_popen


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
            # res = check_output(self.get('service_cmd').split(), stderr=STDOUT).decode('utf-8')
            res = secure_popen(self.get('service_cmd'))
        except Exception as e:
            logger.debug(f'{self.NAME}: Error while executing service ({e})')
        else:
            status = {'running': 0, 'stopped': 0, 'upstart': 0}
            # For each line
            for r in res.split('\n'):
                # Split per space .*
                line = r.split()
                if len(line) < 4:
                    continue
                if line[1] == '+':
                    status['running'] += 1
                elif line[1] == '-':
                    status['stopped'] += 1
                elif line[1] == '?':
                    status['upstart'] += 1
            # Build the output (string) message
            output = 'Services\n'
            for k, v in iteritems(status):
                output += f'{k}: {v}\n'
            self.set_result(output, separator=' ')

        return self.result()
