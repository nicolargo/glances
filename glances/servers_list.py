#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage the servers list used in TUI and WEBUI Central Browser mode"""

import threading

from defusedxml import xmlrpc

from glances import __apiversion__
from glances.client import GlancesClientTransport
from glances.globals import json_loads
from glances.logger import logger
from glances.password_list import GlancesPasswordList as GlancesPassword
from glances.servers_list_dynamic import GlancesAutoDiscoverServer
from glances.servers_list_static import GlancesStaticServer

try:
    import requests
except ImportError as e:
    import_requests_error_tag = True
    # Display debug message if import error
    logger.warning(f"Missing Python Lib ({e}), Client browser will not grab stats from Glances REST server")
else:
    import_requests_error_tag = False

# Correct issue #1025 by monkey path the xmlrpc lib
xmlrpc.monkey_patch()

DEFAULT_COLUMNS = "system:hr_name,load:min5,cpu:total,mem:percent"


class GlancesServersList:
    _section = "serverlist"

    def __init__(self, config=None, args=None):
        # Store the arg/config
        self.args = args
        self.config = config

        # Init the servers and passwords list defined in the Glances configuration file
        self.static_server = None
        self.password = None
        self.load()

        # Init the dynamic servers list by starting a Zeroconf listener
        self.autodiscover_server = None
        if self.args.browser or not self.args.disable_autodiscover:
            self.autodiscover_server = GlancesAutoDiscoverServer()

        # Stats are updated in thread
        # Create a dict of threads
        self.threads_list = {}

    def load(self):
        """Load server and password list from the configuration file."""
        # Init the static server list
        self.static_server = GlancesStaticServer(config=self.config)
        # Init the password list (if defined)
        self.password = GlancesPassword(config=self.config)
        # Load columns to grab/display
        self._columns = self.load_columns()

    def load_columns(self):
        """Load columns definition from the configuration file.
        Read:   'system:hr_name,load:min5,cpu:total,mem:percent,sensors:value:Ambient'
        Return: [{'plugin': 'system', 'field': 'hr_name'},
                 {'plugin': 'load', 'field': 'min5'},
                 {'plugin': 'cpu', 'field': 'total'},
                 {'plugin': 'mem', 'field': 'percent'},
                 {'plugin': 'sensors', 'field': 'value', 'key': 'Ambient'}]
        """
        if self.config is None:
            logger.debug("No configuration file available. Cannot load columns definition.")
        elif not self.config.has_section(self._section):
            logger.warning(f"No [{self._section}] section in the configuration file. Cannot load columns definition.")

        columns_def = (
            self.config.get_value(self._section, 'columns')
            if self.config.get_value(self._section, 'columns')
            else DEFAULT_COLUMNS
        )

        return [dict(zip(['plugin', 'field', 'key'], i.split(':'))) for i in columns_def.split(',')]

    def get_servers_list(self):
        """Return the current server list (list of dict).

        Merge of static + autodiscover servers list.
        """
        ret = []

        if self.args.browser:
            ret = self.static_server.get_servers_list()
            if self.autodiscover_server is not None:
                ret = self.static_server.get_servers_list() + self.autodiscover_server.get_servers_list()

        return ret

    def get_columns(self):
        """Return the columns definitions"""
        return self._columns

    def update_servers_stats(self):
        """For each server in the servers list, update the stats"""
        for v in self.get_servers_list():
            key = v["key"]
            thread = self.threads_list.get(key, None)
            if thread is None or thread.is_alive() is False:
                thread = threading.Thread(target=self.__update_stats, args=[v])
                self.threads_list[key] = thread
                thread.start()

    def get_uri(self, server):
        """Return the URI for the given server dict."""
        # Select the connection mode (with or without password)
        if server['password'] != "":
            if server['status'] == 'PROTECTED':
                # Try with the preconfigure password (only if status is PROTECTED)
                clear_password = self.password.get_password(server['name'])
                if clear_password is not None:
                    server['password'] = self.password.get_hash(clear_password)
            uri = 'http://{}:{}@{}:{}'.format(server['username'], server['password'], server['ip'], server['port'])
        else:
            uri = 'http://{}:{}'.format(server['ip'], server['port'])
        return uri

    def set_in_selected(self, selected, key, value):
        """Set the (key, value) for the selected server in the list."""
        # Static list then dynamic one
        if selected >= len(self.static_server.get_servers_list()):
            self.autodiscover_server.set_server(selected - len(self.static_server.get_servers_list()), key, value)
        else:
            self.static_server.set_server(selected, key, value)

    def __update_stats(self, server):
        """Update stats for the given server"""
        server['uri'] = self.get_uri(server)
        server['columns'] = [self.__get_key(column) for column in self.get_columns()]
        if server['protocol'].lower() == 'rpc':
            self.__update_stats_rpc(server['uri'], server)
        elif server['protocol'].lower() == 'rest' and not import_requests_error_tag:
            self.__update_stats_rest(f"{server['uri']}/api/{__apiversion__}", server)

        return server

    def __update_stats_rpc(self, uri, server):
        # Try to connect to the server
        t = GlancesClientTransport()
        t.set_timeout(3)

        # Get common stats from Glances server
        try:
            s = xmlrpc.xmlrpc_client.ServerProxy(uri, transport=t)
        except Exception as e:
            logger.warning(f"Client browser couldn't create socket ({e})")
            return server

        # Get the stats
        for column in self.get_columns():
            server_key = self.__get_key(column)
            try:
                # Value
                v_json = json_loads(s.getPlugin(column['plugin']))
                if 'key' in column:
                    v_json = [i for i in v_json if i[i['key']].lower() == column['key'].lower()][0]
                server[server_key] = v_json[column['field']]
                # Decoration
                d_json = json_loads(s.getPluginView(column['plugin']))
                if 'key' in column:
                    d_json = d_json.get(column['key'])
                server[server_key + '_decoration'] = d_json[column['field']]['decoration']
            except (KeyError, IndexError, xmlrpc.xmlrpc_client.Fault) as e:
                logger.debug(f"Error while grabbing stats form server ({e})")
            except OSError as e:
                logger.debug(f"Error while grabbing stats form server ({e})")
                server['status'] = 'OFFLINE'
            except xmlrpc.xmlrpc_client.ProtocolError as e:
                if e.errcode == 401:
                    # Error 401 (Authentication failed)
                    # Password is not the good one...
                    server['password'] = None
                    server['status'] = 'PROTECTED'
                else:
                    server['status'] = 'OFFLINE'
                logger.debug(f"Cannot grab stats from server ({e.errcode} {e.errmsg})")
            else:
                # Status
                server['status'] = 'ONLINE'

        return server

    def __update_stats_rest(self, uri, server):
        try:
            requests.get(f'{uri}/status', timeout=3)
        except requests.exceptions.RequestException as e:
            logger.debug(f"Error while grabbing stats form server ({e})")
            server['status'] = 'OFFLINE'
            return server
        else:
            server['status'] = 'ONLINE'

        for column in self.get_columns():
            server_key = self.__get_key(column)
            # Build the URI (URL encoded)
            request_uri = f"{column['plugin']}/{column['field']}"
            if 'key' in column:
                request_uri += f"/{column['key']}"
            request_uri = f'{uri}/' + requests.utils.quote(request_uri)
            # Value
            try:
                r = requests.get(request_uri, timeout=3)
            except requests.exceptions.RequestException as e:
                logger.debug(f"Error while grabbing stats form server ({e})")
            else:
                if r.json() and column['field'] in r.json():
                    server[server_key] = r.json()[column['field']]
            # Decoration
            try:
                d = requests.get(request_uri + '/views', timeout=3)
            except requests.exceptions.RequestException as e:
                logger.debug(f"Error while grabbing stats view form server ({e})")
            else:
                if d.json() and 'decoration' in d.json():
                    server[server_key + '_decoration'] = d.json()['decoration']

        return server

    def __get_key(self, column):
        server_key = column.get('plugin') + '_' + column.get('field')
        if 'key' in column:
            server_key += '_' + column.get('key')
        return server_key
