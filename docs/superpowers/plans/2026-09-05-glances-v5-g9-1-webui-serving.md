# G9-1 — Serve the WebUI from the v5 FastAPI app: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve static assets and a root document from the v5 FastAPI app, add `/api/5/args`, and ship a minimal v5 Vue bundle that proves the whole chain works.

**Architecture:** Three independent layers, in order. `/api/5/args` first, because the bundle calls it. Then the serving plumbing (`/static` mount, `/` route, `--disable-webui` gate) with a static root document. Then the webpack entry and the Vue bootstrap that fills it. Each task is independently testable; nothing depends on a later task.

**Tech Stack:** FastAPI / Starlette `StaticFiles` + `FileResponse`, pytest + `TestClient`, webpack 5, Vue 3.

**Spec:** `docs/superpowers/specs/2026-09-05-glances-v5-g9-1-webui-serving-design.md`

**Depends on:** nothing outstanding. G8 is complete and committed.

## Global Constraints

- **Never commit.** Every task ends with `git add`, never `git commit`. The maintainer commits personally. Never add a `Co-Authored-By` trailer.
- **Never touch `NEWS.rst`.**
- **v4 code is read-only.** `glances/outputs/glances_restful_api.py`, `glances/outputs/static/js/app.js`, `js/browser.js`, `js/components/**`, `js/services.js` and `templates/index.html` must all be byte-identical at the end of this plan. The ONE shared file this plan edits is `webpack.config.js`, and only to add an entry.
- **The v4 bundles must keep building.** `public/glances.js` and `public/browser.js` still produced.
- New Python files carry the 8-line SPDX header copied from `glances/exports/export_base_v5.py`, and `chmod +x` (a pre-commit hook rejects a file with a shebang that is not executable).
- Run the full suite with `uv run pytest -q`. **`tests/test_mcp.py` has 11 pre-existing failures unrelated to this work** (a leaked server squats port 61235 — see `.superpowers/sdd/2026-08-22-glances-v5-g8-export-csv-json/test-mcp-port-collision.md`); ignore them. `tests/test_perf.py` is load-sensitive: re-run it alone before believing a failure.
- **Deviation from the spec, already agreed:** spec §4.3 described auth-conditional redaction for `/api/5/args`. This plan makes it **unconditional**, matching `/api/5/config`, which calls `as_dict_secure()` with no auth branch and already serves the whole merged configuration to unauthenticated callers. Redacting the config file *path* while serving its *contents* would be theatre. Consequence: no `config_path` special case.

---

## File Structure

| File | Responsibility |
|---|---|
| `glances/webserver_v5.py` | `args` on `app.state`; `_STATIC_PATH` / `_TEMPLATE_PATH`; `/static` mount; `/` route; `--disable-webui` gate. |
| `glances/routes_v5.py` | `GET /api/5/args`. |
| `glances/main_v5.py` | `--disable-webui`; pass `args` to `build_app()`; `-s` help text. |
| `glances/outputs/static/templates/index_v5.html` | Root document (new, static — no Jinja2). |
| `glances/outputs/static/js/app_v5.js` | Minimal Vue 3 bootstrap against `/api/5` (new). |
| `glances/outputs/static/webpack.config.js` | Third entry `glances5`. |
| `tests/test_routes_v5.py` | `/api/5/args` shape and redaction (append). |
| `tests/test_webserver_v5.py` | Serving, gate, auth, host validation (append). |

---

### Task 1: `/api/5/args`

**Files:**
- Modify: `glances/webserver_v5.py` (`build_app()` signature, ~line 80; `app.state` block, ~line 113)
- Modify: `glances/routes_v5.py` (add a route beside `/config`, ~line 154)
- Modify: `glances/main_v5.py` (~line 605, the `build_app(...)` call)
- Test: `tests/test_routes_v5.py` (append)

