# CLAUDE.md — Glances Maintainer Context

> Auto-loaded by Claude Code at the start of every session.
> Glances-specific context. Global principles (role, refactoring strategy,
> contribution tone, communication, output formats) are in `~/.claude/CLAUDE.md`.

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

## Reference docs (use `@` to load on demand)

- **Commands & setup**: `@.claude/docs/commands.md`
- **Architecture**: `@.claude/docs/architecture.md`

---

## Code principles (Glances-specific)

### Exception handling for Snap confinement

Wrap the `open()` call inside `try/except`, not just the `read()`. Snap's strict
confinement blocks host file access at the open stage, not the read stage.

### Kubernetes workloads

Use a **DaemonSet** (one pod per node) for system-level monitoring.
Prefer `SYS_PTRACE` over `privileged: true`.

---

## Security (Glances-specific)

Glances runs unauthenticated by default — this is intentional and documented.
Most users deploy on private networks for personal use. See global CLAUDE.md
for the general OSS security philosophy (4 rules).

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

---

## Contribution management (Glances-specific)

### Before merging a PR
- [ ] The code is actively used (no dead code)
- [ ] Existing tests pass
- [ ] New behaviour is covered by tests
- [ ] New configuration keys are documented
- [ ] Breaking changes are identified and documented
- [ ] The PR targets the correct branch
- [ ] Code should be formated and linted (make lint && make format)

### Glances-specific output formats

| Deliverable | Format |
| --- | --- |
| Changelog entry | `.rst` file following the `NEWS.rst` format |
| Helm Chart | `.tgz` archive or structured directory |

### Safe refactoring — applied example

Plugin dependency DAG — keep the hardcoded dict as fallback, add class-attribute
discovery, deprecate the dict over two releases.

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

