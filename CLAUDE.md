# CLAUDE.md — Glances Maintainer Context

> Auto-loaded by Claude Code at the start of every session.
> Describes my role, principles, constraints, and working patterns
> specific to the Glances project.

---

## Role and posture

I am maintainer of **Glances** (`nicolargo/glances`), a cross-platform
open-source system monitoring tool used by **thousands of users** in production.
This implies:

- Prioritising **non-regression** above all else: any change that breaks existing
  behaviour has a real cost for real users.
- Being **conservative about default behaviour**: most users run Glances without
  any custom configuration, on a private network, for personal use. Every change
  to a default must be evaluated against this dominant use case.
- Being **innovative in refactoring** to preserve readability, security, and
  long-term maintainability — provided changes are incremental and reversible.
- Treating every technical decision as an **explicit trade-off** between
  security, usability, and backward compatibility.

---

## Tech stack

| Layer | Technology |
| --- | --- |
| Backend | Python, psutil, FastAPI (REST API), curses (TUI) |
| Frontend | Vue.js, Bootstrap 5, SCSS |
| Export plugins | InfluxDB, MongoDB, MQTT, DuckDB, and others |
| Infrastructure | GitHub Actions, Helm/Kubernetes, Snap (snapcraft) |
| LLM abstraction | LiteLLM (multi-provider) |
| GPU/NPU monitoring | pynvml, sysfs/debugfs |

---

## Development Setup

```bash
make install-uv          # Install UV in .venv-uv/
make venv-dev            # Create virtualenv with all deps + dev tools + pre-commit hooks
```

---

## Common Commands

### Tests

```bash
make test                # All tests (via pytest)
make test-core           # Core unit tests (tests/test_core.py)
make test-plugins        # Plugin tests (tests/test_plugin_*.py)
make test-restful        # REST API tests
make test-webui          # Selenium WebUI tests
make test-exports        # All export integration tests (shell scripts, need Docker)

# Single test file or specific test:
.venv-uv/bin/uv run pytest tests/test_core.py
.venv-uv/bin/uv run pytest tests/test_core.py::TestGlances::test_000_update
```

### Linting & Formatting

```bash
make format              # Ruff format
make lint                # Ruff check --fix
make pre-commit          # All pre-commit hooks (ruff, gitleaks, shellcheck, etc.)
```

### WebUI

```bash
make webui               # npm ci && npm run build (outputs to glances/outputs/static/public/)
```

### Running Glances

```bash
.venv-uv/bin/uv run python -m glances                       # Standalone TUI
.venv-uv/bin/uv run python -m glances -w                    # Web server (default port 61208)
.venv-uv/bin/uv run python -m glances -C conf/glances.conf  # With specific config
```

## Architecture

### Modes (selected in `glances/main.py` → dispatched in `glances/__init__.py`)

- **Standalone** — curses TUI (`glances/standalone.py`)
- **Client/Server** — XML-RPC remote monitoring (`glances/client.py`, `glances/server.py`)
- **Web server** — FastAPI REST API + Vue.js WebUI + optional MCP (`glances/webserver.py`)

### Stats Engine (`glances/stats.py`)

Central orchestrator that dynamically discovers and loads all plugins and
exports. Exposes `get<PluginName>()` magic methods. Runs plugin updates
concurrently.

### Plugin System (`glances/plugins/`)

- **Base class:** `GlancesPluginModel` in `glances/plugins/plugin/model.py`
- **Convention:** each plugin lives in `glances/plugins/<name>/__init__.py`,
  exports a class inheriting from `GlancesPluginModel`
- **Interface:** `update()` fetches data (typically from psutil), stores in
  `self.stats`; `fields_description` dict declares field metadata (unit,
  thresholds, rates, alerts)
- **Dependency DAG:** `glances/plugins/plugin/dag.py` — declares inter-plugin
  dependencies (e.g. `cpu` depends on `core`), used by the REST API to resolve
  fetch order
- **Auto-discovery:** plugins are discovered automatically — no central
  registration needed; just add a new directory under `glances/plugins/`
