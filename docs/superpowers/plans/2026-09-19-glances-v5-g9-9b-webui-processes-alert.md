# Glances v5 — G9-9B WebUI processes and alert Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port `processlist`, `programlist` and `alert` into the v5 WebUI —
taking the registry from 29 to **32 of 32** and closing G9 — and add the two
CLI options (`--programs`, `--sort-processes`) that give the browser the
server signals it needs.

**Architecture:** The alert grid is built from the SAME synthesis the TUI
calls: `_derive_incidents` moves out of the curses renderer into a shared
module, a new route serves it, and the WebUI consumes it. The two process
lists reuse `fit_block.js` (built in G9-9A for exactly this) and cap in the
browser from the config key v4 already uses.

**Tech Stack:** Vue 3 (options API, `.vue` SFCs), webpack (`npm run build`
in `glances/outputs/static/`), FastAPI, pytest, `node --test`, the DOM-less
render probe (`tests/fixtures/webui_render_probe.js`).

**Spec:** `docs/superpowers/specs/2026-09-19-glances-v5-g9-9b-webui-processes-alert-design.md`

---

## Global Constraints

- **Branch:** `develop-v5`, on top of commit `fa92ba77` (G9-9A). Every task
  **stages** (`git add`) and **STOPS**. Never `git commit`, `git push`,
  `git stash`, `git reset`, `git checkout -- <file>`, never open a PR. The
  maintainer commits personally. No `Co-Authored-By` trailer.
- **Never unstage or discard anything.** After each task run
  `git status --short | grep -v '^[AM] '` and report any line it prints.
- **Never touch `NEWS.rst`.**
- **The terminal renderers are the parity authority and are READ-ONLY**,
  with ONE exception: Task 2 moves two functions out of
  `glances/outputs/curses_renderer_v5.py`. No other task may modify any
  `glances/plugins/*/render_curses_v5.py` or `model_v5.py`.
- **A requirement stated in a task brief must be verified against the
  source before it is built.** Every parity claim below carries a
  `file:line`. Open it. If the source disagrees with the brief, STOP and
  report — do not implement the brief. (G9-9A shipped an invented rule that
  passed two reviews because the brief asserted it.)
- **Rebuild the bundle** (`cd glances/outputs/static && npm run build`)
  before running any test in `tests/test_webui_v5_render.py`.
- **Placeholder for a missing value is `-`** (`format.js` `MISSING`).
- **A width that means "N TUI characters" is `calc(N * var(--gl-col))`**,
  never `Nch` — `ch` resolves to 0.5em under the shipped font stack. A
  guard in `tests/test_webui_v5_tokens.py` enforces this.
- **Tier classes come from `levels.js` only**; no colour literal. The tier
  goes on the `<span>` inside the `<td>`, never on the `<td>`.
- **Every component declares all five props** (`payload`, `error`,
  `labels`, `serverArgs`, `degrade`), or the unlisted one leaks into the
  DOM as an attribute.
- **No template comment before the root element** — a root-level comment
  makes a two-root fragment and silently drops `data-plugin`/`aria-label`.
- **An empty collection is asserted through `payload["pluginHidden"]`**,
  never through `slots` (the shell hides with `v-show`).
- ENVIRONMENT: bare `pytest`/`npm` are intercepted — use
  `rtk proxy "<command>"` and `.venv-uv/bin/uv run pytest ...`. When
  redirecting `git diff` to a file, always pass an explicit pathspec.

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `glances/outputs/static/css/v5.css` | `.gl-command` / `.gl-ports` caps become global | 1 |
| `glances/alerts_incidents_v5.py` | the incident synthesis, shared by both UIs | 2 |
| `glances/outputs/curses_renderer_v5.py` | imports the synthesis instead of defining it | 2 |
| `glances/alerts_v5.py` | `get_ongoing_top()` stops aliasing engine state | 3 |
| `glances/routes_v5.py` | `/api/5/alert/incidents` | 4 |
| `glances/main_v5.py` | `--programs`, `--sort-processes` | 5 |
| `glances/outputs/static/js/v5/PluginAlert.vue` | the incident grid | 6 |
| `glances/outputs/static/js/v5/AppShell.vue` | repoint the alert fetch, reduce the footer | 6 |
| `glances/outputs/static/js/v5/PluginProcesslist.vue` | the process table | 7 |
| `glances/outputs/static/js/v5/processlist_columns.js` | its pure column/cascade rules | 7 |
| `glances/outputs/static/js/v5/PluginProgramlist.vue` | the program table | 8 |
| `glances/outputs/static/js/v5/PluginProcesscount.vue` | counter + sort indicator | 8 |
| `glances/outputs/static/js/v5/plugins/index.js` | three registry entries | 6, 7, 8 |
| `tests/…` | per task | all |

