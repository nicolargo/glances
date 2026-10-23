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

| Mechanism | Status | Module |
|---|---|---|
| Basic Auth (PBKDF2-SHA256) | Phase 1.5 ✅ | `glances/webserver.py` + `glances/security.py` |
| JWT Bearer (HS256, v4.5.0+) | Phase 1.5 ✅ (handler) / Phase 1.6 (`/api/5/token` route) | `glances.security.JWTHandler` |
| Unauthenticated mode | Default — startup `WARNING` logged (CVE-2026-32596) | `glances/webserver.py` |

### Config keys (`[outputs]`)

| Key | Default | Effect |
|---|---|---|
| `password` | unset | PBKDF2-SHA256 `salt$hex` hash. Setting it enables Basic + Bearer; unsetting → API open + WARNING (CVE-2026-32596). |
| `username` | `glances` | Basic-Auth username. |
| `jwt_secret_key` | random per process | HS256 signing key. Random default → tokens invalidate on every restart. Set in production. |
| `jwt_expire_minutes` | 60 | JWT lifetime. |

### Middleware order

`build_app()` registers, from inner to outer (Starlette runs them outer-first):

```
TrustedHostMiddleware    ← DNS rebinding (CVE-2026-32632)
    ↓
RateLimitMiddleware      ← per-address limits (glances/ratelimit.py)
    ↓
CORSMiddleware           ← Cross-origin policy (CVE-2026-32610 / 34839)
    ↓
AuthMiddleware           ← Basic / Bearer (CVE-2026-32596)
    ↓
GZipMiddleware           ← response compression
    ↓
route handler / probe
```

### Liveness / readiness probes

`GET /status` (v4-compat) and `GET /healthz` (k8s / Prometheus / Docker convention) — same payload, both **hard-coded as exempt from auth** via `UNAUTH_PATHS` in `glances/webserver.py`. Deliberately not configurable: a probe surface must be predictable.

### Hash format & v4 migration

v5 stored hashes are `salt$pbkdf2_hex` with PBKDF2-SHA256, 100 000 iterations, `dklen=128`. **Not byte-compatible** with v4 (which applies an extra `pbkdf2(plain, salt='')` pre-hash). Users migrating from v4 regenerate it with `glances --set-password` (`make set-password`); algorithmic strength is preserved.

### JWT bearer flow

1. Operator sets `[outputs] password=<pbkdf2>` (and optionally `jwt_secret_key`) in `glances.conf`.
2. Client `POST /api/5/token` with HTTP Basic auth (Phase 1.6) → receives `{"access_token": "...", "token_type": "bearer", "expires_in": <seconds>}`.
3. Subsequent calls use `Authorization: Bearer <jwt>` until expiry.

JWT Bearer is **only enabled when Basic Auth is configured** — otherwise there is no way to mint a token. Matches v4 behaviour.

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
- `Covered by a different v5 mechanism` — the bug class cannot occur in v5 because v5 uses a different technique than the v4 fix; a regression test locking the property in is mandatory

_Table below last synced 2026-10-23. Source of truth is architecture §8; the sync is a release-checklist item._

