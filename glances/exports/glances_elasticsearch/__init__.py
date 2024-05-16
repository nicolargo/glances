#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""ElasticSearch interface class."""

import sys
from datetime import datetime

from elasticsearch import Elasticsearch, helpers

from glances.exports.export import GlancesExport
from glances.logger import logger


class Export(GlancesExport):
    """This class manages the ElasticSearch (ES) export module."""

    def __init__(self, config=None, args=None):
        """Init the ES export IF."""
        super().__init__(config=config, args=args)

        # Mandatory configuration keys (additional to host and port)
        self.index = None

        # Load the ES configuration file
        self.export_enable = self.load_conf(
            'elasticsearch', mandatories=['scheme', 'host', 'port', 'index'], options=[]
        )
        if not self.export_enable:
            sys.exit(2)

        # Init the ES client
        self.client = self.init()

    def init(self):
        """Init the connection to the ES server."""
        if not self.export_enable:
            return None

        try:
            es = Elasticsearch(hosts=[f'{self.scheme}://{self.host}:{self.port}'])
        except Exception as e:
            logger.critical(f"Cannot connect to ElasticSearch server {self.scheme}://{self.host}:{self.port} ({e})")
            sys.exit(2)

        if not es.ping():
            logger.critical(f"Cannot ping the ElasticSearch server {self.scheme}://{self.host}:{self.port}")
            sys.exit(2)
        else:
            logger.info(f"Connected to the ElasticSearch server {self.scheme}://{self.host}:{self.port}")

        return es

    def export(self, name, columns, points):
        """Write the points to the ES server."""
        logger.debug(f"Export {name} stats to ElasticSearch")

        # Generate index name with the index field + current day
        index = '{}-{}'.format(self.index, datetime.utcnow().strftime("%Y.%m.%d"))

        # Create DB input
        # https://elasticsearch-py.readthedocs.io/en/master/helpers.html
        actions = []
        dt_now = datetime.utcnow().isoformat('T')
        action = {
            "_index": index,
            "_id": f'{name}.{dt_now}',
            "_type": f'glances-{name}',
            "_source": {"plugin": name, "timestamp": dt_now},
        }
        action['_source'].update(zip(columns, [str(p) for p in points]))
        actions.append(action)

        logger.debug(f"Exporting the following object to elasticsearch: {action}")

        # Write input to the ES index
        try:
            helpers.bulk(self.client, actions)
        except Exception as e:
            logger.error(f"Cannot export {name} stats to ElasticSearch ({e})")
