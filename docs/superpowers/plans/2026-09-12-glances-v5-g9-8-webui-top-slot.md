# G9-8 — v5 WebUI top row, batch 2: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render `mpp`, `npu`, `percpu` and `quicklook` in the v5 WebUI's top row — closing the `TOP_SLOT` at 9/9 and the WebUI at 25/32 plugins — and repay the two `percpu` parity debts plus the two `quicklook` degradation steps that porting it makes live.

**Architecture:** The two TUI parity fixes come first, because both surfaces then read the same corrected behaviour (Task 1: `[percpu] max_cpu_display`; Task 2: the quicklook↔percpu interaction). The components follow in increasing order of difficulty — `mpp` + `npu` (Task 3), `percpu` (Task 4), `quicklook` with the WebUI's first bar (Task 5) — then the two cross-cutting integrations `quicklook` unlocks (Task 6: `full_quicklook` from the server args, and the cascade's two steps with their drift test). Task 7 verifies against a real server and closes.

**Tech Stack:** Vue 3.5 SFC (options API), webpack 5, `node --test` via `tests/test_webui_v5_js.py`, pytest (`uv run`), the fake-DOM probe `tests/fixtures/webui_render_probe.js`.

**Spec:** `docs/superpowers/specs/2026-09-12-glances-v5-g9-8-webui-top-slot-design.md`

**Depends on:** G9-7, committed as `01c3b9c0`.

**SDD workspace:** `.superpowers/sdd/2026-09-12-glances-v5-g9-8-webui-top-slot/` (git-ignored). Scratch files, captures and screenshots go there, never in the repository.

## Global Constraints

- **Never commit.** Every task ends with `git add`, never `git commit`. The maintainer commits personally. Never add a `Co-Authored-By` trailer. Never `git clean`, never `git checkout`/`restore` over working files, never `git stash`, **never unstage anything** (`git reset`, `git restore --staged`, `git rm --cached`). After staging, run `git status --short | grep -v '^[AM] '` and report any line it prints.
- **Never touch `NEWS.rst`.**
- **An unrelated ` M Makefile` modification may exist in the tree** (a `run-v5-server-local-conf` target). It belongs to the maintainer: never stage it, never revert it. It is the expected output of the `git status` check above.
- **TUI Python files: only these may change, and only in the task named.**
  - Task 1: `glances/plugins/percpu/model_v5.py`, `glances/plugins/percpu/render_curses_v5.py`, `tests/test_plugin_percpu_render_curses_v5.py`, `tests/test_plugin_percpu_v5.py`.
  - Task 2: `glances/plugins/percpu/render_curses_v5.py`, `glances/outputs/curses_renderer_v5.py` (the `view` key only), `tests/test_plugin_percpu_render_curses_v5.py`, `tests/test_curses_renderer_v5.py`.
  - Nothing else under `glances/plugins/*/render_curses_v5.py`, `glances/plugins/*/model_v5.py`, `glances/outputs/glances_curses_v5.py`, `glances/outputs/curses_formatters_v5.py`, `tests/test_*render_curses_v5.py`. In particular **`quicklook`, `npu` and `mpp` Python files are read-only for the whole group** — they are the specification the components mirror. If a task seems to need one, STOP and report.
- **v4 is read-only.** `glances/plugins/*/__init__.py`, `glances/outputs/glances_restful_api.py`, `js/app.js`, `js/browser.js`, `js/components/**`, `js/App.vue`, `js/services.js`, `js/store.js`, `js/filters.js`, `css/*.scss`, `templates/index.html`, `webpack.config.js`. `css/v5.css` IS in scope.
- **After every `npm run build`, the v4 bundles must be byte-identical:**
  ```bash
  for f in glances.js browser.js; do
    W=$(git hash-object glances/outputs/static/public/$f)
    C=$(git rev-parse HEAD:glances/outputs/static/public/$f)
    [ "$W" = "$C" ] && echo "$f IDENTICAL" || echo "$f DIFFERS"
  done
  ```
  Both must print IDENTICAL. If either DIFFERS, STOP and report — do not rebuild, do not `git checkout`, do not stage them.
- **Build with `npm run build` only**, from `glances/outputs/static`. Never `npm install` (`package-lock.json` is tracked); `npm ci` only if `node_modules` is missing. Every task that changes a file under `js/v5/` or `css/v5.css` rebuilds `public/glances5.js` and stages it: the render probe runs against the bundle.
- **`npx` does not work in this sandbox** (a harness wrapper intercepts it). Run eslint as `cd glances/outputs/static && node_modules/.bin/eslint js/v5 --ext .js,.vue` — expect no output, exit 0.
- **No new npm or Python dependency. No colour literal** under `js/v5/` or in a new `css/v5.css` rule — use the `--gl-*` tokens (`tests/test_webui_v5_tokens.py` enforces it).
- **Do not modify** `levels.js`, `columns.js`, `rows.js`, `layout.js`, `api.js`, `labels.js`, `format.js`, `smart_keys.js`, `CollectionBlock.vue`, or any existing `Plugin*.vue`. Importing from them is expected. `AppShell.vue` and `degrade.js` are touched in Task 6 ONLY.
- Test-suite footguns: `tests/test_plugin_sensors_v5.py` has 3 pre-existing failures on a maintainer box (its `config` fixture leaks `~/.config/glances/glances.conf`) — not yours. `tests/test_restful.py::test_050/051` are flaky by construction (a hard-coded `time.sleep(5)`); re-run them alone before believing a failure. `tests/test_mcp.py` fails when a stale server squats port 61235 (`ss -lptn 'sport = :61235'`). `make pre-commit` fails one shebang hook on `tests/test_web_list_ssl_verify.py`, pre-existing.

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `glances/plugins/percpu/model_v5.py` | publishes `max_cpu_display` from `[percpu] max_cpu_display` | 1 |
| `glances/plugins/percpu/render_curses_v5.py` | reads the cap from the payload; honours `view["quicklook_enabled"]` | 1, 2 |
| `glances/outputs/curses_renderer_v5.py` | derives `view["quicklook_enabled"]` from the instantiated plugins | 2 |
| `glances/outputs/static/css/v5.css` | `.gl-bar`, `.gl-bar-track`, `.gl-bar-fill`, `.gl-bar-label`, `.gl-bar-value` | 5 |
| `glances/outputs/static/js/v5/PluginMpp.vue`, `PluginNpu.vue` | **New** | 3 |
| `glances/outputs/static/js/v5/PluginPercpu.vue` | **New** | 4 |
| `glances/outputs/static/js/v5/PluginQuicklook.vue` | **New** — the WebUI's first bar block | 5 |
| `glances/outputs/static/js/v5/plugins/index.js` | four entries in `TOP_SLOT` order | 3, 4, 5 |
| `glances/outputs/static/js/v5/AppShell.vue` | `full_quicklook` hiding; the two quicklook cascade notches | 6 |
| `glances/outputs/static/js/v5/degrade.js` | both `notApplicable` flags removed | 6 |
| `tests/fixtures/webui_render_fixtures.js` | new payload fixtures and scenarios | 3, 4, 5, 6 |
| `tests/test_webui_v5_render.py` | new render assertions; the three registry lists grow 21 → 25 | 3, 4, 5, 6 |
| `tests/test_webui_v5_degrade_drift.py` | the `notApplicable` expectations | 6 |
| `tests/test_plugin_percpu_render_curses_v5.py` | the cap and the quicklook interaction | 1, 2 |
| `glances/outputs/static/public/glances5.js` | rebuilt | 3, 4, 5, 6 |

---

### Task 1: `percpu` honours `[percpu] max_cpu_display`

**Files:**
- Modify: `glances/plugins/percpu/model_v5.py`, `glances/plugins/percpu/render_curses_v5.py`
- Modify: `tests/test_plugin_percpu_render_curses_v5.py` (the renderer tests) and `tests/test_plugin_percpu_v5.py` (the model test) — both files exist; `tests/test_plugin_percpu.py` is the v4 suite and is read-only

**Interfaces:**
- Consumes: nothing.
- Produces: an `internal` `max_cpu_display` field on the `percpu` payload, and a renderer that reads it with `_DEFAULT_MAX_CPU_DISPLAY` as the fallback. Task 4's component reads the same field.

