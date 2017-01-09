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

"""
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

from subprocess import check_output

from glances.logger import logger
from glances.compat import iteritems, to_ascii
from glances.amps.glances_amp import GlancesAmp


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
        except OSError as e:
            logger.debug('{}: Error while executing systemctl ({})'.format(self.NAME, e))
        else:
            status = {}
            # For each line
            for r in to_ascii(res).split('\n')[1:-8]:
                # Split per space .*
                l = r.split()
                if len(l) > 3:
                    # load column
                    for c in range(1, 3):
                        try:
                            status[l[c]] += 1
                        except KeyError:
                            status[l[c]] = 1
            # Build the output (string) message
            output = 'Services\n'
            for k, v in iteritems(status):
                output += '{}: {}\n'.format(k, v)
            self.set_result(output, separator=' ')

        return self.result()
