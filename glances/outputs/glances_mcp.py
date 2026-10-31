#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""MCP (Model Context Protocol) server interface class."""

import json
import logging

from glances.globals import json_dumps
from glances.logger import logger
from glances.plugins.plugin import query as plugin_query
from glances.plugins.plugin.query import PluginQueryError

try:
    from mcp.server.transport_security import TransportSecuritySettings

    try:
        # MCP Python SDK >= 2: FastMCP was renamed to MCPServer
        from mcp.server.mcpserver import MCPServer
        from mcp.server.mcpserver.exceptions import ResourceError, ToolError

        MCP_V2 = True
    except ImportError:
        # MCP Python SDK 1.x
        from mcp.server.fastmcp import FastMCP as MCPServer
        from mcp.server.fastmcp.exceptions import ResourceError, ToolError

        MCP_V2 = False

    MCP_AVAILABLE = True
    logging.getLogger("mcp").setLevel(logging.WARNING)
except ImportError:
    MCP_AVAILABLE = False
    MCP_V2 = False
    MCPServer = None
    TransportSecuritySettings = None
    ResourceError = ToolError = None


# `level` values the alert_analysis prompt accepts: the engine's alert levels
# (warning and above, `careful` never alerts) plus `all`.
ALERT_LEVELS: tuple[str, ...] = ("all", "warning", "critical")


