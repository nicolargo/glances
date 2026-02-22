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

try:
    from mcp.server.fastmcp import FastMCP

    MCP_AVAILABLE = True
    logging.getLogger("mcp").setLevel(logging.WARNING)
except ImportError:
    MCP_AVAILABLE = False
    FastMCP = None


class GlancesMcpServer:
    """MCP server exposing Glances system monitoring data as resources and prompts.

    Resources (read-only data):
        glances://plugins                   - List of active plugins
        glances://stats                     - All plugins' current statistics
        glances://stats/{plugin}            - Current statistics for one plugin
        glances://stats/{plugin}/history    - Historical time-series for one plugin
        glances://limits                    - Alert thresholds for all plugins
        glances://limits/{plugin}           - Alert thresholds for one plugin

    Prompts (analysis templates):
        system_health_summary   - Overall CPU / memory / disk / network health report
        alert_analysis          - Analysis of active alerts with optional severity filter
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

        self._mcp = FastMCP(
            "Glances",
            instructions=(
                "Glances is a cross-platform system monitoring tool. "
                "Use resources to access real-time system metrics "
                "(CPU, memory, disk, network, processes, containers, sensors, …). "
                "Use prompts to generate structured analyses of the current system state."
            ),
        )

        self._setup_resources()
        self._setup_prompts()
        logger.debug("GlancesMcpServer: resources and prompts registered")

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
                        Do NOT forward this to FastMCP.sse_app(): when Starlette
                        mounts a sub-application it sets scope['root_path'] to the
                        mount prefix automatically, and SseServerTransport uses that
                        value to build the correct endpoint URL for clients.
                        Passing mount_path again would cause the prefix to appear
                        twice (e.g. /mcp/mcp/messages/).

        Returns:
            A Starlette ASGI application.
        """
        logger.debug(f"MCP server (SSE transport) mounted at {mount_path}")
        # Call sse_app() without mount_path so FastMCP keeps its default '/'.
        # Starlette will prepend scope['root_path'] (= mount_path) at runtime,
        # producing the correct absolute endpoint URL for clients.
        return self._mcp.sse_app()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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
        """Declare all MCP resources on the FastMCP instance."""
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

    # ------------------------------------------------------------------
    # Prompts
    # ------------------------------------------------------------------

    def _setup_prompts(self):
        """Declare all MCP prompt templates on the FastMCP instance."""
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
                "Analyze active Glances system alerts and warnings. "
                "Accepts an optional 'level' parameter: 'warning', 'critical', or 'all' (default)."
            ),
        )
        def alert_analysis(level: str = "all") -> str:
            stats = server._get_stats()
            alert_plugin = stats.get_plugin("alert")
            data = alert_plugin.get_raw() if alert_plugin is not None else []
            return (
                "You are a system administrator assistant. "
                f"Analyze the following Glances system alerts (severity filter: '{level}').\n"
                "For each alert, explain the likely cause, the risk level, "
                "and the recommended corrective action.\n\n"
                f"Active alerts (JSON):\n{json.dumps(data, default=str, indent=2)}"
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
