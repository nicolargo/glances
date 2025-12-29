#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "   Glances MCP Server Setup Verification"
echo "=========================================="
echo ""

# Check if Docker is running
echo -n "Checking Docker... "
if docker info > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if services are running
echo -n "Checking Ollama service... "
if docker ps | grep -q ollama; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "Error: Ollama container is not running. Run 'docker-compose up -d'"
    exit 1
fi

echo -n "Checking Open WebUI service... "
if docker ps | grep -q open-webui; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "Warning: Open WebUI container is not running."
fi

echo -n "Checking Glances service... "
if docker ps | grep -q glances; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "Warning: Glances container is not running."
fi

echo ""
echo "Testing API endpoints..."
echo ""

# Test Ollama
echo -n "Testing Ollama API... "
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
    echo "  Available models:"
    curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | sed 's/^/    - /'
else
    echo -e "${RED}✗${NC}"
    echo "  Error: Cannot connect to Ollama API"
fi

echo ""

# Test Glances
echo -n "Testing Glances API... "
if curl -s http://localhost:61208/api/4/status > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
    # Test specific endpoints
    echo "  Testing endpoints:"
    echo -n "    - /api/4/pluginslist... "
    if curl -s http://localhost:61208/api/4/pluginslist | grep -q '\['; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
    fi
    echo -n "    - /api/4/cpu... "
    if curl -s http://localhost:61208/api/4/cpu | grep -q 'total'; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
    fi
    echo -n "    - /api/4/mem... "
    if curl -s http://localhost:61208/api/4/mem | grep -q 'total'; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
    fi
else
    echo -e "${RED}✗${NC}"
    echo "  Error: Cannot connect to Glances API"
fi

echo ""

# Test Open WebUI
echo -n "Testing Open WebUI... "
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "  Error: Cannot connect to Open WebUI"
fi

echo ""
echo "=========================================="
echo "   Access URLs"
echo "=========================================="
echo "Open WebUI:   http://localhost:3000"
echo "Glances Web:  http://localhost:61208"
echo "Glances API:  http://localhost:61208/api/4"
echo "Ollama API:   http://localhost:11434"
echo ""

# Check for models
echo "=========================================="
echo "   Ollama Models Status"
echo "=========================================="
if docker exec ollama ollama list > /dev/null 2>&1; then
    MODEL_COUNT=$(docker exec ollama ollama list | tail -n +2 | wc -l)
    if [ "$MODEL_COUNT" -eq 0 ]; then
        echo -e "${YELLOW}No models installed yet.${NC}"
        echo ""
        echo "To install a model, run:"
        echo "  docker exec -it ollama ollama pull llama3.2"
    else
        echo -e "${GREEN}Installed models:${NC}"
        docker exec ollama ollama list
    fi
else
    echo -e "${RED}Cannot check models${NC}"
fi

echo ""
echo "=========================================="
echo "   System Resources"
echo "=========================================="
echo "Container resource usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

echo ""
echo "=========================================="
echo "   Next Steps"
echo "=========================================="
echo "1. Open WebUI at http://localhost:3000"
echo "2. Create an account (stored locally)"
echo "3. If no models, install one:"
echo "   docker exec -it ollama ollama pull llama3.2"
echo "4. Test the Glances API in chat:"
echo "   - 'What is the current CPU usage?'"
echo "   - 'Show me memory statistics'"
echo ""
