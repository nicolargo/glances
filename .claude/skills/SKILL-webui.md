# Skill: Glances v5 — Web UI (Vue.js 3)

The v5 WebUI is a Vue.js 3 rewrite against the `/api/5/` payloads. This
skill captures the stack, the design principles and the contract with the
REST API. Build commands and the pre-PR rules live in `webui.md`.

## Stack

| Layer | Technology |
|---|---|
| Framework | **Vue.js 3** single-file components, compiled by `vue-loader` |
| CSS | Plain CSS with design tokens (custom properties) in `css/glances.css` — no Bootstrap, no SCSS |
| Build | webpack (`glances/outputs/static/webpack.config.js`), `make webui` |
| HTTP client | Native `fetch`, only through `js/api.js` |
| Hosted by | The same FastAPI instance as the REST API (architecture §4) |

Architecture §10 planned "Vue.js 3, Bootstrap 5, SCSS — largely unchanged
from v4"; the WebUI was rewritten instead, and v5 ships no Bootstrap.

Adding a plugin component is one new `js/Plugin<Name>.vue` file plus one
entry in the registry `js/plugins/index.js` (its `slot` and order mirror
the TUI's, `glances/outputs/curses_renderer.py`).

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

`_wire_webui()` in `glances/webserver.py` serves
`glances/outputs/static/templates/index.html` at `/` (and `browser.html`
at `/browser` with `--browser`), and mounts `glances/outputs/static/` at
`/static` (`StaticFiles`). There is no `url_prefix` in v5. `--disable-webui`
leaves only the REST API.

## Security implications

- **DNS rebinding** — `webui_allowed_hosts` (CVE-2026-32632) applies to
  WebUI requests as well as API requests. See `SKILL-security.md`.
- **CORS** — same defaults as the REST API: empty `cors_origins`,
  `allow_credentials = false`. WebUI calls go to its own origin, so CORS
  rarely matters, but third-party dashboards consuming `/api/5/*` are
  affected.
- **Authentication** — `/` is not in `UNAUTH_PATHS`: when
  `[outputs] password` is set, the WebUI is behind the same Basic / Bearer
  auth as the API.

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
but **available via `get_api_payload()`** (which the REST API serves).

## Testing the WebUI

- `make test-js` — JavaScript unit tests of the `js/*.js` modules
  (`tests/js/*.mjs`, `node --test`).
- `make test-webui` — `tests/test_webui_*.py`: rendering, drift tests that
  keep the WebUI aligned with the TUI, and real-browser tests
  (`tests/test_webui_browser*.py`, Playwright + Chromium).
- CI (`.github/workflows/test.yml`, Linux job) runs both.

UI-level changes must be **visually verified** in a real browser before
being merged — type checking and unit tests verify code correctness, not
feature correctness. When testing manually, exercise both:
- the **golden path** (default config, mainstream plugins)
- the **edge cases** (alert states, very long collection lists, narrow
  viewport, dark mode)

## Module path

```
glances/outputs/static/js/app.js               # main page entry (AppShell.vue)
glances/outputs/static/js/browser_app.js       # browser page entry (BrowserPage.vue)
glances/outputs/static/js/Plugin<Name>.vue     # one component per plugin
glances/outputs/static/js/plugins/index.js     # plugin registry
glances/outputs/static/js/api.js               # the only module that calls the REST API
glances/outputs/static/css/glances.css         # design tokens + styles
glances/outputs/static/templates/index.html    # served at /
glances/outputs/static/templates/browser.html  # served at /browser
glances/outputs/static/public/glances.js       # built bundle (make webui) — never in a PR
glances/outputs/static/public/browser.js       # built bundle (make webui) — never in a PR
glances/webserver.py                           # _wire_webui()
.github/workflows/webui.yml                    # WebUI build, bundle committed by CI
```

## Relationship with the `webui.md` skill

`.claude/skills/webui.md` documents the WebUI contribution flow (build
commands, npm scripts, pre-PR checks). This skill documents the design
and the API contract; use both.
