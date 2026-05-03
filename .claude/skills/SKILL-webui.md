# Skill: Glances v5 — Web UI (Vue.js + Bootstrap 5)

> **Phase status — STUB.** The v5 WebUI work lands in **Phase 2** (after
> the FastAPI server can serve `/api/5/all` and the Vue.js bundle).
> This skill captures the locked-in stack and design principles so
> contributors and Claude agree on the contract before the first v5
> WebUI PR. Component-level guidance grows as Phase 2 progresses.

## Stack

| Layer | Technology |
|---|---|
| Framework | **Vue.js 3** |
| CSS | **Bootstrap 5** + **SCSS** |
| Build | Existing v4 toolchain (`glances/outputs/static/`) — kept |
| HTTP client | Native `fetch` against `/api/5/<plugin>` (Phase 2) |
| Hosted by | The same FastAPI instance as the REST API (architecture §4) |

> "Vue.js 3, Bootstrap 5, SCSS — largely unchanged from v4." (architecture §10)

The v4 Vue stack is **largely reused** — the v5 work is primarily about
porting components to the `/api/5/` payload shape, not rewriting the
front-end framework.

## Design principles (project CLAUDE.md)

- **Strict typographic consistency** across all plugins — same font
  size, weight, opacity, letter-spacing throughout.
- **Pixel-perfect sparkline alignment** — CSS grid with fixed row heights;
  no inline `<svg>` widths that drift.
- **Footer = vertical alert list** of up to 10 entries — never a single
  horizontal banner.
- **No gauges.** Sparklines with an inline current value replace any
  gauge widget that v4 inherited.

## Routing the WebUI from FastAPI

The Vue.js bundle is mounted at the WebUI root, configurable in
`glances.conf` (preserved from v4):

```ini
[outputs]
webui_root_path = /              # default — change for sub-path deployments
```

Static files live under `glances/outputs/static/` (v4 path,
**unchanged**). The FastAPI app serves them via `StaticFiles`.

## Security implications

- **DNS rebinding** — `webui_allowed_hosts` (CVE-2026-32632) applies to
  WebUI requests as well as API requests. See `SKILL-security.md`.
- **CORS** — same defaults as the REST API: empty `cors_origins`,
  `allow_credentials = false`. WebUI calls go to its own origin, so CORS
  rarely matters, but third-party dashboards consuming `/api/5/*` are
  affected.
- **Authentication** — when Bearer or Basic Auth is configured, the
  WebUI passes credentials with every API call. The login flow is part
  of Phase 2.

## Data shape (consumer side)

The WebUI consumes the same payloads as any REST API client:

| Plugin flavour | Endpoint | Payload |
|---|---|---|
| Scalar (cpu, mem, load) | `GET /api/5/<plugin>` | `{percent: ..., total: ..., _levels: {...}, time_since_update: ...}` |
| Collection (network, fs) | `GET /api/5/<plugin>` | `{data: [{...}, {...}], _levels: {...}, time_since_update: ...}` |

`_levels` is the source of truth for alert highlighting (architecture
§3.3 / §3.4). The WebUI **does not recompute thresholds** — it reads the
level decided by `GlancesAlerts` and styles the cell accordingly.

`time_since_update` is exposed as an internal field
(`exportable: False`) and is therefore filtered out of `get_export()`
but **available via `get_stats()`** (which the WebUI consumes).

## What's deferred

- **Component-level migration** to `/api/5/` payload shapes — Phase 2,
  one plugin at a time
- **Login flow / auth UI** — Phase 2
- **Browser mode multi-server view** — Phase 3
- **Alert history view** (`/api/5/alert`) — Phase 2

## Testing the WebUI

The v4 WebUI test harness under `.github/workflows/webui.yml` continues
to run. v5 component tests follow the same approach (no test stack
change is planned for the front-end).

UI-level changes must be **visually verified** in a real browser before
being merged — type checking and unit tests verify code correctness, not
feature correctness. When testing manually, exercise both:
- the **golden path** (default config, mainstream plugins)
- the **edge cases** (alert states, very long collection lists, narrow
  viewport, dark mode)

## Module path

```
glances/outputs/static/                        # v4 Vue.js bundle (kept)
glances/outputs/static/src/components/<name>/  # one folder per plugin component
.github/workflows/webui.yml                    # WebUI build + test
```

Phase 2 will introduce a parallel `static_v5/` only if the porting
volume justifies it. Default plan: in-place migration, one component at
a time, gated by feature flags during the transition.

The v4 `glances/outputs/glances_bottle.py` (legacy WebUI server) is
**not modified**, **not imported**, **not subclassed** by v5. The v5
WebUI is served exclusively by the new FastAPI app (see
`SKILL-rest-api.md`).

## Relationship with the existing `webui.md` skill

The pre-existing `.claude/skills/webui.md` documents the **v4** WebUI
contribution flow (build commands, npm scripts, pre-PR checks) and
remains valid for v4 WebUI PRs targeting `develop`. The two skills
coexist until the final `develop-v5 → develop` merge.
