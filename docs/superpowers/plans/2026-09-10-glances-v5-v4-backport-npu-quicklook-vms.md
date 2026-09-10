# Glances v5 — backport of three v4 fixes (npu / quicklook / vms)

**Branch:** `develop-v5`
**Source of truth:** the v4 commits listed per task, on `develop`.
**Sweep report:** the v4 → v5 backport sweep of 2026-09-10 (develop `2bf3aadb`).

Three v4 fixes landed in `develop` on files that v5 **reimplements**, so none of
them reached v5. Each task ports one of them. The tasks are independent: they
touch three different plugins and three different test files.

---

## Context and decisions (the authority this plan argues from)

### Why these three and not the rest of the sweep

The other v4 commits of the same batch are either fixes to engines v5 reuses
verbatim (already live in v5), structurally impossible in v5, or WebUI v4 fixes
(v5 has a separate WebUI). These three touch `plugins/<x>/__init__.py` — the
exact files v5 replaces with `model_v5.py` / `render_curses_v5.py`.

### Decisions already made (do not re-open)

1. **npu temperature — mirror the `gpu` plugin.** `gpu/model_v5.py` already
   declares `temperature` as `watched` with the v4 60/70/80 ladder. `npu` gets
   the same treatment, and `internal: True` is dropped **from the `temperature`
   field only** (the npu renderer displays it, so the "never displayed in any UI"
   contract of `internal` was already false for it). The other npu `internal`
   fields are left alone.
2. **quicklook per-core colour — computed in the model, not the renderer.**
   Threshold logic belongs to the model layer. As a consequence the model also
   owns the display cut (`[percpu] max_cpu_display`), because the colour of the
   `CPU*` row depends on *which* cores were hidden. This closes the
   `TODO(G2+)` already written at `quicklook/render_curses_v5.py:68`.
3. **vms — `EMITS_ALERTS` flips to `True`.** The G6A decision
   (`EMITS_ALERTS = False`, "mirrors v4's dead alert decorations") was correct
   when it was taken: v4's vms decorations were dead code. v4 `f8657a0a` brought
   them to life, so the premise is gone. v4's `get_alert()` also registers
   thresholds and runs configured actions, which is what `EMITS_ALERTS = True`
   buys in v5. The shipped `conf/glances.conf` keys stay **commented**, so a
   default install still shows an uncoloured VM table and fires nothing.
4. **vms MEM — a derived `memory_percent` field, exactly like `containers`.**
   v4 colours MEM with `get_alert(memory_usage, maximum=memory_total)`, i.e. a
   percentage of that VM's own limit. `normalize_by` would force ratio-valued
   thresholds (0..1) and break the percentage-valued config keys v4 documents
   (`mem_careful=20`), so the model computes the percentage into its own field,
   as `containers/model_v5.py` does with `memory_percent` +
   `threshold_field: "mem"`.

---

## Global constraints

- **Never commit, never push.** Stage your work with `git add <files>` and stop.
  The maintainer commits personally.
- **TDD.** Write the failing test first, watch it fail for the right reason, then
  implement. A test that passes before the implementation is not a test of this
  change.
- **Surgical diffs.** Only lines that trace to this plan. Do not reformat, do not
  "improve" neighbouring code, do not touch `NEWS.rst` (release-time file, off
  limits during development).
- **No new configuration keys.** Every key used here already exists in v4 and in
  `conf/glances.conf`.
- **No default-behaviour change** beyond what the ported v4 commit itself
  changes.
- Follow the file's existing style (type hints, `ClassVar`, docstring tone).
- Run the targeted test files (`python -m pytest <files> -q`) and report the
  command and its output. New test files that carry a shebang must be `chmod +x`.
- Line length limit is 120 (ruff).

---

## Task 1 — npu: alert on the temperature both interfaces already ask for

**Ports v4 `20555568`.**

**Files:** `glances/plugins/npu/model_v5.py`,
`glances/plugins/npu/render_curses_v5.py`, `tests/test_plugin_npu_v5.py`,
`tests/test_plugin_npu_render_curses_v5.py`.

**v4 behaviour to reproduce:** the NPU temperature is compared against
`[npu] temperature_careful=60 / temperature_warning=70 / temperature_critical=80`
(already present in `conf/glances.conf`) and the reading is coloured accordingly.

**Model change** — in `glances/plugins/npu/model_v5.py`:

