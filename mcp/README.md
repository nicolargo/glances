# Glances MCP Server

A Model Context Protocol (MCP) server that provides system monitoring capabilities through integration with [Glances](https://github.com/nicolargo/glances), a cross-platform system monitoring tool.

## Overview

The Glances MCP Server exposes Glances monitoring data through the MCP protocol, allowing AI assistants and other MCP clients to query system statistics, monitor processes, check resource usage, and analyze system performance.

## Features

- **Real-time System Monitoring**: Access CPU, memory, disk, network, and process information
- **Multiple Transport Options**: Supports both stdio (standard) and HTTP transports
- **15+ Tools**: Comprehensive set of tools for system monitoring
- **Resource Summaries**: Formatted system statistics summaries
- **Performance Analysis**: Built-in prompts for system performance analysis

## Prerequisites

- Python 3.10 or higher
- [Glances](https://github.com/nicolargo/glances) installed and running
- pip or uv package manager

## Installation

### 1. Install Glances

```bash
# Using pip
pip install glances

# Using system package manager (Ubuntu/Debian)
sudo apt install glances

# Using Homebrew (macOS)
brew install glances
```

### 2. Install MCP Server Dependencies

```bash
# Install required packages
pip install requests mcp uvicorn fastapi
```

Or create a `requirements.txt`:

```txt
requests>=2.31.0
mcp>=1.0.0
uvicorn>=0.27.0
fastapi>=0.104.0
```

Then install:

```bash
pip install -r requirements.txt
```

### 3. Download the MCP Server

Save the `glances_mcp.py` file to your desired location.

## Usage

### Starting Glances

First, start Glances in web server mode:

```bash
glances -w
```

By default, Glances runs on `http://localhost:61208`

### Running the MCP Server

#### Option 1: Stdio Transport (Default - for Claude Desktop)

```bash
python glances_mcp.py
```

This mode is used for direct integration with Claude Desktop and other MCP clients that communicate via stdio.

#### Option 2: HTTP Transport (for testing and remote access)

```bash
# Using uvicorn
uvicorn glances_mcp:app --host 0.0.0.0 --port 8000

# Or with auto-reload for development
uvicorn glances_mcp:app --host 0.0.0.0 --port 8000 --reload

# Or using the built-in flag
python glances_mcp.py --http
```

The MCP endpoint will be available at: `http://localhost:8000/mcp`

## Configuration

### Glances URL

By default, the server connects to Glances at `http://localhost:61208`. To change this, edit the `GLANCES_URL` variable in `glances_mcp.py`:

```python
GLANCES_URL = "http://your-glances-server:61208"
```

### Claude Desktop Integration

Add the following to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

#### For Stdio Transport:

```json
{
  "mcpServers": {
    "glances": {
      "command": "python",
      "args": ["/full/path/to/glances_mcp.py"]
    }
  }
}
```

#### For HTTP Transport:

```json
{
  "mcpServers": {
    "glances": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

## Available Tools

The MCP server provides the following tools:

### System Status
- **get_status**: Check Glances API health status
- **get_all_stats**: Get all system statistics from all plugins
- **get_plugins_list**: Get list of available Glances plugins

### CPU & Memory
- **get_cpu_stats**: Get CPU usage statistics
- **get_memory_stats**: Get memory usage statistics

### Storage & I/O
- **get_disk_stats**: Get disk I/O statistics
- **get_sensors**: Get sensor readings (temperature, fans)

### Network
- **get_network_stats**: Get network interface statistics

### Processes
- **get_processes**: Get process list (optionally limit to top N processes)
- **get_process_by_pid**: Get detailed information for a specific process

### System Information
- **get_system_info**: Get system information (OS, hostname, platform)
- **get_config**: Get Glances configuration

### Docker
- **get_docker_stats**: Get Docker container statistics (if Docker is available)

### Advanced
- **get_plugin_data**: Get data from any specific Glances plugin by name
- **get_plugin_history**: Get historical data for a plugin
- **get_plugin_limits**: Get configured limits for a plugin

## Resources

- **glances://stats**: A formatted summary of system statistics including CPU, memory, and load averages

## Prompts

- **analyze_system_performance**: A template prompt for comprehensive system performance analysis

## Testing

### Using MCP Inspector

The MCP Inspector is a great tool for testing your MCP server:

```bash
# For HTTP transport
npx @modelcontextprotocol/inspector http://localhost:8000/mcp

# For stdio transport
npx @modelcontextprotocol/inspector python glances_mcp.py
```

### Using curl (HTTP transport only)

```bash
# Test if Glances is responding
curl http://localhost:61208/api/4/status

# Test if MCP server is running
curl http://localhost:8000/mcp
```

## Example Usage with Claude

Once configured, you can ask Claude questions like:

- "What's my current CPU usage?"
- "Show me the top 10 processes by memory usage"
- "What's the system load average?"
- "Check if my disk I/O is high"
- "Monitor network traffic"
- "Analyze my system performance and suggest optimizations"

## Troubleshooting

### Connection Issues

**Problem**: MCP server can't connect to Glances

**Solution**:
1. Verify Glances is running: `curl http://localhost:61208/api/4/status`
2. Check the `GLANCES_URL` in `glances_mcp.py`
3. Ensure no firewall is blocking port 61208

### Empty Responses

**Problem**: Tools return empty or error responses

**Solution**:
1. Check Glances logs for errors
2. Verify the plugin exists: `curl http://localhost:61208/api/4/pluginslist`
3. Try accessing the specific endpoint directly via curl

### HTTP Transport 404 Errors

**Problem**: Getting 404 when connecting to MCP server via HTTP

**Solution**:
1. Make sure to connect to `/mcp` endpoint: `http://localhost:8000/mcp`
2. Verify the server is running with `ps aux | grep glances_mcp`
3. Check server logs for startup errors

### Claude Desktop Not Detecting Server

**Problem**: Server doesn't appear in Claude Desktop

**Solution**:
1. Check the configuration file syntax (must be valid JSON)
2. Use full absolute paths in the configuration
3. Restart Claude Desktop after configuration changes
4. Check Claude Desktop logs for errors

## Development

### Adding New Tools

To add a new tool, follow this pattern:

```python
@mcp.tool()
def your_new_tool(param: str) -> dict[str, Any]:
    """
    Description of what your tool does

    Args:
        param: Description of the parameter
    """
    return make_request(f"/api/4/{param}")
```

### Custom Glances Plugins

If you've added custom plugins to Glances, you can access them using:

```python
get_plugin_data("your_plugin_name")
```

## API Reference

For detailed information about the Glances API endpoints, see the [Glances RESTful API documentation](https://github.com/nicolargo/glances/wiki/The-Glances-RESTFULL-JSON-API).

## License

This MCP server follows the same license as Glances (LGPL-3.0).

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

- **Glances Issues**: [Glances GitHub Issues](https://github.com/nicolargo/glances/issues)
- **MCP Protocol**: [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- **General Questions**: Open an issue in this repository

## Changelog

### Latest Version
- ✅ Converted from httpx to requests library
- ✅ Added HTTP transport support via uvicorn
- ✅ Improved error handling for empty responses
- ✅ Added comprehensive documentation
- ✅ Fixed MCP endpoint configuration

## Acknowledgments

- [Glances](https://github.com/nicolargo/glances) by Nicolas Hennion
- [Model Context Protocol](https://modelcontextprotocol.io/) by Anthropic
- [FastMCP](https://github.com/jlowin/fastmcp) by Jeff Lowin