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

Warning: you should use docker-compose v2. If you have v1 installed, please uninstall it first.

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

In Open WebUI, you'll need to configure the MCP server. Here's how to test if your Glances MCP server can access the API:

**Example MCP Configuration** (adjust based on your MCP implementation):

```json
{
  "mcpServers": {
    "glances": {
      "command": "node",
      "args": ["/path/to/your/glances-mcp-server/index.js"],
      "env": {
        "GLANCES_API_URL": "http://host.docker.internal:61208/api/4"
      }
    }
  }
}
```

**Note**: Use `host.docker.internal` to access services on your host machine from within Docker containers.

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
docker-compose down
docker-compose up -d
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
docker-compose logs -f ollama
docker-compose logs -f open-webui
docker-compose logs -f glances

# Restart services
docker-compose restart

# Stop all services
docker-compose down

# Stop and remove volumes (clean start)
docker-compose down -v

# Check Ollama models
docker exec -it ollama ollama list

# Monitor resource usage
docker stats
```

## Troubleshooting

### Ollama not responding
```bash
docker-compose restart ollama
docker exec -it ollama ollama list
```

### Glances API not accessible
```bash
# Check if Glances is running
curl http://localhost:61208/api/4/status

# View Glances logs
docker-compose logs glances
```

### Low memory issues
```bash
# Use a smaller model
docker exec -it ollama ollama pull llama3.2:1b

# Or configure Ollama to use less memory
docker-compose down
# Add to ollama service environment:
# - OLLAMA_MAX_LOADED_MODELS=1
# - OLLAMA_NUM_PARALLEL=1
docker-compose up -d
```

## Recommended Models for Your Hardware

- **4-8GB RAM**: `llama3.2:1b` or `phi3:mini`
- **8-16GB RAM**: `llama3.2` or `mistral`
- **16GB+ RAM**: `llama3.1` or `mixtral`

Choose smaller models for better responsiveness on limited hardware.
