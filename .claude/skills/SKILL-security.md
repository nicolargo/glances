# Skill: Glances v5 — Security model and CVE checklist

Glances is a wide-audience OSS project used in production. Security work
follows a strict OSS philosophy — protections are added without breaking
the experience of users with zero configuration, who are the majority.

## The four OSS rules (apply to every security PR)

1. **Do not change default behaviour** unless the vulnerability is
   critical and exploitable without user action.
2. **Add a startup WARNING** when running in the exposed/insecure mode —
   visible but never fatal.
3. **Offer optional config keys** for advanced deployments — commented
   out by default so the default behaviour is unchanged.
4. **Document the risk and the hardening recommendation** in the official
   docs.

Pattern for a new optional protection:

```ini
# Commented = behaviour unchanged (backward compatibility guaranteed).
# Uncomment and configure to enable the protection.
# my_protection = value, value2
```

## Glances-specific baseline

- **Glances runs unauthenticated by default** — intentional and
  documented. Most users deploy on private networks for personal use.
- The four rules above apply to every CVE fix and every new hardening
  feature, without exception.

## Authentication

| Mechanism | Status |
|---|---|
| Bearer token (v4.5.0+) | Preserved in v5 |
| Basic Auth (PBKDF2) | Preserved in v5 |
| Unauthenticated mode | Default — startup `WARNING` logged (CVE-2026-32596) |

## CVE checklist (architecture §8)

Every published CVE listed below is **non-negotiable** in v5.0 — the v5
release ships from a hardened baseline that covers every advisory ever
issued against Glances v4. Reference table in
`docs/architecture/glances-v5-architecture-decisions.md` §8 is the source
of truth; this skill mirrors it.

**v5 status** values:
- `Carry forward` — same fix mechanism as v4, ported into the v5 module structure
- `Resolved by architecture` — vulnerability does not exist in v5 because the affected component or feature was removed
- `New v5 mitigation` — additional v5-specific work required beyond what v4 shipped

| CVE | Severity | Mitigation in v5 | v5 status |
|---|---|---|---|
| **CVE-2026-30928** | high | Redact secrets from `/api/5/config` for unauthenticated callers via `GlancesConfigV5.as_dict_secure()`. Same mechanism as CVE-2026-32609. | Carry forward (Phase 0.2 ✅) |
| **CVE-2026-30930** | high | Parameterized SQL in TimescaleDB export. Process names, mount points, interface names, container names — every string drawn from monitored data — must be parameterized, never f-string-interpolated. | Carry forward (Phase 3) |
| **CVE-2026-32596** | high | Startup `WARNING` log when REST API runs unauthenticated. Default behaviour unchanged. | Carry forward (Phase 1) |
| **CVE-2026-32608** | high | Shell-escape process names in `[action]` command templates **before** Mustache substitution. Implemented in the `shell` action under `glances/actions_v5/shell/`, not in `GlancesActionBase`. | Carry forward (Phase 1 — concrete `shell` action) |
| **CVE-2026-32609** | high | Redact secret-like values from `/api/5/args` (and any other unauthenticated endpoint) via `GlancesConfigV5.as_dict_secure()`. | Carry forward (Phase 0.2 ✅) |
| **CVE-2026-32610** | high | No wildcard `Access-Control-Allow-Origin`. Allowed origins via `cors_origins` in `[outputs]`. `allow_credentials=False` is the FastAPI default. | Carry forward (Phase 1) |
| **CVE-2026-32611** | high | Parameterized DDL in DuckDB export. Plugin/metric names sanitized, never string-interpolated. | Carry forward (Phase 3 — DuckDB) |
| **CVE-2026-32632** | medium | Host validation against DNS rebinding. `webui_allowed_hosts` config key. Startup warning when unset in non-loopback mode. | Carry forward (Phase 1) |
| **CVE-2026-32633** | critical | `/api/5/serverslist` must not return credential-bearing `uri` fields. Strip `password` and `uri` before serialization. | Carry forward (Phase 3) |
| **CVE-2026-32634** | high | Browser autodiscovery must not forward configured credentials to discovered servers. | Carry forward (Phase 3) |
| **CVE-2026-33533** | high | XML-RPC server removed in v5 (architecture §1.1). The vulnerable code path no longer exists. | Resolved by architecture |
| **CVE-2026-33641** | high | Backtick command substitution in configuration values is **not** ported to `GlancesConfigV5` — the `re_pattern = r'(\`.+?\`)'` + `system_exec()` paths from v4 `glances/config.py` are deliberately absent. Document as a breaking change in `NEWS.rst` at v5.0.0. | Resolved by architecture |
| **CVE-2026-34839** | high | REST API CORS hardening — same mechanism as CVE-2026-32610 applied to `/api/5/*`. `cors_origins` enforced; wildcard rejected when credentials are allowed. | Carry forward (Phase 1) |
| **CVE-2026-35587** | high | SSRF in IP plugin via `public_api`. v5 plugin migration must validate the URL scheme (allow `http`/`https` only), reject loopback / link-local / RFC1918 / cloud metadata IPs unless explicitly opted in via `public_api_allow_internal=true`, and **never** send `public_username`/`public_password` to a hostname not on an allowlist. | New v5 mitigation (Phase 2 — `ip` plugin migration) |
| **CVE-2026-35588** | medium | Parameterized CQL in Cassandra export. `keyspace`, `table`, `replication_factor` validated against an allowlist regex (`^[A-Za-z][A-Za-z0-9_]*$`) before being interpolated into DDL. Same family as CVE-2026-32611 / CVE-2026-30930. | Carry forward (Phase 3 — Cassandra) |