**Interfaces:**
- Consumes: `GlancesConfigV5._secure_value(key, value)` (a `@classmethod`, `glances/config_v5.py:339`).
- Produces: `build_app(*, config, store, alerts=None, args=None) -> FastAPI` — a NEW keyword-only `args` parameter, defaulting to `None`; `app.state.args`; route `GET /api/5/args`.

Note the existing call sites of `build_app()` are keyword-only, so adding a defaulted keyword breaks none of them.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_routes_v5.py`. The module already provides `config_factory`, `store`, `_make_app_with_plugins` and `TestClient`; `_make_app_with_plugins` does not pass `args`, so add a local helper rather than changing it.

```python
# ------------------------------------------------------------------ /args


def _make_app_with_args(config, store, args):
    """build_app() with an args namespace attached, for the /args route."""
    from glances.webserver_v5 import build_app

    return build_app(config=config, store=store, alerts=None, args=args)


def test_args_returns_the_argument_namespace(config_factory, store):
    config = config_factory()
    args = argparse.Namespace(port=61208, bind="127.0.0.1", server=True)
    app = _make_app_with_args(config, store, args)

    with TestClient(app) as client:
        response = client.get("/api/5/args")

    assert response.status_code == 200
    assert response.json() == {"port": 61208, "bind": "127.0.0.1", "server": True}


def test_args_redacts_credentials_embedded_in_a_value(config_factory, store):
    """CVE-2026-68520 is a VALUE-level bypass: a credential inside a URL
    survives any key-name check. Asserted on the value, not on a key name."""
    config = config_factory()
    args = argparse.Namespace(export_url="http://alice:s3cr3t@influx.example:8086")
    app = _make_app_with_args(config, store, args)

    with TestClient(app) as client:
        payload = client.get("/api/5/args").json()

    assert "s3cr3t" not in payload["export_url"]
    assert "alice" not in payload["export_url"]
    assert "influx.example" in payload["export_url"]


def test_args_redacts_a_secret_key_name(config_factory, store):
    config = config_factory()
    args = argparse.Namespace(some_token="abcdef", port=61208)
    app = _make_app_with_args(config, store, args)

    with TestClient(app) as client:
        payload = client.get("/api/5/args").json()

    assert payload["some_token"] == "***"
    assert payload["port"] == 61208


def test_args_returns_an_empty_dict_when_no_namespace_was_supplied(config_factory, store):
    """build_app() is called without args by several tests and by any future
    embedder. The route must answer, not raise."""
    config = config_factory()
    app = _make_app_with_args(config, store, None)

    with TestClient(app) as client:
        response = client.get("/api/5/args")

    assert response.status_code == 200
    assert response.json() == {}


def test_args_matches_the_real_v5_argument_set(config_factory, store):
    """Freeze the key set. Adding a CLI option fails this test on purpose, so
    its author has to decide whether the new argument is sensitive (spec 4.3).

    `set_password` comes back as "***" because `_secure_value()` matches
    "password" as a SUBSTRING of the key name and returns before its
    non-string check. It is a boolean flag, not a credential. This is the
    "over-redact rather than under-redact" behaviour the shared helper
    documents; do NOT special-case it here -- the helper is shared with
    /api/5/config and must not be loosened for cosmetics.
    """
    from glances.main_v5 import build_parser

    config = config_factory()
    args = build_parser().parse_args(["-s"])
    app = _make_app_with_args(config, store, args)

    with TestClient(app) as client:
        payload = client.get("/api/5/args").json()

    assert set(payload) == {
        "api_doc",
        "bind",
        "byte",
        "config_path",
        "debug",
        "disable_config_exec",
        "disable_plugin",
        "disable_webui",
        "enable_mcp",
        "enable_plugin",
        "export",
        "export_csv_file",
        "export_csv_overwrite",
        "export_json_file",
        "export_process_filter",
        "fahrenheit",
        "full_quicklook",
        "hide_public_info",
        "meangpu",
        "no_tui",
        "percpu",
        "port",
        "server",
        "set_password",
    }
    assert payload["set_password"] == "***"
    assert payload["server"] is True