`[percpu] max_cpu_display` caps how many cores are listed before the rest collapse into the `CPU*` mean row. `quicklook` already reads the key (`glances/plugins/quicklook/model_v5.py:261`), publishes it (`:316`) and honours it in its renderer; `percpu` does none of the three, and says so in a `TODO(G2+)` in its renderer docstring. Follow quicklook's shape exactly — it is the precedent, and it is two lines.

- [ ] **Step 1: Read the precedent**

Read `glances/plugins/quicklook/model_v5.py` around lines 200-210 (the schema entry), 255-262 (`_read_max_cpu_display`) and 310-320 (where it lands in the payload). Note that the key lives in the **`[percpu]`** section even for quicklook — v4 parity, v4 reads the same key from the same section.

- [ ] **Step 2: Write the failing tests**

In `tests/test_plugin_percpu_render_curses_v5.py`:

```python
def test_the_core_cap_comes_from_the_payload():
    """`[percpu] max_cpu_display` caps the listed cores; the rest collapse into
    the CPU* mean row. Before this fix the renderer used its own constant and
    the config key was inert for this plugin (its TODO(G2+) said so), while
    `quicklook` honoured the same key — so two blocks disagreed on one setting.
    """
    payload = _payload_with_cores(6)
    payload["max_cpu_display"] = 2
    rows = render(payload, _SCHEMA)
    labels = [r.cells[0].text.strip() for r in rows[1:]]
    assert labels == ["CPU0", "CPU1", "CPU*"], f"got {labels!r}"


def test_an_older_server_without_the_field_falls_back_to_four():
    """A payload that predates the field must not raise: the renderer keeps its
    own constant as the fallback (same contract as quicklook's renderer)."""
    rows = render(_payload_with_cores(6), _SCHEMA)
    labels = [r.cells[0].text.strip() for r in rows[1:]]
    assert labels == ["CPU0", "CPU1", "CPU2", "CPU3", "CPU*"], f"got {labels!r}"
```

`_payload_with_cores(n)` builds a payload whose cores have **descending** `total` values (the renderer sorts by `total` descending, so core `i` gets `total = 90 - i * 10`) and every column the OS headers ask for. Write it as a module-level helper next to the file's existing fixtures, reusing whatever core-dict builder the file already has rather than inventing a second one.

For the model, assert the field is published and typed:

```python
def test_the_model_publishes_the_configured_cap():
    """The key lives in the [percpu] section (v4 parity: v4 reads
    `config.get_int_value('percpu', 'max_cpu_display', 4)`)."""
    model = PluginModel(store, config_with({"percpu": {"max_cpu_display": "2"}}))
    assert model._read_max_cpu_display() == 2
```

Put it in `tests/test_plugin_percpu_v5.py` and use that file's existing store/config fixtures — do not build a new harness. `tests/test_plugin_quicklook_v5.py` has the equivalent test for the plugin that already reads this key; follow it.

- [ ] **Step 3: Run them to verify they fail**

Run: `uv run pytest tests/test_plugin_percpu_render_curses_v5.py -q`
Expected: FAIL — `test_the_core_cap_comes_from_the_payload` lists four cores instead of two (the renderer ignores the payload field), and the model test errors on a missing method.

- [ ] **Step 4: Publish the field from the model**

In `glances/plugins/percpu/model_v5.py`, mirroring quicklook:

```python
    # `[percpu] max_cpu_display` — the cap both this plugin and quicklook
    # honour. Declared `internal`: it is configuration the renderers need,
    # not a metric (the same shape quicklook uses for `stats_list`).
    "max_cpu_display": {
        "description": "Maximum number of CPU cores displayed before the mean row ([percpu] max_cpu_display).",
        "unit": "number",
        "internal": True,
        "watched": False,
    },
```

plus the `_read_max_cpu_display()` reader (`self.config.get("percpu", "max_cpu_display", 4)`) called once in `__init__`, and the line that puts it in the published envelope. Copy quicklook's comments where they apply; do not invent a second mechanism.

- [ ] **Step 5: Read it in the renderer**

In `glances/plugins/percpu/render_curses_v5.py::render`, replace the two uses of `_DEFAULT_MAX_CPU_DISPLAY` with a value resolved from the payload:

```python
    # `[percpu] max_cpu_display`, published by the model. The constant stays as
    # the fallback for a payload that predates the field (a remote v5 server) —
    # the contract quicklook's renderer already uses.
    max_display = payload.get("max_cpu_display")
    if not isinstance(max_display, int):
        max_display = _DEFAULT_MAX_CPU_DISPLAY
```

Keep the constant and its comment. Delete only the `max_cpu_display` half of the docstring's `TODO(G2+)` — the `quicklook=enabled` half is Task 2's.

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/test_plugin_percpu_render_curses_v5.py tests/test_plugin_percpu_v5.py -q`
Expected: PASS, with every pre-existing assertion unchanged.

- [ ] **Step 7: Stage**

```bash
uv run pytest tests/test_curses_renderer_v5.py -q
git add glances/plugins/percpu/model_v5.py glances/plugins/percpu/render_curses_v5.py tests/test_plugin_percpu_render_curses_v5.py
git status --short | grep -v '^[AM] ' && echo "REPORT THE LINES ABOVE (an ` M Makefile` line is expected)" || echo "clean"
```

---

### Task 2: `percpu` drops its title, `total` column and row labels when quicklook is shown

**Files:**
- Modify: `glances/plugins/percpu/render_curses_v5.py`, `glances/outputs/curses_renderer_v5.py`
- Modify: `tests/test_plugin_percpu_render_curses_v5.py`, `tests/test_curses_renderer_v5.py`

**Interfaces:**
- Consumes: Task 1's `max_display` resolution (same function).
- Produces: `view["quicklook_enabled"]` (bool), set by `build_frame` from the instantiated plugins, and a `percpu` renderer whose signature gains `view` — `_accepts_view` detects that automatically (`curses_renderer_v5.py:1324-1335`), no registration needed. Task 4's component mirrors the same three behaviours from `/api/5/pluginslist`.

v4's `percpu` renders differently depending on whether quicklook is enabled, in three places, all gated on `self.is_disabled('quicklook')`:

| v4 | quicklook DISABLED | quicklook ENABLED |
|---|---|---|
| `glances/plugins/percpu/__init__.py:158-161` | a `CPU` title cell, and `total` inserted as the first column | neither |
| `:183-191` | each row starts with its `CPU0` / `12` label | no row label |
| `:210-211` | the mean row starts with `CPU*` | no label |

v5 implements none of it (the second half of the renderer's `TODO(G2+)`). With quicklook on — the default — quicklook already shows the per-core totals, so `percpu` stops repeating them.

- [ ] **Step 1: Write the failing renderer tests**

```python
def test_quicklook_shown_drops_the_title_the_total_column_and_the_labels():
    """v4 parity (glances/plugins/percpu/__init__.py:158,183,210): with
    quicklook on screen, percpu does not repeat what quicklook already shows.
    """
    rows = render(_payload_with_cores(2), _SCHEMA, view={"quicklook_enabled": True})
    header = " ".join(c.text for c in rows[0].cells)
    assert "CPU" not in header, f"no title cell: {header!r}"
    assert "total" not in header, f"no total column: {header!r}"
    assert not any(r.cells[0].text.strip().startswith("CPU") for r in rows[1:]), (
        f"no row labels: {[r.cells[0].text for r in rows[1:]]!r}"
    )


def test_quicklook_absent_keeps_the_title_the_total_column_and_the_labels():
    """The other half of the same v4 branch — and the default for every
    caller that passes no view at all."""
    for view in ({"quicklook_enabled": False}, None):
        rows = render(_payload_with_cores(2), _SCHEMA, view=view)
        header = " ".join(c.text for c in rows[0].cells)
        assert "CPU" in header, f"view={view!r}: {header!r}"
        assert "total" in header, f"view={view!r}: {header!r}"
        assert rows[1].cells[0].text.strip() == "CPU0", f"view={view!r}: {rows[1].cells[0].text!r}"
