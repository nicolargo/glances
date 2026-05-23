# Design — XML-RPC server Host header validation

> Patch for **GHSA-w856-8p3r-p338** / **CVE-2026-46611**
> Branch: `GHSA-w856-8p3r-p338` → `develop`
> Target version: next `4.5.x` release

---

## Context

The Glances XML-RPC server (`glances -s`, implemented in `glances/server.py`)
does not validate the HTTP `Host` header, leaving it vulnerable to DNS
rebinding attacks (CWE-346 / CWE-350, CVSS 5.3 medium).

Equivalent protection was already added to the two other Glances server
backends:

| Backend | Module | Config key | Default |
|---|---|---|---|
| REST / WebUI | `glances/outputs/glances_restful_api.py` | `webui_allowed_hosts` | permissive (warning at startup) |
| MCP | `glances/outputs/glances_mcp.py` | `mcp_allowed_hosts` | restrictive (`localhost,127.0.0.1`) |
| **XML-RPC** | `glances/server.py` | **none — this patch** | — |

The XML-RPC server is the legacy native client/server transport used by
`glances -s` / `glances -c` and the TUI's server browser. It cannot rely on
Starlette's `TrustedHostMiddleware` because it is built on Python's stdlib
`xmlrpc.server.SimpleXMLRPCRequestHandler` (no ASGI stack).

## Goals

1. Add Host header validation to the XML-RPC server, opt-in via configuration.
2. Preserve existing behaviour for all current deployments (no breaking
   change). Operators who do not set the new config key see the same
   functional behaviour as today, plus a startup warning.
3. Keep parity with the REST/WebUI mitigation (config naming convention,
   wildcard semantics, warning style).
4. Cover the new behaviour with regression tests.

## Non-goals

- Not addressed by this patch: the companion CORS issue (CVE-2026-33533).
  That is tracked separately and was already partially mitigated.
- Not addressed: deprecation/removal of the XML-RPC server (option 2 of the
  advisory). That is a separate maintainer decision, out of scope for a
  security patch.
- No `NEWS.rst` entry in this patch — the maintainer updates the changelog
  at release time.

## Design decisions

### D1 — Dedicated config key `xmlrpc_allowed_hosts`

Chosen over reusing `webui_allowed_hosts` because Glances already follows a
*one-key-per-backend* pattern (`webui_allowed_hosts`, `mcp_allowed_hosts`).
The XML-RPC and WebUI servers are mutually exclusive at runtime (`-s` vs
`-w`) so sharing a key brings no operator-side benefit and the name would
be semantically misleading (a WebUI key controlling a non-WebUI backend).

### D2 — Permissive default + startup warning (REST pattern)

Chosen over a restrictive default (`["localhost", "127.0.0.1"]`, like MCP)
because:

- `glances -s` is most often bound to a non-loopback interface (this is the
  whole point of the native client/server mode).
- A restrictive default would silently break every existing client/server
  deployment after upgrade.
- The CVE is medium severity (5.3) and requires browser + DNS rebinding +
  user action; per project security philosophy (see `~/.claude/CLAUDE.md` §
  *Sécurité*) the default should not change.
- The startup warning ensures unprotected deployments are visible to the
  operator without breaking them.

### D3 — Wildcard support via `fnmatch.fnmatchcase`

Chosen over exact-match-only because the REST/WebUI documentation already
promises wildcard support (`*.example.com`) and operators should not have to
learn different rules per backend. `fnmatch` is stdlib, supports `*` / `?`
patterns, and is sufficient for hostnames.

Starlette's `TrustedHostMiddleware` uses subtly different semantics
(`*.example.com` matches `foo.example.com` but not `example.com`). For
consistency, this patch documents that the XML-RPC matcher uses `fnmatch`
semantics; any divergence from REST behaviour is called out in the doc.

### D4 — Validate Host *before* authentication

Same ordering as REST (`TrustedHostMiddleware` is outermost). Reject the
spoofed-Host request as `400 Bad Request` regardless of credentials so the
server does not act as an oracle for valid Host values via auth-error
differentials.

## Implementation outline

### `glances/server.py`

1. `GlancesXMLRPCServer.__init__`: read
   `config.get_list_value('outputs', 'xmlrpc_allowed_hosts', default=None)`,
   store on `self.allowed_hosts`. The handler reaches it via `self.server`.

