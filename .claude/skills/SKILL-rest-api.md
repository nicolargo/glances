# Skill: Glances v5 — REST API (FastAPI)

Phase 1.5 wired the app skeleton + security middlewares. Phase 1.6
shipped the concrete routes. The CLI entrypoint (Phase 1.7) glues the
app, scheduler, and plugin registry together.

## Stack

- **Framework:** FastAPI on a single port `:61208`
- **Replaces:** Bottle (`:61208`) **and** XML-RPC (`:61209`) from v4
- **WebUI hosting:** the same FastAPI instance will serve the Vue.js bundle (Phase 2)
- **No v4 API compatibility.** API version is `5`.

## Route inventory (Phase 1.6 ✅)

All routes live in `glances/routes_v5.py` under the `/api/5` prefix.

| Path | Method | Auth | Source |
|---|---|---|---|
| `/api/5/token` | POST | Basic (route-level) | `app.state.jwt_handler` |
| `/api/5/pluginslist` | GET | per-config | `app.state.plugins` keys |
| `/api/5/all` | GET | per-config | `store.as_dict()` |
| `/api/5/alert` | GET | per-config | `alerts.get_history()` |
| `/api/5/config` | GET | per-config | `config.as_dict_secure()` |
| `/api/5/<plugin>` | GET | per-config | `store.get(plugin)` (with `_levels`) |
| `/api/5/<plugin>/info` | GET | per-config | `plugin.fields_description` |
| `/status`, `/healthz` | GET | **always open** | hardcoded `{"status":"ok","version":"5"}` |
| `/docs`, `/redoc` | GET | per-config | FastAPI Swagger / ReDoc (toggle via `[outputs] api_doc=false`) |

**"per-config"** = behind the global Auth middleware when `[outputs] password` is set; otherwise open.

### `/api/5/token` flow

1. Operator sets `[outputs] password=<pbkdf2>` (and optionally `jwt_secret_key`) in `glances.conf`.
2. Client `POST /api/5/token` with HTTP Basic Auth → receives `{"access_token": "...", "token_type": "bearer", "expires_in": <seconds>}`.
3. Subsequent calls use `Authorization: Bearer <jwt>`.

`/api/5/token` is **exempt from the global Auth middleware** (listed in `UNAUTH_PATHS` alongside the probes). Otherwise the middleware would 401 before the route can read Basic credentials. Auth is enforced **inside the route** via `Depends(HTTPBasic)`.

When `password` is unset → `/api/5/token` returns **404** (no token to mint). Matches v4.

### Cycle-0 semantics

A plugin registered but not yet updated (scheduler cycle 0) → `GET /api/5/<plugin>` returns `200 null`. Distinguishes "unknown plugin" (`404`) from "data not yet available" (transient — clients poll). Decision: never serve a stale-or-empty fallback dict for cycle 0.

### `_levels` payload included

REST clients (UI / WebUI consumers) get the full store payload, including the `_levels` dict computed during `_transform()`. Exporters use `get_export()` instead (which strips `_*` keys).

## Authentication & middlewares

Architecture §4.3 / `SKILL-security.md` are authoritative. Summary:

```
TrustedHostMiddleware    ← DNS rebinding (CVE-2026-32632)
    ↓
CORSMiddleware           ← Cross-origin policy (CVE-2026-32610 / 34839)
    ↓
AuthMiddleware           ← Basic / Bearer (CVE-2026-32596)
    ↓
route handler / probe
```

Config keys in `[outputs]`: `password`, `username`, `jwt_secret_key`, `jwt_expire_minutes`, `cors_origins`, `cors_allow_credentials`, `webui_allowed_hosts`, `bind_address`, `api_doc`.

## Sensitive endpoints

- `/api/5/config` returns `config.as_dict_secure()` — secret-bearing keys are redacted (`***`). See `SKILL-config.md` for the redaction list.
- `/api/5/args` — deferred to Phase 1.7 (no CLI args module yet). Same redaction discipline applies when added.
- `/api/5/serverslist` — Phase 3 (browser mode). CVE-2026-32633 mandates stripping `password`/`uri` fields.

