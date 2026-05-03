# Skill: Glances v5 — REST API (FastAPI)

> **Phase status — STUB.** The FastAPI application lands in **Phase 1**.
> This skill captures the locked-in decisions from architecture §4 / §5
> / §8 so contributors and Claude agree on the contract before the code
> is written. Code examples will be added when the implementation lands.

## Stack

- **Framework:** FastAPI on a single port `:61208`
- **Replaces:** Bottle (`:61208`) **and** XML-RPC (`:61209`) from v4
- **WebUI hosting:** the same FastAPI instance serves the Vue.js bundle
- **No v4 API compatibility.** API version is `5`.

## Route prefix

All routes live under `/api/5/`. Route structure mirrors v4 with the
version number bumped:

| Route | Returns |
|---|---|
| `/api/5/<plugin>` | One plugin's payload |
| `/api/5/<plugin>/info` | Plugin metadata (`fields_description`) |
| `/api/5/all` | Full store |
| `/api/5/config` | Configuration (filtered for unauthenticated) |
| `/api/5/args` | CLI args (filtered for unauthenticated) |
| `/api/5/serverslist` | Browser mode server list (no `password`/`uri` fields) |
| `/api/5/alert` | Alert history |
| `/docs` | Swagger UI |
| `/redoc` | ReDoc |

`/docs` and `/redoc` are exposed **by default**. Disable via:

```ini
[outputs]
api_doc = false
```

## Authentication

Two mechanisms preserved from v4, both supported in v5:

| Mechanism | Header / pattern |
|---|---|
| **Bearer token** (v4.5.0+) | `Authorization: Bearer <token>` |
| **Basic Auth** (PBKDF2) | `Authorization: Basic <base64>` |

**Default mode is unauthenticated** — startup `WARNING` is logged
(CVE-2026-32596). The four OSS rules apply (see `SKILL-security.md`).

## Sensitive endpoints

`/api/5/config` and `/api/5/args` carry credentials in their underlying
data. Unauthenticated access **must** go through
`GlancesConfigV5.as_dict_secure()` which redacts secret-like keys
(CVE-2026-32609). Authenticated access returns the full view.

`/api/5/serverslist` strips `password` and `uri` fields from each entry
before serialization (CVE-2026-32633), regardless of authentication.

See `SKILL-security.md` for the full CVE checklist and
`SKILL-config.md` for the redaction rules implemented in
`as_dict_secure()`.

## CORS

Default values for v5 (CVE-2026-32610):

```ini
[outputs]
cors_origins =                    # empty list — no cross-origin allowed
allow_credentials = false         # mandatory: wildcard + credentials is invalid
```

The combination `allow_origins=["*"]` + `allow_credentials=True` is
**rejected** by the FastAPI CORS middleware (Starlette-level enforcement).
Any new endpoint must respect this default — never opt into wildcards.

## DNS rebinding (`webui_allowed_hosts`)

```ini
[outputs]
# Comma-separated list. Empty = accept any Host header (loopback only).
# webui_allowed_hosts = glances.example.com, 192.0.2.10
```

Implemented via Starlette's `TrustedHostMiddleware`. Startup `WARNING`
when running in non-loopback mode without `webui_allowed_hosts` set
(CVE-2026-32632).

## Data flow

```
HTTP request
    │
    ▼
FastAPI route                     (Phase 1)
    │
    ▼
plugin.get_stats()                ✅ Phase 0 (lockless read)
or as_dict_secure()               ✅ Phase 0 (for /api/5/config and /api/5/args)
    │
    ▼
JSON response
```

The REST API is a **lockless reader** of the StatsStore. Plugin
collection cycles run independently in the asyncio scheduler and never
block API requests.

## Datamodel changes vs v4

> "Datamodel changes between v4 and v5 are allowed. v5 is a clean break;
> API consumers must migrate. Changes must be documented in release
> notes." (architecture §9)

Concretely, the v5 API can:
- rename a field
- change a field type (e.g. integer → float)
- remove a v4-only field
- add a new field
- change the structure of a collection plugin's output

Every datamodel change ships with a release note entry (`NEWS.rst`).

## What's deferred

- **FastAPI app instantiation** — Phase 1
- **Authentication middlewares** (Bearer + Basic) — Phase 1
- **CORS / TrustedHost middleware wiring** — Phase 1
- **Per-plugin route registration** — Phase 1, growing as plugins migrate
- **`/api/5/all` aggregation** — Phase 2 (when most plugins are migrated)
- **`/api/5/serverslist`** — Phase 3 (browser mode)
- **`/api/5/alert`** — Phase 1 (alongside `GlancesAlerts`)

## Testing the REST API

Test stack: `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`) +
`unittest.mock` (architecture decision §9). Style: pytest-native top-level
functions with fixtures and `assert` statements.

Pattern (Phase 1+): use FastAPI's `TestClient` (or `httpx.AsyncClient`
for async-only paths). Build a `StatsStoreV5` populated with one or two
fake plugins, instantiate the FastAPI app, hit each route, assert on the
response.

For security tests: validate that unauthenticated access does **not**
leak secrets, that DNS rebinding is rejected when configured, that CORS
preflights respect `cors_origins`.

## Module path (target — Phase 1+)

```
glances/api_v5/__init__.py        # FastAPI app factory
glances/api_v5/routes/<name>.py   # one router per plugin / topic
glances/api_v5/auth.py            # Bearer + Basic middleware
glances/api_v5/security.py        # CORS + TrustedHost wiring
tests/test_api_v5.py              # route + middleware tests
```

The v4 API code (`glances/main.py`, `glances/outputs/glances_bottle.py`,
`glances/outputs/glances_restful_api.py`, etc.) is **not modified**,
**not imported**, **not subclassed** by v5.