```

Add `import argparse` to the module's imports if it is not already there.

**Note:** the expected key set above INCLUDES `disable_webui`, which Task 2 adds. Run this specific test at the end of Task 2, not Task 1 — Step 3 below says so explicitly.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run pytest tests/test_routes_v5.py -k "args" -v
```

Expected: FAIL — `TypeError: build_app() got an unexpected keyword argument 'args'`.

- [ ] **Step 3: Write the implementation**

In `glances/webserver_v5.py`, add the parameter to `build_app()`:

```python
def build_app(
    *,
    config: GlancesConfigV5,
    store: StatsStoreV5,
    alerts: GlancesAlerts | None = None,
    args: argparse.Namespace | None = None,
) -> FastAPI:
```

Add `import argparse` under `TYPE_CHECKING` if the module does not already import it at runtime; `args` is only annotated, never introspected at import time.

Beside the other `app.state` assignments (~line 113):

```python
    app.state.args = args
```

In `glances/routes_v5.py`, immediately after the `/config` route:

```python
    @router.get("/args")
    async def args_dump(request: Request) -> dict[str, Any]:
        """Return the CLI argument namespace, redacted (issue #1527 / CVE-2026-68520).

        Redaction is UNCONDITIONAL, matching `/config` above: v5 applies no
        auth branch there either, and `/config` already serves the whole
        merged configuration to unauthenticated callers, so withholding the
        config file *path* while serving its *contents* would be theatre.

        `_secure_value()` is reused rather than reimplemented: CVE-2026-68520
        was a value-level bypass (a credential inside a URL), and a second
        redactor is a second place to get it wrong.
        """
        args = getattr(request.app.state, "args", None)
        if args is None:
            return {}
        secure = GlancesConfigV5._secure_value
        return {key: secure(key, value) for key, value in vars(args).items()}
```

`routes_v5.py` does NOT currently import `GlancesConfigV5` (verified: its
imports stop at `glances.security_v5`). Add it at module level beside that one:

```python
from glances.config_v5 import GlancesConfigV5
```

It carries no heavy dependency, and `webserver_v5.py` already imports it.

Add `_RESERVED_NAMES` coverage: `"args"` must join the frozenset at `glances/routes_v5.py:59`, otherwise a plugin literally named `args` would be shadowed and the reservation would be undocumented:

```python
_RESERVED_NAMES: frozenset[str] = frozenset({"token", "pluginslist", "all", "alert", "config", "args"})
```

In `glances/main_v5.py`, line ~605:

```python
    app = build_app(config=config, store=store, alerts=alerts, args=args)
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run pytest tests/test_routes_v5.py -k "args" -v
```

Expected: all PASS except `test_args_matches_the_real_v5_argument_set`, which fails on the missing `disable_webui` key until Task 2. Confirm that is the ONLY failure and that its message is about `disable_webui` specifically — any other difference means the key set drifted for another reason and must be investigated, not accepted.

- [ ] **Step 5: Prove the whole route module still passes**

```bash
uv run pytest tests/test_routes_v5.py -q
```

Expected: only the one known failure above.

- [ ] **Step 6: Stage**

```bash
git add glances/webserver_v5.py glances/routes_v5.py glances/main_v5.py tests/test_routes_v5.py
```

Do NOT commit.

---

### Task 2: Serving plumbing and the `--disable-webui` gate

**Files:**
- Modify: `glances/main_v5.py` (argument parser)
- Modify: `glances/webserver_v5.py` (module constants; `build_app()` body)
- Create: `glances/outputs/static/templates/index_v5.html`
- Test: `tests/test_webserver_v5.py` (append)

**Interfaces:**
- Consumes: `build_app(..., args=...)` and `app.state.args` from Task 1.
- Produces: `--disable-webui` CLI flag (`args.disable_webui: bool`, default `False`); module constants `_STATIC_PATH` and `_TEMPLATE_PATH` in `glances/webserver_v5.py`; routes `GET /` and the `/static` mount.

