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

"""
AMP (Application Monitoring Process)
A Glances AMP is a Python script called (every *refresh* seconds) if:
- the AMP is *enabled* in the Glances configuration file
- a process is running (match the *regex* define in the configuration file)
The script should define a Amp (GlancesAmp) class with, at least, an update method.
The update method should call the set_result method to set the AMP return string.
The return string is a string with one or more line (\n between lines).
If the *one_line* var is true then the AMP will be displayed in one line.
"""

"""
Nginx AMP
=========

Monitor the Nginx process using the status page

Configuration file example:

[nginx]
# Nginx status page should be enable (https://easyengine.io/tutorials/nginx/status-page/)
enable=true
regex=\/usr\/sbin\/nginx
refresh=60
one_line=false
status_url=http://localhost/nginx_status
"""

import requests

from glances.logger import logger
from glances.amps.glances_amp import GlancesAmp


class Amp(GlancesAmp):
    """Glances' Nginx AMP."""

    NAME = 'Nginx Glances AMP'
    VERSION = '1.0'
    DESCRIPTION = 'Get Nginx stats from status-page'
    AUTHOR = 'Nicolargo'
    EMAIL = 'contact@nicolargo.com'

    # def __init__(self, args=None):
    #     """Init the AMP."""
    #     super(Amp, self).__init__(args=args)

    def update(self):
        """Update the AMP"""

        if self.should_update():
            # Get the Nginx status
            logger.debug('{0}: Update stats using status URL {1}'.format(self.NAME, self.get('status_url')))
            req = requests.get(self.get('status_url'))
            if req.ok:
                # u'Active connections: 1 \nserver accepts handled requests\n 1 1 1 \nReading: 0 Writing: 1 Waiting: 0 \n'
                if self.get('one_line') is not None and self.get('one_line').lower() == 'true':
                    self.set_result(req.text.replace('\n', ''))
                else:
                    self.set_result(req.text)
            else:
                logger.debug('{0}: Can not grab status URL {1} ({2})'.format(self.NAME, self.get('status_url'), req.reason))

        return self.result()
