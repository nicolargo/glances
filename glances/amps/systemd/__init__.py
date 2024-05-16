#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

r"""
Systemd AMP
===========

Monitor the state of the systemd system and service (unit) manager.

How to read the stats
---------------------

active: Number of active units. This is usually a fairly basic way to tell if the
unit has started successfully or not.
loaded: Number of loaded units (unit's configuration has been parsed by systemd).
failed: Number of units with an active failed status.

Source reference: https://www.digitalocean.com/community/tutorials/how-to-use-systemctl-to-manage-systemd-services-and-units

Configuration file example
--------------------------

[amp_systemd]
# Systemd
enable=true
regex=\/usr\/lib\/systemd\/systemd
refresh=60
one_line=true
systemctl_cmd=/usr/bin/systemctl --plain
"""

from subprocess import CalledProcessError, check_output

from glances.amps.amp import GlancesAmp
from glances.globals import iteritems, to_ascii
from glances.logger import logger


class Amp(GlancesAmp):
    """Glances' Systemd AMP."""

    NAME = 'Systemd'
    VERSION = '1.0'
    DESCRIPTION = 'Get services list from systemctl (systemd)'
    AUTHOR = 'Nicolargo'
    EMAIL = 'contact@nicolargo.com'

    # def __init__(self, args=None):
    #     """Init the AMP."""
    #     super(Amp, self).__init__(args=args)

    def update(self, process_list):
        """Update the AMP"""
        # Get the systemctl status
        logger.debug('{}: Update stats using systemctl {}'.format(self.NAME, self.get('systemctl_cmd')))
        try:
            res = check_output(self.get('systemctl_cmd').split())
        except (OSError, CalledProcessError) as e:
            logger.debug(f'{self.NAME}: Error while executing systemctl ({e})')
        else:
            status = {}
            # For each line
            for r in to_ascii(res).split('\n')[1:-8]:
                # Split per space .*
                column = r.split()
                if len(column) > 3:
                    # load column
                    for c in range(1, 3):
                        try:
                            status[column[c]] += 1
                        except KeyError:
                            status[column[c]] = 1
            # Build the output (string) message
            output = 'Services\n'
            for k, v in iteritems(status):
                output += f'{k}: {v}\n'
            self.set_result(output, separator=' ')

        return self.result()
