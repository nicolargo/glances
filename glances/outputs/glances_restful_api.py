#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""RestFul API interface class."""

import os
import socket
import sys
import webbrowser
from typing import Annotated, Any
from urllib.parse import urljoin

from glances import __apiversion__, __version__
from glances.events_list import glances_events
from glances.globals import json_dumps
from glances.logger import logger
from glances.password import GlancesPassword

# JWT import with fallback
try:
    from glances.jwt_utils import JWTHandler

    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    JWTHandler = None
# MCP import with fallback
try:
    from glances.outputs.glances_mcp import GlancesMcpServer

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    GlancesMcpServer = None

from glances.plugins.plugin.dag import get_plugin_dependencies
from glances.processes import glances_processes
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
import contextlib
import threading
import time

security = HTTPBasic(auto_error=False)


class GlancesMcpAuthMiddleware:
    """Pure ASGI middleware that applies Basic/JWT authentication to the MCP endpoint.

    Unlike BaseHTTPMiddleware, this implementation does not buffer response bodies
    and is therefore safe to use with Server-Sent Events (SSE) streaming connections.

    It reuses the password and JWT handler already configured on the REST API instance,
    so there is no separate credential store to maintain.
    """

    def __init__(self, app, api_instance, mcp_path: str = "/mcp") -> None:
        self._app = app
        self._api = api_instance
        # Normalise: no trailing slash, so prefix matching is unambiguous.
        self._mcp_path = mcp_path.rstrip("/")

    async def __call__(self, scope, receive, send) -> None:
        # Lifespan and non-HTTP scopes are forwarded unchanged.
        if scope["type"] not in ("http", "websocket"):
            await self._app(scope, receive, send)
            return

        path = scope.get("path", "")
        on_mcp_path = path == self._mcp_path or path.startswith(self._mcp_path + "/")
        if not on_mcp_path:
            await self._app(scope, receive, send)
            return

        # If no password is configured, the MCP endpoint is open (same as REST API).
        if not self._api._password:
            await self._app(scope, receive, send)
            return

        # CORS preflight requests must pass through so that the CORS middleware
        # can respond with the appropriate headers.
        if scope.get("method") == "OPTIONS":
            await self._app(scope, receive, send)
            return

        if self._is_authenticated(scope):
            await self._app(scope, receive, send)
        else:
            await self._send_401(scope, receive, send)

    def _get_auth_header(self, scope) -> str:
        """Extract the raw Authorization header value from the ASGI scope."""
        for name, value in scope.get("headers", []):
            if name.lower() == b"authorization":
                return value.decode("utf-8", errors="replace")
        return ""

    def _is_authenticated(self, scope) -> bool:
        """Return True if the request carries valid Basic or Bearer credentials."""
        import base64

        auth = self._get_auth_header(scope)

        # JWT Bearer token (checked first, as in the REST API handler).
        if self._api._jwt_handler is not None and auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1]
            username = self._api._jwt_handler.verify_token(token)
            return username == self._api.args.username

        # HTTP Basic Auth.
        if auth.lower().startswith("basic "):
            try:
                decoded = base64.b64decode(auth[6:]).decode("utf-8")
                username, _, password = decoded.partition(":")
                if username == self._api.args.username:
                    return self._api._password.check_password(
                        self._api.args.password,
                        self._api._password.get_hash(password),
                    )
            except Exception:
                pass

        return False

    @staticmethod
    async def _send_401(scope, receive, send) -> None:
        """Send an HTTP 401 response directly through the ASGI interface."""
        body = b"Not authenticated"
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"www-authenticate", b"Basic"),
                    (b"content-type", b"text/plain; charset=utf-8"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


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
        # daemon=True: if the main thread exits the process won't be kept alive
        # by a uvicorn thread blocked on a persistent connection (e.g. MCP/SSE).
        thread = threading.Thread(target=self.run, daemon=True)
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
            # Give uvicorn a brief window for graceful shutdown.
            # Extra CTRL+C signals pressed during shutdown are absorbed so that
            # force_exit is always reached when there are lingering connections
            # (e.g. a MCP client holding an SSE connection open).
            # daemon=True above guarantees the process exits even if the thread
            # hasn't fully stopped by the time we leave this block.
            try:
                thread.join(timeout=3)
            except KeyboardInterrupt:
                pass
            if thread.is_alive():
                self.force_exit = True
                try:
                    thread.join(timeout=2)
                except KeyboardInterrupt:
                    pass


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
        self.bind_url = urljoin(f'{self.protocol}://{self.args.bind_address}:{self.args.port}/', self.url_prefix)

        # FastAPI Init
        # Note: Authentication is now applied at router level, not app level,
        # to allow the token endpoint to be unauthenticated
        self._app = FastAPI(default_response_class=GlancesJSONResponse)
        if self.args.password:
            self._password = GlancesPassword(username=args.username, config=config)
            # Initialize JWT handler
            if JWT_AVAILABLE:
                jwt_secret = config.get_value('outputs', 'jwt_secret_key', default=None)
                jwt_expire = config.get_int_value('outputs', 'jwt_expire_minutes', default=60)
                self._jwt_handler = JWTHandler(secret_key=jwt_secret, expire_minutes=jwt_expire)
                logger.info(f"JWT authentication enabled (token expiration: {jwt_expire} minutes)")
            else:
                self._jwt_handler = None
                logger.info("JWT authentication not available (python-jose not installed)")
        else:
            self._password = None
            self._jwt_handler = None

        # Set path for WebUI
        webui_root_path = config.get_value(
            'outputs', 'webui_root_path', default=os.path.dirname(os.path.realpath(__file__))
        )
        if webui_root_path == '':
            webui_root_path = os.path.dirname(os.path.realpath(__file__))
        self.STATIC_PATH = os.path.join(webui_root_path, 'static/public')
        self.TEMPLATE_PATH = os.path.join(webui_root_path, 'static/templates')
        self._templates = Jinja2Templates(directory=self.TEMPLATE_PATH)

        # FastAPI Enable GZIP compression
        # https://fastapi.tiangolo.com/advanced/middleware/
        # Should be done before other middlewares to avoid
        # LocalProtocolError("Too much data for declared Content-Length")
        self._app.add_middleware(GZipMiddleware, minimum_size=1000)

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

        # FastAPI Define routes
        # Token endpoint router (no authentication required) - must be added first
        if self.args.password and self._jwt_handler is not None:
            self._app.include_router(self._token_router())
        self._app.include_router(self._router())

        # MCP server (optional).
        # Activated when either glances.conf [outputs] enable_mcp = true
        # or the --enable-mcp CLI flag is passed.
        # The CLI --mcp-path overrides the config file value when provided.
        if getattr(self.args, 'enable_mcp', False):
            self.mcp_enabled = True
        if getattr(self.args, 'mcp_path', None):
            self.mcp_path = self.args.mcp_path
            if not self.mcp_path.startswith('/'):
                self.mcp_path = '/' + self.mcp_path
        self._mcp_server = None
        if MCP_AVAILABLE and self.mcp_enabled:
            self._mcp_server = GlancesMcpServer(stats=None, args=self.args, config=self.config)
            full_mcp_path = self.url_prefix + self.mcp_path
            # Auth middleware must be outermost (added last) so it intercepts requests
            # before they reach the MCP sub-application.  It is a pure ASGI middleware
            # so it does not buffer the response body and is safe with SSE streams.
            if self.args.password:
                self._app.add_middleware(
                    GlancesMcpAuthMiddleware,
                    api_instance=self,
                    mcp_path=full_mcp_path,
                )
            self._app.mount(
                full_mcp_path,
                self._mcp_server.get_asgi_app(mount_path=full_mcp_path),
            )
            bindmsg = f'Glances MCP server started on {self.protocol}://{self.args.bind_address}:{self.args.port}{full_mcp_path}'
            logger.info(bindmsg)
            print(bindmsg)
        elif self.mcp_enabled and not MCP_AVAILABLE:
            logger.warning("MCP server is enabled in config but the 'mcp' package is not installed.")
            logger.warning("Install it with: pip install 'glances[mcp]'")

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
        # Default values
        self.url_prefix = ''
        self.protocol = 'http'
        self.ssl_keyfile = None
        self.ssl_keyfile_password = None
        self.ssl_certfile = None
        self.mcp_enabled = False
        self.mcp_path = '/mcp'
        if config is not None and config.has_section('outputs'):
            # Max process to display in the WebUI
            n = config.get_value('outputs', 'max_processes_display', default=None)
            logger.debug(f'Number of processes to display in the WebUI: {n}')
            # URL prefix
            self.url_prefix = config.get_value('outputs', 'url_prefix', default='')
            if self.url_prefix != '':
                self.url_prefix = self.url_prefix.rstrip('/')
            logger.debug(f'URL prefix: {self.url_prefix}')
            # SSL
            self.ssl_keyfile = config.get_value('outputs', 'ssl_keyfile', default=None)
            self.ssl_keyfile_password = config.get_value('outputs', 'ssl_keyfile_password', default=None)
            self.ssl_certfile = config.get_value('outputs', 'ssl_certfile', default=None)
            self.protocol = 'https' if self.is_ssl() else 'http'
            # MCP server
            self.mcp_enabled = config.get_bool_value('outputs', 'enable_mcp', default=False)
            self.mcp_path = config.get_value('outputs', 'mcp_path', default='/mcp')
            if not self.mcp_path.startswith('/'):
                self.mcp_path = '/' + self.mcp_path
        logger.debug(f"Protocol for Resful API and WebUI: {self.protocol}")
        logger.debug(f"MCP server enabled: {self.mcp_enabled} (path: {self.url_prefix + self.mcp_path})")

    def is_ssl(self):
        """Return true if the Glances server use SSL."""
        return self.ssl_keyfile is not None and self.ssl_certfile is not None

    def __update_stats(self, plugins_list_to_update=None):
        # Never update more than 1 time per cached_time
        # Also update if specific plugins are requested
        # In  this case, lru_cache will handle the stat's update frequency
        if self.timer.finished() or plugins_list_to_update:
            self.stats.update(plugins_list_to_update=plugins_list_to_update)
            self.timer = Timer(self.args.cached_time)

    def __update_servers_list(self):
        # Never update more than 1 time per cached_time
        if self.timer.finished() and self.servers_list is not None:
            self.servers_list.update_servers_stats()
            self.timer = Timer(self.args.cached_time)

    def authentication(
        self,
        request: Request,
        basic_creds: Annotated[HTTPBasicCredentials | None, Depends(security)] = None,
    ):
        """Check if a username/password combination or JWT token is valid.

        Supports both HTTP Basic Auth and Bearer Token (JWT) authentication.
        JWT Bearer tokens are checked first (manually from header) to avoid
        HTTPBasic(auto_error=True) rejecting Bearer Authorization headers.
        If no Bearer token is found, HTTPBasic handles the browser auth dialog.
        """
        # Try JWT Bearer token first (manually from request header)
        if self._jwt_handler is not None and self._jwt_handler.is_available:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.lower().startswith("bearer "):
                token = auth_header.split(" ", 1)[1]
                username = self._jwt_handler.verify_token(token)
                if username is not None and username == self.args.username:
                    return username
                # Invalid Bearer token - reject immediately
                raise HTTPException(
                    status.HTTP_401_UNAUTHORIZED,
                    "Incorrect authentication",
                    {"WWW-Authenticate": "Bearer"},
                )

        # Fall back to Basic Auth
        # If no credentials provided (basic_creds is None), trigger browser dialog
        if basic_creds is None:
            # Force HTTPBasic auto_error behavior to trigger browser auth dialog
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Not authenticated",
                {"WWW-Authenticate": "Basic"},
            )

        if basic_creds.username == self.args.username:
            if self._password.check_password(self.args.password, self._password.get_hash(basic_creds.password)):
                return basic_creds.username

        # Invalid credentials
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect authentication",
            {"WWW-Authenticate": "Basic"},
        )

    def _logo(self):
        return rf"""
  _____ _
 / ____| |
| |  __| | __ _ _ __   ___ ___  ___
| | |_ | |/ _` | '_ \ / __/ _ \/ __|
| |__| | | (_| | | | | (_|  __/\__
 \_____|_|\__,_|_| |_|\___\___||___/ {__version__}
        """

    def _token_router(self) -> APIRouter:
        """Define a router for the token endpoint (no authentication required)."""
        base_path = f'/api/{self.API_VERSION}'
        router = APIRouter(prefix=self.url_prefix)
        # Override global dependencies with empty list to disable authentication for this route
        router.add_api_route(f'{base_path}/token', self._api_token, methods=['POST'], dependencies=[])
        return router

    def _router(self) -> APIRouter:
        """Define a custom router for Glances path."""
        base_path = f'/api/{self.API_VERSION}'
        plugin_path = f"{base_path}/{{plugin}}"

        # Create the main router with authentication if password is set
        if self.args.password:
            router = APIRouter(prefix=self.url_prefix, dependencies=[Depends(self.authentication)])
        else:
            router = APIRouter(prefix=self.url_prefix)

        # REST API route definition
        # ==========================

        # HEAD
        router.add_api_route(f'{base_path}/status', self._api_status, methods=['HEAD'])

        # POST
        router.add_api_route(f'{base_path}/events/clear/warning', self._events_clear_warning, methods=['POST'])
        router.add_api_route(f'{base_path}/events/clear/all', self._events_clear_all, methods=['POST'])
        router.add_api_route(
            f'{base_path}/processes/extended/disable', self._api_disable_extended_processes, methods=['POST']
        )
        router.add_api_route(
            f'{base_path}/processes/extended/{{pid}}', self._api_set_extended_processes, methods=['POST']
        )

        # GET
        router.add_api_route(f'{base_path}/status', self._api_status, methods=['GET'])
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
            f'{base_path}/processes/extended': self._api_get_extended_processes,
            f'{base_path}/processes/{{pid}}': self._api_get_processes,
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

        # Logo
        print(self._logo())

        # Browser WEBUI
        if hasattr(self.args, 'browser') and self.args.browser:
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

        # Propagate stats to the MCP server (was None at construction time)
        if self._mcp_server is not None:
            self._mcp_server.set_stats(self.stats)

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
            self._app,
            host=self.args.bind_address,
            port=self.args.port,
            access_log=self.args.debug,
            ssl_keyfile=self.ssl_keyfile,
            ssl_certfile=self.ssl_certfile,
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

    async def _api_token(self, request: Request):
        """Glances API RESTful implementation.

        Generate a JWT access token for authenticated users.

        Expected JSON body:
        {
            "username": "string",
            "password": "string"
        }

        Returns:
        {
            "access_token": "string",
            "token_type": "bearer",
            "expires_in": int (seconds)
        }
        """
        # Check if JWT is available
        if self._jwt_handler is None or not self._jwt_handler.is_available:
            raise HTTPException(
                status.HTTP_501_NOT_IMPLEMENTED,
                "JWT authentication is not available. Install python-jose or check configuration.",
            )

        # Check if password authentication is enabled
        if self._password is None:
            raise HTTPException(
                status.HTTP_501_NOT_IMPLEMENTED,
                "Password authentication is not enabled. Start Glances with --password option.",
            )

        # Parse request body
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid JSON body")

        username = body.get('username')
        password = body.get('password')

        if not username or not password:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Missing username or password in request body",
            )

        # Validate credentials
        if username != self.args.username:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Incorrect authentication",
                {"WWW-Authenticate": "Bearer"},
            )

        # Check password
        if not self._password.check_password(self.args.password, self._password.get_hash(password)):
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Incorrect authentication",
                {"WWW-Authenticate": "Bearer"},
            )

        # Generate token
        access_token = self._jwt_handler.create_access_token(username)

        return GlancesJSONResponse(
            {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": self._jwt_handler.expire_minutes * 60,
            }
        )

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
        # TODO: Why ??? Try to comment it
        # self.__update_stats()

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

    # Comment this solve an issue on Home Assistant See #3238
    def _api_all(self):
        """Glances API RESTful implementation.

        Return the JSON representation of all the plugins
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """

        # Update the stat
        self.__update_stats()

        try:
            # Get the RAW value of the stat ID
            # TODO in #3211: use getAllExportsAsDict instead but break UI for uptime, processlist, others ?
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
        self.__update_stats(get_plugin_dependencies(plugin))

        try:
            # Get the RAW value of the stat ID
            statval = self.stats.get_plugin(plugin).get_api()
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
        self.__update_stats(get_plugin_dependencies(plugin))

        try:
            # Get the RAW value of the stat ID
            statval = self.stats.get_plugin(plugin).get_api()
        except Exception as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Cannot get plugin {plugin} ({str(e)})")

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
        self.__update_stats(get_plugin_dependencies(plugin))

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
            ret = self.stats.get_plugin(plugin).get_limits()
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
        self.__update_stats(get_plugin_dependencies(plugin))

        try:
            # Get the RAW value of the stat views
            # TODO in #3211: use a non existing (to be created) get_export_item instead but break API
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
        self.__update_stats(get_plugin_dependencies(plugin))

        try:
            # Get the RAW value of the stat views
            # TODO in #3211: use a non existing (to be created) get_export_key instead but break API
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
        self.__update_stats(get_plugin_dependencies(plugin))

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
        self.__update_stats(get_plugin_dependencies(plugin))

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
        self.__update_stats(get_plugin_dependencies(plugin))

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

    def _api_value(self, plugin: str, item: str, value: str | int | float):
        """Glances API RESTful implementation.

        Return the process stats (dict) for the given item=value
        HTTP/200 if OK
        HTTP/400 if plugin is not found
        HTTP/404 if others error
        """
        self._check_if_plugin_available(plugin)

        # Update the stat
        self.__update_stats(get_plugin_dependencies(plugin))

        try:
            # Get the RAW value
            # TODO in #3211: use a non existing (to be created) get_export_item_value instead but break API
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

    def _api_set_extended_processes(self, pid: str):
        """Glances API RESTful implementation.

        Set the extended process stats for the given PID
        HTTP/200 if OK
        HTTP/400 if PID is not found
        HTTP/404 if others error
        """
        process_stats = glances_processes.get_stats(int(pid))

        if not process_stats:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown PID process {pid}")

        glances_processes.extended_process = process_stats

        return GlancesJSONResponse(True)

    def _api_disable_extended_processes(self):
        """Glances API RESTful implementation.

        Disable extended process stats
        HTTP/200 if OK
        HTTP/400 if PID is not found
        HTTP/404 if others error
        """
        glances_processes.extended_process = None

        return GlancesJSONResponse(True)

    def _api_get_extended_processes(self):
        """Glances API RESTful implementation.

        Get the extended process stats (if set before)
        HTTP/200 if OK
        HTTP/400 if PID is not found
        HTTP/404 if others error
        """
        process_stats = glances_processes.get_extended_stats()

        if not process_stats:
            process_stats = {}

        return GlancesJSONResponse(process_stats)

    def _api_get_processes(self, pid: str):
        """Glances API RESTful implementation.

        Get the process stats for the given PID
        HTTP/200 if OK
        HTTP/400 if PID is not found
        HTTP/404 if others error
        """
        process_stats = glances_processes.get_stats(int(pid))

        if not process_stats:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown PID process {pid}")

        return GlancesJSONResponse(process_stats)


# End of GlancesRestfulApi class