- Add a module-level ladder next to `_PERCENT_THRESHOLDS`, copying the wording of
  `gpu/model_v5.py:34`:
  ```python
  # NPU temperature ladder — exact v4 conf/glances.conf [npu] defaults.
  _TEMP_THRESHOLDS = {"careful": 60.0, "warning": 70.0, "critical": 80.0}
  ```
- Replace the `temperature` field declaration with the `gpu` shape:
  ```python
  "temperature": {
      "description": "NPU temperature.",
      "short_name": "temperature",
      "unit": "celsius",
      "watched": True,
      "watch_direction": "high",
      "prominent": False,
      "default_thresholds": _TEMP_THRESHOLDS,
  },
  ```
  (`internal: True` is dropped for this field only.)

**Renderer change** — in `glances/plugins/npu/render_curses_v5.py`:

- The temperature cell (around line 93-97) must be coloured from the item's level
  in `_levels`, the same way the other npu values already are. Use the helper the
  file already uses for `load` / `freq` / `mem`; do not introduce a second
  mechanism.
- The comment `temperature (never watched in v4 — default colour)` is now false —
  replace it with one line saying the temperature is watched (v4 `20555568`).

**Tests** (add to the existing files, do not create new ones):

- `tests/test_plugin_npu_v5.py`:
  - `temperature` is watched and carries the 60/70/80 defaults;
  - a payload with `temperature=75` on an NPU yields
    `_levels[<npu_id>]["temperature"]["level"] == "warning"`;
  - `temperature=50` yields `ok`;
  - a `[npu] temperature_critical=…` config override wins over the default.
- `tests/test_plugin_npu_render_curses_v5.py`: an NPU at a critical temperature
  renders the temperature cell in the critical colour role, and one at 50 °C in
  the default/ok role.

**Verify:** `python -m pytest tests/test_plugin_npu_v5.py tests/test_plugin_npu_render_curses_v5.py -q`

---

## Task 2 — quicklook: colour each `--percpu` bar by that core's own load

**Ports v4 `26a9fe96`.**

**Files:** `glances/plugins/quicklook/model_v5.py`,
`glances/plugins/quicklook/render_curses_v5.py`,
`tests/test_plugin_quicklook_v5.py`,
`tests/test_plugin_quicklook_render_curses_v5.py`.

**The defect:** `render_curses_v5.py:192` computes `role = _role_for(payload,
"cpu")` **once** and paints every per-core bar and the `CPU*` mean row with it.
A core pegged at 100 % is painted with the colour of the average.

**Model change** — in `glances/plugins/quicklook/model_v5.py`:

- Read `[percpu] max_cpu_display` (v4 key, `glances/plugins/quicklook/__init__.py:108`,
  default `4`) once, in `__init__`.
- Each item of the `percpu` payload list gains a `level` key: the level of that
  core's own `total`, computed against the **same resolved thresholds as the
  `cpu` field** (config overrides included — reuse the base-class threshold
  resolution, do not re-read the config per core, and do not hardcode
  `_PERCENT_THRESHOLDS`).
- Add two internal, non-watched fields, declared in `fields_description` next to
  `percpu`:
  - `percpu_other`: `{"total": <mean of the hidden cores>, "level": <level>}`
    when there are more cores than `max_cpu_display`, `None` otherwise. The
    hidden cores are the ones left after sorting by `total` descending and
    keeping the first `max_cpu_display` — v4 `_build_percpu_decoration`.
  - `max_cpu_display`: the configured value, so the renderer cuts the same set
    the model levelled.
- `EMITS_ALERTS` stays `False`: no per-core value may reach the alert pipeline or
  the history. (v4 went out of its way to avoid `get_alert()` here for the same
  reason; in v5 the flag is enough.)

**Renderer change** — in `glances/plugins/quicklook/render_curses_v5.py`:

- `_per_cpu_rows` takes the cut from `payload["max_cpu_display"]` when present
  (falling back to the existing `_DEFAULT_MAX_CPU_DISPLAY`), colours each bar from
  its own `core["level"]`, and colours the `CPU*` row from
  `payload["percpu_other"]["level"]`, using its `total` as the bar value.
- Remove the now-resolved `TODO(G2+)` comment about `max_cpu_display`.
- A payload from an older server (no `level`, no `percpu_other`) must still
  render — fall back to the current behaviour rather than raising.

