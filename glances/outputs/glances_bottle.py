# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2019 Nicolargo <nicolas@nicolargo.com>
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
import zlib

from glances.compat import b
from glances.timer import Timer
from glances.logger import logger

try:
    from bottle import Bottle, static_file, abort, response, request, auth_basic, template, TEMPLATE_PATH
except ImportError:
    logger.critical('Bottle module not found. Glances cannot start in web server mode.')
    sys.exit(2)


def compress(func):
    """Compress result with deflate algorithm if the client ask for it."""
    def wrapper(*args, **kwargs):
        """Wrapper that take one function and return the compressed result."""
        ret = func(*args, **kwargs)
        logger.debug('Receive {} {} request with header: {}'.format(
            request.method,
            request.url,
            ['{}: {}'.format(h, request.headers.get(h)) for h in request.headers.keys()]
        ))
        if 'deflate' in request.headers.get('Accept-Encoding', ''):
            response.headers['Content-Encoding'] = 'deflate'
            ret = deflate_compress(ret)
        else:
            response.headers['Content-Encoding'] = 'identity'
        return ret

    def deflate_compress(data, compress_level=6):
        """Compress given data using the DEFLATE algorithm"""
        # Init compression
        zobj = zlib.compressobj(compress_level,
                                zlib.DEFLATED,
                                zlib.MAX_WBITS,
                                zlib.DEF_MEM_LEVEL,
                                zlib.Z_DEFAULT_STRATEGY)

        # Return compressed object
        return zobj.compress(b(data)) + zobj.flush()

    return wrapper


