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

"""ElasticSearch interface class."""

import sys
from datetime import datetime

from glances.logger import logger
from glances.exports.glances_export import GlancesExport

from elasticsearch import Elasticsearch, helpers


class Export(GlancesExport):

    """This class manages the ElasticSearch (ES) export module."""

    def __init__(self, config=None, args=None):
        """Init the ES export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Mandatories configuration keys (additional to host and port)
        self.index = None

        # Optionals configuration keys
        # N/A

        # Load the ES configuration file
        self.export_enable = self.load_conf('elasticsearch',
                                            mandatories=['host', 'port', 'index'],
                                            options=[])
        if not self.export_enable:
            sys.exit(2)

        # Init the ES client
        self.client = self.init()

    def init(self):
        """Init the connection to the ES server."""
        if not self.export_enable:
            return None

        try:
            es = Elasticsearch(hosts=['{}:{}'.format(self.host, self.port)])
        except Exception as e:
            logger.critical("Cannot connect to ElasticSearch server %s:%s (%s)" % (self.host, self.port, e))
            sys.exit(2)
        else:
            logger.info("Connected to the ElasticSearch server %s:%s" % (self.host, self.port))

        try:
            index_count = es.count(index=self.index)['count']
        except Exception as e:
            # Index did not exist, it will be created at the first write
            # Create it...
            es.indices.create(self.index)
        else:
            logger.info("There is already %s entries in the ElasticSearch %s index" % (index_count, self.index))

        return es

    def export(self, name, columns, points):
        """Write the points to the ES server."""
        logger.debug("Export {} stats to ElasticSearch".format(name))

        # Create DB input
        # https://elasticsearch-py.readthedocs.io/en/master/helpers.html
        actions = []
        for c, p in zip(columns, points):
            action = {
                "_index": self.index,
                "_type": name,
                "_id": c,
                "_source": {
                    "value": str(p),
                    "timestamp": datetime.now()
                }
            }
            actions.append(action)

        # Write input to the ES index
        try:
            helpers.bulk(self.client, actions)
        except Exception as e:
            logger.error("Cannot export {} stats to ElasticSearch ({})".format(name, e))
