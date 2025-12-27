"""
Glances MCP Server using requests library with HTTP transport
"""
from typing import Any

import requests
from mcp.server.fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("Glances Monitor")

# Configuration
GLANCES_URL = "http://localhost:61208"  # Default Glances API URL

def make_request(endpoint: str) -> dict[str, Any]:
    """Make a GET request to the Glances API"""
    url = f"{GLANCES_URL}{endpoint}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Handle empty responses (204 No Content, etc.)
        if response.status_code == 204 or not response.content:
            return {"status": "success", "message": "No content"}

        return response.json()
    except requests.exceptions.JSONDecodeError as e:
        return {"error": f"JSON decode error: {str(e)}", "content": response.text[:200]}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

@mcp.tool()
def get_status() -> dict[str, Any]:
    """Check Glances API health status"""
    return make_request("/api/4/status")

@mcp.tool()
def get_all_stats() -> dict[str, Any]:
    """Get all system statistics from all plugins"""
    return make_request("/api/4/all")

@mcp.tool()
def get_plugins_list() -> list[str]:
    """Get list of available Glances plugins"""
    result = make_request("/api/4/pluginslist")
    if isinstance(result, list):
        return result
    return []

@mcp.tool()
def get_plugin_data(plugin: str) -> dict[str, Any]:
    """
    Get data from a specific plugin

    Args:
        plugin: Name of the plugin (e.g., cpu, mem, disk, network)
    """
    return make_request(f"/api/4/{plugin}")

@mcp.tool()
def get_plugin_history(plugin: str, nb: int = 10) -> dict[str, Any]:
    """
    Get historical data for a plugin

    Args:
        plugin: Name of the plugin
        nb: Number of historical items to retrieve (0 for all)
    """
    return make_request(f"/api/4/{plugin}/history/{nb}")

@mcp.tool()
def get_plugin_limits(plugin: str) -> dict[str, Any]:
    """
    Get limits configured for a plugin

    Args:
        plugin: Name of the plugin
    """
    return make_request(f"/api/4/{plugin}/limits")

@mcp.tool()
def get_cpu_stats() -> dict[str, Any]:
    """Get CPU statistics"""
    return make_request("/api/4/cpu")

@mcp.tool()
def get_memory_stats() -> dict[str, Any]:
    """Get memory statistics"""
    return make_request("/api/4/mem")

@mcp.tool()
def get_disk_stats() -> dict[str, Any]:
    """Get disk I/O statistics"""
    return make_request("/api/4/diskio")

@mcp.tool()
def get_network_stats() -> dict[str, Any]:
    """Get network statistics"""
    return make_request("/api/4/network")

@mcp.tool()
def get_processes(top: int | None = None) -> dict[str, Any]:
    """
    Get process list

    Args:
        top: Limit to top N processes by resource usage
    """
    if top:
        return make_request(f"/api/4/processlist/top/{top}")
    return make_request("/api/4/processlist")

@mcp.tool()
def get_process_by_pid(pid: str) -> dict[str, Any]:
    """
    Get process information by PID

    Args:
        pid: Process ID
    """
    return make_request(f"/api/4/processes/{pid}")

@mcp.tool()
def get_system_info() -> dict[str, Any]:
    """Get system information"""
    return make_request("/api/4/system")

@mcp.tool()
def get_sensors() -> dict[str, Any]:
    """Get sensor readings (temperature, fans)"""
    return make_request("/api/4/sensors")

@mcp.tool()
def get_docker_stats() -> dict[str, Any]:
    """Get Docker container statistics"""
    return make_request("/api/4/docker")

@mcp.tool()
def get_config() -> dict[str, Any]:
    """Get Glances configuration"""
    return make_request("/api/4/config")

@mcp.resource("glances://stats")
def get_system_stats() -> str:
    """Get a formatted summary of system statistics"""
    stats = make_request("/api/4/all")

    if "error" in stats:
        return f"Error fetching stats: {stats['error']}"

    summary = "=== Glances System Statistics ===\n\n"

    # CPU
    if "cpu" in stats:
        cpu = stats["cpu"]
        summary += f"CPU: {cpu.get('total', 0):.1f}% \
            (User: {cpu.get('user', 0):.1f}%, System: {cpu.get('system', 0):.1f}%)\n"

    # Memory
    if "mem" in stats:
        mem = stats["mem"]
        total_gb = mem.get("total", 0) / (1024**3)
        used_gb = mem.get("used", 0) / (1024**3)
        summary += f"Memory: {mem.get('percent', 0):.1f}% ({used_gb:.1f}GB / {total_gb:.1f}GB)\n"

    # Load
    if "load" in stats:
        load = stats["load"]
        summary += f"Load Average: {load.get('min1', 0):.2f}, {load.get('min5', 0):.2f}, {load.get('min15', 0):.2f}\n"

    return summary

@mcp.prompt()
def analyze_system_performance() -> str:
    """Generate a prompt to analyze system performance"""
    return """Please analyze the current system performance by:
1. Checking CPU usage and identifying any bottlenecks
2. Reviewing memory utilization
3. Examining disk I/O statistics
4. Looking at network traffic
5. Identifying top resource-consuming processes
6. Providing recommendations for optimization if needed"""

# For HTTP transport - create the ASGI app
# Note: The MCP endpoint will be at /mcp by default
app = mcp.streamable_http_app()

if __name__ == "__main__":
    # Run with stdio transport by default
    # For HTTP, run with: uvicorn glances_mcp:app --host 0.0.0.0 --port 8000
    # Then connect MCP clients to: http://localhost:8000/mcp
    # Or use: python glances_mcp.py --http
    import sys
    if "--http" in sys.argv:
        import uvicorn
        print("Starting Glances MCP Server on http://0.0.0.0:8000")
        print("MCP endpoint available at: http://0.0.0.0:8000/mcp")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        mcp.run()

# End of glances_mcp.py
# End of glances_mcp.py