| CVE | Severity | Mitigation in v5 | v5 status |
|---|---|---|---|
| **CVE-2026-30928** | high | Redact secrets from `/api/5/config` for unauthenticated callers via `GlancesConfig.as_dict_secure()`. Same mechanism as CVE-2026-32609. | Carry forward (Phase 0.2 ✅) |
| **CVE-2026-30930** | high | Parameterized SQL in TimescaleDB export. Process names, mount points, interface names, container names — every string drawn from monitored data — must be parameterized, never f-string-interpolated. | Carry forward (Phase 3) |
| **CVE-2026-32596** | high | Startup `WARNING` log when REST API runs unauthenticated. Default behaviour unchanged. | Carry forward (Phase 1.5 ✅) |
| **CVE-2026-32608** | high | Shell-escape process names in `[action]` command templates **before** Mustache substitution. Implemented in the `shell` action under `glances/actions/shell/`, not in `GlancesActionBase`. | Carry forward (Phase 1.4 ✅ — concrete `shell` action) |
| **CVE-2026-32609** | high | Redact secret-like values from `/api/5/args` (and any other unauthenticated endpoint) via `GlancesConfig.as_dict_secure()`. | Carry forward (Phase 0.2 ✅) |
| **CVE-2026-32610** | high | No wildcard `Access-Control-Allow-Origin` with credentials. Allowed origins via `cors_origins` in `[outputs]`. `cors_allow_credentials=False` default; wildcard + credentials downgrades to no-credentials with WARNING. | Carry forward (Phase 1.5 ✅) |
| **CVE-2026-32611** | high | Parameterized DDL in DuckDB export. Plugin/metric names sanitized, never string-interpolated. | Carry forward (Phase 3 — DuckDB) |
| **CVE-2026-32632** | medium | Host validation against DNS rebinding. `webui_allowed_hosts` config key. Startup warning when unset in non-loopback mode. | Carry forward (Phase 1.5 ✅) |
| **CVE-2026-32633** | critical | `/api/5/serverslist` must not return credential-bearing `uri` fields. Strip `password` and `uri` before serialization. | Carry forward (Phase 3) |
| **CVE-2026-32634** | high | Browser autodiscovery must not forward configured credentials to discovered servers. | Carry forward (Phase 3) |
| **CVE-2026-33533** | high | XML-RPC server removed in v5 (architecture §1.1). The vulnerable code path no longer exists. | Resolved by architecture |
| **CVE-2026-33641** | high | Backtick command substitution in configuration values is **not** ported to `GlancesConfig` — the `re_pattern = r'(\`.+?\`)'` + `system_exec()` paths from v4 `glances/config.py` are deliberately absent. Document as a breaking change in `NEWS.rst` at v5.0.0. | Resolved by architecture |
| **CVE-2026-34839** | high | REST API CORS hardening — same mechanism as CVE-2026-32610 applied to `/api/5/*`. `cors_origins` enforced; wildcard + credentials downgrades to no-credentials. | Carry forward (Phase 1.5 ✅) |
| **CVE-2026-35587** | high | SSRF in IP plugin via `public_api`. v5 plugin migration must validate the URL scheme (allow `http`/`https` only), reject loopback / link-local / RFC1918 / cloud metadata IPs unless explicitly opted in via `public_api_allow_internal=true`, and **never** send `public_username`/`public_password` to a hostname not on an allowlist. | New v5 mitigation (Phase 2 — `ip` plugin migration) |
| **CVE-2026-35588** | medium | Parameterized CQL in Cassandra export. `keyspace`, `table`, `replication_factor` validated against an allowlist regex (`^[A-Za-z][A-Za-z0-9_]*$`) before being interpolated into DDL. Same family as CVE-2026-32611 / CVE-2026-30930. | Carry forward (Phase 3 — Cassandra) |
| **CVE-2026-68520** | high | `as_dict_secure()` value-level bypass. v5 `config.as_dict_secure()` scrubs URL userinfo (`scheme://user:pass@host`) in every string value via `_URL_CREDENTIALS_RE`, and redacts `username` / `user` / `login` key names (`user` / `login` via exact match so `user_careful` / `user_warning` thresholds stay visible). A future `/api/5/args` must reuse `_secure_value()`. | Carry forward (Phase 0.2, extended 2026-08-01 ✅) |
| **GHSA-73wf-9vmv-5pv9** | high | Incomplete fix of CVE-2026-32608 (nested list/dict values). v5 `ShellAction` pre-quotes every value with `shlex.quote(str(value))`, so a stringified list is one token — v4's operator-stripping sanitizer is not used. | Covered by a different v5 mechanism |
| **GHSA-qcpp-8x79-hhp3** | high | Incomplete fix of CVE-2026-32608 (operator reconstruction across adjacent `{{{a}}}{{{b}}}`). v5 `shlex.quote` closes/reopens a quote at every boundary → single literal word. | Covered by a different v5 mechanism |
| **GHSA-59fj-m2j6-hcxh** | high | Incomplete fix of CVE-2026-53925: `--disable-config-exec` did not cover on-alert action commands. v5 `ShellAction.allow_shell()` reads `[global] disable_config_exec` (set by the `--disable-config-exec` CLI overlay) and, when hardened, runs the rendered command through `create_subprocess_exec(*shlex.split(cmd))` — no shell, operators stay literal. | Carry forward (CVE-2026-68519 port ✅) |
| **GHSA-2jqf-3j6f-683p** | high | `ports` plugin served `web_N_url` credentials/proxies unauthenticated. v5 publishes `scheme://host/path` only (`web_list.py`). | Covered by a different v5 mechanism — `test_ports_no_credential_leak.py` |
| **GHSA-5344-6x9j-2w33** | high | Plugin config secrets via the limits endpoints and exports (incomplete fix of GHSA-2jqf). v5 `get_limits()` is a closed key space; exported options go through `_is_secret_key` + URL redaction. | Covered — `test_export_base.py`, `test_routes.py` |
| **GHSA-2hvx-g9v6-w29h** | moderate | ClickHouse SQL injection / OOB exfiltration. v5 quotes identifiers for CREATE/ALTER **and** `insert(table=)` (2026-10-23), binds values, validates remote plugin names. | Carry forward — `test_export_wave_c.py` |
| **GHSA-56xw-p9qm-r437** | moderate | Argument injection via quotes in `secure_popen`'s tokenizer. v5 tokenizes first, renders per argument (`secure.py`). | Carry forward — `test_secure_popen.py` |
| **GHSA-vg43-q6xr-hp92** | moderate | `--hide-public-info` did not hide `public_info_human`. v5 TUI and WebUI hide both (2026-10-23); the API serves the address by design. | Carry forward — `test_plugin_ip.py` |
| **GHSA-48jj-p764-8x75** | moderate | SSRF bypass of CVE-2026-35587 (scheme-only check). v5 checks and pins the resolved address, re-checks redirects. Residual: FTP redirect (B-14). | Carry forward — `test_plugin_ip.py` |
| **GHSA-fp27-88fp-2phg** | high | CORS credentials guard used exact-match (`== ["*"]`) instead of membership; a multi-origin allowlist containing `*` bypassed it. v5 `_wire_cors` already uses `any(o == "*" for o in origins)`. | Carry forward (Phase 1.5 ✅) |

