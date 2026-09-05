# CLAUDE.md — Glances Maintainer Context

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```md
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## Additionnal context

### Tech stack

| Layer | Technology |
| --- | --- |
| Backend | Python, psutil, FastAPI (REST API), curses (TUI) |
| Frontend | Vue.js, Bootstrap 5, SCSS |
| Export plugins | InfluxDB, MongoDB, MQTT, DuckDB, and others |
| Infrastructure | GitHub Actions, Helm/Kubernetes, Snap (snapcraft) |
| LLM abstraction | LiteLLM (multi-provider) |
| GPU/NPU monitoring | pynvml, sysfs/debugfs |

### Code principles

#### Exception handling for Snap confinement

Wrap the `open()` call inside `try/except`, not just the `read()`. Snap's strict
confinement blocks host file access at the open stage, not the read stage.

### Security

Glances runs unauthenticated by default — this is intentional and documented.
Most users deploy on private networks for personal use. See global CLAUDE.md
for the general OSS security philosophy (4 rules).

#### Sensitive endpoints

- `/api/4/config` and `/api/4/args` — never expose credentials in plain text
  (InfluxDB passwords, MongoDB tokens, MQTT passphrases, SSL key paths, etc.)
  for unauthenticated access. Use the conditional `as_dict_secure()` method,
  applied when `self.args.password` is `False`.
- CORS: `allow_origins=["*"]` + `allow_credentials=True` is invalid per the
  CORS spec and reflected by Starlette. Default: `allow_credentials=False`.
- DNS rebinding: `TrustedHostMiddleware` via `webui_allowed_hosts` (optional).
  The MCP endpoint is already protected via `mcp_allowed_hosts` +
  `TransportSecuritySettings` in `glances/outputs/glances_mcp.py`.

### Contribution management

#### Before merging a PR

- [ ] The code is actively used (no dead code)
- [ ] Existing tests pass
- [ ] New behaviour is covered by tests
- [ ] New configuration keys are documented
- [ ] Breaking changes are identified and documented
- [ ] The PR targets the correct branch
- [ ] Code should be formated and linted (make lint && make format)

#### Glances-specific output formats

| Deliverable | Format |
| --- | --- |
| Changelog entry | `.rst` file following the `NEWS.rst` format |
| Helm Chart | `.tgz` archive or structured directory |

### UI / TUI

#### Web UI

Stack: Vue.js + Bootstrap 5 + SCSS.

Design principles:

- Strict typographic consistency across all plugins (size, weight, opacity,
  letter-spacing).
- Pixel-perfect sparkline alignment (CSS grid, fixed row heights).
- Footer = vertical alert list (up to 10 entries), not a single horizontal row.
- No gauges — prefer sparklines with an inline current value.

#### TUI (curses)

- 256-colour system with automatic fallback for limited terminals.
- Lightweight hierarchical separators for information density.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