`index_v5.html` references `static/glances5.js`, which Task 3 builds. Until then the page loads and the script 404s — that is expected and is why Task 2's tests assert on `/static/glances.js` (the existing v4 bundle, already in `public/`) to prove the mount, and only on the status and content type of `/`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_webserver_v5.py`, following its existing fixture style.

```python
# ------------------------------------------------------- WebUI serving (G9-1)


def _args(**overrides):
    base = {"disable_webui": False}
    base.update(overrides)
    return argparse.Namespace(**base)


def test_index_is_served_when_the_webui_is_enabled(config_factory, store):
    app = build_app(config=config_factory(), store=store, args=_args())

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "glances5.js" in response.text


def test_static_directory_is_mounted(config_factory, store):
    """Asserted against the v4 bundle, which is committed in public/ --
    glances5.js does not exist until Task 3."""
    app = build_app(config=config_factory(), store=store, args=_args())

    with TestClient(app) as client:
        response = client.get("/static/glances.js")

    assert response.status_code == 200


def test_disable_webui_unregisters_both_routes(config_factory, store):
    """Assert on the route table, not on a 404: a 404 can come from anywhere,
    and a disabled WebUI must not leave the asset directory reachable."""
    app = build_app(config=config_factory(), store=store, args=_args(disable_webui=True))

    paths = {getattr(route, "path", None) for route in app.routes}
    assert "/" not in paths
    assert "/static" not in paths

    with TestClient(app) as client:
        assert client.get("/").status_code == 404
        assert client.get("/static/glances.js").status_code == 404


def test_webui_is_absent_when_no_args_namespace_is_supplied(config_factory, store):
    """build_app() without args is the embedder / unit-test path. It must not
    start serving a UI by accident."""
    app = build_app(config=config_factory(), store=store)

    paths = {getattr(route, "path", None) for route in app.routes}
    assert "/" not in paths


def test_index_requires_authentication_when_a_password_is_configured(config_factory, store):
    """UNAUTH_PATHS is {"/status", "/healthz", "/api/5/token"}, so the WebUI
    is behind auth -- v4 parity. Pinned so a future UNAUTH_PATHS edit cannot
    expose it silently."""
    config = config_factory(password=hash_password("hunter2"))
    app = build_app(config=config, store=store, args=_args())

    with TestClient(app) as client:
        assert client.get("/").status_code == 401
        assert client.get("/", headers=_basic_header("glances", "hunter2")).status_code == 200


def test_cors_policy_applies_to_the_index(config_factory, store):
    """Spec 5 claims `/` inherits the CORS wiring. A new route silently
    falling outside a middleware is how these protections rot, so verify it
    rather than assume it."""
    config = config_factory(cors_origins="https://trusted.example")
    app = build_app(config=config, store=store, args=_args())

    with TestClient(app) as client:
        allowed = client.get("/", headers={"Origin": "https://trusted.example"})
        denied = client.get("/", headers={"Origin": "https://evil.example"})

    assert allowed.headers.get("access-control-allow-origin") == "https://trusted.example"
    assert "access-control-allow-origin" not in denied.headers


def test_trusted_host_middleware_applies_to_the_index(config_factory, store):
    """TrustedHostMiddleware is the outermost middleware, so a new route
    inherits DNS-rebinding protection. Verify rather than assume."""
    config = config_factory(webui_allowed_hosts="trusted.example")
    app = build_app(config=config, store=store, args=_args())

    with TestClient(app) as client:
        assert client.get("/", headers={"Host": "evil.example"}).status_code == 400
        assert client.get("/", headers={"Host": "trusted.example"}).status_code == 200
```