---

## Task 1: the parked debt — both measuring caps become global

**Files:**
- Modify: `glances/outputs/static/css/v5.css`
- Modify: `glances/outputs/static/js/v5/PluginContainers.vue`
- Test: `tests/test_webui_v5_tokens.py`

**Interfaces:**
- Consumes: nothing.
- Produces: global `.gl-command` and `.gl-ports` rules, so Task 7 can put
  `class="gl-command"` on the process list's command cell and inherit a
  real cap.

**Why first:** `css/v5.css` excludes `.gl-command` and `.gl-ports` from the
measuring pass, but both caps live in `PluginContainers.vue`'s scoped
style. `processlist` has a command column and reuses `fit_block.js`; it
would inherit the exclusion WITHOUT the cap and its cascade would silently
under-fire.

- [ ] **Step 1: Read the two rules and the exclusion**

```bash
cd /home/nicolargo/dev/glances
grep -n "gl-measuring" -A6 glances/outputs/static/css/v5.css
sed -n '/<style scoped>/,$p' glances/outputs/static/js/v5/PluginContainers.vue
```
Both scoped rules carry `display: block` — that half is load-bearing:
`max-width` does not apply to a non-replaced inline element.

- [ ] **Step 2: Write the failing test**

In `tests/test_webui_v5_tokens.py`:

```python
def test_a_measuring_exclusion_has_its_cap_in_the_token_file():
    """`.gl-measuring` excludes `.gl-name`, `.gl-command` and `.gl-ports` so
    their caps survive the measurement. `.gl-name`'s cap is global; the
    other two were scoped to PluginContainers.vue, so a SECOND component
    using either class would inherit the exclusion with no cap and its
    cascade would under-fire -- silently, because an uncapped span simply
    measures narrower than it should.

    Reads the token file only: a cap defined in a component cannot serve a
    class the token file exempts globally.
    """
    css = _strip_comments(_TOKENS.read_text())
    for cls in (".gl-name", ".gl-command", ".gl-ports"):
        body = _rule_body(css, cls)
        assert re.search(r"\bdisplay:\s*block\s*;", body), f"{cls} needs a block box for its cap: {body!r}"
        assert re.search(r"\bmax-width:", body), f"{cls} has no cap in the token file: {body!r}"
```

- [ ] **Step 3: Run it, see it fail**

```bash
cd /home/nicolargo/dev/glances
.venv-uv/bin/uv run pytest tests/test_webui_v5_tokens.py -k measuring_exclusion -v
```
Expected: FAIL, `no '.gl-command' rule found`.

- [ ] **Step 4: Move both rules**

Cut `.gl-command` and `.gl-ports` (comments included) from
`PluginContainers.vue`'s scoped style and paste them into `css/v5.css` next
to `.gl-name`. Keep `--gl-name-width` in the component: that one is
per-block by design. Add one line to each moved comment saying it is global
because `.gl-measuring` exempts the class globally.

- [ ] **Step 5: Rebuild and run**

```bash
cd /home/nicolargo/dev/glances/glances/outputs/static && npm run build
cd /home/nicolargo/dev/glances && .venv-uv/bin/uv run pytest tests/test_webui_v5_tokens.py tests/test_webui_v5_render.py -q
```
Expected: green, and **no containers test edited** — the rules moved, their
effect did not change.

- [ ] **Step 6: Stage** the three files plus the bundle, then
`git status --short | grep -v '^[AM] '`.

---

## Task 2: extract the incident synthesis

**Files:**
- Create: `glances/alerts_incidents_v5.py`
- Modify: `glances/outputs/curses_renderer_v5.py`
- Test: the EXISTING alert tests, unedited

**Interfaces:**
- Produces: `derive_incidents(history, ongoing=None, ongoing_since=None, ongoing_top=None) -> list[dict]`
  and `incident_duration(incident, now=None) -> str | None`, public names
  (no leading underscore) since they now have two callers.