```

And in `tests/test_curses_renderer_v5.py`, a test that `build_frame` derives the flag from the instantiated plugins rather than from what has published:

```python
def test_build_frame_tells_percpu_whether_quicklook_is_instantiated():
    """The flag comes from `fields_by_plugin` — the plugins that EXIST — not
    from the store, so percpu does not flip its columns for one cycle while
    quicklook waits for its first payload.
    """
    # quicklook instantiated but not yet published:
    frame = build_frame({"percpu": _percpu_payload()}, {"percpu": _percpu_fields(), "quicklook": {}})
    percpu_block = next(b for b in frame.top if b.name == "percpu")
    assert "total" not in " ".join(c.text for c in percpu_block.rows[0].cells)
    # quicklook not instantiated at all:
    frame = build_frame({"percpu": _percpu_payload()}, {"percpu": _percpu_fields()})
    percpu_block = next(b for b in frame.top if b.name == "percpu")
    assert "total" in " ".join(c.text for c in percpu_block.rows[0].cells)
```

Use the helpers that file already has for building a frame; if its `build_frame` calls take more arguments, follow its existing call sites rather than the sketch above.

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_plugin_percpu_render_curses_v5.py tests/test_curses_renderer_v5.py -q`
Expected: FAIL — the renderer's signature has no `view` (a `TypeError`), and the painter sets no such key.

- [ ] **Step 3: Give the renderer the `view` parameter and the three branches**

```python
def render(
    payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]], view: dict[str, Any] | None = None
) -> list[Row]:
    """Render the percpu plugin's TUI block — mirrors v4 ``percpu.msg_curse``.

    When quicklook is on screen it already shows the per-core totals, so v4
    drops this block's title, its ``total`` column and its row labels
    (``glances/plugins/percpu/__init__.py:158,183,210``, all gated on
    ``is_disabled('quicklook')``). ``view["quicklook_enabled"]`` carries that
    state; a caller that passes no view gets the standalone shape.
    """
    standalone = not (view or {}).get("quicklook_enabled")
    headers = ["total", *_os_headers()] if standalone else list(_os_headers())
```

The title cell and the row-label cells become conditional on `standalone`. Keep `_LABEL_WIDTH` padding only where a label is actually drawn — an empty 4-char cell would leave v4's column gap where v4 has none.

- [ ] **Step 4: Derive the flag in `build_frame`**

In `glances/outputs/curses_renderer_v5.py::build_frame`, before the per-plugin render loop:

```python
    # `percpu` renders differently when quicklook is on screen (v4 parity).
    # Derived from the INSTANTIATED plugins, not from the store: a quicklook
    # that has not published yet still exists, and keying off the store would
    # make percpu flip its columns for one cycle at startup. Same notion the
    # WebUI reads from /api/5/pluginslist.
    view = {**(view or {}), "quicklook_enabled": "quicklook" in fields_by_plugin}
```

Match the function's existing parameter names and the way it already threads `view` to the renderers; do not change any other key.

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/test_plugin_percpu_render_curses_v5.py tests/test_curses_renderer_v5.py tests/test_curses_v5.py -q`
Expected: PASS. A pre-existing painter test that asserted percpu's `total` column with quicklook instantiated will now legitimately fail — if one does, report it with its name and output rather than editing it; the controller decides.

- [ ] **Step 6: Stage**

```bash
git add glances/plugins/percpu/render_curses_v5.py glances/outputs/curses_renderer_v5.py \
        tests/test_plugin_percpu_render_curses_v5.py tests/test_curses_renderer_v5.py
git status --short | grep -v '^[AM] ' && echo "REPORT THE LINES ABOVE (an ` M Makefile` line is expected)" || echo "clean"
```

---

### Task 3: `mpp` and `npu` — the two small blocks

**Files:**
- Create: `glances/outputs/static/js/v5/PluginMpp.vue`, `glances/outputs/static/js/v5/PluginNpu.vue`
- Modify: `glances/outputs/static/js/v5/plugins/index.js`
- Modify: `tests/fixtures/webui_render_fixtures.js`, `tests/test_webui_v5_render.py`
- Rebuild: `glances/outputs/static/public/glances5.js`

**Interfaces:**
- Consumes: `CollectionBlock.vue` (G9-7) — props `payload`, `error`, `title`, `hidden`; slots `head` (the whole `<tr>` of `<th>`s; omit it and no `<thead>` is rendered) and `body` (one or more `<tbody>`).
- Produces: the registry entries `{ name: "npu", component: PluginNpu, slot: "top", spec: { shape: "collection", required: ["npu_id"] } }` and `{ name: "mpp", component: PluginMpp, slot: "top", spec: { shape: "collection", required: ["engine_id"] } }`.

Both mirror their TUI renderers, which are **read-only** references for this whole group: `glances/plugins/mpp/render_curses_v5.py` (58 lines) and `glances/plugins/npu/render_curses_v5.py` (106 lines). Read both before writing anything.

Registry order is `TOP_SLOT` order (`glances/outputs/curses_renderer_v5.py:61`): `quicklook, cpu, percpu, npu, mpp, gpu, mem, memswap, load`. After this task the rendered top row is `cpu, npu, mpp, gpu, mem, memswap, load` — `npu` and `mpp` go between `cpu` and `gpu`.

- [ ] **Step 1: Write the fixtures**

In `tests/fixtures/webui_render_fixtures.js`, before `ALL_FIXTURES`:

```js
// `mpp` — one engine per branch of mpp/render_curses_v5.py:32-57: a load with
// sessions, a load with ZERO sessions (v4 omits the session cell entirely),
// and a null load rendered "N/A". Only the load is coloured.
const MPP_FIXTURE = {
	_key: "engine_id",
	data: [
		{ engine_id: "rkvenc", name: "RKVENC", type: "enc", load: 24.8, sessions: 2 },
		{ engine_id: "jpegd", name: "JPEGD", type: "jpeg", load: 0.0, sessions: 0 },
		{ engine_id: "rkvdec", name: "RKVDEC", type: "dec", load: null, sessions: 0 },
	],
	_levels: {
		rkvenc: { load: { level: "careful", prominent: false } },
		jpegd: { load: { level: "ok", prominent: false } },
	},
};

// `npu` — TWO devices on purpose: the renderer shows the FIRST only (v4
// parity, npu/render_curses_v5.py:40-43), so a component that rendered both
// must fail. The first has a load; the second would show the freq fallback,
// which the dedicated scenario below exercises instead.
const NPU_FIXTURE = {
	_key: "npu_id",
	data: [
		{
			npu_id: "npu0", name: "Intel NPU 3720 (very long name that gets cut)", load: 45.0,
			freq: 80.0, mem: null, freq_current: 1000000000, freq_max: 2000000000, temperature: 55.0, power: null,
		},
		{ npu_id: "npu1", name: "Second NPU", load: 10.0, freq: 20.0, mem: 5.0, freq_current: 1, freq_max: 2, temperature: 30.0 },
	],
	_levels: { npu0: { load: { level: "careful", prominent: false }, temperature: { level: "ok", prominent: false } } },
};

// Load absent -> the percentage cell falls back to the FREQUENCY percentage
// (npu/render_curses_v5.py:47-54), coloured from the `freq` level.
const NPU_NO_LOAD = {
	_key: "npu_id",
	data: [{ ...NPU_FIXTURE.data[0], load: null, freq: 80.0 }],
	_levels: { npu0: { freq: { level: "warning", prominent: false } } },
};
```

and in `ALL_FIXTURES`:

```js
	mpp: { mpp: MPP_FIXTURE },
	"mpp-empty": { mpp: { _key: "engine_id", data: [], _levels: {} } },
	npu: { npu: NPU_FIXTURE },
	"npu-no-load": { npu: NPU_NO_LOAD },
	"npu-empty": { npu: { _key: "npu_id", data: [], _levels: {} } },
	// Same payload as `npu`; only ARGS_FIXTURES differs (--fahrenheit).
	"npu-fahrenheit": { npu: NPU_FIXTURE },