class GlancesBottle(object):
    """This class manages the Bottle Web server."""

    API_VERSION = '3'

    def __init__(self, config=None, args=None):
        # Init config
        self.config = config

        # Init args
        self.args = args

        # Init stats
        # Will be updated within Bottle route
        self.stats = None

        # cached_time is the minimum time interval between stats updates
        # i.e. HTTP/RESTful calls will not retrieve updated info until the time
        # since last update is passed (will retrieve old cached info instead)
        self.timer = Timer(0)

        # Load configuration file
        self.load_config(config)

        # Set the bind URL
        self.bind_url = 'http://{}:{}/'.format(self.args.bind_address,
                                               self.args.port)

        # Init Bottle
        self._app = Bottle()
        # Enable CORS (issue #479)
        self._app.install(EnableCors())
        # Password
        if args.password != '':
            self._app.install(auth_basic(self.check_auth))
        # Define routes
        self._route()

        # Path where the statics files are stored
        self.STATIC_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/public')

        # Paths for templates
        TEMPLATE_PATH.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/templates'))

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
        # REST API
        self._app.route('/api/%s/config' % self.API_VERSION, method="GET",
                        callback=self._api_config)
        self._app.route('/api/%s/config/<item>' % self.API_VERSION, method="GET",
                        callback=self._api_config_item)
        self._app.route('/api/%s/args' % self.API_VERSION, method="GET",
                        callback=self._api_args)
        self._app.route('/api/%s/args/<item>' % self.API_VERSION, method="GET",
                        callback=self._api_args_item)
        self._app.route('/api/%s/help' % self.API_VERSION, method="GET",
                        callback=self._api_help)
        self._app.route('/api/%s/pluginslist' % self.API_VERSION, method="GET",
                        callback=self._api_plugins)
        self._app.route('/api/%s/all' % self.API_VERSION, method="GET",
                        callback=self._api_all)
        self._app.route('/api/%s/all/limits' % self.API_VERSION, method="GET",
                        callback=self._api_all_limits)
        self._app.route('/api/%s/all/views' % self.API_VERSION, method="GET",
                        callback=self._api_all_views)
        self._app.route('/api/%s/<plugin>' % self.API_VERSION, method="GET",
                        callback=self._api)
        self._app.route('/api/%s/<plugin>/history' % self.API_VERSION, method="GET",
                        callback=self._api_history)
        self._app.route('/api/%s/<plugin>/history/<nb:int>' % self.API_VERSION, method="GET",
                        callback=self._api_history)
        self._app.route('/api/%s/<plugin>/limits' % self.API_VERSION, method="GET",
                        callback=self._api_limits)
        self._app.route('/api/%s/<plugin>/views' % self.API_VERSION, method="GET",
                        callback=self._api_views)
        self._app.route('/api/%s/<plugin>/<item>' % self.API_VERSION, method="GET",
                        callback=self._api_item)
        self._app.route('/api/%s/<plugin>/<item>/history' % self.API_VERSION, method="GET",
                        callback=self._api_item_history)
        self._app.route('/api/%s/<plugin>/<item>/history/<nb:int>' % self.API_VERSION, method="GET",
                        callback=self._api_item_history)
        self._app.route('/api/%s/<plugin>/<item>/<value>' % self.API_VERSION, method="GET",
                        callback=self._api_value)
        bindmsg = 'Glances RESTful API Server started on {}api/{}/'.format(self.bind_url,
                                                                           self.API_VERSION)
        logger.info(bindmsg)

        # WEB UI
        if not self.args.disable_webui:
            self._app.route('/', method="GET", callback=self._index)
            self._app.route('/<refresh_time:int>', method=["GET"], callback=self._index)
            self._app.route('/<filepath:path>', method="GET", callback=self._resource)
            bindmsg = 'Glances Web User Interface started on {}'.format(self.bind_url)
            logger.info(bindmsg)
        else:
            logger.info('The WebUI is disable (--disable-webui)')

        print(bindmsg)

    def start(self, stats):
        """Start the bottle."""
        # Init stats
        self.stats = stats

        # Init plugin list
        self.plugins_list = self.stats.getPluginsList()

        # Bind the Bottle TCP address/port
        if self.args.open_web_browser:
            # Implementation of the issue #946
            # Try to open the Glances Web UI in the default Web browser if:
            # 1) --open-web-browser option is used
            # 2) Glances standalone mode is running on Windows OS
            webbrowser.open(self.bind_url,
                            new=2,
                            autoraise=1)

        self._app.run(host=self.args.bind_address,
                      port=self.args.port,
                      quiet=not self.args.debug)

    def end(self):
        """End the bottle."""
        pass

    def _index(self, refresh_time=None):
        """Bottle callback for index.html (/) file."""

        if refresh_time is None or refresh_time < 1:
            refresh_time = int(self.args.time)

        # Update the stat
        self.__update__()

        # Display
        return template("index.html", refresh_time=refresh_time)

    def _resource(self, filepath):
        """Bottle callback for resources files."""
        # Return the static file
        return static_file(filepath, root=self.STATIC_PATH)

    @compress
    def _api_help(self):
        """Glances API RESTful implementation.

        Return the help data or 404 error.
        """
        response.content_type = 'application/json; charset=utf-8'

        # Update the stat
        view_data = self.stats.get_plugin("help").get_view_data()
        try:
            plist = json.dumps(view_data, sort_keys=True)
        except Exception as e:
            abort(404, "Cannot get help view data (%s)" % str(e))
        return plist

    @compress
    def _api_plugins(self):
        """Glances API RESTFul implementation.

        @api {get} /api/%s/pluginslist Get plugins list
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
        response.content_type = 'application/json; charset=utf-8'

        # Update the stat
        self.__update__()

        try:
            plist = json.dumps(self.plugins_list)
        except Exception as e:
            abort(404, "Cannot get plugin list (%s)" % str(e))
        return plist

    @compress
    def _api_all(self):
        """Glances API RESTful implementation.

        Return the JSON representation of all the plugins
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        response.content_type = 'application/json; charset=utf-8'

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

    @compress
    def _api_all_limits(self):
        """Glances API RESTful implementation.

        Return the JSON representation of all the plugins limits
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        response.content_type = 'application/json; charset=utf-8'

        try:
            # Get the JSON value of the stat limits
            limits = json.dumps(self.stats.getAllLimitsAsDict())
        except Exception as e:
            abort(404, "Cannot get limits (%s)" % (str(e)))
        return limits

    @compress
    def _api_all_views(self):
        """Glances API RESTful implementation.

        Return the JSON representation of all the plugins views
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        response.content_type = 'application/json; charset=utf-8'

        try:
            # Get the JSON value of the stat view
            limits = json.dumps(self.stats.getAllViewsAsDict())
        except Exception as e:
            abort(404, "Cannot get views (%s)" % (str(e)))
        return limits

    @compress
    def _api(self, plugin):
        """Glances API RESTful implementation.

        Return the JSON representation of a given plugin
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        response.content_type = 'application/json; charset=utf-8'

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

    @compress
    def _api_history(self, plugin, nb=0):
        """Glances API RESTful implementation.

        Return the JSON representation of a given plugin history
        Limit to the last nb items (all if nb=0)
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        response.content_type = 'application/json; charset=utf-8'

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

    @compress
    def _api_limits(self, plugin):
        """Glances API RESTful implementation.

        Return the JSON limits of a given plugin
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        response.content_type = 'application/json; charset=utf-8'

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

    @compress
    def _api_views(self, plugin):
        """Glances API RESTful implementation.

        Return the JSON views of a given plugin
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        response.content_type = 'application/json; charset=utf-8'

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

    @compress
    def _api_itemvalue(self, plugin, item, value=None, history=False, nb=0):
        """Father method for _api_item and _api_value."""
        response.content_type = 'application/json; charset=utf-8'

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

    @compress
    def _api_item(self, plugin, item):
        """Glances API RESTful implementation.

        Return the JSON representation of the couple plugin/item
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error

        """
        return self._api_itemvalue(plugin, item)

    @compress
    def _api_item_history(self, plugin, item, nb=0):
        """Glances API RESTful implementation.

        Return the JSON representation of the couple plugin/history of item
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error

        """
        return self._api_itemvalue(plugin, item, history=True, nb=int(nb))

    @compress
    def _api_value(self, plugin, item, value):
        """Glances API RESTful implementation.

        Return the process stats (dict) for the given item=value
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        return self._api_itemvalue(plugin, item, value)

    @compress
    def _api_config(self):
        """Glances API RESTful implementation.

        Return the JSON representation of the Glances configuration file
        HTTP/200 if OK
        HTTP/404 if others error
        """
        response.content_type = 'application/json; charset=utf-8'

        try:
            # Get the JSON value of the config' dict
            args_json = json.dumps(self.config.as_dict())
        except Exception as e:
            abort(404, "Cannot get config (%s)" % str(e))
        return args_json

    @compress
    def _api_config_item(self, item):
        """Glances API RESTful implementation.

        Return the JSON representation of the Glances configuration item
        HTTP/200 if OK
        HTTP/400 if item is not found
        HTTP/404 if others error
        """
        response.content_type = 'application/json; charset=utf-8'

        config_dict = self.config.as_dict()
        if item not in config_dict:
            abort(400, "Unknown configuration item %s" % item)

        try:
            # Get the JSON value of the config' dict
            args_json = json.dumps(config_dict[item])
        except Exception as e:
            abort(404, "Cannot get config item (%s)" % str(e))
        return args_json

    @compress
    def _api_args(self):
        """Glances API RESTful implementation.

        Return the JSON representation of the Glances command line arguments
        HTTP/200 if OK
        HTTP/404 if others error
        """
        response.content_type = 'application/json; charset=utf-8'

        try:
            # Get the JSON value of the args' dict
            # Use vars to convert namespace to dict
            # Source: https://docs.python.org/%s/library/functions.html#vars
            args_json = json.dumps(vars(self.args))
        except Exception as e:
            abort(404, "Cannot get args (%s)" % str(e))
        return args_json

    @compress
    def _api_args_item(self, item):
        """Glances API RESTful implementation.

        Return the JSON representation of the Glances command line arguments item
        HTTP/200 if OK
        HTTP/400 if item is not found
        HTTP/404 if others error
        """
        response.content_type = 'application/json; charset=utf-8'

        if item not in self.args:
            abort(400, "Unknown argument item %s" % item)

        try:
            # Get the JSON value of the args' dict
            # Use vars to convert namespace to dict
            # Source: https://docs.python.org/%s/library/functions.html#vars
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