### Watching — unpublished advisories

| GHSA | Severity | State | v5 plan |
|---|---|---|---|
| GHSA-mcm7-fmh3-v6v3 | medium | draft | Curses terminal escape injection + memory exhaustion via process names rendered in alerts. v5 alerts plugin (Phase 2) must sanitize control sequences and cap rendered string size. Tracked separately until the advisory is published. |

### Closed — fixed in v4, no v5 action required

The following advisories were fixed in v4 before the v5 effort began. The
fixes are present in the v4 codebase that `develop-v5` inherits via the
weekly merge, and no additional v5-specific work is needed.

- GHSA-93gr-c454-3xw7 — Passwords exposed in plain text
- GHSA-w4m6-4mpc-gq25 — BasicAuth Bypass
- GHSA-f533-jmqq-4www — Public IP visible on documentation screenshot

## Secret redaction — `as_dict_secure()`

Used by the unauthenticated REST API endpoints (`/api/5/config`,
`/api/5/args`) — CVE-2026-32609. Already implemented in
`glances/config_v5.py` (Phase 0.2). See `SKILL-config.md` for the full
list of redacted key fragments and the conditional access pattern.

The same redaction discipline applies **anywhere** the API may be
consumed unauthenticated — not just `/api/5/config`. When adding a new
endpoint, ask: "could this leak a credential to an anonymous caller?".

## CORS

Default values for v5:

```ini
[outputs]
cors_origins =                  # empty list — no cross-origin allowed
allow_credentials = false       # mandatory — wildcard + credentials is invalid per CORS spec
```

Wildcard `*` is **forbidden** when `allow_credentials = true` (Starlette
reflects this — the FastAPI middleware rejects the combination).

## DNS rebinding (`webui_allowed_hosts`)

```ini
[outputs]
# Comma-separated list. Empty = accept any Host header (loopback only).
# webui_allowed_hosts = glances.example.com, 192.0.2.10
```

Implemented via Starlette's `TrustedHostMiddleware` in the FastAPI
application. The MCP endpoint already enforces equivalent protection via
`mcp_allowed_hosts` + `TransportSecuritySettings` in
`glances/outputs/glances_mcp.py` (v4 codebase, kept untouched in v5).

