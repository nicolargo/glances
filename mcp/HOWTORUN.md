Complete Steps:

# Terminal 1: Start Glances

    glances -w

# Terminal 2: Start MCP server

    uvicorn glances_mcp:app --host 0.0.0.0 --port 8000 --reload

You should see in the logs that it's running

The MCP endpoint is at: http://localhost:8000/mcp

# Terminal 3: Start MCP Inspector

    npx @modelcontextprotocol/inspector http://localhost:8000/mcp

Or in the MCP Inspector web UI:

    Transport Type: Streamable HTTP
    URL: http://localhost:8000/mcp
    Click Connect

