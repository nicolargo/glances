# G9-1 — Serve the WebUI from the v5 FastAPI app: Design

**Status:** approved (2026-09-05)
**Phase:** 2 — closes the last remaining Phase 2 slot (architecture §10)
**Sub-project of:** G9 (see §2.1 for the decomposition)

---

## 1. Goals

Close architecture §10's Phase 2 bullet "WebUI served by FastAPI":

1. Serve static assets and a root document from the v5 FastAPI app.
2. Add `/api/5/args`, the last endpoint the future v5 UI needs that does not
   exist. The architecture doc already anticipates it by name (§8,
   CVE-2026-68520: *"When `/api/5/args` lands it must run its payload through
   the same `_secure_value()`"*).
3. Ship a **minimal v5 bundle** that proves the whole chain — webpack build →
   static serving → `fetch` → Vue render — so this group is verifiable on its
   own rather than being inert plumbing.

The current v4 Vue application is NOT made to work against `/api/5`. It calls
`api/4/*` and reads v4 payload shapes; it stays on v4 until it is replaced.

## 2. Out of scope

- **Porting or fixing the v4 Vue components.** They will be rewritten, not
  migrated — see §2.1. Their bundle (`public/glances.js`) is untouched here and
  keeps building.
- **`/api/5/all/views`.** It will never be built. v4's `views` structure is a
  v4 concept; v5 carries the same information as `_levels` inside the payload,
  and the rewritten UI reads that directly. Building a `views` endpoint would
  bake a v4 shape into the v5 API that its only future consumer does not want.
- **Browser / multi-server mode** (`/browser`, `browser.js`) — Phase 3, per
  architecture §10.
- **Retiring the v4 bundle and `templates/index.html`** — Phase 4 cleanup,
  alongside the removal of the v4 code.
- **`url_prefix`.** v4 supports serving under a path prefix; v5 has no such
  concept anywhere today. Adding one for the WebUI alone would be the only
  prefix-aware surface in v5. Deferred until something asks for it.

### 2.1 Where G9-1 sits

G9 was decomposed into three sub-projects because "serve the WebUI" and
"rewrite the UI" are independent subsystems with different risk profiles:

| | Scope | Closes |
|---|---|---|
| **G9-1** (this spec) | Serving plumbing, `--disable-webui`, `/api/5/args`, minimal v5 bundle | Phase 2 §10 bullet |
| **G9-2** | v5 UI foundation: service layer, app shell, theme, two reference plugins (one scalar, one collection) | — |
| **G9-3…N** | Per-plugin component rewrites, in groups, following G9-2's pattern | — |

`5.0.0a2` can ship on G9-1 alone: TUI, REST API and a WebUI that is served and
alive, with the plugin views arriving over G9-2+.

## 3. Constraints

- **v4 code is read-only.** `glances/outputs/glances_restful_api.py` and
  `glances/outputs/static/js/**` (the v4 app) stay byte-identical. The only
  shared file this group edits is `webpack.config.js`, and only to add an entry.
- **The v4 bundle must keep building.** `npm run build` produces
  `public/glances.js` and `public/browser.js` exactly as before, plus the new
  bundle.
- **Never commit.** Changes are staged; the maintainer commits.
- **Never touch `NEWS.rst`.**
- The built bundle is a generated artifact. Per the maintainer's workflow,
  rebuilding the WebUI is its own commit — the plan must keep source changes
  and the rebuilt bundle separable.

## 4. Components

| File | Responsibility |
|---|---|
| `glances/webserver_v5.py` | `/static` mount, `/` route, enable/disable gate. |
| `glances/routes_v5.py` | `/api/5/args`. |
| `glances/main_v5.py` | `--disable-webui`; `-s` help text. |
| `glances/outputs/static/webpack.config.js` | Third entry `glances5`. |
| `glances/outputs/static/js/app_v5.js` | Minimal v5 bootstrap (new). |
| `glances/outputs/static/templates/index_v5.html` | Root document (new). |
| `tests/test_webserver_v5.py` | Serving, gate, auth and host-validation tests. |
| `tests/test_routes_v5.py` | `/api/5/args` shape and redaction. |

### 4.1 Serving

`build_app()` gains, after `include_router()`:

```python
app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")

@app.get("/", response_class=FileResponse)
async def index() -> FileResponse: ...
```

`STATIC_PATH` is `glances/outputs/static/public` — the same directory v4 serves,
so both bundles are reachable and the v4 app is not disturbed.

**No route-collision risk.** The v5 router carries `prefix="/api/5"`
(`routes_v5.py:74`), so the dynamic `/{plugin_name}` handler lives at
`/api/5/{plugin_name}` and cannot capture `/` or `/static/*`. This differs from
v4, where the same handler sits closer to the root and the ordering matters.

**No Jinja2.** v4 renders `templates/index.html` through `Jinja2Templates`
solely to interpolate `url_prefix` and `refresh_time`. v5 has no `url_prefix`
(§2), and the refresh rate is already reachable over HTTP as `[global] refresh`
via the existing `/api/5/config` — measured: the v5 argument namespace carries
no refresh key at all, so `/api/5/args` is NOT its source. `index_v5.html` is
therefore a static file served with `FileResponse`, dropping a runtime
templating dependency from the v5 web path.

### 4.2 Enable / disable

v4's `-w` starts the REST API **and** the WebUI, and `--disable-webui` turns
the UI off while keeping the API. v5's `-s` is the equivalent entry point, so
it gains the same behaviour:

| Invocation | REST API | WebUI |
|---|---|---|
| (none) | no | no |
| `-s` | yes | **yes** |
| `-s --disable-webui` | yes | no |

`-s`'s help text changes from "Run as a REST API server" to name the Web UI as
well. This is a widening of what `-s` does, and existing v5-alpha users of `-s`
will start getting a WebUI; that is deliberate v4 parity and belongs in the
release notes.

When disabled, neither `/` nor `/static` is registered — a disabled WebUI must
not leave the asset directory reachable.

### 4.3 `/api/5/args`

```
GET /api/5/args → dict
```

Returns `vars(args)` with the same redaction `config_v5.as_dict_secure()`
applies, reusing its `_secure_value()` helper rather than re-implementing it —
CVE-2026-68520 was a *value-level* bypass (a credential inside a URL value,
`scheme://user:pass@host`), and a second redactor is a second place to get it
wrong.

**Measured first: the v5 argument namespace holds no credential.** It has 23
keys — `api_doc, bind, byte, config_path, debug, disable_config_exec,
disable_plugin, enable_mcp, enable_plugin, export, export_csv_file,
export_csv_overwrite, export_json_file, export_process_filter, fahrenheit,
full_quicklook, hide_public_info, meangpu, no_tui, percpu, port, server,
set_password`. There is no `password` argument: v5 configures authentication
through the config file (`[outputs]`), not the command line, and `set_password`
is a boolean that triggers the interactive hash generator.

v4's list — `snmp_community`, `snmp_user`, `snmp_auth`, `conf_file`, `username`,
`password` — therefore transfers almost entirely to nothing: v5 has no SNMP
options, no `username`, no `password`, and names the config path `config_path`.
**Copying v4's frozenset would pin six key names of which five do not exist**,
which reads as coverage while protecting nothing.

Rules for v5:

- Every value goes through `_secure_value()` when no authentication is
  configured. This is the load-bearing rule: it catches a credential embedded
  in a value (`scheme://user:pass@host`) regardless of the key it arrives
  under, which is precisely the CVE-2026-68520 shape and the only credential
  path that can reach this endpoint today.
- `config_path` is redacted when no authentication is configured — v4's
  treatment of `conf_file`; a filesystem path discloses layout.
- Nothing needs unconditional redaction, because no argument is a secret. If a
  future argument ever carries one, it must be added to the redaction set in
  the same commit that adds it; a test asserts the current key set so that
  adding an argument forces the author past this decision.

### 4.4 Minimal v5 bundle

`webpack.config.js` gains a third entry beside the existing two:

```js
entry: {
    glances:  "./js/app.js",     // v4 app — untouched
    browser:  "./js/browser.js", // v4 browser — untouched
    glances5: "./js/app_v5.js",  // v5 app — this group
},
```

Output goes to `public/glances5.js` under the existing `[name].js` rule.

`app_v5.js` mounts a Vue 3 app that calls `/api/5/all`, `/api/5/args` and
`/api/5/config` once, and renders the Glances version, the plugin count and the
refresh rate (the last from `[global] refresh` in the config response, per
§4.1). It is
deliberately not a layout: G9-2 replaces its body with the real app shell. Its
job here is to prove the chain end to end.

`index_v5.html` mirrors `templates/index.html` minus the Jinja2 placeholders,
loading `static/glances5.js`.

## 5. Security

Both new surfaces inherit the existing middleware stack; nothing is added.
Each line below is a **verified** property of the current code, and each gets a
regression test — the point of listing them is that a new surface silently
falling outside a middleware is exactly how these protections rot.

| Protection | Status for `/` and `/static/*` |
|---|---|
| DNS rebinding (CVE-2026-32632) | Covered. `TrustedHostMiddleware` is the outermost middleware (`webserver_v5.py` §"Middleware composition"), so it sees every request regardless of route. |
| Authentication (CVE-2026-32596) | Covered. `UNAUTH_PATHS` is `{"/status", "/healthz", "/api/5/token"}` (`webserver_v5.py:65`), so `/` and `/static/*` require credentials whenever a password is configured — v4 parity. |
| CORS (CVE-2026-32610 / 34839) | Covered by the existing `CORSMiddleware` wiring. |
| Credential leakage (CVE-2026-68520) | `/api/5/args` reuses `_secure_value()`; see §4.3. |

One consequence worth stating: serving a UI does not widen the unauthenticated
surface, because the UI is not in `UNAUTH_PATHS`. An operator running without a
password already exposes everything the UI would show, via the REST API.

## 6. Testing

Unit and route level:

1. `/` returns 200 and `text/html` when the WebUI is enabled.
2. `/static/glances5.js` returns 200 when the bundle is present.
3. Neither route is registered under `--disable-webui` (assert on the app's
   route table, not only on a 404 — a 404 could come from anywhere).
4. `/` requires authentication when a password is configured.
5. `TrustedHostMiddleware` rejects a bad `Host` header on `/`, not only on
   `/api/5/*`.
6. `/api/5/args` redacts URL-embedded credentials when unauthenticated — the
   CVE-2026-68520 shape, asserted on a **value**, not a key name.
7. `/api/5/args` redacts `config_path` when unauthenticated and returns it
   when authenticated.
8. `/api/5/args` returns the non-sensitive arguments unredacted in both
   postures (`port`, `bind`, `server`).
8b. The argument key set is asserted explicitly, so adding a future argument
   fails this test and forces its author to decide whether it is sensitive
   (§4.3).

End-to-end, run manually and reported in the task notes:

9. `python -m glances.main_v5 -s --port <p>`, then `curl /` returns the
   document and `curl /static/glances5.js` returns the bundle.
10. `npm run build` still produces `public/glances.js` and `public/browser.js`.
    Webpack 5 uses deterministic module ids in production, so adding an entry
    should leave them unchanged; if their content does move, the task report
    must say why rather than wave it through.

## 7. Risks

| Risk | Mitigation |
|---|---|
| Widening `-s` surprises v5-alpha users who wanted a headless REST server. | It is v4 parity and `--disable-webui` restores the old behaviour. Release-notes item. |
| The rebuilt bundles inflate the diff and mix generated output with source. | Keep the source change and the rebuild in separate commits, as the maintainer already does (`Rebuild WebUI`). |
| `app_v5.js` becomes a second app nobody finishes, i.e. dead code. | It is explicitly the seed G9-2 grows, not a parallel implementation. If G9-2 does not follow, the honest move is to delete it, not to keep it. |
| The minimal bundle is mistaken for a working WebUI by a user on `5.0.0a2`. | It renders its own status plainly (version, plugin count) and does not imitate a dashboard. |

## 8. Deliverables

1. `/static` mount and `/` route in `webserver_v5.py`, gated by
   `--disable-webui`.
2. `/api/5/args` in `routes_v5.py`, reusing `_secure_value()`.
3. `--disable-webui` in `main_v5.py`; `-s` help text updated.
4. Third webpack entry, `js/app_v5.js`, `templates/index_v5.html`.
5. Tests 1-8 above; 9-10 run and reported.
6. Release-notes items: `-s` now serves the WebUI; `/api/5/args` added.