- Consumed by: Task 4 (the route) and the TUI renderer.

**This is the riskiest task in the group: it is the only one that can break
a TUI that works today.**

- [ ] **Step 1: Read what moves, and what must NOT**

```bash
cd /home/nicolargo/dev/glances
sed -n '527,575p' glances/outputs/curses_renderer_v5.py   # _incident_duration
sed -n '576,700p' glances/outputs/curses_renderer_v5.py   # _derive_incidents
grep -rn "_derive_incidents\|_incident_duration" glances/ tests/ --include=*.py
```
Moves: those two functions and whatever module-level constants ONLY they
use. Stays: `render_alert_block` (`:876`), `_alert_block_height` (`:807`),
`_build_alert_title_cells`, `_format_alert_time` and every `Cell`/`Row`
helper — those are curses geometry.

- [ ] **Step 2: Find the whole call surface first**

The grep above is the task's real specification. Every caller must keep
working, including tests that import the private names. If a test imports
`_derive_incidents` directly, re-export it from the renderer
(`from glances.alerts_incidents_v5 import derive_incidents as _derive_incidents`)
rather than editing the test — **the success criterion for this task is
that no alert test needs editing.**

- [ ] **Step 3: Run the alert tests BEFORE moving anything, and record the count**

```bash
cd /home/nicolargo/dev/glances
.venv-uv/bin/uv run pytest tests/ -q -k "alert or incident" 2>&1 | tail -3
```
Write the number in your report. It is the number that must come back.

- [ ] **Step 4: Move**

Create `glances/alerts_incidents_v5.py` with the standard project header
(SPDX lines, copy them from `glances/alerts_v5.py`) and a module docstring
saying: this is the collapse of a transition log into incidents, it is pure,
and it has two consumers — the curses renderer and `/api/5/alert/incidents`
— which is why it is not in either.

Paste both functions verbatim, rename to the public names, and in
`curses_renderer_v5.py` replace the definitions with the import plus the
two private aliases.

- [ ] **Step 5: Verify the move was pure**

```bash
cd /home/nicolargo/dev/glances
.venv-uv/bin/uv run pytest tests/ -q -k "alert or incident" 2>&1 | tail -3
```
Expected: the SAME number as Step 3, all passing, **no test file edited**.
If a test needed an edit, stop and report what and why.

- [ ] **Step 6: Stage** and `git status --short | grep -v '^[AM] '`.

---

## Task 3: close the `get_ongoing_top()` race

**Files:**
- Modify: `glances/alerts_v5.py`
- Test: `tests/test_alerts_v5.py` (or the file the alert engine tests live
  in — find it with `grep -rln "get_ongoing_top" tests/`)

**Interfaces:**
- Produces: `get_ongoing_top()` returning data that no longer aliases
  engine state. Task 4's route depends on it.

- [ ] **Step 1: Read the accessor and its own warning**

```bash
cd /home/nicolargo/dev/glances
sed -n '238,275p' glances/alerts_v5.py
```
Its docstring says it returns the `top` list object stored on the history
event, **not a copy**, and that a future caller must not mutate it. A REST
route is worse than a mutator: it SERIALIZES that list while
`_accumulate_top` may be appending from the asyncio side.

- [ ] **Step 2: Write the failing test**

```python
def test_get_ongoing_top_does_not_alias_engine_state():
    """The accessor returned the list stored on the history event, so a
    caller holding the result saw it change under them -- and a caller
    SERIALIZING it (the /api/5/alert/incidents route) can hit a list
    mutated mid-iteration, which raises. The TUI reads the same accessor
    from its own thread, where a raise kills the thread for good.
    """
    alerts = <build an engine with one active incident carrying a top list>
    returned = alerts.get_ongoing_top()
    key = next(iter(returned))
    before = list(returned[key]["top"])

    <append a process name to the list the ENGINE holds for that key>

    assert returned[key]["top"] == before, (
        f"the accessor handed out a live reference: {returned[key]['top']!r} != {before!r}"
    )
```

Build the engine the way the existing tests in that file do — read two of
them first and follow their fixture style rather than inventing one.

