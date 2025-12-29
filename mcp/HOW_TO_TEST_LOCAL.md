# Glances MCP Server Testing Setup

## Prerequisites

```bash
# Install Docker and Docker Compose
sudo apt update
sudo apt install docker.io docker-compose
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect
```

## Setup Steps

### 1. Start the Services

Warning: you should use docker compose v2. If you have v1 installed, please uninstall it first.

```bash
# Save the docker-compose.yml file and run:
docker compose up -d

# Check if services are running:
docker compose ps
```

### 2. Pull an LLM Model

```bash
# Pull a recommended model (choose based on your RAM):

# For 8GB RAM - Llama 3.2 (3B parameters)
docker exec -it ollama ollama pull llama3.2

# For 16GB RAM - Llama 3.1 (8B parameters)
docker exec -it ollama ollama pull llama3.1

# For 32GB+ RAM - Llama 3.1 (70B parameters)
docker exec -it ollama ollama pull llama3.1:70b

# List available models:
docker exec -it ollama ollama list
```

### 3. Access the Services

- **Open WebUI**: http://localhost:3000
  - Create an account on first visit
  - The LLM will be automatically detected

- **Glances API**: http://localhost:61208
  - API endpoint: http://localhost:61208/api/4/
  - Web interface: http://localhost:61208

### 4. Test the Glances API

```bash
# Test basic endpoints:
curl http://localhost:61208/api/4/status
curl http://localhost:61208/api/4/pluginslist
curl http://localhost:61208/api/4/cpu
curl http://localhost:61208/api/4/mem
curl http://localhost:61208/api/4/all
```

### 5. Configure MCP Server Connection

Install mcpo:

```bash
uv add mcpo
```

Create MCPO configuration file:

```bash
cd /home/nicolargo/dev/glances/mcp

# Create configuration
cat > mcp_config.json << 'EOF'
{
  "mcpServers": {
    "glances": {
      "command": "python3",
      "args": ["glances_mcp.py"],
      "env": {
        "GLANCES_API_URL": "http://localhost:61208/api/4"
      }
    }
  }
}
EOF
```

Run MCPO proxy:

```bash
../.venv-uv/bin/uv run mcpo --port 8000 --config mcp_config.json
Starting MCP OpenAPI Proxy with config file: mcp_config.json
2025-12-29 09:38:29,310 - INFO - Starting MCPO Server...
2025-12-29 09:38:29,310 - INFO -   Name: MCP OpenAPI Proxy
2025-12-29 09:38:29,310 - INFO -   Version: 1.0
2025-12-29 09:38:29,310 - INFO -   Description: Automatically generated API from MCP Tool Schemas
2025-12-29 09:38:29,310 - INFO -   Hostname: nicolargo-xps15
2025-12-29 09:38:29,310 - INFO -   Port: 8000
2025-12-29 09:38:29,310 - INFO -   API Key: Not Provided
2025-12-29 09:38:29,310 - INFO -   CORS Allowed Origins: ['*']
2025-12-29 09:38:29,310 - INFO -   Path Prefix: /
2025-12-29 09:38:29,310 - INFO -   Root Path:
2025-12-29 09:38:29,311 - INFO - Loading MCP server configurations from: mcp_config.json
2025-12-29 09:38:29,311 - INFO - Configuring MCP Servers:
2025-12-29 09:38:29,311 - INFO - Uvicorn server starting...
INFO:     Started server process [167852]
INFO:     Waiting for application startup.
2025-12-29 09:38:29,324 - INFO - Initiating connection for server: 'glances'...
2025-12-29 09:38:29,800 - INFO - Successfully connected to 'glances'.
2025-12-29 09:38:29,800 - INFO - --------------------------

INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

Check:

```bash
curl http://localhost:8000/glances/openapi.json
```

And configure Open WebUI to use MCP server at `http://host.docker.internal:8000/glances`.

Open Open WebUI: Go to `http://localhost:3000`
Open Settings:

Click your profile icon (top right)
Select "Settings"

Add Tool Server:

Navigate to "Tools" section in the left sidebar
Click the "+" button to add a new tool server

Configure the Connection:

    Server URL: `http://172.17.0.1:8000/glances`
    API Key: Leave blank (unless you configured one)

Enable the Tool:

The Glances tools should now appear in your tools list

In the conversation interface, click the "Tools" button (usually represented by a toolbox icon) and enable the Glances tool.

Test a prompt like: "What is the current CPU usage on my system ?"

## Intel GPU Acceleration (Optional)

If you want to enable Intel GPU acceleration:

### 1. Install Intel GPU Drivers

```bash
# Install Intel compute runtime
sudo apt update
sudo apt install -y intel-opencl-icd intel-media-va-driver-non-free

# Verify GPU is accessible
ls -la /dev/dri
```

### 2. Enable GPU in Docker Compose

Uncomment these lines in `docker-compose.yml`:

```yaml
devices:
  - /dev/dri:/dev/dri
environment:
  - OLLAMA_GPU_DRIVER=intel
```

Then restart:

```bash
docker compose down
docker compose up -d
```

## Testing Your MCP Server

### Manual Test with cURL

```bash
# Test if your MCP server can call Glances endpoints
# Example: Get CPU stats
curl http://localhost:61208/api/4/cpu

# Expected response: JSON with CPU stats
```

### Test in Open WebUI

1. Open http://localhost:3000
2. Start a new chat
3. Try prompts like:
   - "What is the current CPU usage?"
   - "Show me memory statistics"
   - "List all available system plugins"

## Useful Commands

```bash
# View logs
docker compose logs -f ollama
docker compose logs -f open-webui
docker compose logs -f glances

# Restart services
docker compose restart

# Stop all services
docker compose down

# Stop and remove volumes (clean start)
docker compose down -v

# Check Ollama models
docker exec -it ollama ollama list

# Monitor resource usage
docker stats
```

## Troubleshooting

### Ollama not responding
```bash
docker compose restart ollama
docker exec -it ollama ollama list
```

### Glances API not accessible
```bash
# Check if Glances is running
curl http://localhost:61208/api/4/status

# View Glances logs
docker compose logs glances
```

### Low memory issues
```bash
# Use a smaller model
docker exec -it ollama ollama pull llama3.2:1b

# Or configure Ollama to use less memory
docker compose down
# Add to ollama service environment:
# - OLLAMA_MAX_LOADED_MODELS=1
# - OLLAMA_NUM_PARALLEL=1
docker compose up -d
```

## Recommended Models for Your Hardware

- **4-8GB RAM**: `llama3.2:1b` or `phi3:mini`
- **8-16GB RAM**: `llama3.2` or `mistral`
- **16GB+ RAM**: `llama3.1` or `mixtral`

Choose smaller models for better responsiveness on limited hardware.
