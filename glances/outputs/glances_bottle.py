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

"""Web interface class."""

import json
import os
import sys
import tempfile
from io import open
import webbrowser

from glances.timer import Timer
from glances.logger import logger

try:
    from bottle import Bottle, static_file, abort, response, request, auth_basic
except ImportError:
    logger.critical('Bottle module not found. Glances cannot start in web server mode.')
    sys.exit(2)


class GlancesBottle(object):

    """This class manages the Bottle Web server."""

    def __init__(self, config=None, args=None):
        # Init config
        self.config = config

        # Init args
        self.args = args

        # Init stats
        # Will be updated within Bottle route
        self.stats = None

        # cached_time is the minimum time interval between stats updates
        # i.e. HTTP/Restful calls will not retrieve updated info until the time
        # since last update is passed (will retrieve old cached info instead)
        self.timer = Timer(0)

        # Load configuration file
        self.load_config(config)

        # Init Bottle
        self._app = Bottle()
        # Enable CORS (issue #479)
        self._app.install(EnableCors())
        # Password
        if args.password != '':
            self._app.install(auth_basic(self.check_auth, realm=args.realm))
        # Define routes
        self._route()

        # Path where the statics files are stored
        self.STATIC_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/public')

    def load_config(self, config):
        """Load the outputs section of the configuration file."""
        # Limit the number of processes to display in the WebUI
        if config is not None and config.has_section('outputs'):
            logger.debug('Read number of processes to display in the WebUI')
            n = config.get_value('outputs', 'max_processes_display', default=None)
            logger.debug('Number of processes to display in the WebUI: {}'.format(n))

    def __update__(self):
        # Never update more than 1 time per cached_time
        if self.timer.finished():
            self.stats.update()
            self.timer = Timer(self.args.cached_time)

    def app(self):
        return self._app()

    def check_auth(self, username, password):
        """Check if a username/password combination is valid."""
        if username == self.args.username:
            from glances.password import GlancesPassword
            pwd = GlancesPassword()
            return pwd.check_password(self.args.password, pwd.sha256_hash(password))
        else:
            return False

    def _route(self):
        """Define route."""
        self._app.route('/', method="GET", callback=self._index)
        self._app.route('/<refresh_time:int>', method=["GET"], callback=self._index)

        # REST API
        self._app.route('/api/2/config', method="GET", callback=self._api_config)
        self._app.route('/api/2/config/<item>', method="GET", callback=self._api_config_item)
        self._app.route('/api/2/args', method="GET", callback=self._api_args)
        self._app.route('/api/2/args/<item>', method="GET", callback=self._api_args_item)
        self._app.route('/api/2/help', method="GET", callback=self._api_help)
        self._app.route('/api/2/pluginslist', method="GET", callback=self._api_plugins)
        self._app.route('/api/2/all', method="GET", callback=self._api_all)
        self._app.route('/api/2/all/limits', method="GET", callback=self._api_all_limits)
        self._app.route('/api/2/all/views', method="GET", callback=self._api_all_views)
        self._app.route('/api/2/<plugin>', method="GET", callback=self._api)
        self._app.route('/api/2/<plugin>/history', method="GET", callback=self._api_history)
        self._app.route('/api/2/<plugin>/history/<nb:int>', method="GET", callback=self._api_history)
        self._app.route('/api/2/<plugin>/limits', method="GET", callback=self._api_limits)
        self._app.route('/api/2/<plugin>/views', method="GET", callback=self._api_views)
        self._app.route('/api/2/<plugin>/<item>', method="GET", callback=self._api_item)
        self._app.route('/api/2/<plugin>/<item>/history', method="GET", callback=self._api_item_history)
        self._app.route('/api/2/<plugin>/<item>/history/<nb:int>', method="GET", callback=self._api_item_history)
        self._app.route('/api/2/<plugin>/<item>/<value>', method="GET", callback=self._api_value)

        self._app.route('/<filepath:path>', method="GET", callback=self._resource)

    def start(self, stats):
        """Start the bottle."""
        # Init stats
        self.stats = stats

        # Init plugin list
        self.plugins_list = self.stats.getAllPlugins()

        # Bind the Bottle TCP address/port
        bindurl = 'http://{}:{}/'.format(self.args.bind_address,
                                         self.args.port)
        bindmsg = 'Glances web server started on {}'.format(bindurl)
        logger.info(bindmsg)
        print(bindmsg)
        if self.args.open_web_browser:
            # Implementation of the issue #946
            # Try to open the Glances Web UI in the default Web browser if:
            # 1) --open-web-browser option is used
            # 2) Glances standalone mode is running on Windows OS
            webbrowser.open(bindurl, new=2, autoraise=1)
        self._app.run(host=self.args.bind_address, port=self.args.port, quiet=not self.args.debug)

    def end(self):
        """End the bottle."""
        pass

    def _index(self, refresh_time=None):
        """Bottle callback for index.html (/) file."""
        # Update the stat
        self.__update__()

        # Display
        return static_file("index.html", root=self.STATIC_PATH)

    def _resource(self, filepath):
        """Bottle callback for resources files."""
        # Return the static file
        return static_file(filepath, root=self.STATIC_PATH)

    def _api_help(self):
        """Glances API RESTFul implementation.

        Return the help data or 404 error.
        """
        response.content_type = 'application/json'

        # Update the stat
        view_data = self.stats.get_plugin("help").get_view_data()
        try:
            plist = json.dumps(view_data, sort_keys=True)
        except Exception as e:
            abort(404, "Cannot get help view data (%s)" % str(e))
        return plist

    def _api_plugins(self):
        """
        @api {get} /api/2/pluginslist Get plugins list
        @apiVersion 2.0
        @apiName pluginslist
        @apiGroup plugin

        @apiSuccess {String[]} Plugins list.

        @apiSuccessExample Success-Response:
            HTTP/1.1 200 OK
            [
               "load",
               "help",
               "ip",
               "memswap",
               "processlist",
               ...
            ]

         @apiError Cannot get plugin list.

         @apiErrorExample Error-Response:
            HTTP/1.1 404 Not Found
        """
        response.content_type = 'application/json'

        # Update the stat
        self.__update__()

        try:
            plist = json.dumps(self.plugins_list)
        except Exception as e:
            abort(404, "Cannot get plugin list (%s)" % str(e))
        return plist

    def _api_all(self):
        """Glances API RESTFul implementation.

        Return the JSON representation of all the plugins
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        response.content_type = 'application/json'

        if self.args.debug:
            fname = os.path.join(tempfile.gettempdir(), 'glances-debug.json')
            try:
                with open(fname) as f:
                    return f.read()
            except IOError:
                logger.debug("Debug file (%s) not found" % fname)

        # Update the stat
        self.__update__()

        try:
            # Get the JSON value of the stat ID
            statval = json.dumps(self.stats.getAllAsDict())
        except Exception as e:
            abort(404, "Cannot get stats (%s)" % str(e))
        return statval

    def _api_all_limits(self):
        """Glances API RESTFul implementation.

        Return the JSON representation of all the plugins limits
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        response.content_type = 'application/json'

        try:
            # Get the JSON value of the stat limits
            limits = json.dumps(self.stats.getAllLimitsAsDict())
        except Exception as e:
            abort(404, "Cannot get limits (%s)" % (str(e)))
        return limits

    def _api_all_views(self):
        """Glances API RESTFul implementation.

        Return the JSON representation of all the plugins views
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        response.content_type = 'application/json'

        try:
            # Get the JSON value of the stat view
            limits = json.dumps(self.stats.getAllViewsAsDict())
        except Exception as e:
            abort(404, "Cannot get views (%s)" % (str(e)))
        return limits

    def _api(self, plugin):
        """Glances API RESTFul implementation.

        Return the JSON representation of a given plugin
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        response.content_type = 'application/json'

        if plugin not in self.plugins_list:
            abort(400, "Unknown plugin %s (available plugins: %s)" % (plugin, self.plugins_list))

        # Update the stat
        self.__update__()

        try:
            # Get the JSON value of the stat ID
            statval = self.stats.get_plugin(plugin).get_stats()
        except Exception as e:
            abort(404, "Cannot get plugin %s (%s)" % (plugin, str(e)))
        return statval

    def _api_history(self, plugin, nb=0):
        """Glances API RESTFul implementation.

        Return the JSON representation of a given plugin history
        Limit to the last nb items (all if nb=0)
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        response.content_type = 'application/json'

        if plugin not in self.plugins_list:
            abort(400, "Unknown plugin %s (available plugins: %s)" % (plugin, self.plugins_list))

        # Update the stat
        self.__update__()

        try:
            # Get the JSON value of the stat ID
            statval = self.stats.get_plugin(plugin).get_stats_history(nb=int(nb))
        except Exception as e:
            abort(404, "Cannot get plugin history %s (%s)" % (plugin, str(e)))
        return statval

    def _api_limits(self, plugin):
        """Glances API RESTFul implementation.

        Return the JSON limits of a given plugin
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        response.content_type = 'application/json'

        if plugin not in self.plugins_list:
            abort(400, "Unknown plugin %s (available plugins: %s)" % (plugin, self.plugins_list))

        # Update the stat
        # self.__update__()

        try:
            # Get the JSON value of the stat limits
            ret = self.stats.get_plugin(plugin).limits
        except Exception as e:
            abort(404, "Cannot get limits for plugin %s (%s)" % (plugin, str(e)))
        return ret

    def _api_views(self, plugin):
        """Glances API RESTFul implementation.

        Return the JSON views of a given plugin
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        response.content_type = 'application/json'

        if plugin not in self.plugins_list:
            abort(400, "Unknown plugin %s (available plugins: %s)" % (plugin, self.plugins_list))

        # Update the stat
        # self.__update__()

        try:
            # Get the JSON value of the stat views
            ret = self.stats.get_plugin(plugin).get_views()
        except Exception as e:
            abort(404, "Cannot get views for plugin %s (%s)" % (plugin, str(e)))
        return ret

    def _api_itemvalue(self, plugin, item, value=None, history=False, nb=0):
        """Father method for _api_item and _api_value"""
        response.content_type = 'application/json'

        if plugin not in self.plugins_list:
            abort(400, "Unknown plugin %s (available plugins: %s)" % (plugin, self.plugins_list))

        # Update the stat
        self.__update__()

        if value is None:
            if history:
                ret = self.stats.get_plugin(plugin).get_stats_history(item, nb=int(nb))
            else:
                ret = self.stats.get_plugin(plugin).get_stats_item(item)

            if ret is None:
                abort(404, "Cannot get item %s%s in plugin %s" % (item, 'history ' if history else '', plugin))
        else:
            if history:
                # Not available
                ret = None
            else:
                ret = self.stats.get_plugin(plugin).get_stats_value(item, value)

            if ret is None:
                abort(404, "Cannot get item %s(%s=%s) in plugin %s" % ('history ' if history else '', item, value, plugin))

        return ret

    def _api_item(self, plugin, item):
        """Glances API RESTFul implementation.

        Return the JSON representation of the couple plugin/item
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error

        """
        return self._api_itemvalue(plugin, item)

    def _api_item_history(self, plugin, item, nb=0):
        """Glances API RESTFul implementation.

        Return the JSON representation of the couple plugin/history of item
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error

        """
        return self._api_itemvalue(plugin, item, history=True, nb=int(nb))

    def _api_value(self, plugin, item, value):
        """Glances API RESTFul implementation.

        Return the process stats (dict) for the given item=value
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        return self._api_itemvalue(plugin, item, value)

    def _api_config(self):
        """Glances API RESTFul implementation.

        Return the JSON representation of the Glances configuration file
        HTTP/200 if OK
        HTTP/404 if others error
        """
        response.content_type = 'application/json'

        try:
            # Get the JSON value of the config' dict
            args_json = json.dumps(self.config.as_dict())
        except Exception as e:
            abort(404, "Cannot get config (%s)" % str(e))
        return args_json

    def _api_config_item(self, item):
        """Glances API RESTFul implementation.

        Return the JSON representation of the Glances configuration item
        HTTP/200 if OK
        HTTP/400 if item is not found
        HTTP/404 if others error
        """
        response.content_type = 'application/json'

        config_dict = self.config.as_dict()
        if item not in config_dict:
            abort(400, "Unknown configuration item %s" % item)

        try:
            # Get the JSON value of the config' dict
            args_json = json.dumps(config_dict[item])
        except Exception as e:
            abort(404, "Cannot get config item (%s)" % str(e))
        return args_json

    def _api_args(self):
        """Glances API RESTFul implementation.

        Return the JSON representation of the Glances command line arguments
        HTTP/200 if OK
        HTTP/404 if others error
        """
        response.content_type = 'application/json'

        try:
            # Get the JSON value of the args' dict
            # Use vars to convert namespace to dict
            # Source: https://docs.python.org/2/library/functions.html#vars
            args_json = json.dumps(vars(self.args))
        except Exception as e:
            abort(404, "Cannot get args (%s)" % str(e))
        return args_json

    def _api_args_item(self, item):
        """Glances API RESTFul implementation.

        Return the JSON representation of the Glances command line arguments item
        HTTP/200 if OK
        HTTP/400 if item is not found
        HTTP/404 if others error
        """
        response.content_type = 'application/json'

        if item not in self.args:
            abort(400, "Unknown argument item %s" % item)

        try:
            # Get the JSON value of the args' dict
            # Use vars to convert namespace to dict
            # Source: https://docs.python.org/2/library/functions.html#vars
            args_json = json.dumps(vars(self.args)[item])
        except Exception as e:
            abort(404, "Cannot get args item (%s)" % str(e))
        return args_json


class EnableCors(object):
    name = 'enable_cors'
    api = 2

    def apply(self, fn, context):
        def _enable_cors(*args, **kwargs):
            # set CORS headers
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

            if request.method != 'OPTIONS':
                # actual request; reply with the actual response
                return fn(*args, **kwargs)

        return _enable_cors
