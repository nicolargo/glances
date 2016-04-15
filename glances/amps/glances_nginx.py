# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2016 Nicolargo <nicolas@nicolargo.com>
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

"""Nginx AMP."""

import requests

from glances.logger import logger
from glances.amps.glances_amp import GlancesAmp


class Amp(GlancesAmp):

    """Glances' Nginx AMP."""

    # def __init__(self, args=None):
    #     """Init the AMP."""
    #     super(Amp, self).__init__(args=args)

    def update(self):
        """Update the AMP"""

        if self.should_update():
            logger.debug('AMPS: Update {0} using status URL {1}'.format(self.amp_name, self.get('status_url')))
            # Get the Nginx status
            req = requests.get(self.get('status_url'))
            if req.ok:
                # u'Active connections: 1 \nserver accepts handled requests\n 1 1 1 \nReading: 0 Writing: 1 Waiting: 0 \n'
                if self.get('one_line') is not None and self.get('one_line').lower() == 'true':
                    self.set_result(req.text.replace('\n', ''))
                else:
                    self.set_result(req.text)
            else:
                logger.debug('AMPS: Can not grab status URL {0} ({1})'.format(self.get('status_url'), req.reason))

        return self.result()