```

`npu-fahrenheit` needs an `ARGS_FIXTURES` entry setting `fahrenheit: true` — follow the existing `sensors-fahrenheit` scenario's entry exactly.

- [ ] **Step 2: Write the failing render tests**

Append to `tests/test_webui_v5_render.py`:

```python
# -------------------------------------------------------- mpp (G9-8 Task 3)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_mpp_renders_one_row_per_engine():
    """mpp/render_curses_v5.py:38-57 — name + type, the load as a percentage
    or N/A, and the session cell ONLY when the count is non-zero (v4 omits it
    entirely at zero, it does not render "0 sess").
    """
    payload = _run_render_probe("mpp")
    texts = [cell["text"] for cell in payload["pluginTableCells"]["mpp"]]
    assert texts == [
        "RKVENC enc", "24.8%", "2 sess",
        "JPEGD jpeg", "0.0%",
        "RKVDEC dec", "N/A",
    ], f"got {texts!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_mpp_colours_only_the_load():
    payload = _run_render_probe("mpp")
    spans = [cell["value"] for cell in payload["pluginTableCells"]["mpp"]]
    assert "gl-level-careful" in (spans[1] or ""), f"got {spans!r}"
    assert not any("gl-level-" in (s or "") for s in (spans[0], spans[2])), f"only the load: {spans!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_mpp_collection_is_hidden():
    payload = _run_render_probe("mpp-empty")
    assert payload["pluginHidden"].get("mpp") is True, f"got {payload['pluginHidden']!r}"