**Fixture API — verified, use exactly this.** `tests/test_webserver_v5.py`
already imports `build_app`, `hash_password` and `TestClient` at module level,
and defines `_basic_header(user, password)` at line 121, so the tests above use
them unqualified. Its `config_factory` takes **keyword arguments**, one per
`[outputs]` key — `config_factory(password=..., cors_origins=...,
webui_allowed_hosts=...)` — and sets them as `GLANCES_OUTPUTS__<KEY>` env vars.
It does NOT take a sections dict. Add `import argparse` to the module if absent;
introduce no duplicate helper.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run pytest tests/test_webserver_v5.py -k "webui or index or static or applies_to_the_index" -v
```

Expected: FAIL — `/` returns 404, there is no `/static` mount.

- [ ] **Step 3: Add the CLI flag**

In `glances/main_v5.py`, beside the other server options:

```python
    parser.add_argument(
        "--disable-webui",
        action="store_true",
        help="Serve the REST API without the Web UI (requires --server).",
    )
```

and widen the `-s` help text, which currently says the server is REST-only:

```python
    parser.add_argument(
        "-s",
        "--server",
        action="store_true",
        help="Run as a REST API server (FastAPI) and serve the Web UI. "
        "Use --disable-webui for a headless REST deployment.",
    )
```

Copy the existing `-s` declaration's other keyword arguments verbatim; only `help` changes.

- [ ] **Step 4: Write the serving implementation**

At module level in `glances/webserver_v5.py`, beside the other constants (~line 65-77):

```python
# WebUI assets. `public/` holds the webpack output and is committed; the
# templates directory holds the root documents. Both are package data, not
# user-writable paths -- a UI served from a config-specified directory would
# be an arbitrary-file-read surface.
_WEBUI_ROOT = Path(__file__).parent / "outputs" / "static"
_STATIC_PATH = _WEBUI_ROOT / "public"
_TEMPLATE_PATH = _WEBUI_ROOT / "templates"
```

Add `from pathlib import Path` and, at the top of the file,
`from fastapi.responses import FileResponse` and
`from fastapi.staticfiles import StaticFiles`.

In `build_app()`, AFTER `app.include_router(build_router())` (~line 128):

```python
    if args is not None and not getattr(args, "disable_webui", False):
        _wire_webui(app)
```

and a module-level helper beside the other `_wire_*` functions:

```python
def _wire_webui(app: FastAPI) -> None:
    """Mount the WebUI assets and the root document.

    No route-collision guard is needed: the v5 router carries
    ``prefix="/api/5"``, so its dynamic ``/{plugin_name}`` handler lives at
    ``/api/5/{plugin_name}`` and cannot capture ``/`` or ``/static/*``. This
    differs from v4, where the same handler sits nearer the root.

    Both surfaces inherit the existing middleware stack unchanged:
    TrustedHost (outermost, so it sees every route) and Auth (``/`` is not in
    ``UNAUTH_PATHS``, so a configured password protects the UI as it does in
    v4). Nothing security-related is added here, and nothing may be bypassed.

    No Jinja2: v4 templates its index only to interpolate ``url_prefix`` and
    ``refresh_time``. v5 has no ``url_prefix``, and the refresh rate is
    already reachable as ``[global] refresh`` through ``/api/5/config``.
    """
    index = _TEMPLATE_PATH / "index_v5.html"
    if not _STATIC_PATH.is_dir() or not index.is_file():
        # Source checkout with no build, or a trimmed package. The REST API
        # must still come up: a missing UI is not a reason to refuse to serve
        # stats. Warn loudly enough to be actionable.
        logger.warning(
            "WebUI assets not found (%s). Serving the REST API only — run `npm run build` in %s.",
            _STATIC_PATH,
            _WEBUI_ROOT,
        )
        return

    app.mount("/static", StaticFiles(directory=_STATIC_PATH), name="static")

    @app.get("/", response_class=FileResponse, include_in_schema=False)
    async def index_page() -> FileResponse:
        return FileResponse(index, media_type="text/html")

    logger.info("Glances Web User Interface enabled at /")
```

- [ ] **Step 5: Create the root document**

Create `glances/outputs/static/templates/index_v5.html`. It mirrors `templates/index.html` minus the Jinja2 placeholders — do NOT edit the v4 template.

```html
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">