- [ ] **Step 3: Run it, see it fail** (the returned list grows with the
engine's).

- [ ] **Step 4: Fix** — copy `names` when building the result. One line.
Delete the docstring paragraph that warned about the alias, and say instead
that the result is a snapshot safe to serialize.

- [ ] **Step 5: Run the whole alert engine test file.** Expected: green.

- [ ] **Step 6: Stage** and check the tree.

---

## Task 4: `/api/5/alert/incidents`

**Files:**
- Modify: `glances/routes_v5.py`
- Test: the REST test file (`grep -rln "api/5/alert" tests/`)

**Interfaces:**
- Consumes: `derive_incidents` (Task 2), the safe `get_ongoing_top`
  (Task 3).
- Produces: the endpoint Task 6's component reads.

- [ ] **Step 1: Read the existing alert route and the ones around it**

```bash
cd /home/nicolargo/dev/glances
sed -n '160,200p' glances/routes_v5.py
```
Note how `/alert` 404s when `request.app.state.alerts` is `None`, and that
routes are matched in declaration order — `/alert/incidents` must be
declared BEFORE any `/{plugin_name}`-style dynamic route, exactly as
`/all/info` is.

- [ ] **Step 2: Write the failing tests**

Three, following the existing file's client fixture style:

```python
def test_the_incidents_route_serves_the_synthesis(...):
    """Same function the TUI calls (glances/alerts_incidents_v5.py), so the
    browser cannot drift from the terminal."""
    # seed an engine with one resolved and one ongoing incident
    response = client.get("/api/5/alert/incidents")
    assert response.status_code == 200
    incidents = response.json()
    assert [i["ongoing"] for i in incidents] == [...]

def test_the_incidents_route_marks_a_partial_incident(...):
    """`partial` says the opening event aged out of the bounded history, so
    the duration is a LOWER BOUND. A client that lost the flag would print
    a lower bound as if it were exact."""
    # seed ongoing_since with no matching opening event in the history
    assert response.json()[0]["partial"] is True

def test_the_incidents_route_404s_when_alerts_are_disabled(...):
    """Same contract as /api/5/alert."""
    assert response.status_code == 404
```

- [ ] **Step 3: Run them, see them fail** (404 — the route does not exist).

- [ ] **Step 4: Implement**

```python
    @router.get("/alert/incidents")
    async def alert_incidents(request: Request) -> list[dict[str, Any]]:
        """The alert history collapsed into incidents — the same synthesis
        the TUI's alert block paints (glances/alerts_incidents_v5.py).

        Declared before the dynamic plugin route, like /all/info, or
        `alert` would be matched as a plugin name.
        """
        alerts = request.app.state.alerts
        if alerts is None:
            raise HTTPException(status_code=404, detail="Alerts subsystem disabled")
        return derive_incidents(
            alerts.get_history(),
            ongoing=alerts.get_ongoing(),
            ongoing_since=alerts.get_ongoing_since(),
            ongoing_top=alerts.get_ongoing_top(),
        )
```

- [ ] **Step 5: Run the REST test file.** Then check the route is reachable
on a live server:

```bash
cd /home/nicolargo/dev/glances
(.venv-uv/bin/uv run python -m glances.main_v5 -s > /tmp/g5.log 2>&1 &) ; sleep 8
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:61208/api/5/alert/incidents
kill %1 2>/dev/null || pkill -f "glances.main_v5 -s"
```

- [ ] **Step 6: Stage** and check the tree.

---

## Task 5: `--programs` and `--sort-processes`

**Files:**
- Modify: `glances/main_v5.py`
- Test: the CLI test file (`grep -rln "main_v5" tests/ | head`)

**Interfaces:**
- Produces: `args.programs` (bool) and `args.sort_processes_key` (str |
  None), both reaching `/api/5/args`, which is what Tasks 7 and 8 read.

- [ ] **Step 1: Read v4's definitions — they are the contract**

```bash
cd /home/nicolargo/dev/glances
grep -n -B4 -A8 "'--programs'" glances/main.py
grep -n -B2 -A8 "'--sort-processes'" glances/main.py
.venv-uv/bin/uv run python -c "from glances.processes import sort_processes_stats_list as s; print(s)"
```
v4 uses `dest='sort_processes_key'` and `choices=sort_processes_stats_list`
= `['cpu_percent', 'memory_percent', 'username', 'cpu_times',
'io_counters', 'name', 'cpu_num']`. **Import that list, never retype it** —
a retyped copy is a drift waiting to happen, and v4 is the authority.

- [ ] **Step 2: Write the failing tests**

```python
def test_the_programs_option_parses():
    args = <parse ["--programs"]>
    assert args.programs is True

def test_the_default_is_the_process_list():
    args = <parse []>
    assert args.programs is False

def test_the_sort_option_uses_v4s_dest_and_choices():
    """A script written against v4 must keep working against v5, so the
    dest name is v4's (`sort_processes_key`), not a v5 invention."""
    args = <parse ["--sort-processes", "memory_percent"]>
    assert args.sort_processes_key == "memory_percent"

def test_the_sort_option_rejects_a_value_outside_the_shared_list():
    from glances.processes import sort_processes_stats_list
    assert "nonsense" not in sort_processes_stats_list
    with pytest.raises(SystemExit):
        <parse ["--sort-processes", "nonsense"]>
```

- [ ] **Step 3: Run, see them fail** (`unrecognized arguments`).

- [ ] **Step 4: Add both options** to `main_v5.py`'s parser, next to the
other display options, with help strings copied from v4 so `--help` reads
the same on both.

- [ ] **Step 5: Verify they reach `/api/5/args`**

```bash
cd /home/nicolargo/dev/glances
(.venv-uv/bin/uv run python -m glances.main_v5 -s --programs --sort-processes memory_percent > /tmp/g5.log 2>&1 &) ; sleep 8
curl -s http://localhost:61208/api/5/args -o /tmp/args.json
.venv-uv/bin/uv run python -c "
import json; a=json.load(open('/tmp/args.json'))
print('programs =', a.get('programs'), '| sort_processes_key =', a.get('sort_processes_key'))"
pkill -f "glances.main_v5 -s"
```
Both must appear. If `/api/5/args` redacts or drops them, say so — Tasks 7
and 8 depend on them being visible.

- [ ] **Step 6: Stage** and check the tree.

---

## Task 6: `PluginAlert.vue` and the footer

**Files:**
- Create: `glances/outputs/static/js/v5/PluginAlert.vue`
- Modify: `glances/outputs/static/js/v5/AppShell.vue`, `plugins/index.js`
- Modify: `tests/fixtures/webui_render_fixtures.js`, `webui_render_probe.js`
- Test: `tests/test_webui_v5_render.py`

**Interfaces:**
- Consumes: `/api/5/alert/incidents` (Task 4).
- Produces: registry at 30; the alert payload plumbing Tasks 7-8 leave alone.

**Reference:** `curses_renderer_v5.py:1004-1062`. Columns, in order:
glyph, `TIME`, `DURATION`, `TARGET`, `TOP PROCESSES`, `LEVEL`.

Two rules that are easy to lose and are the point of the block:
- **`LEVEL` is tier-coloured only while the incident is ONGOING** (`:1056`):
  a resolved one goes neutral, so colour in that column means "still
  happening". The glyph keeps the level colour either way, so the severity
  reached stays readable.
- **`partial`** means the opening event aged out of the bounded history, so
  the duration is a lower bound and the TUI prefixes it `>`. Render the
  prefix; a bare number would be a lie.

The TUI width-gates `DURATION`, `TOP PROCESSES` and `LEVEL`. The browser
renders all of them — the block sits in the wide right column and, like
`vms`, scrolls rather than dropping. Record it in the report.

- [ ] **Step 1: Read the reference and the incident shape**

```bash
cd /home/nicolargo/dev/glances
sed -n '1004,1062p' glances/outputs/curses_renderer_v5.py
grep -n "def derive_incidents" -A40 glances/alerts_incidents_v5.py
```

- [ ] **Step 2: Fixtures** — add an `ALERT_INCIDENTS_FIXTURE` with three
incidents: one ongoing+prominent critical, one resolved warning, one
ongoing+`partial`. The probe answers `api/5/alert/incidents` with it (the
existing `api/5/alert` handler is the model; note the URL check for
`/alert/incidents` must come BEFORE the one for `/alert`, the same trap
`/all/info` documents in that file).

- [ ] **Step 3: Write the failing tests**

```python
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_alert_grid_renders_the_tui_columns():
    payload = _run_render_probe("alert")
    assert payload["pluginHeaderCells"]["alert"] == ["", "TIME", "DURATION", "TARGET", "TOP PROCESSES", "LEVEL"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_only_an_ongoing_incident_colours_its_level():
    """curses_renderer_v5.py:1056 -- a resolved incident's LEVEL goes
    neutral so colour there means "still happening"."""
    payload = _run_render_probe("alert")
    rows = _table_rows(payload, "alert", 6)
    # the resolved row's LEVEL cell carries no tier class
    ...


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_partial_incident_marks_its_duration_as_a_lower_bound():
    """`partial` means the opening event aged out of the history, so the
    duration is a lower bound -- printed bare it would be a lie."""
    payload = _run_render_probe("alert")
    assert any(cell.startswith(">") for cell in <the DURATION column>)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_footer_keeps_the_cadence_and_drops_the_alert_list():
    payload = _run_render_probe("alert")
    assert "refresh" in payload["footerText"]
    assert "No alert" not in payload["footerText"]
```

- [ ] **Step 4: Run, see them fail.**

- [ ] **Step 5: Implement** the component, repoint `AppShell.tick()`'s
existing alert fetch at `/api/5/alert/incidents` and hand its result to the
component instead of the footer list, and strip the footer to the cadence
(`AppShell.vue:27` and `:297`). Keep the fetch in its own try/catch: a
failing alert endpoint must not disturb the plugins above it.

Register `alert` last in `PLUGINS` with `slot: "right"`. It is fed by its
own endpoint, so it declares no payload `shape`.

- [ ] **Step 6: Rebuild, run the WebUI files** (registry now 30; extend the
verbatim registry lists and the `pluginAttrs` count).

- [ ] **Step 7: Stage** and check the tree.

---

## Task 7: `PluginProcesslist.vue`

**Files:**
- Create: `glances/outputs/static/js/v5/PluginProcesslist.vue`,
  `glances/outputs/static/js/v5/processlist_columns.js`
- Create: `tests/js/processlist_columns.test.mjs`,
  `tests/test_webui_v5_processlist_drop_order_drift.py`
- Modify: `plugins/index.js`, the fixtures, `tests/test_webui_v5_render.py`

**Interfaces:**
- Consumes: `fit_block.js` (`fitBlockMixin`, `dropCascadeSteps`,
  `dropFlags`), `dropCascade` from `drop_order.js`, the global
  `.gl-command` cap (Task 1), `serverArgs.sort_processes_key` (Task 5).
- Produces: registry at 31.

**Reference:** `glances/plugins/processlist/render_curses_v5.py`. Verify
each of these against the file before building:
- `_FIXED_COL_KEYS` (`:91`): `CPU% MEM% VIRT RES PID USER THR NI S TIME+ R/s W/s`, then `Command`.
- `_DROP_ORDER` (`:89`): `VIRT → TIME+ → RES → USER → PID → THR → S → NI`.
  **`Command` is the protected TAIL here** — the opposite of `containers`,
  which drops `command` first. Both mirror their own renderer.
- `_HEADER_SORT_KEY` (`:97`) maps a header label to the engine sort key;
  the active one is underlined.
- `_MAX_ROWS = 20` (`:66`) is the TUI's own bound and is NOT ported.

- [ ] **Step 1: Read the renderer's cell builders** and write down, in your
report, the formatter each column uses. Reuse `format.js`; add nothing to
it without saying why.

- [ ] **Step 2: The pure module + its tests**

`processlist_columns.js` exports `PROCESSLIST_DROP_ORDER` and
`hiddenColumns(flags)`, mirroring `drop_order.js`/`containers_columns.js`.
The drift test mirrors `tests/test_webui_v5_containers_drop_order_drift.py`
— copy its structure, compare order AND membership, and assert the
never-dropped columns are absent from the order.

- [ ] **Step 3: Write the failing render tests**

At minimum: the TUI column set; rows in payload order (the engine sorts,
the component must not); the cap from `max_processes_display` with the
right number of rows; the sort underline on the column named by
`serverArgs.sort_processes_key` and on no other; `Command` surviving a
cascade that drops all eight droppable columns.

- [ ] **Step 4: Run, see them fail. Step 5: implement. Step 6: rebuild and
see them pass.**

- [ ] **Step 7: Stage** and check the tree.

---

## Task 8: `programlist`, the exclusivity rule, and the `TASKS` line

**Files:**
- Create: `glances/outputs/static/js/v5/PluginProgramlist.vue`
- Modify: `PluginProcesscount.vue`, `plugins/index.js`, the fixtures,
  `tests/test_webui_v5_render.py`

**Interfaces:**
- Consumes: `serverArgs.programs` and `serverArgs.sort_processes_key`
  (Task 5), Task 7's column module where the shapes match.
- Produces: registry at **32 of 32** — G9 closed.

**Two rules:**
- **Exactly one of `processlist` / `programlist` renders**, never both, on
  `serverArgs.programs` — the same shape as the `cpu`/`percpu` exclusivity
  in `AppShell.slots()`, and the same failure if forgotten (two process
  tables on one page). The TUI does it at `glances_curses_v5.py:574`.
- **The `TASKS` line gains its two deferred halves** (G9-9A §6.3): the
  `N/M` counter — shown only when the list is actually cut, and **never in
  the programs view**, where the total counts processes while the list
  shows programs — and the `Threads/Programs sorted by …` indicator, whose
  wording is at `processcount/render_curses_v5.py:58`.

- [ ] **Step 1: Read `programlist/render_curses_v5.py:62` onward** and the
two `processcount` helpers (`:37`, `:58`).

- [ ] **Step 2: Write the failing tests** — exclusivity both ways; the
counter present when cut and absent when not; the counter ABSENT in the
programs view; the indicator's wording for both views and for the
auto-sort flag.

- [ ] **Step 3: Run, fail, implement, pass, rebuild.**

- [ ] **Step 4: Confirm 32/32**

```bash
cd /home/nicolargo/dev/glances
grep -c 'component: Plugin' glances/outputs/static/js/v5/plugins/index.js
```
Expected: `32`.

- [ ] **Step 5: Stage** and check the tree.

---

## Task 9: group verification

**Files:** none created.

- [ ] **Step 1:** registry is 32; the right slot order matches the TUI's
`RIGHT_SLOT` tuple.
- [ ] **Step 2:** `cd glances/outputs/static && npm run lint` — no new
error on this group's files (the v4 legacy files are already noisy).
- [ ] **Step 3:** every WebUI test file, then the full suite.
  **Establish the attribution of every failure yourself.** Known and
  pre-existing: `tests/test_perf.py` under load; a leaked server on port
  61235 making every `test_mcp` test 404 (check
  `ss -lptn 'sport = :61235'` BEFORE diagnosing). Re-run each failing file
  in isolation and state, per failure: pre-existing, or caused by this
  group. Any failure caused by this group is the headline of your report.
- [ ] **Step 4:** `make pre-commit`. If a hook rewrites a staged file,
re-stage and re-run (gitleaks scans the index). If it rewrites a file
OUTSIDE this group, do not stage it — report and stop.
- [ ] **Step 5:** live smoke of the two new server surfaces:

```bash
cd /home/nicolargo/dev/glances
(.venv-uv/bin/uv run python -m glances.main_v5 -s --programs --sort-processes memory_percent > /tmp/g5.log 2>&1 &) ; sleep 8
curl -s -o /dev/null -w "incidents %{http_code}\n" http://localhost:61208/api/5/alert/incidents
curl -s -o /dev/null -w "args %{http_code}\n" http://localhost:61208/api/5/args
pkill -f "glances.main_v5 -s"
```

- [ ] **Step 6: Report** `git status --short` in full, the suite counts
verbatim, the browser smoke still owed, and the three spec divergences.

---

## Self-Review

**Spec coverage:** §4 → T1; §5.1 → T2; §5.3 → T3; §5.2 → T4; §7 → T5;
§5.4/§5.5 → T6; §6.1/§6.2 → T7; §6.3/§7.1 → T8; §9 → every task plus T9.

**Type consistency:** `derive_incidents` / `incident_duration` are defined
in T2 and used by T4 and T6 under those exact names.
`hiddenColumns(flags)` in T7 mirrors `containers_columns.js`'s signature
minus the data-driven arguments, which `processlist` does not have.
`fitBlockMixin` requires a `dropCascadeSteps` computed, a `payload`
watcher, `dropFlags` in the template and a `<table>` descendant — its own
header documents the contract.

**Known weakness, stated rather than hidden:** Tasks 6, 7 and 8 specify
their components by reference (column lists, the rules that are easy to
lose, and full test code) rather than by pasting a finished `.vue` file.
That is deliberate: `processlist`'s renderer is 479 lines, and a
transcribed component in this plan would be a second source of truth
written by someone who had not read the first. The guard is the constraint
at the top — verify every parity claim against its `file:line` before
building, and stop if the source disagrees.
