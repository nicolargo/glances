#!/bin/bash
# Installation and configuration script for Glances MCP Server

set -e

echo "🚀 Glances MCP Server Installation"
echo "======================================"

# Colors for display
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to display messages
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check Python
info "Checking Python..."
if ! command -v python3 &> /dev/null; then
    error "Python 3 is not installed. Please install it first."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
info "Python version: $PYTHON_VERSION"

# Create virtual environment
info "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    info "Virtual environment created"
else
    warn "Virtual environment already exists"
fi

# Install dependencies
info "Installing dependencies..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# Check if Glances is installed
info "Checking Glances..."
if ! command -v glances &> /dev/null; then
    warn "Glances is not installed globally"
    info "Installing Glances in virtual environment..."
    ./venv/bin/pip install glances
else
    info "Glances is already installed"
fi

# Start Glances in server mode
info "Checking Glances server..."
if ! curl -s http://localhost:61208/api/4/status > /dev/null 2>&1; then
    warn "Glances is not running"
    read -p "Do you want to start Glances now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        info "Starting Glances..."
        ./venv/bin/glances -w --disable-webui --quiet &
        GLANCES_PID=$!
        sleep 2

        if curl -s http://localhost:61208/api/4/status > /dev/null 2>&1; then
            info "Glances started successfully (PID: $GLANCES_PID)"
            echo $GLANCES_PID > glances.pid
        else
            error "Failed to start Glances"
            exit 1
        fi
    fi
else
    info "Glances is already running"
fi

# Determine absolute path of MCP script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MCP_SCRIPT="$SCRIPT_DIR/glances_mcp.py"

# Determine Claude Desktop configuration file location
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    CONFIG_DIR="$HOME/Library/Application Support/Claude"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    CONFIG_DIR="$HOME/.config/Claude"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    CONFIG_DIR="$APPDATA/Claude"
else
    warn "Unrecognized operating system"
    CONFIG_DIR=""
fi

# Claude Desktop configuration
if [ -n "$CONFIG_DIR" ]; then
    info "Configuring Claude Desktop..."
    CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"

    if [ ! -f "$CONFIG_FILE" ]; then
        warn "Claude Desktop configuration file not found"
        info "Creating configuration file..."
        mkdir -p "$CONFIG_DIR"
        cat > "$CONFIG_FILE" << EOF
{
  "mcpServers": {
    "glances": {
      "command": "python",
      "args": ["$MCP_SCRIPT"],
      "env": {
        "GLANCES_URL": "http://localhost:61208"
      }
    }
  }
}
EOF
        info "Configuration created: $CONFIG_FILE"
    else
        warn "Claude Desktop configuration file already exists"
        info "Manually add the following configuration:"
        echo ""
        cat << EOF
{
  "mcpServers": {
    "glances": {
      "command": "python",
      "args": ["$MCP_SCRIPT"],
      "env": {
        "GLANCES_URL": "http://localhost:61208"
      }
    }
  }
}
EOF
        echo ""
    fi
fi

# Test MCP server
info "Testing MCP server..."
python3 "$MCP_SCRIPT" --help > /dev/null 2>&1 || true

echo ""
echo "======================================"
info "✅ Installation completed successfully!"
echo "======================================"
echo ""
echo "📋 Next steps:"
echo ""
echo "1. If not already done, start Glances:"
echo "   glances -w"
echo ""
echo "2. Restart Claude Desktop to load the MCP server"
echo ""
echo "3. In Claude, you can now use commands like:"
echo "   - 'What is the current CPU usage?'"
echo "   - 'Show me the most resource-intensive processes'"
echo "   - 'Analyze my system state'"
echo ""
echo "📚 Check README.md for more usage examples"
echo ""

# Create startup script
cat > start_glances.sh << 'EOF'
#!/bin/bash
# Glances startup script

echo "🚀 Starting Glances..."

# Check if Glances is already running
if curl -s http://localhost:61208/api/4/status > /dev/null 2>&1; then
    echo "✅ Glances is already running"
    exit 0
fi

# Start Glances
glances -w --disable-webui --quiet &
GLANCES_PID=$!

# Wait for Glances to be ready
sleep 2

# Verify
if curl -s http://localhost:61208/api/4/status > /dev/null 2>&1; then
    echo "✅ Glances started successfully (PID: $GLANCES_PID)"
    echo $GLANCES_PID > glances.pid
else
    echo "❌ Failed to start Glances"
    exit 1
fi
EOF

chmod +x start_glances.sh
info "Startup script created: start_glances.sh"

# Create shutdown script
cat > stop_glances.sh << 'EOF'
#!/bin/bash
# Glances shutdown script

echo "🛑 Stopping Glances..."

if [ -f glances.pid ]; then
    PID=$(cat glances.pid)
    if kill $PID 2>/dev/null; then
        echo "✅ Glances stopped (PID: $PID)"
        rm glances.pid
    else
        echo "⚠️  Process not found"
        rm glances.pid
    fi
else
    echo "⚠️  PID file not found"
    echo "Attempting to stop via pkill..."
    pkill -f "glances -w"
fi
EOF

chmod +x stop_glances.sh
info "Shutdown script created: stop_glances.sh"

echo ""
info "🎉 Complete setup!"
