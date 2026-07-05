# Glances v5 — G4A-1 design: `gpu` + `npu` + quicklook GPU addendum + cascade step (g)

> Spec for Phase 2 group **G4A-1**. Follows the mirror-v4 rule (read v4
> `msg_curse()` first), the no-dead-code rule, and the two-phase refactoring
> strategy. `sensors` is deferred to a separate **G4A-2** spec.

**Goal:** Port the v4 `gpu` and `npu` plugins to v5 (top-row), add the GPU
addendum to the v5 quicklook, and extend the responsive top-row degradation
cascade with a final `hide_gpu` step.

**Architecture:** Both plugins are v5 collections that *reuse the existing v4
hardware grabbers* (`gpu/cards/*`, `npu/cards/*`) as pure collectors, called
from an async `_grab_stats` via `asyncio.to_thread`. The quicklook GPU means
flow through the v5 stats store (quicklook reads the `gpu` plugin's published
cards) — **not** through a global mutable module. The cascade gains a measured
`hide_gpu` last-resort step.

**Tech stack:** Python, asyncio, psutil/pynvml/sysfs (via reused v4 grabbers),
curses TUI v5 (`Frame`/`PluginBlock`/`Row`/`Cell`), pytest.

---

## Decisions locked (2026-07-05, maintainer)

1. **Decomposition** — G4A is split: **G4A-1** = `gpu` + `npu` + quicklook GPU
   addendum + cascade step (g). **G4A-2** = `sensors` (separate spec/plan/branch).
2. **Backends** — the v5 models **reuse the v4 hardware grabbers** (`cards/`
   modules) as pure collectors. No rewrite of NVML/sysfs code. The v4 plugin
   `__init__.py` orchestration is *not* reused — only the per-card
   `get_device_stats()` collectors. Coupling to v4 card internals is accepted
   and will be deprecated in Phase 3.
3. **Quicklook GPU channel** — quicklook reads `self.store.get("gpu")` and
   computes the `gpu_mem`/`gpu_proc` means itself. The v4 `glances.gpu_percent`
   global mutable channel is **abandoned** (global-mutable anti-pattern).
4. **Quicklook GPU default** — GPU bars **auto-show** when the `gpu` plugin
   publishes at least one card AND `gpu` is not disabled (`--disable-gpu`). No
   new config key. This is a slight default change vs v4 (which hid GPU behind
   `[quicklook] list`), but only affects machines with a GPU, where the info is
   useful.

---

## Shared v4 facts (grounding)

- **v4 top-row order** (`glances/outputs/glances_curses.py:110`):
  `quicklook, cpu, percpu, npu, mpp, gpu, mem, memswap, load`.
- **v5 `TOP_SLOT`** (`curses_renderer_v5.py:56`) currently:
  `("quicklook","cpu","percpu","gpu","mem","memswap","load")` — `gpu` slot
  already reserved; `npu` and `mpp` absent. G4A-1 inserts `npu` after `percpu`,
  before `gpu`. (`mpp` stays out until G6.)
- **v5 store API**: `store.get(plugin_name, default)` (sync) — a plugin reads
  another plugin's last published payload. `self.store` available on every
  `GlancesPluginBase` (`base_v5.py:104`).
- **v5 alerts**: `_levels` from `fields_description` thresholds drive both TUI
  colouring and the alert engine. `EMITS_ALERTS` opt-out exists.

---

## Component 1 — `gpu` plugin (v5 collection)

**Files:**
- Create: `glances/plugins/gpu/model_v5.py`
- Create: `glances/plugins/gpu/render_curses_v5.py`
- Test: `tests/test_plugin_gpu_v5.py`, `tests/test_plugin_gpu_render_curses_v5.py`

### Model
- `PluginModel(GlancesPluginBase[list])`, `plugin_name="gpu"`,
  `IS_COLLECTION=True`, `_primary_key="gpu_id"`.
- `_grab_stats`: instantiate the reused v4 card backends
  (`nvidia.NvidiaGPU`, `amd.AmdGPU`, `intel.IntelGPU`, `arm.ArmGPU`) once (in
  `__init__`, guarded — failed init leaves the backend out), then each cycle
  call every available backend's `get_device_stats()` inside
  `asyncio.to_thread` and concatenate the returned card dicts. Each backend
  call independently try/except-guarded so one failing GPU never drops others.