<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Glances</title>

  <link rel="icon" type="image/x-icon" href="static/favicon.ico" />
  <script src="static/glances5.js" defer></script>
</head>

<body>
  <div id="app"></div>
</body>

</html>
```

- [ ] **Step 6: Run the tests to verify they pass**

```bash
uv run pytest tests/test_webserver_v5.py -q
```

Expected: PASS, including every pre-existing test in the module.

- [ ] **Step 7: Close Task 1's deferred assertion**

```bash
uv run pytest tests/test_routes_v5.py -q
```

Expected: PASS in full now — `disable_webui` exists, so `test_args_matches_the_real_v5_argument_set` is satisfied.

- [ ] **Step 8: Verify the v4 web path is untouched**

```bash
git diff --stat HEAD -- glances/outputs/glances_restful_api.py glances/outputs/static/templates/index.html
```

Expected: empty output.

- [ ] **Step 9: Stage**

```bash
git add glances/main_v5.py glances/webserver_v5.py \
        glances/outputs/static/templates/index_v5.html \
        tests/test_webserver_v5.py
```

Do NOT commit.

---

### Task 3: The minimal v5 bundle

**Files:**
- Create: `glances/outputs/static/js/app_v5.js`
- Modify: `glances/outputs/static/webpack.config.js` (the `entry` block, lines 14-17)
- Test: `tests/test_webserver_v5.py` (append one test)

**Interfaces:**
- Consumes: `GET /api/5/all`, `GET /api/5/args` (Task 1), `GET /api/5/config`; the `/static` mount and `#app` div (Task 2).
- Produces: `glances/outputs/static/public/glances5.js` (a build artifact).

This bundle is deliberately NOT a layout. G9-2 replaces its body with the real app shell; its only job here is to prove build → serve → fetch → render end to end.

- [ ] **Step 1: Add the webpack entry**

In `glances/outputs/static/webpack.config.js`, replace the `entry` block:

```js
		entry: {
			glances: "./js/app.js",
			browser: "./js/browser.js",
			glances5: "./js/app_v5.js",
		},
```

Change nothing else in that file. The existing `output.filename` is `"[name].js"`, so the new entry lands at `public/glances5.js` with no further configuration.

- [ ] **Step 2: Write the bootstrap**

Create `glances/outputs/static/js/app_v5.js`:

```js
import { createApp } from "vue";

// Minimal v5 bootstrap. Its purpose is to prove the chain
// webpack build -> /static -> fetch -> Vue render against the v5 API.
// G9-2 replaces this body with the real application shell; it is a seed,
// not a parallel implementation.

const app = createApp({
	data() {
		return {
			version: null,
			pluginCount: null,
			refresh: null,
			error: null,
		};
	},
	async mounted() {
		try {
			const [all, args, config] = await Promise.all([
				fetch("api/5/all").then((r) => r.json()),
				fetch("api/5/args").then((r) => r.json()),
				fetch("api/5/config").then((r) => r.json()),
			]);
			this.pluginCount = Object.keys(all).length;
			this.version = all.version ? all.version.version : null;
			// The refresh rate lives in [global] refresh, not in the argument
			// namespace -- measured: v5's args carry no refresh key at all.
			this.refresh = config.global ? config.global.refresh : null;
			this.port = args.port;
		} catch (e) {
			this.error = String(e);
		}
	},
	template: `
		<main style="font-family: system-ui; padding: 2rem">
			<h1>Glances 5</h1>
			<p v-if="error">Cannot reach the Glances API: {{ error }}</p>
			<template v-else>
				<p>Version: {{ version ?? "…" }}</p>
				<p>Plugins served: {{ pluginCount ?? "…" }}</p>
				<p>Refresh: {{ refresh ?? "…" }} s</p>
				<p>The v5 web interface is under construction. The REST API is live at
					<a href="api/5/all">/api/5/all</a>.</p>
			</template>
		</main>
	`,
});

app.mount("#app");
```

- [ ] **Step 3: Build**