class GlancesMcpServer:
    """MCP server exposing Glances system monitoring data as resources and prompts.

    Resources (read-only data):
        glances://plugins                   - List of active plugins
        glances://stats                     - All plugins' current statistics
        glances://stats/{plugin}            - Current statistics for one plugin
        glances://stats/{plugin}/history    - Historical time-series for one plugin
        glances://limits                    - Alert thresholds for all plugins
        glances://limits/{plugin}           - Alert thresholds for one plugin
        glances://info                      - Field schema for all plugins
        glances://info/{plugin}             - Field schema for one plugin
        glances://alerts/incidents          - Ongoing and resolved alert incidents

    Prompts (analysis templates):
        system_health_summary   - Overall CPU / memory / disk / network health report
        alert_analysis          - Analysis of alert incidents with optional severity filter
        top_processes_report    - Report on the most CPU-intensive processes
        storage_health          - Disk usage and I/O statistics analysis

    Usage:
        mcp_server = GlancesMcpServer(stats, args, config)
        app.mount("/mcp", mcp_server.get_asgi_app())

    Authentication:
        The MCP endpoint inherits the authentication policy applied at the FastAPI
        router/middleware level (see glances_restful_api.py).  No authentication
        logic lives inside this class.
    """

    MCP_DEFAULT_PATH = "/mcp"

    # Anticipated failures (unknown plugin, field or item) raise ToolError from
    # a tool and ResourceError from a resource: MCP SDK >= 2 forwards only those
    # messages to the client, and replaces any other exception's text with a
    # generic "Error executing tool <name>" the model cannot correct itself from.

    def __init__(self, stats, args, config):
        """Initialize the MCP server.

        Args:
            stats: GlancesStats instance.  May be None at construction time if the
                   stats manager has not been created yet; call set_stats() before
                   the server receives its first request.
            args:  Parsed command-line arguments (argparse.Namespace).
            config: Glances configuration object (GlancesConfig).
        """
        self._stats = stats
        self._args = args
        self._config = config

        if not MCP_AVAILABLE:
            raise RuntimeError(
                "The 'mcp' package is required for MCP support. Install it with: pip install 'glances[mcp]'"
            )

        self._load_config(config)

        # MCP SDK >= 2 takes transport_security in sse_app(), 1.x in the constructor
        self._transport_security = self._build_transport_security()
        self._mcp = MCPServer(
            "Glances",
            instructions=(
                "Glances is a cross-platform system monitoring tool. "
                "Use resources to access real-time system metrics "
                "(CPU, memory, disk, network, processes, containers, sensors, …). "
                "Use prompts to generate structured analyses of the current system state."
            ),
            **({} if MCP_V2 else {"transport_security": self._transport_security}),
        )

        self._setup_resources()
        self._setup_tools()
        self._setup_prompts()
        logger.debug("GlancesMcpServer: resources, tools and prompts registered")

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def set_stats(self, stats):
        """Update the stats manager reference.

        Call this method after the GlancesStats object is created when it was
        not yet available at construction time.
        """
        self._stats = stats

    def get_asgi_app(self, mount_path: str = MCP_DEFAULT_PATH):
        """Return the SSE ASGI application ready to be mounted into FastAPI.

        Args:
            mount_path: Informational only — the URL path where this app is mounted
                        in the parent FastAPI instance (used for the log message).
                        Do NOT forward this to MCPServer.sse_app(): when Starlette
                        mounts a sub-application it sets scope['root_path'] to the
                        mount prefix automatically, and SseServerTransport uses that
                        value to build the correct endpoint URL for clients.
                        Passing mount_path again would cause the prefix to appear
                        twice (e.g. /mcp/mcp/messages/).

        Returns:
            A Starlette ASGI application.
        """
        logger.debug(f"MCP server (SSE transport) mounted at {mount_path} with allowed hosts: {self.mcp_allowed_hosts}")
        # Call sse_app() without mount_path so the server keeps its default '/'.
        # Starlette will prepend scope['root_path'] (= mount_path) at runtime,
        # producing the correct absolute endpoint URL for clients.
        if MCP_V2:
            return self._mcp.sse_app(transport_security=self._transport_security)
        # MCP SDK 1.x: transport_security is already configured on self._mcp at construction time.
        return self._mcp.sse_app()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_config(self, config):
        # MCP allowed hosts for DNS rebinding protection
        # Default: loopback only (safe for existing deployments)
        self.mcp_allowed_hosts = ["localhost", "127.0.0.1"]
        if config is not None and config.has_section('outputs'):
            raw_mcp_hosts = config.get_value("outputs", "mcp_allowed_hosts", default=None)
            if raw_mcp_hosts == "*":
                self.mcp_allowed_hosts = ["*"]
                logger.warning(
                    "MCP mcp_allowed_hosts is set to wildcard (*). Ensure the server is behind a trusted reverse proxy."
                )
            elif raw_mcp_hosts:
                self.mcp_allowed_hosts = [h.strip() for h in raw_mcp_hosts.split(",") if h.strip()]
        logger.debug(f"MCP allowed hosts: {self.mcp_allowed_hosts}")

    def _build_transport_security(self):
        """Return TransportSecuritySettings derived from mcp_allowed_hosts.

        Wildcard ("*") disables DNS rebinding protection entirely.
        Otherwise each hostname is converted to a "host:*" pattern (any port)
        and paired with http/https origin patterns.
        """
        if self.mcp_allowed_hosts == ["*"]:
            return TransportSecuritySettings(enable_dns_rebinding_protection=False)

        # Append :* to plain hostnames so the middleware matches any port.
        allowed_hosts = [h if ":" in h else f"{h}:*" for h in self.mcp_allowed_hosts]
        allowed_origins = [f"http://{h}" for h in allowed_hosts] + [f"https://{h}" for h in allowed_hosts]
        return TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts,
            allowed_origins=allowed_origins,
        )

    def _get_stats(self):
        """Return the stats manager, raising RuntimeError if not yet set."""
        if self._stats is None:
            raise RuntimeError(
                "GlancesMcpServer: stats manager is not yet initialized. Call set_stats() before serving MCP requests."
            )
        return self._stats

    def _serialize(self, data) -> str:
        """Return a UTF-8 JSON string using Glances' custom serializer.

        Glances' json_dumps handles non-standard numeric types and datetime
        objects that the stdlib json module cannot encode out of the box.
        """
        return json_dumps(data).decode("utf-8")

    # ------------------------------------------------------------------
    # Resources
    # ------------------------------------------------------------------

    def _setup_resources(self):
        """Declare all MCP resources on the MCP server instance."""
        mcp = self._mcp
        server = self  # captured by closures below

        # ---- plugins list ------------------------------------------------

        @mcp.resource(
            "glances://plugins",
            name="plugins_list",
            description=(
                "List of all active monitoring plugin names available in this "
                "Glances instance (e.g. 'cpu', 'mem', 'network', 'processlist', …)."
            ),
            mime_type="application/json",
        )
        def plugins_list() -> str:
            return server._serialize(server._get_stats().getPluginsList())

        # ---- all stats ---------------------------------------------------

        @mcp.resource(
            "glances://stats",
            name="all_stats",
            description=(
                "Current statistics from every active monitoring plugin. Returns a JSON object keyed by plugin name."
            ),
            mime_type="application/json",
        )
        def all_stats() -> str:
            return server._serialize(server._get_stats().getAllAsDict())

        # ---- per-plugin stats (resource template) ------------------------

        @mcp.resource(
            "glances://stats/{plugin}",
            name="plugin_stats",
            description=(
                "Current statistics for a specific monitoring plugin. "
                "Fetch glances://plugins first to discover available plugin names."
            ),
            mime_type="application/json",
        )
        def plugin_stats(plugin: str) -> str:
            stats = server._get_stats()
            plugin_obj = stats.get_plugin(plugin)
            if plugin_obj is None:
                available = stats.getPluginsList()
                raise ValueError(f"Plugin '{plugin}' not found. Available plugins: {available}")
            return server._serialize(plugin_obj.get_raw())

        # ---- per-plugin history (resource template) ----------------------

        @mcp.resource(
            "glances://stats/{plugin}/history",
            name="plugin_history",
            description=(
                "Historical time-series data for a specific monitoring plugin. "
                "Returns a dict of field→list pairs, most-recent value last."
            ),
            mime_type="application/json",
        )
        def plugin_history(plugin: str) -> str:
            stats = server._get_stats()
            plugin_obj = stats.get_plugin(plugin)
            if plugin_obj is None:
                raise ValueError(f"Plugin '{plugin}' not found")
            # nb=0 → return all available history points
            return server._serialize(plugin_obj.get_raw_history(item=None, nb=0))

        # ---- all limits --------------------------------------------------

        @mcp.resource(
            "glances://limits",
            name="all_limits",
            description=(
                "Warning and critical alert thresholds for all monitoring plugins. "
                "Returns a JSON object keyed by plugin name."
            ),
            mime_type="application/json",
        )
        def all_limits() -> str:
            return server._serialize(server._get_stats().getAllLimitsAsDict())

        # ---- per-plugin limits (resource template) -----------------------

        @mcp.resource(
            "glances://limits/{plugin}",
            name="plugin_limits",
            description=("Warning and critical alert thresholds for a specific monitoring plugin."),
            mime_type="application/json",
        )
        def plugin_limits(plugin: str) -> str:
            stats = server._get_stats()
            plugin_obj = stats.get_plugin(plugin)
            if plugin_obj is None:
                raise ValueError(f"Plugin '{plugin}' not found")
            return server._serialize(plugin_obj.get_limits())

        # ---- field schema ------------------------------------------------

        @mcp.resource(
            "glances://info",
            name="all_info",
            description=(
                "Field schema of every monitoring plugin: unit, description, whether a field is a "
                "rate or a cumulative counter. Read it to interpret the values in glances://stats."
            ),
            mime_type="application/json",
        )
        def all_info() -> str:
            return server._serialize(server._get_stats().getAllInfoAsDict())

        @mcp.resource(
            "glances://info/{plugin}",
            name="plugin_info",
            description="Field schema (unit, description, rate or counter) of a specific monitoring plugin.",
            mime_type="application/json",
        )
        def plugin_info(plugin: str) -> str:
            plugin_obj = server._get_stats().get_plugin(plugin)
            if plugin_obj is None:
                raise ResourceError(f"Plugin '{plugin}' not found")
            return server._serialize(plugin_obj.get_info())

        # ---- alert incidents ---------------------------------------------

        @mcp.resource(
            "glances://alerts/incidents",
            name="alert_incidents",
            description=(
                "Alerts collapsed into incidents, ongoing first: the authoritative view of what is "
                "active right now (glances://stats/alert is the raw, bounded transition log). "
                "Returns {is_initializing, incidents}; an empty list while is_initializing is "
                "true is a warm-up, not an all-clear."
            ),
            mime_type="application/json",
        )
        def alert_incidents() -> str:
            return server._serialize(server._get_alert_incidents())

    def _get_alert_incidents(self) -> dict:
        """The incidents envelope, raising when the alerts pipeline is off."""
        payload = self._get_stats().get_alert_incidents()
        if payload is None:
            raise ResourceError("Alerts subsystem disabled")
        return payload

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def _get_plugin_view(self, plugin: str):
        """The plugin view, raising the canonical 'not found' error."""
        plugin_obj = self._get_stats().get_plugin(plugin)
        if plugin_obj is None:
            raise ToolError(f"Plugin '{plugin}' not found")
        return plugin_obj

    def _run_query(self, plugin: str, query, *args) -> str:
        """Serialize a plugin query; `null` before the plugin's first cycle."""
        try:
            return self._serialize(self._get_plugin_view(plugin).query(query, *args))
        except (PluginQueryError, ValueError) as exc:
            raise ToolError(str(exc)) from exc

    def _setup_tools(self):
        """Declare the read-only MCP tools.

        Tools, not resource templates: they take the optional filters the REST
        routes take as query parameters, which URI templates cannot carry
        portably across MCP clients. Every tool reads the same filtered payload
        as the resources (issue #3211) and changes nothing on the host.
        """
        mcp = self._mcp
        server = self  # captured by closures below

        @mcp.tool(
            name="get_plugin_history",
            description=(
                "Historical time-series of a monitoring plugin, as {timestamps, series}. "
                "Narrow it to save context: 'nb' keeps the last nb points (0 = all), 'field' one "
                "historised field, 'item' one item of a collection plugin (e.g. an interface name)."
            ),
        )
        def get_plugin_history(plugin: str, nb: int = 0, field: str | None = None, item: str | None = None) -> str:
            if nb < 0:
                raise ToolError(f"nb must be >= 0, got {nb}")
            view = server._get_plugin_view(plugin)
            try:
                return server._serialize(view.get_raw_history(item=item, nb=nb, field=field))
            except KeyError as exc:
                raise ToolError(str(exc.args[0])) from exc

        @mcp.tool(
            name="get_plugin_field",
            description=(
                "One field of a monitoring plugin: {field: value}, or the list of its values for a "
                "collection plugin. With 'item' (a primary-key value such as a pid or an interface "
                "name), the field of that one item. null while the plugin has not published yet."
            ),
        )
        def get_plugin_field(plugin: str, field: str, item: str | None = None) -> str:
            if item is None:
                return server._run_query(plugin, plugin_query.field_values, field)
            return server._run_query(plugin, plugin_query.item_field, field, item)

        @mcp.tool(
            name="get_plugin_top",
            description=(
                "The first n items of a collection plugin, in the plugin's own order (processlist: "
                "the server's current process sort). null while the plugin has not published yet."
            ),
        )
        def get_plugin_top(plugin: str, n: int) -> str:
            return server._run_query(plugin, plugin_query.top, n)

        @mcp.tool(
            name="get_plugin_items_by_value",
            description=(
                "The items of a collection plugin whose field equals value (compared as text): "
                "{value: [items]}. null while the plugin has not published yet."
            ),
        )
        def get_plugin_items_by_value(plugin: str, field: str, value: str) -> str:
            return server._run_query(plugin, plugin_query.items_by_value, field, value)

    # ------------------------------------------------------------------
    # Prompts
    # ------------------------------------------------------------------

    def _setup_prompts(self):
        """Declare all MCP prompt templates on the MCP server instance."""
        mcp = self._mcp
        server = self  # captured by closures below

        # ---- system health summary ---------------------------------------

        @mcp.prompt(
            name="system_health_summary",
            description=(
                "Generate a comprehensive system health report covering CPU, "
                "memory, swap, load average, filesystems, and network interfaces."
            ),
        )
        def system_health_summary() -> str:
            stats = server._get_stats()
            data = {
                plugin: stats.get_plugin(plugin).get_raw()
                for plugin in ("cpu", "mem", "memswap", "load", "fs", "network")
                if stats.get_plugin(plugin) is not None
            }
            return (
                "You are a system administrator assistant. "
                "Analyze the following real-time system monitoring data collected by Glances "
                "and produce a concise health report.\n"
                "Highlight any metrics that exceed warning or critical thresholds, "
                "identify potential bottlenecks, and suggest remediation steps where needed.\n\n"
                f"System data (JSON):\n{json.dumps(data, default=str, indent=2)}"
            )

        # ---- alert analysis ----------------------------------------------

        @mcp.prompt(
            name="alert_analysis",
            description=(
                "Analyze Glances alert incidents (ongoing and recently resolved). "
                "Accepts an optional 'level' parameter: 'warning', 'critical', or 'all' (default)."
            ),
        )
        def alert_analysis(level: str = "all") -> str:
            if level not in ALERT_LEVELS:
                raise ValueError(f"Unknown level {level!r}, expected one of: {', '.join(ALERT_LEVELS)}")
            data = server._get_alert_incidents()
            if level != "all":
                data = {**data, "incidents": [i for i in data["incidents"] if i.get("level") == level]}
            return (
                "You are a system administrator assistant. "
                f"Analyze the following Glances alert incidents (severity filter: '{level}').\n"
                "Incidents with \"ongoing\": true are active now; the others are resolved. "
                "If \"is_initializing\" is true, Glances is still warming up: an empty list "
                "then does not mean the system is healthy.\n"
                "For each incident, explain the likely cause, the risk level, "
                "and the recommended corrective action.\n\n"
                f"Alert incidents (JSON):\n{json.dumps(data, default=str, indent=2)}"
            )

        # ---- top processes report ----------------------------------------

        @mcp.prompt(
            name="top_processes_report",
            description=(
                "Report on the most resource-consuming processes currently running. "
                "Accepts an optional 'nb' parameter for the number of processes (default: 10)."
            ),
        )
        def top_processes_report(nb: int = 10) -> str:
            stats = server._get_stats()
            proc_plugin = stats.get_plugin("processlist")
            processes: list = []
            if proc_plugin is not None:
                all_procs = proc_plugin.get_raw() or []
                # The v5 stats facade serves the collection envelope {"data": [...]}
                if isinstance(all_procs, dict):
                    all_procs = all_procs.get("data", [])
                processes = sorted(
                    all_procs,
                    key=lambda p: p.get("cpu_percent", 0),
                    reverse=True,
                )[:nb]
            return (
                "You are a system administrator assistant. "
                f"Analyze the following top {nb} processes sorted by CPU usage, "
                "as reported by Glances.\n"
                "Identify processes that may be causing performance issues, "
                "explain what each process likely does, "
                "and suggest optimization steps where appropriate.\n\n"
                f"Top processes (JSON):\n{json.dumps(processes, default=str, indent=2)}"
            )

        # ---- storage health ----------------------------------------------

        @mcp.prompt(
            name="storage_health",
            description=(
                "Analyze disk usage and I/O statistics to assess storage health and identify potential issues."
            ),
        )
        def storage_health() -> str:
            stats = server._get_stats()
            data = {
                plugin: stats.get_plugin(plugin).get_raw()
                for plugin in ("fs", "diskio")
                if stats.get_plugin(plugin) is not None
            }
            return (
                "You are a system administrator assistant. "
                "Analyze the following disk and filesystem statistics collected by Glances.\n"
                "Identify filesystems that are critically full, "
                "highlight unusual I/O patterns, "
                "and provide actionable recommendations.\n\n"
                f"Storage data (JSON):\n{json.dumps(data, default=str, indent=2)}"
            )
