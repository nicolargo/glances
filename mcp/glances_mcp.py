"""
MCP Server for Glances API
Enables system monitoring integration with AI workflows via Glances
"""

from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("Glances Monitor")

# Glances base URL configuration
# Can be modified via environment variable
GLANCES_BASE_URL = "http://localhost:61208"


# ===== Basic Tools =====


@mcp.tool()
async def check_glances_status() -> dict[str, Any]:
    """
    Check the Glances API status.
    Returns a 200 status code if the API is operational.

    Returns:
        dict: API status
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{GLANCES_BASE_URL}/api/4/status")
        response.raise_for_status()
        return {"status": "healthy", "status_code": response.status_code}


@mcp.tool()
async def get_plugins_list() -> list[str]:
    """
    Retrieve the list of all available plugins in Glances.
    Plugins represent different types of available system data
    (cpu, memory, disk, network, processes, etc.).

    Returns:
        list[str]: List of available plugin names
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{GLANCES_BASE_URL}/api/4/pluginslist")
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_all_system_stats() -> dict[str, Any]:
    """
    Retrieve all system statistics from all plugins.
    Warning: may return a large amount of data.

    Returns:
        dict: Dictionary containing all stats from all plugins
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{GLANCES_BASE_URL}/api/4/all")
        response.raise_for_status()
        return response.json()


# ===== Plugin Tools =====


@mcp.tool()
async def get_plugin_data(plugin_name: str) -> dict[str, Any]:
    """
    Retrieve data from a specific plugin.

    Args:
        plugin_name: Plugin name (e.g., 'cpu', 'mem', 'disk', 'network', 'sensors')

    Returns:
        dict: Requested plugin data

    Examples:
        - plugin_name='cpu' : CPU statistics
        - plugin_name='mem' : memory usage
        - plugin_name='disk' : disk usage
        - plugin_name='network' : network statistics
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{GLANCES_BASE_URL}/api/4/{plugin_name}")
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_plugin_history(plugin_name: str, nb_items: int = 10) -> dict[str, Any]:
    """
    Retrieve the history of data from a plugin.

    Args:
        plugin_name: Plugin name
        nb_items: Number of historical items to retrieve (0 = all)

    Returns:
        dict: Plugin data history
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{GLANCES_BASE_URL}/api/4/{plugin_name}/history/{nb_items}")
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_plugin_limits(plugin_name: str) -> dict[str, Any]:
    """
    Retrieve the configured limits for a plugin.
    Limits define alert thresholds (warning, critical).

    Args:
        plugin_name: Plugin name

    Returns:
        dict: Configured limits for the plugin
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{GLANCES_BASE_URL}/api/4/{plugin_name}/limits")
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_plugin_item(plugin_name: str, item_name: str) -> Any:
    """
    Retrieve a specific value from a plugin.

    Args:
        plugin_name: Plugin name
        item_name: Item name to retrieve

    Returns:
        Any: Value of the requested item

    Examples:
        - plugin_name='cpu', item_name='total' : total CPU usage
        - plugin_name='mem', item_name='percent' : memory usage percentage
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{GLANCES_BASE_URL}/api/4/{plugin_name}/{item_name}")
        response.raise_for_status()
        return response.json()


# ===== Process Tools =====


@mcp.tool()
async def get_process_info(pid: int) -> dict[str, Any]:
    """
    Retrieve detailed information about a specific process.

    Args:
        pid: Process ID (PID)

    Returns:
        dict: Detailed information about the process
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{GLANCES_BASE_URL}/api/4/processes/{pid}")
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_top_processes(nb_processes: int = 10) -> list[dict[str, Any]]:
    """
    Retrieve the N most resource-intensive processes.

    Args:
        nb_processes: Number of processes to retrieve

    Returns:
        list[dict]: List of the most active processes
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{GLANCES_BASE_URL}/api/4/processlist/top/{nb_processes}")
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_extended_processes() -> dict[str, Any]:
    """
    Retrieve extended process statistics (if configured).

    Returns:
        dict: Extended process statistics
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{GLANCES_BASE_URL}/api/4/processes/extended")
        response.raise_for_status()
        return response.json()


# ===== Configuration Tools =====


@mcp.tool()
async def get_glances_config() -> dict[str, Any]:
    """
    Retrieve the complete Glances configuration.

    Returns:
        dict: Glances configuration
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{GLANCES_BASE_URL}/api/4/config")
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_config_section(section_name: str) -> dict[str, Any]:
    """
    Retrieve a specific configuration section.

    Args:
        section_name: Configuration section name

    Returns:
        dict: Content of the requested section
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{GLANCES_BASE_URL}/api/4/config/{section_name}")
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_command_args() -> dict[str, Any]:
    """
    Retrieve Glances command-line arguments.

    Returns:
        dict: Command-line arguments used
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{GLANCES_BASE_URL}/api/4/args")
        response.raise_for_status()
        return response.json()


# ===== Administration Tools =====


@mcp.tool()
async def clear_warning_events() -> dict[str, str]:
    """
    Clear all warning-type events.

    Returns:
        dict: Operation confirmation
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{GLANCES_BASE_URL}/api/4/events/clear/warning")
        response.raise_for_status()
        return {"status": "success", "message": "Warning events cleared"}


@mcp.tool()
async def clear_all_events() -> dict[str, str]:
    """
    Clear all events.

    Returns:
        dict: Operation confirmation
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{GLANCES_BASE_URL}/api/4/events/clear/all")
        response.raise_for_status()
        return {"status": "success", "message": "All events cleared"}


# ===== Specific Tools for Common Metrics =====


@mcp.tool()
async def get_cpu_usage() -> dict[str, Any]:
    """
    Shortcut to get CPU usage.

    Returns:
        dict: Detailed CPU statistics
    """
    return await get_plugin_data("cpu")


@mcp.tool()
async def get_memory_usage() -> dict[str, Any]:
    """
    Shortcut to get memory usage.

    Returns:
        dict: Detailed memory statistics
    """
    return await get_plugin_data("mem")


@mcp.tool()
async def get_disk_usage() -> dict[str, Any]:
    """
    Shortcut to get disk usage.

    Returns:
        dict: Detailed disk statistics
    """
    return await get_plugin_data("fs")


@mcp.tool()
async def get_network_stats() -> dict[str, Any]:
    """
    Shortcut to get network statistics.

    Returns:
        dict: Detailed network statistics
    """
    return await get_plugin_data("network")


@mcp.tool()
async def get_system_sensors() -> dict[str, Any]:
    """
    Retrieve system sensor data (temperature, fans).

    Returns:
        dict: System sensor data
    """
    return await get_plugin_data("sensors")


# ===== Entry Point =====

if __name__ == "__main__":
    # The MCP server can be started with:
    # python glances_mcp.py
    # or configured in claude_desktop_config.json
    mcp.run()

# End of mcp/glances_mcp.py
