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

"""CloudAdmin HTTP interface class."""
import os
import csv
import sys
import time
import json
import requests
import datetime
import ConfigParser
from numbers import Number

from glances import __version__
from glances.compat import PY3, iterkeys, itervalues
from glances.logger import logger
from glances.exports.glances_export_bulk import GlancesExportBulk

class Export(GlancesExportBulk):

    """This class manages the CSV export module."""

    def __init__(self, config=None, args=None):
        """Init the CSV export IF."""
        super(Export, self).__init__(config=config, args=args)

        self.version = __version__
        #parse our config file
        config = ConfigParser.RawConfigParser()
        config.read('/etc/cloudadmin/cloudadmin.conf')
        self.api_key = config.get('CloudAdmin','APIKey')
        self.http_endpoint = config.get('CloudAdmin','URL')
        self.host = config.get('CloudAdmin','Host')

        metadata = {
          #so we actually know which user is sending us this data
          'api-key' : self.api_key,
          'version' : self.version,
        }

        headers = {
          'apikey' : self.api_key,
          'host' : self.host,
        }

        self.metadata = metadata
        self.headers = headers

        self.bulk = {}

        self.export_enable = True

    def export(self, name, columns, points):
      data = {k: v for (k, v) in dict(zip(columns, points)).iteritems()}
      self.bulk[name] = data

    def flush(self):
      self.bulk['metadata'] = self.metadata
      self.bulk['sent_at'] = str(datetime.datetime.utcnow())
      if 'TEST' in os.environ:
        f = open('/tmp/glances-out', 'w')
        f.write(json.dumps(self.bulk))
        f.close()
        os._exit(0)
      else:
        r = requests.post(self.http_endpoint, json=self.bulk, headers=self.headers)
      self.bulk = {}