## Sensitive endpoints — checklist before merging an API change

For every new or modified endpoint, ask:

- [ ] Does it expose any value that could be a credential? → use `as_dict_secure()` for unauthenticated access.
- [ ] Does it accept user-supplied input that flows into a SQL or CQL query? → parameterize, never interpolate (CVE-2026-32611 / CVE-2026-30930 / CVE-2026-35588 pattern).
- [ ] Does it rely on the Host header? → `webui_allowed_hosts` must guard it.
- [ ] Does it leak the configuration of upstream servers (URIs with credentials)? → strip them (CVE-2026-32633 pattern).

## Sensitive plugin configuration — checklist when migrating a plugin

For every plugin that reads a URL, hostname, or remote endpoint from
configuration, ask:

- [ ] Does the plugin accept a URL / endpoint from `glances.conf` that becomes the destination of an HTTP request? → validate scheme (`http`/`https` only), reject loopback / link-local / RFC1918 / cloud-metadata IPs unless an explicit `*_allow_internal=true` opt-in is set (CVE-2026-35587 pattern).
- [ ] Does the plugin send credentials (username / password / token) alongside that request? → never forward credentials to a hostname not on an allowlist; this is the rule that makes the SSRF actually exfiltrate data.
- [ ] Does the plugin shell out, eval, or otherwise interpret a config value? → forbidden by design in v5. The v4 backtick command substitution (CVE-2026-33641) was deliberately not ported.

## Responding to a security report

Structure for the public response (architecture / global CLAUDE.md):

1. Acknowledgement of the report and confirmation of the bug
2. Impact analysis per user profile (default vs. configured)
3. Maintainer's position on the default behaviour (justified)
4. What will be done / what will not be done (and why)
5. Diff or pseudo-code of the proposed fix
6. Timeline
7. Thanks to the reporter

Internal security reports and remediation plans are **confidential
documents** — produced as downloadable `.md` files, never inline in a
conversation.

## Reproduction of v4 fixes

> "All v4.x security fixes are reproduced in v5.0. v5 starts from the
> hardened baseline." (architecture §8)

Concretely: when a CVE is patched in `develop` (v4) post-Phase-0, it
**must** also land in `develop-v5`. The weekly automated merge `develop
→ develop-v5` (CI) is the primary channel; conflicts are resolved
immediately, not accumulated. See `SKILL-ci-cd.md`.

## What's deferred

- **Concrete enforcement** of CORS / `webui_allowed_hosts` / unauthenticated WARNING (CVE-2026-32596, -32610, -32632, -34839) — Phase 1 (FastAPI app)
- **Shell escaping** for `[action]` (CVE-2026-32608) — Phase 1 (concrete `shell` action in `glances/actions_v5/shell/`)
- **IP plugin SSRF mitigation** (CVE-2026-35587) — Phase 2 (`ip` plugin migration). New v5 mitigation, not present in v4.
- **Curses escape sanitization in alerts** (GHSA-mcm7-fmh3-v6v3 — draft) — Phase 2 (alerts plugin / curses TUI)
- **DDL parameterization** in SQL/CQL exporters (CVE-2026-32611, -30930, -35588) — Phase 3 (DuckDB, TimescaleDB, Cassandra)
- **Browser autodiscovery hardening** (CVE-2026-32633, -32634) — Phase 3 (browser mode)
- **NEWS.rst entry** documenting backtick config substitution removal (CVE-2026-33641 → resolved by architecture, breaking change for users who rely on `` `cmd` `` in `glances.conf`) — at v5.0.0 release

## Module path

This skill is documentation-only. It points to:

```
glances/config_v5.py                  # as_dict_secure() (✅ Phase 0)
glances/outputs/glances_mcp.py        # MCP host protection (v4 — untouched)
docs/architecture/glances-v5-architecture-decisions.md  # §8 CVE table
```

The implementation of every Phase-1+ item lives in modules that **do not
exist yet**. This skill is the contract; the code follows.