```bash
cd glances/outputs/static && npm install && npm run build
```

Expected: `public/glances5.js` exists, alongside `public/glances.js` and `public/browser.js`.

- [ ] **Step 4: Confirm the v4 bundles did not move**

```bash
git status --short glances/outputs/static/public/
```

Webpack 5 uses deterministic module ids in production, so adding an entry should leave the other two bundles byte-identical. If `glances.js` or `browser.js` shows as modified, **say so in the task report with the reason** — do not wave it through, and do not revert it by hand.

- [ ] **Step 5: Add the serving test**

Append to `tests/test_webserver_v5.py`:

```python
def test_the_v5_bundle_is_served(config_factory, store):
    """The bundle is a build artifact. If this fails with 404, run
    `npm run build` in glances/outputs/static/ before looking anywhere else."""
    app = build_app(config=config_factory(), store=store, args=_args())

    with TestClient(app) as client:
        response = client.get("/static/glances5.js")

    assert response.status_code == 200
    assert len(response.content) > 0
```

- [ ] **Step 6: Run the tests**

```bash
uv run pytest tests/test_webserver_v5.py -q
```

Expected: PASS.

- [ ] **Step 7: End-to-end smoke**

```bash
timeout 20 uv run python -m glances.main_v5 -s --port 61799 --quiet &
until curl -s --max-time 1 -o /dev/null http://127.0.0.1:61799/api/5/all; do sleep 0.5; done
echo "index:   $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:61799/)"
echo "bundle:  $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:61799/static/glances5.js)"
echo "args:    $(curl -s http://127.0.0.1:61799/api/5/args | head -c 120)"
wait
```

Expected: `index: 200`, `bundle: 200`, and an args JSON object with `set_password` shown as `***`.

Then repeat with `--disable-webui` and confirm `index: 404`, `bundle: 404`, while `/api/5/all` still answers 200.

Report the ACTUAL output of both runs in the task report, not a claim that they passed.

- [ ] **Step 8: Stage**

```bash
git add glances/outputs/static/webpack.config.js \
        glances/outputs/static/js/app_v5.js \
        glances/outputs/static/public/glances5.js \
        tests/test_webserver_v5.py
```

Do NOT commit. Mention in the report that `public/glances5.js` is a generated artifact, so the maintainer can split it into its own "Rebuild WebUI" commit if he prefers.

---

### Task 4: Full verification and hooks

**Files:** all files touched by Tasks 1-3.

- [ ] **Step 1: Run the full suite**

```bash
uv run pytest -q --ignore=tests/test_mcp.py
```

Expected: no new failures. If `tests/test_perf.py::test_perf_update` fails, re-run it alone (`uv run pytest tests/test_perf.py -q`) before reporting it — it is load-sensitive and exercises the v4 stack, so no v5-only change can cause it.

- [ ] **Step 2: Confirm every v4 web-path file is untouched**

```bash
git diff --stat HEAD -- \
  glances/outputs/glances_restful_api.py \
  glances/outputs/static/templates/index.html \
  glances/outputs/static/js/app.js \
  glances/outputs/static/js/browser.js \
  glances/outputs/static/js/services.js \
  glances/outputs/static/js/components/
```

Expected: empty output.

- [ ] **Step 3: Run the hooks**

```bash
git add -A
make pre-commit
```

Expected: all hooks pass. Restage and re-run if `ruff` reformats. Note that `eslint` may cover `js/app_v5.js`; fix what it reports rather than excluding the file.

- [ ] **Step 4: Stage the final state**

```bash
git add -A
git status --short
```

Do NOT commit.

- [ ] **Step 5: Release-notes items for the maintainer**

Record in the task report, do NOT write them anywhere in the repo:

- `-s` now serves the Web UI as well as the REST API; `--disable-webui` restores headless behaviour. Deliberate v4 parity (v4's `-w` did both).
- `/api/5/args` added, redacted unconditionally.
- The v5 Web UI is a placeholder in this release; plugin views arrive in G9-2+.