### Watching — unpublished advisories

| GHSA | Severity | State | v5 plan |
|---|---|---|---|
| GHSA-mcm7-fmh3-v6v3 | medium | draft | Curses terminal escape injection + memory exhaustion via process names rendered in alerts. v5 alerts plugin (Phase 2) must sanitize control sequences and cap rendered string size. Tracked separately until the advisory is published. |

### Closed — fixed in v4, no v5 action required

The following advisories were fixed in v4 before the v5 effort began. The
v5 code covers them by construction, and no additional v5-specific work is
needed.

- GHSA-93gr-c454-3xw7 — Passwords exposed in plain text
- GHSA-w4m6-4mpc-gq25 — BasicAuth Bypass
- GHSA-f533-jmqq-4www — Public IP visible on documentation screenshot

## Secret redaction — `as_dict_secure()`

Used by the REST API — CVE-2026-32609. Implemented in
`glances/config.py`. `/api/5/config` serves `as_dict_secure()` when
`[outputs] password` is set and only `as_dict_public()` otherwise
(security audit 2026-10-04, M1). See `SKILL-config.md` for the full list
of redacted key fragments and the conditional access pattern.

Redaction is **value-level as well as key-level** (CVE-2026-68520):
`as_dict_secure()` scrubs credentials embedded in URL values
(`scheme://user:pass@host`) even when the key name looks innocuous, via
`_URL_CREDENTIALS_RE`. Key names `username` / `user` / `login` are also
redacted (`user` / `login` matched exactly so the `user_careful` /
`user_warning` CPU-load thresholds stay visible).

The same redaction discipline applies **anywhere** the API may be
consumed unauthenticated — not just `/api/5/config`. When adding a new
endpoint, ask: "could this leak a credential to an anonymous caller?".
**`/api/5/args`** routes its payload through the same
`GlancesConfig._secure_value()` (`_redact_args()` in `glances/routes.py`).