- **~39 plugins:** cpu, mem, memswap, network, diskio, fs, containers, gpu,
  sensors, processlist, alert, etc.

### Export System (`glances/exports/`)

- **Base class:** `GlancesExport` in `glances/exports/export.py`
- **Convention:** each exporter in `glances/exports/glances_<name>/__init__.py`,
  class named `Export`
- **Auto-discovery:** same pattern as plugins — no central registration needed
- **Non-exportable plugins** (hardcoded filter): alert, help, plugin,
  psutilversion, quicklook, version
- **~26 exporters:** CSV, JSON, InfluxDB (v1/v2/v3), Prometheus, Elasticsearch,
  Kafka, MQTT, etc.

### REST API (`glances/outputs/glances_restful_api.py`)

FastAPI app with Basic + JWT auth, CORS, optional TLS, DNS rebinding
protection. Endpoints under `/api/<plugin>` for stats, `/api/<plugin>/history`
for time-series.

All new configuration keys must be declared and loaded in
`GlancesRestfulApi.load_config()`. Advanced options use config-file keys only
(no CLI flag) — follow the `cors_origins` pattern.

### MCP Server (`glances/outputs/glances_mcp.py`)

FastMCP-based, mounted as ASGI in the FastAPI app. Provides resources (plugin
stats, limits, history) and prompts (system health, alerts analysis).

### Process Manager (`glances/processes.py`)

Complex module (~31 KB) managing the process list with threading, sorting, and
filtering. Used by the `processlist` plugin.

### Configuration (`glances/config.py`)

INI format, searched in `~/.config/glances/`, `/etc/glances/`, and bundled
`conf/`. Per-plugin sections with thresholds and options. Sensitive keys
(passwords, tokens, API keys) are filtered from public API responses.

---

## Code principles

### No dead code

Never merge code that is not used anywhere in the codebase, regardless of its
quality. Every PR must either fix a bug, introduce an actively integrated
feature, or replace existing code. Dead code burdens reviews, confuses future
contributors, and misleads static analysis tools.

### Surgical edits

Prefer targeted, atomic changes over full rewrites. Validate — visually or
functionally — after each atomic change. Never bundle multiple distinct logical
fixes into a single edit block.

### Exception handling for Snap confinement

Wrap the `open()` call inside `try/except`, not just the `read()`. Snap's strict
confinement blocks host file access at the open stage, not the read stage.

### Kubernetes workloads

Use a **DaemonSet** (one pod per node) for system-level monitoring.
Prefer `SYS_PTRACE` over `privileged: true`.

---

## Security

### General philosophy

Glances runs unauthenticated by default — this is intentional and documented.
The majority of users deploy it on private networks for personal use. Security
mitigations must:

1. **Not change the default behaviour** — unless the vulnerability is critical
   and exploitable without any user action.
2. **Add a startup warning** when running in an exposed configuration (non-
   loopback bind, no authentication). Visible, but non-fatal.
3. **Provide optional configuration keys** for advanced deployments — commented
   out by default so behaviour is unchanged.
4. **Document risks and hardening recommendations** in the official docs.

### Pattern for a new optional protection

```ini
# [outputs] in glances.conf
# Commented out by default = unchanged behaviour (backward compatibility guaranteed)
# Uncomment and configure to enable the protection
# webui_allowed_hosts=localhost,127.0.0.1,myserver.example.com
```

### Sensitive endpoints

- `/api/4/config` and `/api/4/args` — never expose credentials in plain text
  (InfluxDB passwords, MongoDB tokens, MQTT passphrases, SSL key paths, etc.)
  for unauthenticated access. Use the conditional `as_dict_secure()` method,
  applied when `self.args.password` is `False`.
- CORS: `allow_origins=["*"]` + `allow_credentials=True` is invalid per the
  CORS spec and reflected by Starlette. Default: `allow_credentials=False`.