2. `GlancesXMLRPCHandler.parse_request`: override the existing method.

   ```python
   def parse_request(self):
       if not super_simple_xmlrpc.parse_request(self):
           return False
       if getattr(self.server, 'allowed_hosts', None):
           host = self.headers.get('Host', '').split(':')[0]
           if not any(fnmatch.fnmatchcase(host, pat)
                      for pat in self.server.allowed_hosts):
               self.send_error(400, 'Bad Request: invalid Host header')
               return False
       if self.authenticate(self.headers):
           return True
       self.send_error(401, 'Authentication failed')
       return False
   ```

   The current implementation already overrides `parse_request`; this patch
   inserts the Host check between the stdlib parse and the existing auth.

3. `GlancesServer.__init__`: after the existing CORS warning block, add a
   warning when `self.server.allowed_hosts` is falsy, mirroring the REST
   warning style:

   ```
   WARNING: Glances XML-RPC server is running without Host header validation.
            DNS rebinding attacks may allow untrusted pages to read the XML-RPC API.
            Set xmlrpc_allowed_hosts in glances.conf [outputs] to restrict access:
              xmlrpc_allowed_hosts=localhost,127.0.0.1,<your-hostname>
   ```

   Plus `logger.warning(...)` companion entry.

### `conf/glances.conf`

Add a commented entry in the `[outputs]` section, right after
`mcp_allowed_hosts`:

```ini
# DNS rebinding protection for the XML-RPC server (glances -s)
# Restrict the HTTP Host header accepted by the XML-RPC server.
# Comma-separated list of hostnames or IPs. Wildcards supported (e.g. *.example.com).
# When this key is absent or commented out, no host filtering is applied (default behaviour).
# Recommended for any internet-facing or multi-tenant deployment.
#xmlrpc_allowed_hosts=localhost,127.0.0.1,myserver.example.com
```

### Documentation

Add a *Security — DNS rebinding protection (XML-RPC)* section to
`docs/cmds.rst` (client/server section) mirroring the existing block in
`docs/api/restful.rst`. Cover: what it does, default behaviour, how to
enable, wildcard syntax, recommendation for non-loopback deployments.

### Tests — `tests/test_xmlrpc_server.py` (new file)

| Test | Setup | Expectation |
|---|---|---|
| `test_allowed_hosts_disabled` | no config | any Host → 200 (regression of current behaviour) |
| `test_allowed_hosts_match` | `xmlrpc_allowed_hosts=127.0.0.1` | `Host: 127.0.0.1` → 200 |
| `test_allowed_hosts_mismatch` | `xmlrpc_allowed_hosts=127.0.0.1` | `Host: attacker.example.com` → 400 |
| `test_allowed_hosts_wildcard` | `xmlrpc_allowed_hosts=*.example.com` | `Host: foo.example.com` → 200, `Host: example.com` → 400 |
| `test_allowed_hosts_port_stripped` | `xmlrpc_allowed_hosts=127.0.0.1` | `Host: 127.0.0.1:61209` → 200 |
| `test_allowed_hosts_missing_header` | `xmlrpc_allowed_hosts=127.0.0.1` | request without Host → 400 |

Tests spin up a `GlancesServer` on `127.0.0.1` with a random free port in a
background thread, issue raw HTTP POSTs with `urllib.request` so the `Host`
header can be controlled, then shut the server down.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Breaking existing `glances -s` deployments | Permissive default — opt-in only. Warning, not enforcement. |
| Operator confusion (3 different `*_allowed_hosts` keys) | All three documented in the same `[outputs]` block, consistent naming. |
| Wildcard semantic divergence vs REST | Documented in the new section, explicit reference to `fnmatch`. |
| Future XML-RPC deprecation makes this dead code | Acceptable — the protection runs until deprecation lands, and the code is ~20 LoC. |

## Out of scope

- Re-implementing the XML-RPC server on top of an ASGI stack.
- Adding a `--xmlrpc-allowed-hosts` CLI flag (config-only for now, matches
  the REST/MCP pattern).
- Modifying `NEWS.rst` (release-time concern, not per-PR).

## Acceptance criteria

1. With no config change, `glances -s` behaves exactly as before (any Host
   accepted), plus a new WARNING on stdout and in the log.
2. With `xmlrpc_allowed_hosts=127.0.0.1` set, the curl PoC from the
   advisory (`Host: attacker.example.com`) returns `400 Bad Request`.
3. New tests pass, existing tests still pass.
4. `make lint && make format` clean.
5. Doc section is rendered correctly in `docs/_build/html/cmds.html`.