## CORS — `glances/webserver.py::_wire_cors`

Default values for v5:

```ini
[outputs]
cors_origins =                  # empty list — middleware not wired, browsers block cross-origin
cors_allow_credentials = false  # wildcard + credentials downgrades to false with WARNING
```

When `cors_origins` is unset the CORS middleware is **not added** at all — browsers' default same-origin policy blocks cross-origin requests, which is the safe stance. Setting any origin wires Starlette's `CORSMiddleware` with `allow_methods=["GET", "POST"]` and `allow_headers=["Authorization", "Content-Type"]`.

`cors_origins=*` with `cors_allow_credentials=true` is **invalid per the CORS spec** (CVE-2026-32610). The middleware logs a WARNING and forces `allow_credentials=False`. It never refuses to start.

## DNS rebinding — `glances/webserver.py::_wire_trusted_hosts`

```ini
[outputs]
# Comma-separated list. Empty = no Host filtering + WARNING when bind is non-loopback.
# webui_allowed_hosts = glances.example.com, 192.0.2.10
```

Implemented via Starlette's `TrustedHostMiddleware`. Default behaviour matches v4: no allowlist → no filtering. When `bind_address` is **not** loopback (`127.0.0.1`, `::1`, `localhost`) and `webui_allowed_hosts` is empty, a startup WARNING is logged — this is the only signal that DNS-rebinding mitigation is off.

The MCP endpoint already enforces equivalent protection via `mcp_allowed_hosts` + `TransportSecuritySettings` in `glances/outputs/glances_mcp.py`.

## Rate limiting (architecture §4.5)

`glances/ratelimit.py`, a pure ASGI middleware between TrustedHost and CORS:

```ini
[outputs]
rate_limit_per_minute = 0       # general limit per client address, 0 = off (default)
rate_limit_burst = 0            # 0 = one minute's worth
auth_fail_per_minute = 10       # failed authentications per address, 0 = off
```

- A request with an `Authorization` header that ends in a 401 spends a try;
  with none left the address gets 429 before PBKDF2 runs. The try that
  empties the bucket logs one WARNING naming the address (fail2ban).
- Exempt: `/status` and `/healthz` only. `/api/5/token` is limited.
- Never read `X-Forwarded-For` in Glances: uvicorn already trusts it from
  127.0.0.1 only. IPv6 clients count per /64.

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

Since the cutover, v4 and v5 live on separate branches and nothing
propagates automatically. A security fix for v4 targets
`support/glancesv4`; when the same flaw exists in v5, a separate PR
targets `develop` (and conversely). See `SKILL-ci-cd.md`.

## v5 cybersecurity audit (release blocker)

The full v5 audit (architecture §4.8) ran on 2026-10-04:
`docs/architecture/glances-v5-security-audit.md` answers the §4.8 open
items and re-checks every CVE of §8 against the v5 code. Its correction
plan lists what remains before `5.0.0` (M5, M6, M9, M11 and the remaining
low findings) — a release blocker for `5.0.0`.

No code may import a deleted v4 module: `tests/test_imports.py` checks
every `glances` import statically.

## What's deferred

- **Remaining audit findings** (M5, M6, M9, M11, low findings) — before `5.0.0`, see the audit's correction plan.
- **v4 counterparts of the audit findings** — to port to `support/glancesv4` (list in the audit).

## Module path

```
glances/config.py                  # as_dict_secure() / as_dict_public()
glances/security.py                # PBKDF2 + JWTHandler
glances/webserver.py               # build_app + middlewares
glances/ratelimit.py               # rate limiting middleware
glances/routes.py                  # /api/5/config, /api/5/args redaction
glances/actions/shell/             # shell escaping
glances/outputs/glances_mcp.py     # MCP host protection
tests/test_security.py             # PBKDF2 + JWT unit tests
tests/test_webserver.py            # middleware + auth integration tests
tests/test_imports.py              # no import of a deleted module
docs/architecture/glances-v5-architecture-decisions.md  # §4 + §8 CVE table
docs/architecture/glances-v5-security-audit.md          # v5 audit (2026-10-04)
```