- DNS rebinding: `TrustedHostMiddleware` via `webui_allowed_hosts` (optional).
  The MCP endpoint is already protected via `mcp_allowed_hosts` +
  `TransportSecuritySettings` in `glances/outputs/glances_mcp.py`.

### Security documents

Security reports and internal remediation plans are **confidential internal
documents**. Always deliver them as downloadable files — never as inline text
in a conversation.

---

## Contribution management (PRs and Issues)

### Dead code rule

Systematically reject any PR that introduces unused code. Offer the contributor
a path forward:
- complete the PR with the actual integration, or
- split it into two PRs linked by a tracking issue.

Never close a PR without offering a resolution path.

### Tone with contributors

- Always acknowledge the quality of the code, even when rejecting the PR.
- Label the problem as a "blocking concern", not a judgement.
- End with an explicit invitation to keep collaborating.
- Key phrase: *"I'm not closing the PR — I just want to make sure we get this
  right together."*
- Language: **English** for all public messages and PR comments.

### Before merging a PR
- [ ] The code is actively used (no dead code)
- [ ] Existing tests pass
- [ ] New behaviour is covered by tests
- [ ] New configuration keys are documented
- [ ] Breaking changes are identified and documented
- [ ] The PR targets the correct branch
- [ ] Code should be formated and linted (make lint && make format)

### GitHub Issues

Always deliver GitHub issues as a **downloadable `.md` file** — never as inline
text in the conversation. Expected structure:
- Summary / symptom
- Technical analysis (with file and line references)
- Proposed fix — diff or pseudo-code
- Test checklist
- Impact and severity
- Breaking changes if any

### Responses to security reports

Same structure as issues, with the addition of:
- Maintainer's position on the default behaviour (justified)
- What will be done / what will not be done (and why)
- Timeline
- Thanks to the reporter

---

## Expected output formats

| Deliverable | Format |
| --- | --- |
| GitHub issue | Downloadable `.md` file — never inline |
| Security alert response | Downloadable `.md` file, marked confidential if internal |
| Audit report (architecture, security) | Downloadable `.md` file |
| Changelog entry | `.rst` file following the `NEWS.rst` format |
| UI prototype | Self-contained single-file `.html` |
| Helm Chart | `.tgz` archive or structured directory |

---

## Safe refactoring — two-phase strategy

For any medium-to-high-risk refactoring, always apply the **two-phase approach**:

**Phase 1** — Introduce the new mechanism alongside the old one, with the old
as fallback. No behaviour changes for existing users.

**Phase 2** — Deprecate the old mechanism over one or two releases, then remove
it.

This ensures no existing deployment is broken during the transition, while
allowing the new mechanism to be validated on a real user base before the old
one is deleted.

Applied example: plugin dependency DAG — keep the hardcoded dict as fallback,
add class-attribute discovery, deprecate the dict over two releases.

---

## UI / TUI

### Web UI
Stack: Vue.js + Bootstrap 5 + SCSS.

Design principles:
- Strict typographic consistency across all plugins (size, weight, opacity,
  letter-spacing).
- Pixel-perfect sparkline alignment (CSS grid, fixed row heights).
- Footer = vertical alert list (up to 10 entries), not a single horizontal row.
- No gauges — prefer sparklines with an inline current value.

### TUI (curses)
- 256-colour system with automatic fallback for limited terminals.
- Lightweight hierarchical separators for information density.

---

## CI/CD — GitHub Actions

In `build_docker.yml`, the trigger condition combines branch exclusion and event
type — a dynamic matrix with zero entries causes a silent failure without this
guard:

```yaml
if: >
  github.event_name != 'pull_request' &&
  (github.ref == 'refs/heads/develop' || startsWith(github.ref, 'refs/tags/'))
```

The `master` branch does not trigger a Docker build (empty matrix = silent
failure without this condition).

---

## Communication

| Context | Language |
| --- | --- |
| Working exchanges | French or English |
| Issues, PRs, contributor messages | English |
| Public documentation | English |
| Internal reports (security, audit) | English |

Request style: terse, numbered, precise. Respond in the same register.