> **Open audit item** (architecture §4.8): is `/api/5/config` returning redacted data sufficient to remain unauthenticated, or should it require auth even when redacted? Captured for the end-of-v5 cybersecurity audit before merging `develop-v5 → develop`.

## Plugin registry — `app.state.plugins`

```python
from glances.webserver_v5 import build_app, register_plugin

app = build_app(config=config, store=store, alerts=alerts)
register_plugin(app, mem_plugin)
register_plugin(app, cpu_plugin)
```

`build_app()` initialises `app.state.plugins = {}`. Phase 1.7 CLI calls `register_plugin` for each instantiated plugin (alongside `scheduler.register(plugin)`). The registry is consulted by `/pluginslist` and `/<plugin>/info`; routes that read store payloads bypass it.

`register_plugin` raises `ValueError` on duplicate registrations.

## Data flow

```
HTTP request
    │
    ▼
TrustedHost → CORS → Auth (middleware stack)
    │
    ▼
FastAPI route handler                          (glances/routes_v5.py)
    │
    ▼
app.state.store.get(plugin)                    ← lockless read (architecture §1.3)
or alerts.get_history()
or config.as_dict_secure()
or jwt_handler.create_access_token(user)
    │
    ▼
JSON response
```

The REST API never blocks the asyncio scheduler — reads are lockless, writes happen exclusively in plugin update cycles.

## Datamodel changes vs v4

> "Datamodel changes between v4 and v5 are allowed. v5 is a clean break; API consumers must migrate." (architecture §9)

The v5 API can rename fields, change types, drop v4-only fields, add new fields, restructure collection outputs. Each datamodel change ships with a `NEWS.rst` entry.

## Testing the REST API

Test stack: `pytest` + `pytest-asyncio` (auto mode) + `unittest.mock`. Reference: `tests/test_routes_v5.py` + `tests/test_webserver_v5.py`.

Pattern:

```python
from fastapi.testclient import TestClient
from glances.webserver_v5 import build_app, register_plugin

def test_my_route(config, store):
    plugin = FakePlugin(store, config)
    asyncio.run(plugin.update())                    # populate the store
    app = build_app(config=config, store=store)
    register_plugin(app, plugin)
    with TestClient(app) as client:
        r = client.get("/api/5/fake")
    assert r.status_code == 200
    assert "_levels" in r.json()
```

Auth flow for tests: either skip auth (default — no `password` set), or set `password=hash_password("hunter2")` and call `client.post("/api/5/token", auth=("glances", "hunter2"))` then reuse the JWT.

## What's deferred

- `/api/5/<plugin>/<field>` (scalar single-field convenience) — follow-up
- `/api/5/<plugin>/<field>/history` — needs plugin history buffer (Phase 2)
- `/api/5/<plugin>/<pk_value>` (collection item lookup) — follow-up
- `/api/5/args` — depends on Phase 1.7 CLI args module
- `/api/5/serverslist` — Phase 3 (browser mode)
- WebUI static mount — Phase 2
- Rate limiting middleware — Phase 2+ (reserved keys in §4.5)

## Module path

```
glances/webserver_v5.py        # build_app + middlewares + register_plugin
glances/routes_v5.py           # /api/5/* router (Phase 1.6 ✅)
glances/security_v5.py         # PBKDF2 + JWTHandler
glances/alerts_v5.py           # state machine + history (consumed by /api/5/alert)
glances/stats_store_v5.py      # the lockless store
tests/test_webserver_v5.py     # middleware + auth integration tests
tests/test_routes_v5.py        # route handler tests
tests/test_security_v5.py      # PBKDF2 + JWT unit tests
```

The v4 API code (`glances/main.py`, `glances/outputs/glances_bottle.py`, `glances/outputs/glances_restful_api.py`) is **not modified**, **not imported**, **not subclassed** by v5.