**Tests:**

- `tests/test_plugin_quicklook_v5.py`: with cores at `[95, 10, 5, 2, 1]`,
  `max_cpu_display=4` and the default ladder, the first core's `level` is
  `critical` while the second is `ok`; `percpu_other` carries the mean of the
  hidden cores and its own level; with 4 cores or fewer, `percpu_other is None`;
  a `[quicklook] critical=…` override changes the per-core levels too.
- `tests/test_plugin_quicklook_render_curses_v5.py`: with `--percpu`, the bar of
  a core at 95 % is painted with the critical role while the aggregate `cpu`
  level is `ok` (this is the regression the v4 commit fixes), and the `CPU*` row
  takes `percpu_other`'s role.

**Verify:** `python -m pytest tests/test_plugin_quicklook_v5.py tests/test_plugin_quicklook_render_curses_v5.py -q`

---

## Task 3 — vms: colour the columns the renderer already prints

**Ports v4 `f8657a0a` + `ef11e7d4`.**

**Files:** `glances/plugins/vms/model_v5.py`,
`glances/plugins/vms/render_curses_v5.py`, `tests/test_plugin_vms_v5.py`,
`tests/test_plugin_vms_render_curses_v5.py`.

**v4 behaviour to reproduce:** CPU, MEM and LOAD of each VM are coloured from
`[vms]` thresholds, with the same per-item override shape as `containers`
(`<vmname>_mem_careful=10`). The shipped keys are **commented out**, so a default
install is unchanged: no threshold configured → no colour, nothing fires.

**Model change** — in `glances/plugins/vms/model_v5.py`:

- `EMITS_ALERTS` becomes `True` (see decision 3 above; update the class docstring
  line that states the opposite).
- `cpu_time` (already `rate: True`, unit percent) becomes
  `watched: True`, `watch_direction: "high"`, `prominent: False`,
  `threshold_field: "cpu"`. **No `default_thresholds`** — like `containers`,
  thresholds exist only when the operator configures them.
- Add a derived field `memory_percent` (unit percent, description in the style of
  the `containers` one), computed by the model as
  `100 * memory_usage / memory_total` when `memory_total` is a non-zero number,
  `None` otherwise. Declare it `watched: True`, `watch_direction: "high"`,
  `prominent: False`, `threshold_field: "mem"`.
- `load_1min` becomes `watched: True`, `watch_direction: "high"`,
  `prominent: False`, `threshold_field: "load"`. `load_5min` / `load_15min` stay
  unwatched (v4 only alerts on the 1 min value).
- A VM whose engine reports no value (`None` — no load, or a `cpu_time` rate with
  no previous sample yet) must be left **uncoloured**, never painted as idle.
  Confirm the base class already skips `None` values; if it does, say so in the
  report rather than adding a guard.

**Renderer change** — in `glances/plugins/vms/render_curses_v5.py`:

- The CPU%, MEM and LOAD cells take their colour from the item's `_levels`
  entry (`cpu_time`, `memory_percent`, `load_1min`). The status cell keeps its
  own `_status_role` mapping — do not touch it.
- Update the module docstring line that says the payload carries no `_levels`.

**Tests:**

- `tests/test_plugin_vms_v5.py`: with `[vms] cpu_careful=50 / cpu_warning=70 /
  cpu_critical=90`, a VM at 95 % `cpu_time` levels `critical`; `memory_percent`
  is computed from `memory_usage` / `memory_total` and levels against `mem_*`; a
  per-VM key (`<vmname>_mem_careful=10`) overrides the plugin-wide one; with **no**
  threshold configured (the shipped default) no level is produced for any of the
  three fields; a VM with `load_1min = None` produces no load level;
  `memory_total` of `0` or `None` yields `memory_percent is None`.
- `tests/test_plugin_vms_render_curses_v5.py`: the three cells carry the colour
  role of their level, and an unconfigured (default) install still renders the
  table with default-coloured cells.

**Verify:** `python -m pytest tests/test_plugin_vms_v5.py tests/test_plugin_vms_render_curses_v5.py -q`

---

## Done bar (whole plan)

- [ ] The three ports implemented, each with tests that fail before and pass after.
- [ ] `python -m pytest tests/ -q` green (no regression elsewhere).
- [ ] `make pre-commit` run at the end of the phase, on the staged index.
- [ ] Everything **staged, not committed**.
