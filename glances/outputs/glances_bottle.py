# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2015 Nicolargo <nicolas@nicolargo.com>
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

from glances.core.glances_logging import logger

try:
    from bottle import Bottle, static_file, abort, response, request, auth_basic
except ImportError:
    logger.critical('Bottle module not found. Glances cannot start in web server mode.')
    sys.exit(2)


class GlancesBottle(object):

    """This class manages the Bottle Web server."""

    def __init__(self, args=None):
        # Init args
        self.args = args

        # Init stats
        # Will be updated within Bottle route
        self.stats = None

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
        self.STATIC_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static')

    def check_auth(self, username, password):
        """Check if a username/password combination is valid."""
        if username == self.args.username:
            from glances.core.glances_password import GlancesPassword
            pwd = GlancesPassword()
            return pwd.check_password(self.args.password, pwd.sha256_hash(password))
        else:
            return False

    def _route(self):
        """Define route."""
        self._app.route('/', method="GET", callback=self._index)
        self._app.route('/<refresh_time:int>', method=["GET", "POST"], callback=self._index)

        self._app.route('/<filename:re:.*\.css>', method="GET", callback=self._css)
        self._app.route('/<filename:re:.*\.js>', method="GET", callback=self._js)
        self._app.route('/<filename:re:.*\.js.map>', method="GET", callback=self._js_map)
        self._app.route('/<filename:re:.*\.html>', method="GET", callback=self._html)

        self._app.route('/<filename:re:.*\.png>', method="GET", callback=self._images)
        self._app.route('/favicon.ico', method="GET", callback=self._favicon)

        # REST API
        self._app.route('/api/2/help', method="GET", callback=self._api_help)
        self._app.route('/api/2/pluginslist', method="GET", callback=self._api_plugins)
        self._app.route('/api/2/all', method="GET", callback=self._api_all)
        self._app.route('/api/2/all/limits', method="GET", callback=self._api_all_limits)
        self._app.route('/api/2/all/views', method="GET", callback=self._api_all_views)
        self._app.route('/api/2/:plugin', method="GET", callback=self._api)
        self._app.route('/api/2/:plugin/limits', method="GET", callback=self._api_limits)
        self._app.route('/api/2/:plugin/views', method="GET", callback=self._api_views)
        self._app.route('/api/2/:plugin/:item', method="GET", callback=self._api_item)
        self._app.route('/api/2/:plugin/:item/:value', method="GET", callback=self._api_value)

    def start(self, stats):
        """Start the bottle."""
        # Init stats
        self.stats = stats

        # Init plugin list
        self.plugins_list = self.stats.getAllPlugins()

        # Bind the Bottle TCP address/port
        bindmsg = 'Glances web server started on http://{0}:{1}/'.format(self.args.bind_address, self.args.port)
        logger.info(bindmsg)
        print(bindmsg)
        self._app.run(host=self.args.bind_address, port=self.args.port, quiet=not self.args.debug)

    def end(self):
        """End the bottle."""
        pass

    def _index(self, refresh_time=None):
        """Bottle callback for index.html (/) file."""
        # Manage parameter
        if refresh_time is None:
            refresh_time = self.args.time

        # Update the stat
        self.stats.update()

        # Display
        return static_file("index.html", root=os.path.join(self.STATIC_PATH, 'html'))

    def _html(self, filename):
        """Bottle callback for *.html files."""
        # Return the static file
        return static_file(filename, root=os.path.join(self.STATIC_PATH, 'html'))

    def _css(self, filename):
        """Bottle callback for *.css files."""
        # Return the static file
        return static_file(filename, root=os.path.join(self.STATIC_PATH, 'css'))

    def _js(self, filename):
        """Bottle callback for *.js files."""
        # Return the static file
        return static_file(filename, root=os.path.join(self.STATIC_PATH, 'js'))

    def _js_map(self, filename):
        """Bottle callback for *.js.map files."""
        # Return the static file
        return static_file(filename, root=os.path.join(self.STATIC_PATH, 'js'))

    def _images(self, filename):
        """Bottle callback for *.png files."""
        # Return the static file
        return static_file(filename, root=os.path.join(self.STATIC_PATH, 'images'))

    def _favicon(self):
        """Bottle callback for favicon."""
        # Return the static file
        return static_file('favicon.ico', root=self.STATIC_PATH)

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
        self.stats.update()

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
            with open(fname) as f:
                return f.read()

        # Update the stat
        self.stats.update()

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
        self.stats.update()

        try:
            # Get the JSON value of the stat ID
            statval = self.stats.get_plugin(plugin).get_stats()
        except Exception as e:
            abort(404, "Cannot get plugin %s (%s)" % (plugin, str(e)))
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
        # self.stats.update()

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
        # self.stats.update()

        try:
            # Get the JSON value of the stat views
            ret = self.stats.get_plugin(plugin).get_views()
        except Exception as e:
            abort(404, "Cannot get views for plugin %s (%s)" % (plugin, str(e)))
        return ret

    def _api_item(self, plugin, item):
        """Glances API RESTFul implementation.

        Return the JSON represenation of the couple plugin/item
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error

        """
        response.content_type = 'application/json'

        if plugin not in self.plugins_list:
            abort(400, "Unknown plugin %s (available plugins: %s)" % (plugin, self.plugins_list))

        # Update the stat
        self.stats.update()

        plist = self.stats.get_plugin(plugin).get_stats_item(item)

        if plist is None:
            abort(404, "Cannot get item %s in plugin %s" % (item, plugin))
        else:
            return plist

    def _api_value(self, plugin, item, value):
        """Glances API RESTFul implementation.

        Return the process stats (dict) for the given item=value
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        response.content_type = 'application/json'

        if plugin not in self.plugins_list:
            abort(400, "Unknown plugin %s (available plugins: %s)" % (plugin, self.plugins_list))

        # Update the stat
        self.stats.update()

        pdict = self.stats.get_plugin(plugin).get_stats_value(item, value)

        if pdict is None:
            abort(404, "Cannot get item(%s)=value(%s) in plugin %s" % (item, value, plugin))
        else:
            return pdict


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
