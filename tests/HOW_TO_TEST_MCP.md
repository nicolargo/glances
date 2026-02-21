# How to test the Glances MCP server

This guide covers both the automated test suite (`tests/test_mcp.py`) and
manual verification of the MCP server that is now built into Glances.

---

## Prerequisites

Install Glances with the `mcp` and `web` extras:

```bash
pip install 'glances[web,mcp]'
```

Or, inside the development virtual environment:

```bash
pip install -e '.[web,mcp]'
```

---

## Automated test suite

```bash
# From the repository root
python -m pytest tests/test_mcp.py -v

# Or with the project venv
.venv/bin/python -m pytest tests/test_mcp.py -v
```

The suite automatically:
1. Starts a Glances web server with `--enable-mcp` on port **61235**
2. Runs smoke tests (HTTP-level) and full MCP-client tests for every resource
   and prompt
3. Shuts the server down

> Tests are skipped automatically when the `mcp` package is not installed.

---

## Manual testing

### 1. Start Glances with MCP enabled

```bash
glances -w --enable-mcp
```

| Endpoint         | URL                                      |
|------------------|------------------------------------------|
| SSE transport    | `http://localhost:61208/mcp/sse`         |
| POST messages    | `http://localhost:61208/mcp/messages/`   |

### 2. Verify the SSE endpoint with curl

```bash
curl -N http://localhost:61208/mcp/sse
```

You should see a continuous `text/event-stream` response with an `endpoint`
event pointing to the messages URL.

### 3. Explore resources and prompts with the Python client

```python
import asyncio, json
from mcp.client.sse import sse_client
from mcp import ClientSession
from pydantic import AnyUrl

MCP_SSE = "http://localhost:61208/mcp/sse"

async def demo():
    async with sse_client(MCP_SSE) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List static resources
            res = await session.list_resources()
            print("Resources:", [str(r.uri) for r in res.resources])

            # List resource templates
            tmpl = await session.list_resource_templates()
            print("Templates:", [t.uriTemplate for t in tmpl.resourceTemplates])

            # Read all plugin names
            plugins = await session.read_resource(AnyUrl("glances://plugins"))
            print("Plugins:", json.loads(plugins.contents[0].text)[:5], "…")

            # Read CPU stats
            cpu = await session.read_resource(AnyUrl("glances://stats/cpu"))
            print("CPU:", json.loads(cpu.contents[0].text))

            # Read CPU alert thresholds
            limits = await session.read_resource(AnyUrl("glances://limits/cpu"))
            print("CPU limits:", json.loads(limits.contents[0].text))

            # List prompts
            prompts = await session.list_prompts()
            print("Prompts:", [p.name for p in prompts.prompts])

            # Run system health summary prompt
            health = await session.get_prompt("system_health_summary")
            print("Health prompt (first 200 chars):", health.messages[0].content.text[:200])

            # Run alert analysis with a severity filter
            alerts = await session.get_prompt("alert_analysis", arguments={"level": "critical"})
            print("Alerts:", alerts.messages[0].content.text[:200])

            # Top-5 processes report
            procs = await session.get_prompt("top_processes_report", arguments={"nb": "5"})
            print("Processes:", procs.messages[0].content.text[:200])

asyncio.run(demo())
```

### 4. Connect Claude CLI (Linux)

Add the Glances MCP server with:

```bash
claude mcp add --transport sse glances http://localhost:61208/mcp/sse
```

Then verify that the server is recognised:

```bash
claude mcp list
# glances: http://localhost:61208/mcp/sse
```

Once configured, start a Claude CLI session and try:

- *"Is my system healthy ?"

It will return:

```markdown
Here's your system health summary:

  CPU — Good

  - 6% total usage, load average 0.88 (on 16 cores) — very light

  Memory — Warning

  - RAM: 76.8% used (12.6 GB / 16.4 GB)
  - Swap: 95.9% used (3.9 GB / 4.0 GB) — critical, nearly exhausted

  Disk — Good

  - Root (/): 40.2% used, 530 GB free

  Temperatures — Good

  ┌────────────┬──────┐
  │   Sensor   │ Temp │
  ├────────────┼──────┤
  │ CPU        │ 54°C │
  ├────────────┼──────┤
  │ HDD        │ 40°C │
  ├────────────┼──────┤
  │ NVMe       │ 36°C │
  ├────────────┼──────┤
  │ RAM        │ 41°C │
  ├────────────┼──────┤
  │ GPU (i915) │ 49°C │
  └────────────┴──────┘

  - CPU Fan: 2992 RPM, Video Fan: 2822 RPM — both spinning normally

  Battery — Good

  - 96%, currently charging

  Alerts — None active

  ---
  Verdict: mostly healthy, but swap is nearly full. Your system is swapping heavily (12.7 GB
  swapped out), which suggests RAM pressure. You may want to check for memory-hungry processes
   and consider killing or restarting any you don't need.
```

- *"What is the current CPU usage on my machine ?"*
- *"Are there any active alerts ?"*
- *"Show me the top 5 processes by CPU."*
- *"How is my disk space looking ?"*

> If Glances requires authentication, add a Bearer token or Basic Auth header
> via the `headers` key in `settings.json` (see the authentication section
> below).

### 5. Connect Claude Desktop

Add to `claude_desktop_config.json`
(`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS,
`%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "glances": {
      "url": "http://localhost:61208/mcp/sse"
    }
  }
}
```

Restart Claude Desktop, then try:

- *"What is the current CPU usage on my machine?"*
- *"Are there any active alerts?"*
- *"Show me the top 5 processes by CPU."*
- *"How is my disk space looking?"*

---

## Testing authentication

Start Glances with a password:

```bash
glances -w --enable-mcp --username
# Follow the prompts to create a username/password pair
```

A request without credentials should return **HTTP 401**:

```bash
curl -I http://localhost:61208/mcp/sse
# HTTP/1.1 401 Unauthorized
```

Connect with Basic Auth:

```python
import base64
creds = base64.b64encode(b"myuser:mypassword").decode()
headers = {"Authorization": f"Basic {creds}"}

async with sse_client(MCP_SSE, headers=headers) as (read, write):
    ...
```

Or with a JWT Bearer token (see the RESTful API docs for how to obtain one):

```python
headers = {"Authorization": "Bearer <your_jwt_token>"}
async with sse_client(MCP_SSE, headers=headers) as (read, write):
    ...
```

The unit tests for the auth middleware live in `tests/test_mcp.py`
(`TestGlancesMcpAuthMiddleware`) and do not require a running server.