# -------------------------------------------------------- npu (G9-8 Task 3)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_npu_renders_the_first_device_only():
    """v4 parity (npu/render_curses_v5.py:40-43): the block shows ONE NPU, the
    first, whatever the payload carries. The fixture holds two."""
    text = _run_render_probe("npu")["pluginText"]["npu"]
    assert "Second NPU" not in text, f"only the first NPU may render: {text!r}"
    assert "45" in text and "1.0G/2.0GHz" in text, f"got {text!r}"
    assert "mem:" in text and "N/A" in text, f"a null mem renders N/A: {text!r}"
    assert "temperature:" in text and "55C" in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_npu_truncates_the_name_to_the_tui_width():
    """`name[:17]` in the TUI (_HEADER_MAX); the browser caps the cell and
    keeps the full text in `title`."""
    cells = _run_render_probe("npu")["pluginNameCells"]["npu"]
    assert cells and cells[0]["title"].startswith("Intel NPU 3720"), f"got {cells!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_npu_without_a_load_shows_the_frequency_percentage():
    """npu/render_curses_v5.py:47-54 — no load, so the cell shows the FREQ
    percentage, coloured from the `freq` level rather than the `load` one."""
    payload = _run_render_probe("npu-no-load")
    assert "80" in payload["pluginText"]["npu"], f"got {payload['pluginText']['npu']!r}"
    assert any("gl-level-warning" in (c or "") for c in payload["pluginValueClasses"]["npu"]), (
        f"the freq tier must colour the cell: {payload['pluginValueClasses']['npu']!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_npu_honours_fahrenheit():
    """Same payload as `npu`, `--fahrenheit` on the server: 55C -> 131F."""
    text = _run_render_probe("npu-fahrenheit")["pluginText"]["npu"]
    assert "131F" in text, f"got {text!r}"
    assert "55C" not in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_npu_collection_is_hidden():
    payload = _run_render_probe("npu-empty")
    assert payload["pluginHidden"].get("npu") is True, f"got {payload['pluginHidden']!r}"
```

- [ ] **Step 3: Run them to verify they fail**

Run: `uv run pytest tests/test_webui_v5_render.py -q -k "mpp or npu"`
Expected: FAIL — `KeyError: 'mpp'` / `'npu'`: neither component is registered.

- [ ] **Step 4: Write `PluginMpp.vue`**

A collection on the shell, title `MPP`, **no `#head` slot** (the TUI's first row is the title alone, with no column labels — same shape as `ports`, so no `<thead>`):

- rows: every dict item, payload order, no sorting (the TUI does not sort).
- cell 1: `` `${name} ${type}` `` — the TUI packs `{:<8}{:>5}` into ONE cell, so one `<td>` here too; keep the raw strings, the padding is a terminal concern.
- cell 2 (`gl-num`): `formatPercent`-style `NN.N%` from `load`, or `N/A` when `load == null`. Use the existing `format.js` helper that produces one decimal (read the file and pick the one the TUI's `{:>6.1f}%` matches — do not add a formatter). Coloured with `cellClassFor(payload, item, "load")`.
- cell 3 (`gl-num`): `` `${sessions} sess` `` **only when `sessions` is truthy** — v4 omits the cell at zero. A `<td>` that renders an empty string is NOT the same thing; use `v-if` on the cell.
- `:hidden="!!payload && rows.length === 0"`, `title="MPP"`, and the two deliberately-unused props (`serverArgs`, `degrade`) with the comments every sibling component carries.

A three-cell row whose third cell is conditional makes the `<tr>`s ragged. That is what the TUI does; do not pad it with an empty cell.

- [ ] **Step 5: Write `PluginNpu.vue`**

The payload is a collection but the block is a **four-line scalar view of its first item**. Use the shell with no `#head` slot and one `<tbody>`, or the `.gl-stat-grid` + `<dl>` shape — pick the one whose rendered shape matches the TUI's four rows, and say in your report which and why. The four rows:

1. the name, truncated with `.gl-name .gl-truncate` (cap `17ch`, the TUI's `_HEADER_MAX`) and the full text in `title`;
2. the load percentage as `NNN%` — or, when `load` is null, the **frequency** percentage, coloured from the `freq` level instead of the `load` one (`N/A` when both are null) — then the frequency range `current/maxHz` right-aligned, each side through an auto-Hz formatter;
3. `mem:` and its percentage, or `N/A`;
4. `temperature:` and its value, `F` with `--fahrenheit` (read `serverArgs.fahrenheit` and convert with the same helper `PluginSensors.vue` uses — do not write a second conversion), `C` otherwise, `N/A` when null.

The Hz formatter: the TUI's `_auto_hz` divides by 1e9/1e6/1e3 and prints `1.0G` / `1.0M` / `1.0K`, with `?` when the value is not a number. `format.js` has no such function; add one there only if no existing export fits — check `formatAutoUnit` first (it is BINARY, 1024-based, so it almost certainly does not fit) and say in your report which you chose and why. If you add one, it needs its own `tests/js/format.test.mjs` cases including the `?` path.

Colour comes from `_levels[npu_id][field]` — use `cellClassFor(payload, item, field)` with the item, so the helper resolves the key itself.

- [ ] **Step 6: Register both**

Two entries in `glances/outputs/static/js/v5/plugins/index.js`, in `TOP_SLOT` order: `npu` then `mpp`, both after `cpu` and before `gpu`.

Then extend the three hardcoded registry lists in `tests/test_webui_v5_render.py` — purely additively, nothing weakened:
`test_an_unreadable_pluginslist_renders_the_whole_registry` (the name list), `test_the_registry_renders_every_registered_plugin`, and `test_cross_cutting_props_do_not_leak_into_the_dom_as_attributes` (a count: 21 → 23). Also add both names to `test_a_collection_keeps_its_title_heading_while_loading`, and to `test_a_loaded_collection_puts_its_title_in_the_header_row` **only if** the component you wrote renders a header row — if it does not (no `#head` slot), assert the absence the way the `ports` case does, in the same test.

- [ ] **Step 7: Rebuild, run, stage**

```bash
cd glances/outputs/static && npm run build && node_modules/.bin/eslint js/v5 --ext .js,.vue; cd -
uv run pytest tests/test_webui_v5_render.py tests/test_webui_v5_tokens.py tests/test_webui_v5_js.py -q
```
Expected: green, including `test_every_slot_orders_its_plugins_like_the_tui` (it reads the real `TOP_SLOT`). Then the v4 bundle identity check, then:
```bash
git add glances/outputs/static/js/v5/PluginMpp.vue glances/outputs/static/js/v5/PluginNpu.vue \
        glances/outputs/static/js/v5/plugins/index.js glances/outputs/static/public/glances5.js \
        tests/fixtures/webui_render_fixtures.js tests/test_webui_v5_render.py
git status --short | grep -v '^[AM] ' && echo "REPORT THE LINES ABOVE (an ` M Makefile` line is expected)" || echo "clean"
```
Add `glances/outputs/static/js/v5/format.js` and `tests/js/format.test.mjs` to that list if Step 5 added a formatter.

---

### Task 4: `percpu` — the transposed grid

**Files:**
- Create: `glances/outputs/static/js/v5/PluginPercpu.vue`
- Modify: `glances/outputs/static/js/v5/plugins/index.js`
- Modify: `tests/fixtures/webui_render_fixtures.js`, `tests/test_webui_v5_render.py`
- Rebuild: `glances/outputs/static/public/glances5.js`

**Interfaces:**
- Consumes: `CollectionBlock.vue`; Task 1's `max_cpu_display` payload field; Task 2's three conditional behaviours.
- Produces: the registry entry `{ name: "percpu", component: PluginPercpu, slot: "top", spec: { shape: "collection", required: ["cpu_number"] } }`.

The specification is `glances/plugins/percpu/render_curses_v5.py` as Tasks 1 and 2 leave it — read it after those tasks, not before.

- [ ] **Step 1: Write the fixtures**

```js
// `percpu` — six cores so the cap bites, with DESCENDING totals so the
// renderer's sort (by `total`, descending) is observable, plus the full set of
// Linux columns the grid shows. `max_cpu_display` is the field Task 1 added.
const PERCPU_FIXTURE = {
	_key: "cpu_number",
	max_cpu_display: 4,
	data: [0, 1, 2, 3, 4, 5].map((n) => ({
		cpu_number: n,
		total: 90 - n * 10,
		user: 50 - n * 5, system: 20 - n * 2, idle: 10 + n * 10, iowait: 1, irq: 0,
		softirq: 0, nice: 0, steal: 0, guest: 0, guest_nice: 0,
	})),
	_levels: {},
};
```

Scenarios: `percpu` (the fixture as-is, with `quicklook` absent from that scenario's `pluginslist` so the block renders standalone), `percpu-with-quicklook` (the same payload, with `quicklook` present in `pluginslist`), `percpu-cap-2` (`{ ...PERCPU_FIXTURE, max_cpu_display: 2 }`), and `percpu-empty`.

The `pluginslist` half matters: `PLUGINSLIST_FIXTURES` is how a scenario says which plugins the server instantiated, and Task 2's behaviour keys off exactly that. Read how `gpu-disabled` builds its list and follow it.

- [ ] **Step 2: Write the failing render tests**

```python
# ----------------------------------------------------- percpu (G9-8 Task 4)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_percpu_renders_the_transposed_grid_standalone():
    """percpu/render_curses_v5.py — columns are stats, rows are cores, sorted
    by `total` descending. Standalone (no quicklook instantiated) the block
    keeps its CPU title, its `total` column and its row labels.
    """
    payload = _run_render_probe("percpu")
    assert payload["pluginColumnHeaders"]["percpu"][:2] == ["CPU", "total"], (
        f"got {payload['pluginColumnHeaders']['percpu']!r}"
    )
    names = [cell["text"] for cell in payload["pluginNameCells"]["percpu"]]
    assert names == ["CPU0", "CPU1", "CPU2", "CPU3", "CPU*"], f"got {names!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_percpu_drops_title_total_and_labels_when_quicklook_is_instantiated():
    """v4 parity, mirrored from the TUI (Task 2): quicklook already shows the
    per-core totals, so percpu stops repeating them. The WebUI learns the
    state from /api/5/pluginslist, the same notion build_frame derives from
    the instantiated plugins.
    """
    payload = _run_render_probe("percpu-with-quicklook")
    headers = payload["pluginColumnHeaders"]["percpu"]
    assert "CPU" not in headers and "total" not in headers, f"got {headers!r}"
    assert "percpu" not in payload["pluginNameCells"], f"no row labels: {payload['pluginNameCells'].get('percpu')!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_percpu_honours_the_configured_core_cap():
    """The test that makes `[percpu] max_cpu_display` non-inert in the browser:
    with a cap of 2, four cores collapse into the mean row."""
    payload = _run_render_probe("percpu-cap-2")
    names = [cell["text"] for cell in payload["pluginNameCells"]["percpu"]]
    assert names == ["CPU0", "CPU1", "CPU*"], f"got {names!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_percpu_never_colours_a_cell():
    """v5 percpu publishes no field-level alert (its model docstring says so);
    the system-wide `cpu` plugin is the source of CPU alerts."""
    payload = _run_render_probe("percpu")
    spans = [cell["value"] for cell in payload["pluginTableCells"]["percpu"]]
    assert not any("gl-level-" in (s or "") for s in spans), f"got {spans!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_percpu_collection_is_hidden():
    payload = _run_render_probe("percpu-empty")
    assert payload["pluginHidden"].get("percpu") is True, f"got {payload['pluginHidden']!r}"
```

- [ ] **Step 3: Run them to verify they fail**

Run: `uv run pytest tests/test_webui_v5_render.py -q -k percpu`
Expected: FAIL — the component is not registered.

- [ ] **Step 4: Write `PluginPercpu.vue`**

On the shell, title `CPU`, with a `#head` slot whose `<th>`s are: the title cell and `total` **only when standalone**, then the OS-specific stat columns. The columns the TUI computes from `sys.platform` cannot be computed in the browser, so take them from the payload: the union of the numeric fields the first item actually carries, in the schema's own order (`labels`/`/api/5/all/info` gives you that order — the same source every other component labels columns from). Do NOT hardcode a platform list, and do not reorder.

The body: the cores sorted by `total` descending, the first `max_cpu_display` of them (falling back to `4` when the field is absent, like the renderer), then a mean row labelled `CPU*` averaging **only the cores that did not fit** — the displayed ones already have their own row (the TUI's comment cites issue #3687 for exactly this). Row labels (`CPU0`, `CPU*`) are rendered only when standalone.

`standalone` comes from the instantiated plugin list: `quicklook` absent → standalone. `AppShell` already fetches `/api/5/pluginslist` and filters the registry with it; pass what the component needs as a prop rather than re-fetching, and keep the prop name explicit (e.g. `serverPlugins`). If that means touching `AppShell.vue`, STOP and report — `AppShell.vue` is Task 6's file, and the controller will decide whether to move the prop there or to let this task add it.

Percentages use the existing one-decimal formatter; no cell is ever tier-coloured.

- [ ] **Step 5: Register it, extend the lists**

`percpu` goes between `cpu` and `npu` in the registry. Extend the three hardcoded registry lists (count 23 → 24) and the two collection title guards, as in Task 3.

- [ ] **Step 6: Rebuild, run, stage**

```bash
cd glances/outputs/static && npm run build && node_modules/.bin/eslint js/v5 --ext .js,.vue; cd -
uv run pytest tests/test_webui_v5_render.py tests/test_webui_v5_tokens.py -q
```
Expected: green. Then the v4 bundle identity check, then stage the component, the registry, the bundle, the fixtures and the test file.

---

### Task 5: `quicklook` — the WebUI's first bar block

**Files:**
- Create: `glances/outputs/static/js/v5/PluginQuicklook.vue`
- Modify: `glances/outputs/static/css/v5.css` (the bar rules)
- Modify: `glances/outputs/static/js/v5/plugins/index.js`
- Modify: `tests/fixtures/webui_render_fixtures.js`, `tests/test_webui_v5_render.py`
- Rebuild: `glances/outputs/static/public/glances5.js`

**Interfaces:**
- Consumes: nothing from earlier tasks except the `max_cpu_display` field (which `quicklook`'s own model has always published).
- Produces: the `.gl-bar*` CSS contract and the registry entry `{ name: "quicklook", component: PluginQuicklook, slot: "top", spec: { shape: "scalar", required: [] } }`. Task 6 consumes the component's `degrade` handling.

The specification is `glances/plugins/quicklook/render_curses_v5.py` (read-only, 224 lines). Read it in full first — it has four parts (header, bar selection, bar row, per-core rows) and every one of them has a fallback branch for an older payload.

- [ ] **Step 1: Add the bar CSS**

In `glances/outputs/static/css/v5.css`, after the `.gl-num` block:

```css
/* A bar row: the TUI's `CPU  [||||      45.0%]` drawn with the browser's
 * means (G9-8 D1 — not the terminal's characters, not a sparkline). Three
 * parts on one line: the TUI's 4-char label, a track that takes the rest of
 * the width, and the value. Global like .gl-table: any later bar block reuses
 * this shape instead of inventing a second one. */
.gl-bar {
  display: grid;
  grid-template-columns: 4ch 1fr auto;
  align-items: center;
  gap: var(--gl-gap);
}

.gl-bar-track {
  background: var(--gl-border);
  height: 0.6em;
  overflow: hidden;
}

/* `currentColor` is load-bearing: the tier class (.gl-level-*) sets `color`,
 * so the fill takes the payload's tier with no second token and no colour
 * literal. A fill with no tier class inherits the body colour, which is what
 * an undecorated value should look like. */
.gl-bar-fill {
  background: currentColor;
  height: 100%;
}
```

Add no colour literal: `tests/test_webui_v5_tokens.py` fails on one, and the tier comes from the class.

- [ ] **Step 2: Write the fixtures**

```js
// `quicklook` — the scalar payload: the bars `stats_list` selects and in which
// order, the CPU name/frequency header, and the per-core list with the mean of
// the cores the cap hides (`percpu_other`, published by the model).
const QUICKLOOK_FIXTURE = {
	cpu: 45.0,
	mem: 71.2,
	swap: 12.0,
	load: 18.0,
	cpu_name: "Intel Core i7-9750H",
	cpu_hz_current: 2600000000,
	cpu_hz: 4500000000,
	cpu_log_core: 12,
	cpu_phys_core: 6,
	stats_list: ["cpu", "mem", "load"],
	bar_char: "|",
	max_cpu_display: 2,
	percpu: [
		{ cpu_number: 0, total: 90.0, level: "critical" },
		{ cpu_number: 1, total: 40.0, level: "careful" },
		{ cpu_number: 2, total: 10.0, level: "ok" },
		{ cpu_number: 3, total: 20.0, level: "ok" },
	],
	percpu_other: { total: 15.0, level: "ok" },
	_levels: {
		cpu: { level: "careful", prominent: true },
		mem: { level: "warning", prominent: false },
		load: { level: "ok", prominent: false },
	},
};
```

Scenarios: `quicklook` (as-is); `quicklook-percpu` (same payload, with `ARGS_FIXTURES` setting `percpu: true` — the per-core view is gated on the server's `--percpu`, see Step 4); `quicklook-gpu` (`stats_list: ["cpu", "mem", "gpu_mem", "gpu_proc"]` plus `gpu_mem`/`gpu_proc` values, to pin the two renamed labels); `quicklook-no-freq` (`cpu_hz_current: null` — the header disappears entirely); `quicklook-empty` (`{}`).

- [ ] **Step 3: Write the failing render tests**

```python
# -------------------------------------------------- quicklook (G9-8 Task 5)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_quicklook_renders_one_bar_per_stats_list_entry_in_order():
    """`[quicklook] list` drives the selection AND the order
    (quicklook/render_curses_v5.py:161-175). The fixture asks for cpu, mem,
    load — `swap` is in the payload and must NOT render.
    """
    payload = _run_render_probe("quicklook")
    labels = payload["barLabels"]["quicklook"]
    assert labels == ["CPU", "MEM", "LOAD"], f"got {labels!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_bars_width_is_its_percentage_and_its_colour_is_its_tier():
    """D1: the fill's width IS the value, and the tier reaches it as a class
    (the CSS turns that into `background: currentColor`). A bar drawn at a
    fixed width, or coloured from the aggregate instead of its own field,
    would pass a text-only assertion.
    """
    payload = _run_render_probe("quicklook")
    bars = payload["bars"]["quicklook"]
    assert bars[0]["width"] == "45%", f"got {bars[0]!r}"
    assert "gl-level-careful" in bars[0]["fillClass"], f"got {bars[0]!r}"
    assert "gl-level-warning" in bars[1]["fillClass"], f"mem is warning: {bars[1]!r}"
    assert bars[0]["role"] == "progressbar" and bars[0]["valuenow"] == "45", (
        f"a bar is a progress indicator for assistive tech: {bars[0]!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_prominent_bar_value_still_renders_its_badge():
    """`cpu` is prominent in the fixture: the VALUE keeps the badge every other
    prominent value in the UI renders, independently of the fill's colour."""
    payload = _run_render_probe("quicklook")
    assert "gl-prominent" in payload["bars"]["quicklook"][0]["valueClass"], (
        f"got {payload['bars']['quicklook'][0]!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_quicklook_renders_its_cpu_name_and_frequency_header():
    text = _run_render_probe("quicklook")["pluginText"]["quicklook"]
    assert "Intel Core i7-9750H" in text, f"got {text!r}"
    assert "2.60/4.50GHz" in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_quicklook_without_a_current_frequency_has_no_header():
    """`cur is None -> return None` (render_curses_v5.py:115-117): no header
    row at all, not an empty one."""
    text = _run_render_probe("quicklook-no-freq")["pluginText"]["quicklook"]
    assert "GHz" not in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_quicklook_per_core_replaces_the_cpu_bar_and_caps_with_a_mean_row():
    """With the server's --percpu, the `cpu` bar is REPLACED by one bar per
    core (render_curses_v5.py:168-170), capped by max_cpu_display (2 here),
    sorted by total descending, plus the CPU* row whose value comes from
    `percpu_other` — not from the displayed cores.
    """
    payload = _run_render_probe("quicklook-percpu")
    labels = payload["barLabels"]["quicklook"]
    assert labels == ["CPU0", "CPU1", "CPU*", "MEM", "LOAD"], f"got {labels!r}"
    bars = {b["label"]: b for b in payload["bars"]["quicklook"]}
    assert bars["CPU0"]["width"] == "90%", f"got {bars['CPU0']!r}"
    assert "gl-level-critical" in bars["CPU0"]["fillClass"], (
        f"each core takes ITS OWN level, not the aggregate: {bars['CPU0']!r}"
    )
    assert bars["CPU*"]["width"] == "15%", f"the mean of the HIDDEN cores: {bars['CPU*']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_quicklook_renames_the_two_gpu_bar_labels():
    """`gpu_mem` -> GMEM and `gpu_proc` -> GPU (_BAR_LABEL): the raw upper-cased
    keys are 7 chars and break the TUI's grid, so both surfaces use the short
    form."""
    labels = _run_render_probe("quicklook-gpu")["barLabels"]["quicklook"]
    assert labels == ["CPU", "MEM", "GMEM", "GPU"], f"got {labels!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_quicklook_payload_is_hidden():
    payload = _run_render_probe("quicklook-empty")
    assert payload["pluginHidden"].get("quicklook") is True, f"got {payload['pluginHidden']!r}"
```

- [ ] **Step 4: Extend the probe with `bars` and `barLabels`**

`tests/fixtures/webui_render_probe.js` has no way to see a bar. Add two fields to `collect()`'s result, next to `pluginTableCells`:

```js
		// Each `.gl-bar` row of a plugin: the label, the fill's inline width and
		// class list, the value's class list, and the ARIA attributes. The fill's
		// WIDTH is the only place a bar's value reaches the DOM, so a test cannot
		// see a wrong bar any other way.
		bars: {},
		// The ordered bar labels, keyed by data-plugin -- `[quicklook] list`
		// drives both the selection and the order, and this is what pins it.
		barLabels: {},
```

and, in the per-article block, collect every element whose class list contains `gl-bar`, reading from each: the `.gl-bar-label` text, the `.gl-bar-fill`'s `style.width` and `className`, the `.gl-bar-value`'s `className`, and the track's `role` / `aria-valuenow`. The probe's `FakeElement.style` is a plain object (`webui_render_probe.js:109`), so Vue's `:style="{ width: pct + '%' }"` lands on it as `style.width` and is readable as-is — no probe change needed for that. Read the attribute helpers the probe already has for the ARIA values rather than adding a second accessor.

- [ ] **Step 5: Write `PluginQuicklook.vue`**

Scalar, so no `CollectionBlock` — its own `<article class="gl-plugin" v-show="!hidden" aria-label="QUICKLOOK">`, with the loading/error shape every scalar component uses (`PluginLoad.vue` is the reference). Then:

1. **The header row** — `cpu_name` and the frequency, mirroring `_header_row`: `{cur}/{max}GHz` with two decimals in GHz, or `{cur}GHz` when `cpu_hz` is null; the whole row absent when `cpu_hz_current` is null. Under `degrade.top.quicklook_freq_only` (Task 6) the name is replaced by the literal `Frequency` — that is what the TUI does, it does not merely hide the name.
2. **The bars** — `payload.stats_list` or, when absent, the fallback order `["cpu", "mem", "load", "gpu_mem", "gpu_proc"]`; a key whose payload value is null or missing is skipped; the label is the upper-cased key except `gpu_mem` → `GMEM` and `gpu_proc` → `GPU`.
3. **The per-core replacement** — when `serverArgs.percpu` is true AND `payload.percpu` is an array, the `cpu` entry renders the per-core bars instead of the aggregate one: the cores sorted by `total` descending **only when** there are more than `max_cpu_display` of them (the TUI keeps payload order otherwise), the first `max_cpu_display` shown, each labelled `CPU{n}` for `n < 10` and right-aligned in 4 otherwise, each coloured from its OWN `level` (falling back to the aggregate `cpu` tier when a core carries none), then a `CPU*` bar from `percpu_other.total` and `percpu_other.level`. When the payload has no `percpu_other`, average the overflow cores — the ones NOT displayed — and use the aggregate tier.
4. **Markup per bar**: the three-part `.gl-bar` grid from Step 1; the fill carries `:style="{ width: pct + '%' }"` and the tier class; the value carries the tier class the way every other value cell does; the track carries `role="progressbar"`, `aria-valuenow`, `aria-valuemin="0"`, `aria-valuemax="100"` and an `aria-label` naming the bar.

`bar_char` and `percent_char` are terminal concerns and are deliberately NOT read — say so in a comment so the next reader does not "fix" it.

Percentages: the TUI's `Bar` prints one decimal; use the existing one-decimal formatter from `format.js` for the value text, and the raw number for the width.

- [ ] **Step 5b: Register it**

`quicklook` is FIRST in `TOP_SLOT`, before `cpu`. Extend the three hardcoded registry lists (24 → 25) and `test_a_scalar_plugin_keeps_its_title_while_loading` with `("quicklook", "QUICKLOOK")` — check what the component actually renders as its loading title and use that string.

- [ ] **Step 6: Rebuild, run, stage**

```bash
cd glances/outputs/static && npm run build && node_modules/.bin/eslint js/v5 --ext .js,.vue; cd -
uv run pytest tests/test_webui_v5_render.py tests/test_webui_v5_tokens.py -q
```
**`tests/test_webui_v5_degrade_drift.py` is expected to FAIL from now on** — it is written to go red the moment `quicklook` renders while its two cascade steps are still flagged `notApplicable`. Do not touch it; Task 6 owns it. Say in your report that you saw it fail and left it.

Then the v4 bundle identity check, then stage the component, the CSS, the registry, the bundle, the probe, the fixtures and the render test file.

---

### Task 6: `full_quicklook` and the cascade's last two notches

**Files:**
- Modify: `glances/outputs/static/js/v5/AppShell.vue`, `glances/outputs/static/js/v5/degrade.js`
- Modify: `glances/outputs/static/js/v5/PluginQuicklook.vue` (the `freq_only` notch, if Task 5 left it unwired)
- Create: `tests/test_webui_v5_full_quicklook_drift.py`
- Modify: `tests/test_webui_v5_degrade_drift.py`, `tests/fixtures/webui_render_fixtures.js`, `tests/test_webui_v5_render.py`
- Rebuild: `glances/outputs/static/public/glances5.js`

**Interfaces:**
- Consumes: Task 5's component and the `degrade` prop it already declares.
- Produces: `FULL_QUICKLOOK_HIDDEN` in `AppShell.vue` and its drift test; `HIDDEN_BY.hide_quicklook`; a `degrade.js` with no `notApplicable` step left.

Two independent mechanisms that both hide top-row blocks, and they must compose rather than fight:

- **`full_quicklook`** is a SERVER state (`--full-quicklook`, `glances/main_v5.py:208`, already on the wire via `/api/5/args`). It hides `cpu`, `npu`, `mpp`, `gpu`, `mem`, `memswap` — and deliberately NOT `load` and `percpu` (`glances/outputs/curses_renderer_v5.py:86`, `_FULL_QUICKLOOK_HIDDEN`).
- **The cascade** is a VIEWPORT response. Its last two notches are `quicklook_freq_only` then `hide_quicklook`.

- [ ] **Step 1: Write the failing drift test for the hidden set**

`_FULL_QUICKLOOK_HIDDEN` is a Python frozenset the WebUI must mirror; the precedent for mirroring a Python constant into JS is `tests/test_webui_v5_smart_keys_drift.py` (and `degrade.js` for the cascades). Create `tests/test_webui_v5_full_quicklook_drift.py` on that model: import `_FULL_QUICKLOOK_HIDDEN` from `glances.outputs.curses_renderer_v5`, pull `FULL_QUICKLOOK_HIDDEN` out of `AppShell.vue`'s module via node, and compare the two sorted lists. Add the same "not empty" guard the smart-keys test has (`len(...) == 6`), for the same reason: two empty sets compare equal.

`AppShell.vue` is a `.vue` file, so a bare `import()` cannot read it. Put the constant where node can import it — a tiny `js/v5/full_quicklook.js` exporting `FULL_QUICKLOOK_HIDDEN`, imported by `AppShell.vue` — and say so in your report. That is the same reason `degrade.js` is a `.js` module and not part of the shell.

- [ ] **Step 2: Write the failing render tests**

Add a `quicklook-full` scenario: the `quicklook` payload for `quicklook`, plus payloads for `cpu`, `mem`, `memswap`, `load` and `gpu` so the hiding is observable, and an `ARGS_FIXTURES` entry with `full_quicklook: true`.

```python
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_full_quicklook_hides_the_tui_s_six_blocks_and_spares_load():
    """--full-quicklook hides cpu/npu/mpp/gpu/mem/memswap and deliberately NOT
    load or percpu (curses_renderer_v5.py:86, exact v4 parity). The WebUI reads
    the flag from /api/5/args, the way mem reads --byte.
    """
    payload = _run_render_probe("quicklook-full")
    rendered = set(payload["pluginNames"])
    for name in ("cpu", "mem", "memswap", "gpu"):
        assert name not in rendered, f"{name} must be hidden: {sorted(rendered)!r}"
    assert "load" in rendered, f"load is spared: {sorted(rendered)!r}"
    assert "quicklook" in rendered, f"vacuous: {sorted(rendered)!r}"
```

And two cascade tests, following the existing narrow-viewport tests in the file (`test_a_narrow_top_row_degrades_in_the_tui_order` is the model — reuse its `WIDTH_FIXTURES` mechanism rather than inventing a second one):

```python
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_narrow_top_row_collapses_the_quicklook_header_to_the_frequency():
    """Cascade step (d), `quicklook_freq_only`: the CPU name is replaced by the
    literal "Frequency" — the TUI shrinks the block that way rather than
    dropping the line."""
    payload = _run_render_probe("top-narrow-quicklook")
    text = payload["pluginText"]["quicklook"]
    assert "Frequency" in text and "Intel Core" not in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_exhausted_cascade_hides_quicklook_last():
    """Cascade step (e), `hide_quicklook`: the last notch before the top row
    crops."""
    payload = _run_render_probe("top-narrowest-quicklook")
    assert payload["pluginHidden"].get("quicklook") is True, f"got {payload['pluginHidden']!r}"
```

- [ ] **Step 3: Run them to verify they fail**

Run: `uv run pytest tests/test_webui_v5_render.py tests/test_webui_v5_full_quicklook_drift.py -q -k "quicklook"`
Expected: FAIL — no `FULL_QUICKLOOK_HIDDEN` module, no `hide_quicklook` entry, and the header does not react to the flag.

- [ ] **Step 4: Wire `full_quicklook`**

`slots()` in `AppShell.vue` already builds a `hidden` set from the cascade flags through `HIDDEN_BY`; add the server-state source to the same set — union, not a second filter, so the two mechanisms compose and a block hidden by either stays hidden:

```js
// `--full-quicklook` gives the quicklook block the whole row: the TUI hides
// the same six siblings (curses_renderer_v5.py:86 `_FULL_QUICKLOOK_HIDDEN`)
// and deliberately spares `load` and `percpu`. Server state, not a viewport
// response, so it is unioned with the cascade's own hidden set rather than
// being a cascade step.
if (this.serverArgs.full_quicklook) {
	for (const name of FULL_QUICKLOOK_HIDDEN) hidden.add(name);
}
```

Check how `serverArgs` reaches `AppShell` (the components receive it as a prop; the shell fetches `/api/5/args`) and read it from wherever the shell already holds it — do not add a second fetch.

- [ ] **Step 5: Wire the two cascade notches**

- `HIDDEN_BY` gains `hide_quicklook: "quicklook"` — that is all step (e) needs.
- Step (d) is a shrink, not a hide, so it belongs to the component (the degradation spec's D7): `PluginQuicklook.vue` reads `degrade.top.quicklook_freq_only` and replaces the CPU name with the literal `Frequency`.
- `degrade.js`: remove both `notApplicable: true` flags and the comment block that explains why they were there. Update `tests/test_webui_v5_degrade_drift.py::test_only_the_unported_steps_are_marked_not_applicable` to expect NO not-applicable step — if the test's name no longer describes what it asserts, rename it to say that every step is live.

- [ ] **Step 6: Run everything**

```bash
cd glances/outputs/static && npm run build && node_modules/.bin/eslint js/v5 --ext .js,.vue; cd -
uv run pytest tests/test_webui_v5_render.py tests/test_webui_v5_tokens.py tests/test_webui_v5_degrade_drift.py tests/test_webui_v5_full_quicklook_drift.py -q
```
Expected: all green — including the drift test that Task 5 deliberately left red.

- [ ] **Step 7: Stage**

```bash
git add glances/outputs/static/js/v5/AppShell.vue glances/outputs/static/js/v5/degrade.js \
        glances/outputs/static/js/v5/full_quicklook.js glances/outputs/static/js/v5/PluginQuicklook.vue \
        glances/outputs/static/public/glances5.js \
        tests/test_webui_v5_full_quicklook_drift.py tests/test_webui_v5_degrade_drift.py \
        tests/fixtures/webui_render_fixtures.js tests/test_webui_v5_render.py
git status --short | grep -v '^[AM] ' && echo "REPORT THE LINES ABOVE (an ` M Makefile` line is expected)" || echo "clean"
```

---

### Task 7: Verify against a real server, and close

**Files:** none changed unless a defect is found (then: the file that holds it, and the test that should have caught it).

- [ ] **Step 1: Run the whole suite**

```bash
uv run pytest -q 2>&1 | tail -15
```
Expected: no failure beyond the three pre-existing `tests/test_plugin_sensors_v5.py` ones (its `config` fixture leaks the real user config). Re-run `test_restful.py::test_050/051` alone before believing a failure there; check `ss -lptn 'sport = :61235'` before believing a `test_mcp.py` one.

- [ ] **Step 2: Serve it, with the options that matter**

`irq`/`raid`/`smart` are irrelevant here; what this group needs is a many-core box (any modern CPU), and three runs:

```bash
D=.superpowers/sdd/2026-09-12-glances-v5-g9-8-webui-top-slot
# 1. defaults
uv run python -m glances.main_v5 -s
# 2. the per-core view and a non-default cap
printf '[percpu]\nmax_cpu_display=2\n' > $D/g9-8.conf
uv run python -m glances.main_v5 -s -C $D/g9-8.conf --percpu
# 3. full quicklook
uv run python -m glances.main_v5 -s --full-quicklook
```

The v5 server is `python -m glances.main_v5 -s`; `-s` is what binds the socket and serves the Web UI (there is no `-w`). Run each in the background, give it a few seconds, capture, then kill it by PID. Open the TUI on the same config in a second terminal for the side-by-side read.

- [ ] **Step 3: Compare each block against the terminal**

| Check | What must match |
|---|---|
| `quicklook` bars | the same bars in the same order as the terminal, each proportional to its value, the tier colour on the fill, the value to the right |
| `quicklook` header | the CPU name and the `cur/max GHz` pair |
| `--percpu` | the `cpu` bar replaced by per-core bars, capped at 2, each core with its OWN colour, plus `CPU*` |
| `max_cpu_display=2` | **both** surfaces show two cores and a mean row — the check that proves the key is no longer inert |
| `percpu` block | with quicklook on: no title, no `total` column, no row labels; with `[quicklook] disable=True`: all three back |
| `npu` / `mpp` | absent on a machine with neither — and that is correct, not a failure; say so explicitly |
| `--full-quicklook` | `cpu`, `npu`, `mpp`, `gpu`, `mem`, `memswap` gone, `load` and `percpu` still there |

Capture each run:
```bash
google-chrome --headless --disable-gpu --screenshot=$D/g9-8-<run>.png --window-size=1600,1200 http://localhost:61208/
```

- [ ] **Step 4: Narrow viewport and both themes**

Resize to ~700px and watch the top row take its notches in order: the quicklook header collapses to `Frequency`, then the block disappears. Then ~400px: no horizontal scrollbar on the page body. Toggle `[outputs] theme=light` and reload: every tier colour still present (they are tokens, not literals), and the bar track still visible against the light background — **the one thing in this group that could be invisible in one theme**, so look at it deliberately.

- [ ] **Step 5: Run the hooks**

```bash
git add -A -- glances tests docs
make pre-commit
```
It supersedes lint+format. gitleaks scans the index, so stage first and restage anything a formatter rewrites. The shebang hook failure on `tests/test_web_list_ssl_verify.py` is pre-existing and not this group's.

- [ ] **Step 6: Report**

Report to the maintainer: the suite result and `make pre-commit`; the screenshot paths; the `max_cpu_display` before/after evidence from both surfaces; anything found and NOT fixed with file and line; and `git status --short` (everything staged, nothing committed).

**Owed by the maintainer afterwards:** the browser smoke on a machine that actually has an NPU or an MPP device, which this one may not.

---

## Self-Review

- **Spec coverage.** §4 the bar → Task 5 Steps 1, 5. §5.1 `max_cpu_display` → Task 1, mirrored in Task 4. §5.2 the quicklook interaction → Task 2, mirrored in Task 4. §5.3 how percpu learns it → Task 2 Step 4 (TUI, from `fields_by_plugin`) and Task 4 Step 4 (WebUI, from the plugin list). §6 `full_quicklook` → Task 6 Steps 1, 2, 4. §7 the cascade → Task 6 Step 5. §8.1 `mpp` and §8.2 `npu` → Task 3. §8.3 `percpu` → Task 4. §8.4 `quicklook` → Task 5. §9 registry/layout → the registry steps of Tasks 3, 4, 5. §10 tests → every task's test step, plus the two drift tests. §11 risks → the bar CSS is global (Task 5 Step 1), the two percpu behaviours have separate tests (Tasks 1 and 2), one source of truth for the quicklook state (§5.3), the cascade is exercised by render tests at width (Task 6 Step 2), and `full_quicklook` unions into the cascade's own hidden set (Task 6 Step 4).
- **Two places the plan deliberately leaves a decision to the implementer**, each with an instruction to report it: the `npu` block's shape (table row vs `.gl-stat-grid`, Task 3 Step 5) and where the auto-Hz formatter lives (same step). Both are local, both are reversible, and both would be worse guessed by me than by someone reading the rendered result.
- **One place the plan says STOP:** Task 4 Step 4, if the plugin list cannot reach `PluginPercpu` without editing `AppShell.vue` — that file belongs to Task 6, and the controller decides rather than letting two tasks edit it.
- **Type consistency.** `view["quicklook_enabled"]` (Task 2) is read in `percpu/render_curses_v5.py` only. `max_cpu_display` is a payload field in both `percpu` (Task 1) and `quicklook` (pre-existing). `FULL_QUICKLOOK_HIDDEN` is produced in Task 6 Step 1 and consumed in Step 4. The probe fields `bars` / `barLabels` are produced in Task 5 Step 4 and consumed in Steps 3 and Task 6 Step 2. `cellClassFor(payload, item, field)`, `levelClass`, `scalarLevel`, `labelFor(labels, field)` and the `format.js` exports are used with their existing signatures.
