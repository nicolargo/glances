#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""RestFull API interface class."""

import os
import socket
import sys
import tempfile
import webbrowser
from typing import Annotated, Any, Union
from urllib.parse import urljoin

from glances import __apiversion__, __version__
from glances.events_list import glances_events
from glances.globals import json_dumps
from glances.logger import logger
from glances.password import GlancesPassword
from glances.servers_list import GlancesServersList
from glances.servers_list_dynamic import GlancesAutoDiscoverClient
from glances.stats import GlancesStats
from glances.timer import Timer

# FastAPI import
try:
    from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.gzip import GZipMiddleware
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.security import HTTPBasic, HTTPBasicCredentials
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
except ImportError as e:
    logger.critical(f'FastAPI import error: {e}')
    logger.critical('Glances cannot start in web server mode.')
    sys.exit(2)

try:
    import uvicorn
except ImportError:
    logger.critical('Uvicorn import error. Glances cannot start in web server mode.')
    sys.exit(2)
import builtins
import contextlib
import threading
import time

security = HTTPBasic()


class GlancesJSONResponse(JSONResponse):
    """
    Glances impl of fastapi's JSONResponse to use internal JSON Serialization features

    Ref: https://fastapi.tiangolo.com/advanced/custom-response/
    """

    def render(self, content: Any) -> bytes:
        return json_dumps(content)


class GlancesUvicornServer(uvicorn.Server):
    def install_signal_handlers(self):
        pass

    @contextlib.contextmanager
    def run_in_thread(self, timeout=3):
        thread = threading.Thread(target=self.run)
        thread.start()
        try:
            chrono = Timer(timeout)
            while not self.started and not chrono.finished():
                time.sleep(0.5)
            # Timeout reached
            # Something go wrong...
            # The Uvicorn server should be stopped
            if not self.started:
                self.should_exit = True
                thread.join()
            yield
        finally:
            self.should_exit = True
            thread.join()