- **Fields** (`fields_description`): `gpu_id` (key), `name` (`internal:True`),
  `mem` (watched, %, thresholds 50/70/90, `prominent:True`),
  `proc` (watched, %, same ladder), `temperature` (watched, °C — thresholds
  **60/70/80** careful/warning/critical, exact v4 `conf/glances.conf` `[gpu]`
  defaults), `fan_speed` (`internal:True, watched:False`).
- **No** write to any global module (v4's `gpu_percent` side effect is dropped).

### Renderer (`render(payload, fields_desc, view=None)`)
Mirror v4 `msg_curse()` (`gpu/__init__.py:343`):
- Empty payload → `[]`.
- Header row: replicate `_build_header` — >1 card same name → `"N NAME"`;
  >1 differing → `"N GPUs"`; single → the name; truncated 17 chars;
  `ColorRole.HEADER`.
- **Summary mode** (`len(cards)==1` OR `view["meangpu"]`): 3 rows via a helper
  mirroring `_add_metric_line`/`_format_value` — `proc`/`proc mean`,
  `mem`/`mem mean`, `temperature`/`temp mean`. Values coloured from
  `payload["_levels"][gpu_id][field]["level"]`. `N/A` when None. Fahrenheit on
  temperature when `view["fahrenheit"]`.
- **Multi mode** (else): one row per card — id column `name[0:9]` width 7, then
  ` {proc}` and ` mem {mem}` each coloured by that card's level.

### Placement
`gpu` already in `TOP_SLOT`. No slot change needed for gpu itself.

---

## Component 2 — `npu` plugin (v5 collection)

**Files:**
- Create: `glances/plugins/npu/model_v5.py`
- Create: `glances/plugins/npu/render_curses_v5.py`
- Modify: `glances/outputs/curses_renderer_v5.py` (insert `"npu"` into `TOP_SLOT`)
- Test: `tests/test_plugin_npu_v5.py`, `tests/test_plugin_npu_render_curses_v5.py`

### Model
- `PluginModel(GlancesPluginBase[list])`, `plugin_name="npu"`,
  `IS_COLLECTION=True`, `_primary_key="npu_id"`.
- `_grab_stats`: reuse `npu/cards/{amd,intel,rockchip}.py`. These cards use an
  availability model (`is_available()`, `get_device_stats()`, `disable()` on
  error). Instantiate once (with default root `/`); each cycle call available
  cards via `asyncio.to_thread`, append each returned dict.
- **Fields**: `npu_id` (key), `name` (`internal`), `load` (watched %, 50/70/90),
  `freq` (watched %, 50/70/90), `freq_current`/`freq_max` (`internal`, Hz),
  `mem` (watched %, 50/70/90), `temperature`/`power` (`internal`).
- **Default-disabled**: v4 ships `[npu] disable=True` — NPU is OFF by default.
  Mirror this in v5 (the plugin exists and is discovered, but collects/publishes
  nothing unless enabled). With no data the renderer returns `[]`, so keeping
  `npu` in `TOP_SLOT` is harmless when disabled.

### Renderer
Mirror v4 `msg_curse()` (`npu/__init__.py:200`) — renders **first card only**:
- Header: `payload["data"][0]["name"][:17]`, `HEADER`.
- Row 2: if `load is not None` → `load%` (level-coloured); else `freq%`. Then
  right-justified `cur/maxHz` via a Hz auto-unit helper, default colour.
- Row 3: `mem:` + `_format_value(mem, "%")`.
- Row 4: `temperature:` + `_format_value(temperature, "C")`.
- `_format_value`: `N/A` when None, else `f"{v:>4.0f}{unit}"`.

### Placement
Insert `"npu"` into `TOP_SLOT` after `"percpu"`, before `"gpu"`:
`("quicklook","cpu","percpu","npu","gpu","mem","memswap","load")`.
(`npu` is already in `_FULL_QUICKLOOK_HIDDEN` — no change there.)

---

## Component 3 — quicklook GPU addendum

**Files:**
- Modify: `glances/plugins/quicklook/model_v5.py`
- Modify: `glances/plugins/quicklook/render_curses_v5.py` (if needed for ordering)
- Test: extend `tests/test_plugin_quicklook_v5.py`,
  `tests/test_plugin_quicklook_render_curses_v5.py`

### Model
- Add `gpu_mem` and `gpu_proc` to `fields_description` — watched, %, standard
  50/70/90 ladder, `prominent:True`.
- In `_grab_stats` (after the existing cpu/mem/swap/load collection): read
  `cards = self.store.get("gpu")`. If it's a non-empty list AND gpu is not
  disabled, compute `gpu_mem = mean(non-None card["mem"])` and
  `gpu_proc = mean(non-None card["proc"])`, rounding to 1 decimal; set them in
  the returned dict. If no cards / all None / gpu disabled, omit the keys
  entirely (renderer then shows no GPU bar — the existing renderer already
  iterates only present percent fields).
- Disabled check: the model reads the gpu-disabled state from config/args the
  same way other plugins gate optional collection (resolve during planning —
  likely `self.args.disable_gpu` if the model has args, else skip the gate and
  rely on "no cards published"). If gpu is disabled it publishes nothing, so
  "no cards" already covers it; the explicit gate is a belt-and-suspenders.

### Renderer
The existing quicklook renderer draws one bar per present percent field in a
fixed order. Ensure `gpu_mem`/`gpu_proc` render **after** load (bottom of the
block), labelled `GPU_MEM` / `GPU_PROC` (v4 uses the upper-cased key). Colour
from `_levels`. Bars justify to header width like the others.

---

## Component 4 — cascade step (g) `hide_gpu`

**Files:**
- Modify: `glances/outputs/glances_curses_v5.py` (`_DEGRADE_STEPS`)
- Modify: `glances/outputs/curses_renderer_v5.py` (`build_frame` guard)
- Modify: `docs/architecture/tui-v4-rendering-patterns.md` (cascade table)
- Test: extend `tests/test_curses_v5.py`

- Append `("hide_gpu", True)` to `_DEGRADE_STEPS` **after** `("hide_memswap", True)`
  — gpu is hidden only as the very last resort. Remove the `TODO(G4A — gpu)`
  marker.
- In `build_frame`, add a `hide_gpu` guard skipping the gpu block, mirroring the
  existing `hide_quicklook` / `hide_memswap` guards.
- Update the cascade table in the docs to list step (g).

**Note on ordering**: gpu sits mid-top-row (after npu, before mem), not at the
edge. Hiding it removes its block and the measure pass re-fits the remainder —
no special positional handling needed since `_top_fits` re-measures the whole
row.

---

## Testing strategy

TDD throughout (`.venv/bin/python -m pytest`, `ruff check`/`format`).

- **gpu model**: card dicts assembled from mocked backends; one backend raising
  → others survive; watched vs internal fields; empty when no backend available.
- **gpu renderer**: summary mode (1 card) 3 rows; multi mode (2 cards) 2 rows;
  `_build_header` variants; Fahrenheit; `N/A` for None; level colouring.
- **npu model**: mocked cards; availability gating; first-card-only render input.
- **npu renderer**: load-present vs freq-fallback row; `cur/maxHz`; mem/temp rows.
- **npu placement**: `TOP_SLOT` contains `npu` after `percpu`, before `gpu`.
- **quicklook addendum**: means computed from a mocked `store.get("gpu")`;
  no `gpu` key when store empty / all-None; keys present when cards published;
  gpu bars byte-absent by default when no GPU (regression guard for non-GPU
  machines).
- **cascade step g**: on a terminal narrow enough that (a)–(f) don't fit, the
  gpu block is dropped; gpu stays visible whenever any earlier step suffices;
  `hide_gpu` is strictly last.

---

## Out of scope (explicit)

- `sensors` (→ G4A-2), `mpp` (→ G6).
- Rewriting hardware backends (reuse v4).
- A `[quicklook] list` config key (auto-show chosen instead).
- `NEWS.rst` (release-time only).
- Sparklines in quicklook GPU bars (no v5 history store yet).
