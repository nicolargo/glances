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
Nginx AMP
=========

Monitor the Nginx process using the status page.

How to read the stats
---------------------

Active connections – Number of all open connections. This doesn’t mean number of users.
A single user, for a single pageview can open many concurrent connections to your server.
Server accepts handled requests – This shows three values.
    First is total accepted connections.
    Second is total handled connections. Usually first 2 values are same.
    Third value is number of and handles requests. This is usually greater than second value.
    Dividing third-value by second-one will give you number of requests per connection handled
    by Nginx. In above example, 10993/7368, 1.49 requests per connections.
Reading – nginx reads request header
Writing – nginx reads request body, processes request, or writes response to a client
Waiting – keep-alive connections, actually it is active – (reading + writing).
This value depends on keepalive-timeout. Do not confuse non-zero waiting value for poor
performance. It can be ignored.

Source reference: https://easyengine.io/tutorials/nginx/status-page/

Configuration file example
--------------------------

[amp_nginx]
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

    NAME = 'Nginx'
    VERSION = '1.0'
    DESCRIPTION = 'Get Nginx stats from status-page'
    AUTHOR = 'Nicolargo'
    EMAIL = 'contact@nicolargo.com'

    # def __init__(self, args=None):
    #     """Init the AMP."""
    #     super(Amp, self).__init__(args=args)

    def update(self, process_list):
        """Update the AMP"""
        # Get the Nginx status
        logger.debug('{}: Update stats using status URL {}'.format(self.NAME, self.get('status_url')))
        res = requests.get(self.get('status_url'))
        if res.ok:
            # u'Active connections: 1 \nserver accepts handled requests\n 1 1 1 \nReading: 0 Writing: 1 Waiting: 0 \n'
            self.set_result(res.text.rstrip())
        else:
            logger.debug('{}: Can not grab status URL {} ({})'.format(self.NAME, self.get('status_url'), res.reason))

        return self.result()