class GlancesRestfulApi:
    """This class manages the Restful API server."""

    API_VERSION = __apiversion__

    def __init__(self, config=None, args=None):
        # Init config
        self.config = config

        # Init args
        self.args = args

        # Init stats
        # Will be updated within route
        self.stats = None

        # Init servers list (only for the browser mode)
        if self.args.browser:
            self.servers_list = GlancesServersList(config=config, args=args)
        else:
            self.servers_list = None

        # cached_time is the minimum time interval between stats updates
        # i.e. HTTP/RESTful calls will not retrieve updated info until the time
        # since last update is passed (will retrieve old cached info instead)
        self.timer = Timer(0)

        # Load configuration file
        self.load_config(config)

        # Set the bind URL
        self.bind_url = urljoin(f'http://{self.args.bind_address}:{self.args.port}/', self.url_prefix)

        # FastAPI Init
        if self.args.password:
            self._app = FastAPI(default_response_class=GlancesJSONResponse, dependencies=[Depends(self.authentication)])
            self._password = GlancesPassword(username=args.username, config=config)

        else:
            self._app = FastAPI(default_response_class=GlancesJSONResponse)
            self._password = None

        # Set path for WebUI
        webui_root_path = config.get_value(
            'outputs', 'webui_root_path', default=os.path.dirname(os.path.realpath(__file__))
        )
        if webui_root_path == '':
            webui_root_path = os.path.dirname(os.path.realpath(__file__))
        self.STATIC_PATH = os.path.join(webui_root_path, 'static/public')
        self.TEMPLATE_PATH = os.path.join(webui_root_path, 'static/templates')
        self._templates = Jinja2Templates(directory=self.TEMPLATE_PATH)

        # FastAPI Enable CORS
        # https://fastapi.tiangolo.com/tutorial/cors/
        self._app.add_middleware(
            CORSMiddleware,
            # Related to https://github.com/nicolargo/glances/issues/2812
            allow_origins=config.get_list_value('outputs', 'cors_origins', default=["*"]),
            allow_credentials=config.get_bool_value('outputs', 'cors_credentials', default=True),
            allow_methods=config.get_list_value('outputs', 'cors_methods', default=["*"]),
            allow_headers=config.get_list_value('outputs', 'cors_headers', default=["*"]),
        )

        # FastAPI Enable GZIP compression
        # https://fastapi.tiangolo.com/advanced/middleware/
        self._app.add_middleware(GZipMiddleware, minimum_size=1000)

        # FastAPI Define routes
        self._app.include_router(self._router())

        # Enable auto discovering of the service
        self.autodiscover_client = None
        if not self.args.disable_autodiscover:
            logger.info('Autodiscover is enabled with service name {}'.format(socket.gethostname().split('.', 1)[0]))
            self.autodiscover_client = GlancesAutoDiscoverClient(socket.gethostname().split('.', 1)[0], self.args)
        else:
            logger.info("Glances autodiscover announce is disabled")

    def load_config(self, config):
        """Load the outputs section of the configuration file."""
        # Limit the number of processes to display in the WebUI
        self.url_prefix = ''
        if config is not None and config.has_section('outputs'):
            # Max process to display in the WebUI
            n = config.get_value('outputs', 'max_processes_display', default=None)
            logger.debug(f'Number of processes to display in the WebUI: {n}')
            # URL prefix
            self.url_prefix = config.get_value('outputs', 'url_prefix', default='')
            if self.url_prefix != '':
                self.url_prefix = self.url_prefix.rstrip('/')
            logger.debug(f'URL prefix: {self.url_prefix}')

    def __update_stats(self):
        # Never update more than 1 time per cached_time
        if self.timer.finished():
            self.stats.update()
            self.timer = Timer(self.args.cached_time)

    def __update_servers_list(self):
        # Never update more than 1 time per cached_time
        if self.timer.finished() and self.servers_list is not None:
            self.servers_list.update_servers_stats()
            self.timer = Timer(self.args.cached_time)

    def authentication(self, creds: Annotated[HTTPBasicCredentials, Depends(security)]):
        """Check if a username/password combination is valid."""
        if creds.username == self.args.username:
            # check_password and get_hash are (lru) cached to optimize the requests
            if self._password.check_password(self.args.password, self._password.get_hash(creds.password)):
                return creds.username

        # If the username/password combination is invalid, return an HTTP 401
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Incorrect username or password", {"WWW-Authenticate": "Basic"}
        )

    def _router(self) -> APIRouter:
        """Define a custom router for Glances path."""
        base_path = f'/api/{self.API_VERSION}'
        plugin_path = f"{base_path}/{{plugin}}"

        # Create the main router
        router = APIRouter(prefix=self.url_prefix)

        # REST API route definition
        # ==========================

        # HEAD
        router.add_api_route(f'{base_path}/status', self._api_status, methods=['HEAD', 'GET'])

        # POST
        router.add_api_route(f'{base_path}/events/clear/warning', self._events_clear_warning, methods=['POST'])
        router.add_api_route(f'{base_path}/events/clear/all', self._events_clear_all, methods=['POST'])

        # GET
        route_mapping = {
            f'{base_path}/config': self._api_config,
            f'{base_path}/config/{{section}}': self._api_config_section,
            f'{base_path}/config/{{section}}/{{item}}': self._api_config_section_item,
            f'{base_path}/args': self._api_args,
            f'{base_path}/args/{{item}}': self._api_args_item,
            f'{base_path}/help': self._api_help,
            f'{base_path}/all': self._api_all,
            f'{base_path}/all/limits': self._api_all_limits,
            f'{base_path}/all/views': self._api_all_views,
            f'{base_path}/pluginslist': self._api_plugins,
            f'{base_path}/serverslist': self._api_servers_list,
            f'{plugin_path}': self._api,
            f'{plugin_path}/history': self._api_history,
            f'{plugin_path}/history/{{nb}}': self._api_history,
            f'{plugin_path}/top/{{nb}}': self._api_top,
            f'{plugin_path}/limits': self._api_limits,
            f'{plugin_path}/views': self._api_views,
            f'{plugin_path}/{{item}}': self._api_item,
            f'{plugin_path}/{{item}}/views': self._api_item_views,
            f'{plugin_path}/{{item}}/history': self._api_item_history,
            f'{plugin_path}/{{item}}/history/{{nb}}': self._api_item_history,
            f'{plugin_path}/{{item}}/description': self._api_item_description,
            f'{plugin_path}/{{item}}/unit': self._api_item_unit,
            f'{plugin_path}/{{item}}/value/{{value:path}}': self._api_value,
            f'{plugin_path}/{{item}}/{{key}}': self._api_key,
            f'{plugin_path}/{{item}}/{{key}}/views': self._api_key_views,
        }
        for path, endpoint in route_mapping.items():
            router.add_api_route(path, endpoint)

        # Browser WEBUI
        if self.args.browser:
            # Template for the root browser.html file
            router.add_api_route('/browser', self._browser, response_class=HTMLResponse)

            # Statics files
            self._app.mount(self.url_prefix + '/static', StaticFiles(directory=self.STATIC_PATH), name="static")
            logger.debug(f"The Browser WebUI is enable and got statics files in {self.STATIC_PATH}")

            bindmsg = f'Glances Browser Web User Interface started on {self.bind_url}browser'
            logger.info(bindmsg)
            print(bindmsg)

        # WEBUI
        if not self.args.disable_webui:
            # Template for the root index.html file
            router.add_api_route('/', self._index, response_class=HTMLResponse)

            # Statics files
            self._app.mount(self.url_prefix + '/static', StaticFiles(directory=self.STATIC_PATH), name="static")
            logger.debug(f"The WebUI is enable and got statics files in {self.STATIC_PATH}")

            bindmsg = f'Glances Web User Interface started on {self.bind_url}'
            logger.info(bindmsg)
            print(bindmsg)
        else:
            logger.info('The WebUI is disable (--disable-webui)')

        # Restful API
        bindmsg = f'Glances RESTful API Server started on {self.bind_url}api/{self.API_VERSION}'
        logger.info(bindmsg)
        print(bindmsg)

        return router

    def start(self, stats: GlancesStats) -> None:
        """Start the bottle."""
        # Init stats
        self.stats = stats

        # Init plugin list
        self.plugins_list = self.stats.getPluginsList()

        if self.args.open_web_browser:
            # Implementation of the issue #946
            # Try to open the Glances Web UI in the default Web browser if:
            # 1) --open-web-browser option is used
            # 2) Glances standalone mode is running on Windows OS
            webbrowser.open(self.bind_url, new=2, autoraise=1)

        # Start Uvicorn server
        self._start_uvicorn()

    def _start_uvicorn(self):
        # Run the Uvicorn Web server
        uvicorn_config = uvicorn.Config(
            self._app, host=self.args.bind_address, port=self.args.port, access_log=self.args.debug
        )
        try:
            self.uvicorn_server = GlancesUvicornServer(config=uvicorn_config)
        except Exception as e:
            logger.critical(f'Error: Can not ran Glances Web server ({e})')
            self.uvicorn_server = None
        else:
            with self.uvicorn_server.run_in_thread():
                while not self.uvicorn_server.should_exit:
                    time.sleep(1)

    def end(self):
        """End the Web server"""
        if not self.args.disable_autodiscover and self.autodiscover_client:
            self.autodiscover_client.close()
        logger.info("Close the Web server")

    def _index(self, request: Request):
        """Return main index.html (/) file.

        Parameters are available through the request object.
        Example: http://localhost:61208/?refresh=5

        Note: This function is only called the first time the page is loaded.
        """
        refresh_time = request.query_params.get('refresh', default=max(1, int(self.args.time)))

        # Update the stat
        self.__update_stats()

        # Display
        return self._templates.TemplateResponse("index.html", {"request": request, "refresh_time": refresh_time})

    def _browser(self, request: Request):
        """Return main browser.html (/browser) file.

        Note: This function is only called the first time the page is loaded.
        """
        refresh_time = request.query_params.get('refresh', default=max(1, int(self.args.time)))

        # Display
        return self._templates.TemplateResponse("browser.html", {"request": request, "refresh_time": refresh_time})

    def _api_status(self):
        """Glances API RESTful implementation.

        Return a 200 status code.
        This entry point should be used to check the API health.

        See related issue:  Web server health check endpoint #1988
        """

        return GlancesJSONResponse({'version': __version__})

    def _events_clear_warning(self):
        """Glances API RESTful implementation.

        Return a 200 status code.

        It's a post message to clean warning events
        """
        glances_events.clean()
        return GlancesJSONResponse({})

    def _events_clear_all(self):
        """Glances API RESTful implementation.

        Return a 200 status code.

        It's a post message to clean all events
        """
        glances_events.clean(critical=True)
        return GlancesJSONResponse({})

    def _api_help(self):
        """Glances API RESTful implementation.

        Return the help data or 404 error.
        """
        try:
            plist = self.stats.get_plugin("help").get_view_data()
        except Exception as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Cannot get help view data ({str(e)})")

        return GlancesJSONResponse(plist)

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
        # Update the stat
        self.__update_stats()

        try:
            plist = self.plugins_list
        except Exception as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Cannot get plugin list ({str(e)})")

        return GlancesJSONResponse(plist)

    def _api_servers_list(self):
        """Glances API RESTful implementation.

        Return the JSON representation of the servers list (for browser mode)
        HTTP/200 if OK
        """
        # Update the servers list (and the stats for all the servers)
        self.__update_servers_list()

        return GlancesJSONResponse(self.servers_list.get_servers_list() if self.servers_list else [])

    def _api_all(self):
        """Glances API RESTful implementation.

        Return the JSON representation of all the plugins
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        if self.args.debug:
            fname = os.path.join(tempfile.gettempdir(), 'glances-debug.json')
            try:
                with builtins.open(fname) as f:
                    return f.read()
            except OSError:
                logger.debug(f"Debug file ({fname}) not found")

        # Update the stat
        self.__update_stats()

        try:
            # Get the RAW value of the stat ID
            statval = self.stats.getAllAsDict()
        except Exception as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Cannot get stats ({str(e)})")

        return GlancesJSONResponse(statval)

    def _api_all_limits(self):
        """Glances API RESTful implementation.

        Return the JSON representation of all the plugins limits
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        try:
            # Get the RAW value of the stat limits
            limits = self.stats.getAllLimitsAsDict()
        except Exception as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Cannot get limits ({str(e)})")

        return GlancesJSONResponse(limits)

    def _api_all_views(self):
        """Glances API RESTful implementation.

        Return the JSON representation of all the plugins views
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        try:
            # Get the RAW value of the stat view
            limits = self.stats.getAllViewsAsDict()
        except Exception as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Cannot get views ({str(e)})")

        return GlancesJSONResponse(limits)

    def _api(self, plugin: str):
        """Glances API RESTful implementation.

        Return the JSON representation of a given plugin
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        self._check_if_plugin_available(plugin)

        # Update the stat
        self.__update_stats()

        try:
            # Get the RAW value of the stat ID
            statval = self.stats.get_plugin(plugin).get_raw()
        except Exception as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Cannot get plugin {plugin} ({str(e)})")

        return GlancesJSONResponse(statval)

    def _check_if_plugin_available(self, plugin: str) -> None:
        if plugin in self.plugins_list:
            return

        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Unknown plugin {plugin} (available plugins: {self.plugins_list})"
        )

    def _api_top(self, plugin: str, nb: int = 0):
        """Glances API RESTful implementation.

        Return the JSON representation of a given plugin limited to the top nb items.
        It is used to reduce the payload of the HTTP response (example: processlist).

        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        self._check_if_plugin_available(plugin)

        # Update the stat
        self.__update_stats()

        try:
            # Get the RAW value of the stat ID
            statval = self.stats.get_plugin(plugin).get_raw()
        except Exception as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Cannot get plugin {plugin} ({str(e)})")

        print(statval)

        if isinstance(statval, list):
            statval = statval[:nb]

        return GlancesJSONResponse(statval)

    def _api_history(self, plugin: str, nb: int = 0):
        """Glances API RESTful implementation.

        Return the JSON representation of a given plugin history
        Limit to the last nb items (all if nb=0)
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        self._check_if_plugin_available(plugin)

        # Update the stat
        self.__update_stats()

        try:
            # Get the RAW value of the stat ID
            statval = self.stats.get_plugin(plugin).get_raw_history(nb=int(nb))
        except Exception as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Cannot get plugin history {plugin} ({str(e)})")

        return statval

    def _api_limits(self, plugin: str):
        """Glances API RESTful implementation.

        Return the JSON limits of a given plugin
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        self._check_if_plugin_available(plugin)

        try:
            # Get the RAW value of the stat limits
            ret = self.stats.get_plugin(plugin).limits
        except Exception as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Cannot get limits for plugin {plugin} ({str(e)})")

        return GlancesJSONResponse(ret)

    def _api_views(self, plugin: str):
        """Glances API RESTful implementation.

        Return the JSON views of a given plugin
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        if plugin not in self.plugins_list:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"Unknown plugin {plugin} (available plugins: {self.plugins_list})"
            )

        try:
            # Get the RAW value of the stat views
            ret = self.stats.get_plugin(plugin).get_views()
        except Exception as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Cannot get views for plugin {plugin} ({str(e)})")

        return GlancesJSONResponse(ret)

    def _api_item(self, plugin: str, item: str):
        """Glances API RESTful implementation.

        Return the JSON representation of the couple plugin/item
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        self._check_if_plugin_available(plugin)

        # Update the stat
        self.__update_stats()

        try:
            # Get the RAW value of the stat views
            ret = self.stats.get_plugin(plugin).get_raw_stats_item(item)
        except Exception as e:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"Cannot get item {item} in plugin {plugin} ({str(e)})",
            )

        return GlancesJSONResponse(ret)

    def _api_key(self, plugin: str, item: str, key: str):
        """Glances API RESTful implementation.

        Return the JSON representation of  plugin/item/key
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        self._check_if_plugin_available(plugin)

        # Update the stat
        self.__update_stats()

        try:
            # Get the RAW value of the stat views
            ret = self.stats.get_plugin(plugin).get_raw_stats_key(item, key)
        except Exception as e:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"Cannot get item {item} for key {key} in plugin {plugin} ({str(e)})",
            )

        return GlancesJSONResponse(ret)

    def _api_item_views(self, plugin: str, item: str):
        """Glances API RESTful implementation.

        Return the JSON view representation of the couple plugin/item
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        self._check_if_plugin_available(plugin)

        # Update the stat
        self.__update_stats()

        try:
            # Get the RAW value of the stat views
            ret = self.stats.get_plugin(plugin).get_views().get(item)
        except Exception as e:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"Cannot get item {item} in plugin view {plugin} ({str(e)})",
            )

        return GlancesJSONResponse(ret)

    def _api_key_views(self, plugin: str, item: str, key: str):
        """Glances API RESTful implementation.

        Return the JSON view representation of plugin/item/key
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        self._check_if_plugin_available(plugin)

        # Update the stat
        self.__update_stats()

        try:
            # Get the RAW value of the stat views
            ret = self.stats.get_plugin(plugin).get_views().get(key).get(item)
        except Exception as e:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"Cannot get item {item} for key {key} in plugin view {plugin} ({str(e)})",
            )

        return GlancesJSONResponse(ret)

    def _api_item_history(self, plugin: str, item: str, nb: int = 0):
        """Glances API RESTful implementation.

        Return the JSON representation of the couple plugin/history of item
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error

        """
        self._check_if_plugin_available(plugin)

        # Update the stat
        self.__update_stats()

        try:
            # Get the RAW value of the stat history
            ret = self.stats.get_plugin(plugin).get_raw_history(item, nb=nb)
        except Exception as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Cannot get history for plugin {plugin} ({str(e)})")
        else:
            return GlancesJSONResponse(ret)

    def _api_item_description(self, plugin: str, item: str):
        """Glances API RESTful implementation.

        Return the JSON representation of the couple plugin/item description
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        self._check_if_plugin_available(plugin)

        try:
            # Get the description
            ret = self.stats.get_plugin(plugin).get_item_info(item, 'description')
        except Exception as e:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"Cannot get {item} description for plugin {plugin} ({str(e)})"
            )
        else:
            return GlancesJSONResponse(ret)

    def _api_item_unit(self, plugin: str, item: str):
        """Glances API RESTful implementation.

        Return the JSON representation of the couple plugin/item unit
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        self._check_if_plugin_available(plugin)

        try:
            # Get the unit
            ret = self.stats.get_plugin(plugin).get_item_info(item, 'unit')
        except Exception as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Cannot get {item} unit for plugin {plugin} ({str(e)})")
        else:
            return GlancesJSONResponse(ret)

    def _api_value(self, plugin: str, item: str, value: Union[str, int, float]):
        """Glances API RESTful implementation.

        Return the process stats (dict) for the given item=value
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        self._check_if_plugin_available(plugin)

        # Update the stat
        self.__update_stats()

        try:
            # Get the RAW value
            ret = self.stats.get_plugin(plugin).get_raw_stats_value(item, value)
        except Exception as e:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"Cannot get {item} = {value} for plugin {plugin} ({str(e)})"
            )
        else:
            return GlancesJSONResponse(ret)

    def _api_config(self):
        """Glances API RESTful implementation.

        Return the JSON representation of the Glances configuration file
        HTTP/200 if OK
        HTTP/404 if others error
        """
        try:
            # Get the RAW value of the config' dict
            args_json = self.config.as_dict()
        except Exception as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Cannot get config ({str(e)})")
        else:
            return GlancesJSONResponse(args_json)

    def _api_config_section(self, section: str):
        """Glances API RESTful implementation.

        Return the JSON representation of the Glances configuration section
        HTTP/200 if OK
        HTTP/400 if item is not found
        HTTP/404 if others error
        """
        config_dict = self.config.as_dict()
        if section not in config_dict:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown configuration item {section}")

        try:
            # Get the RAW value of the config' dict
            ret_section = config_dict[section]
        except Exception as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Cannot get config section {section} ({str(e)})")

        return GlancesJSONResponse(ret_section)

    def _api_config_section_item(self, section: str, item: str):
        """Glances API RESTful implementation.

        Return the JSON representation of the Glances configuration section/item
        HTTP/200 if OK
        HTTP/400 if item is not found
        HTTP/404 if others error
        """
        config_dict = self.config.as_dict()
        if section not in config_dict:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown configuration item {section}")

        try:
            # Get the RAW value of the config' dict section
            ret_section = config_dict[section]
        except Exception as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Cannot get config section {section} ({str(e)})")

        try:
            # Get the RAW value of the config' dict item
            ret_item = ret_section[item]
        except Exception as e:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"Cannot get item {item} in config section {section} ({str(e)})"
            )

        return GlancesJSONResponse(ret_item)

    def _api_args(self):
        """Glances API RESTful implementation.

        Return the JSON representation of the Glances command line arguments
        HTTP/200 if OK
        HTTP/404 if others error
        """
        try:
            # Get the RAW value of the args' dict
            # Use vars to convert namespace to dict
            # Source: https://docs.python.org/%s/library/functions.html#vars
            args_json = vars(self.args)
        except Exception as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Cannot get args ({str(e)})")

        return GlancesJSONResponse(args_json)

    def _api_args_item(self, item: str):
        """Glances API RESTful implementation.

        Return the JSON representation of the Glances command line arguments item
        HTTP/200 if OK
        HTTP/400 if item is not found
        HTTP/404 if others error
        """
        if item not in self.args:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown argument item {item}")

        try:
            # Get the RAW value of the args' dict
            # Use vars to convert namespace to dict
            # Source: https://docs.python.org/%s/library/functions.html#vars
            args_json = vars(self.args)[item]
        except Exception as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Cannot get args item ({str(e)})")

        return GlancesJSONResponse(args_json)
