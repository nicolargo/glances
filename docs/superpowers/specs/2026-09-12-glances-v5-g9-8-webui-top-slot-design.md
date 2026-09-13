# G9-8 — v5 WebUI top row, batch 2 (`mpp`, `npu`, `percpu`, `quicklook`): Design

**Status:** approved (2026-09-12)
**Sub-project of:** G9 (see the G9-1 spec §2.1 for the decomposition)
**Predecessors:** `2026-09-06-glances-v5-g9-4-webui-plugins-design.md`,
`2026-09-11-glances-v5-g9-5-webui-layout-header-design.md`,
`2026-09-12-glances-v5-webui-horizontal-degradation-design.md`,
`2026-09-12-glances-v5-g9-7-webui-left-sidebar-2-design.md`

---

## 1. Goals

G9-7 closed the left column. The `top` slot still holds five of its nine
plugins (`cpu`, `gpu`, `mem`, `memswap`, `load`); G9-8 ports the remaining
four and **closes the top row**, taking the WebUI from 21 to 25 of the 32
plugins. Only `RIGHT_SLOT` will remain.

    TOP_SLOT = quicklook, cpu, percpu, npu, mpp, gpu, mem, memswap, load
                  ^^^^^^^^^      ^^^^^^  ^^^  ^^^
                  this group ports these four

It also settles three things the earlier groups deferred or got wrong:

1. **The WebUI's first bar block.** `quicklook` is the only plugin that
   draws a bar, and §3 decides what a bar is in a browser.
2. **`[percpu] max_cpu_display` reaches `percpu`.** `quicklook` already
   honours it; `percpu` never has (§5, a `TODO(G2+)` in its renderer).
3. **The degradation cascade's two `quicklook` steps become real** (§7).
   `js/v5/degrade.js` declares them `notApplicable`, and
   `tests/test_webui_v5_degrade_drift.py` is written to go RED the day
   `quicklook` is rendered. That day is this group.

## 2. Out of scope

- **Browser keyboard shortcuts.** The TUI toggles `full_quicklook` with
  the `4` key (`glances/outputs/glances_curses_v5.py:159`). The WebUI has
  no key handling at all today, and adding it is a subsystem of its own
  (which keys, persistence, accessibility, conflicts). The WebUI renders
  the state the server publishes — §6.
- **The empty-collection v4 non-regression in the other five left-column
  blocks** (`network`, `wifi`, `diskio`, `fs`, `sensors` still build
  `rows = [header]` unconditionally). Found during the G9-7 review, tracked
  as its own issue.
- **A history sparkline for `quicklook`.** v4 has one behind
  `[quicklook] sparkline=true`; the v5 TUI renderer dropped it (its own
  docstring says so, "minus the GPU section and the sparkline history
  path"). Porting it to the WebUI alone would put the browser ahead of the
  terminal, which inverts this project's parity rule.
- **`bar_char` / `percent_char`.** `[quicklook] bar_char` picks the glyph
  the terminal draws a bar with, and the schema publishes it. A browser bar
  has no glyph; the field stays in the payload, unread by the WebUI. Stated
  divergence, §3.

## 3. Decisions taken before design (2026-09-12)

| # | Decision | Consequence |
|---|---|---|
| D1 | **A bar is a proportional CSS element**, not copied terminal characters and not a sparkline | §4. The maintainer chose it over a verbatim `[\|\|\|\|\|    45.0%]` string and over the CLAUDE.md "sparklines with an inline value" principle: the TUI's bar rendered with the browser's means, exactly as `.gl-truncate` renders the TUI's ellipsis with the browser's means |
| D2 | **`full_quicklook` mirrors the server, with no keyboard** | §6. `/api/5/args` already dumps the whole argparse namespace (`glances/routes_v5.py:175,227`), so `--full-quicklook` (`glances/main_v5.py:208`) is already on the wire |
| D3 | **`[percpu] max_cpu_display` is fixed for `percpu` in this group** | §5. NOT for `quicklook`: it already reads the key (`quicklook/model_v5.py:261`), publishes it (`:316`) and its renderer honours it |
| D4 | **The quicklook↔percpu interaction is implemented in this group** | §5.2. v4's `percpu` drops its `CPU` title, its `total` column and its row labels when quicklook is enabled (`glances/plugins/percpu/__init__.py:158,183,210`); v5 never did |
| D5 | **`percpu` learns quicklook's state from the plugins actually rendered** | §5.3. The TUI painter knows its own top-slot blocks; the WebUI has had `/api/5/pluginslist` since G9-5. No new config key, no new CLI flag |

## 4. The bar (D1)

`quicklook` is the first WebUI block with a bar, so the shape decided here
is the one any later bar reuses.

One bar row is three parts on one line:

    label (4ch)   track (fills the remaining width)   value (right-aligned)

- **The track** is a container with a fill element whose `width` is the
  percentage itself. The fill's background is the field's tier colour, taken
  from `_levels` through the existing `levelClass` helper — never a colour
  literal, which `tests/test_webui_v5_tokens.py` enforces anyway. The track's
  own background is the existing muted surface token.
- **The value** carries the same tier class every other value cell in the
  WebUI carries, so a `prominent` field still renders as the tier badge the
  rest of the UI uses.
- **The label** is the TUI's 4-char label, including its two renamed keys:
  `gpu_mem` → `GMEM` and `gpu_proc` → `GPU` (`quicklook/render_curses_v5.py`
  `_BAR_LABEL`) — the raw upper-cased keys are 7 chars and would break the
  grid in the terminal; in the browser they would merely look wrong, and
  the two surfaces must read the same.
- **Which bars, in which order**, comes from the payload's `stats_list`
  (the model fills it from `[quicklook] list`), with the renderer's
  `_BAR_KEYS` order as the fallback for a payload that lacks the field.

The bar is a visual element with a numeric meaning, so it carries the ARIA
role for a progress indicator with its value, not a bare `<div>`: the value
text alone is not attached to the track for a screen reader otherwise.

## 5. `percpu`, and what it never learned

### 5.1 `max_cpu_display` (D3)

`[percpu] max_cpu_display` caps how many cores are listed before the rest
collapse into a single mean row. Today:

| | reads the key | publishes it | renderer honours it |
|---|---|---|---|
| `quicklook` | yes (`model_v5.py:261`) | yes (`:316`) | yes (`render_curses_v5.py`, `payload.get("max_cpu_display")`) |
| `percpu` | **no** | **no** | **no** — `_DEFAULT_MAX_CPU_DISPLAY = 4`, with a `TODO(G2+)` saying so |

So the key works in the quicklook per-core view and is inert in the `percpu`
block. The fix is the shape `quicklook` already uses: `percpu`'s model reads
`[percpu] max_cpu_display` and publishes it as an `internal` field, its
renderer reads it from the payload with the existing constant as the
fallback for an older server, and the WebUI component reads the same field.
`percpu`'s renderer docstring loses the `max_cpu_display` half of its TODO.

### 5.2 The quicklook interaction (D4) — corrected after the final review

v4's `percpu` renders differently depending on whether `quicklook` is
enabled — three places, all gated on `self.is_disabled('quicklook')`:

| v4 line | When quicklook is DISABLED | When quicklook is ENABLED |
|---|---|---|
| `:158-161` | a `CPU` title cell, and `total` inserted as the first column | neither |
| `:183-191` | each row starts with its `CPU0` / `12` label | no row label |
| `:210-211` | the mean row starts with `CPU*` | no label |

The reason is not cosmetic: with quicklook on (the default), quicklook
already shows the per-core totals, so `percpu` drops the repetition. In v4
this is safe to gate on "quicklook enabled" alone because ONE flag
(`args.percpu`) governs both things at once: whenever `percpu` is on
screen, quicklook is necessarily drawing the per-core bars whose
`CPU0`/`CPU*` labels the table borrows.

v5 split that one flag into two independent ones — `_view.show_percpu`
(the TOP-row cpu/percpu toggle, hotkey `1`) and `_percpu`/`--percpu` (which
gates quicklook's per-core bars) — so "quicklook is instantiated" and
"quicklook is drawing per-core bars" are no longer the same fact. The
predicate must therefore be narrowed to what v4 can actually reach:
quicklook present **and** actually drawing per-core bars, i.e.
`view["quicklook_enabled"]` requires BOTH `quicklook` being instantiated
AND `view["percpu"]` (`--percpu`) being set. Gating on "quicklook
instantiated" alone — the first cut of this group — fires in a state v4
can never reach (quicklook on screen but showing only the aggregate `cpu`
bar) and silently drops `percpu`'s title, `total` column and row labels for
no reason: a regression against pre-G9-8 v5, which always painted them.

This group implements the (corrected) rule in the TUI renderer and mirrors
it in the component. The remaining columns keep the OS-specific order
`_os_headers()` already computes.

### 5.3 How `percpu` learns it (D5)

The state is "is `quicklook` among the plugins being shown **and** is it
drawing per-core bars" — the second half is a CLI flag, and both surfaces
already have access to both facts:

- **TUI**: the painter builds the frame's top-slot blocks, so it knows
  whether a `quicklook` block exists; it passes that answer, ANDed with
  `view["percpu"]` (`self._percpu`, seeded from `--percpu`), to `percpu` in
  the `view` dict the renderer already accepts.
- **WebUI**: `/api/5/pluginslist` (G9-5) lists the instantiated plugins and
  `AppShell` already filters the registry with it; `serverArgs.percpu`
  (`--percpu`, from `/api/5/args`) is the second half. The `percpu`
  component reads both: `standalone` is true unless quicklook is
  instantiated AND `serverArgs.percpu` is set.

A `quicklook` that is disabled, that renders nothing on a machine with no
data, or that is merely showing the aggregate `cpu` bar (no `--percpu`),
therefore gives `percpu` its title and its `total` column back — matching
v4's behaviour, since in v4 all three of those states also leave `percpu`
un-repeated-by-quicklook.

### 5.4 `cpu` ↔ `percpu` mutual exclusion (Critical 1 fix, not considered by the original design)

Neither the original design nor any per-task review considered that the
TUI shows exactly ONE of `cpu` / `percpu` in the TOP row —
`glances_curses_v5.py:565-567` drops one of them from `frame.top` on every
frame: `hidden_top = "cpu" if self._view.show_percpu else "percpu"`. The
WebUI registered `percpu` as an unconditional TOP entry, so both blocks
rendered side by side: a duplicated CPU surface on the default screen.

The TUI's own signal, `show_percpu`, is a runtime hotkey toggle (`1`) with
no server-side representation — out of scope here (§2, no browser hotkey
handling) — so the browser cannot mirror it exactly. The best available
server-side signal is `serverArgs.percpu` (`--percpu`), which is also what
gates quicklook's per-core view (§5.3): `AppShell`'s `slots()` computed
hides `percpu` when `serverArgs.percpu` is falsy, and hides `cpu` when it
is set. This is an accepted approximation, not v4/TUI parity: a server
started with `--percpu` still boots the TUI showing the aggregate `cpu`
block until the operator presses `1`, so a WebUI viewer and a TUI viewer of
the same `--percpu` server can legitimately see different blocks. The v4
WebUI does not help here either — its equivalent block is commented out
(`glances/outputs/static/js/App.vue:43-52`), so v4's WebUI renders no
`percpu` at all.

## 6. `full_quicklook` (D2)

`--full-quicklook` makes `quicklook` take the full width and hides
`cpu`, `npu`, `mpp`, `gpu`, `mem`, `memswap` — and deliberately NOT `load`
and `percpu` (`curses_renderer_v5.py:89`, exact v4 parity). `/api/5/args`
dumps the argparse namespace, so the flag reaches the browser with no
server change; the component reads it from the `serverArgs` prop every
plugin component already declares, the way `mem` reads `--byte` and
`sensors` reads `--fahrenheit`.

The shell hides the six blocks the same way the horizontal-degradation
group hides a block (`HIDDEN_BY`), so the two mechanisms compose instead of
fighting: a block hidden by `full_quicklook` is hidden whatever the
cascade then decides.

The TUI's `4` key is out of scope (§2): with no browser key handling, the
WebUI reflects the server's startup state and nothing more.

## 7. The degradation cascade (§4 of the degradation spec)

`js/v5/degrade.js` carries the TUI's cascade verbatim, including two steps
it cannot act on:

```
{ key: "quicklook_freq_only", value: true, notApplicable: true },
{ key: "hide_quicklook",      value: true, notApplicable: true },
```

`tests/test_webui_v5_degrade_drift.py::test_only_the_unported_steps_are_marked_not_applicable`
was believed to fail as soon as `quicklook` renders. **It does not** — verified
during implementation: it compares `degrade.js`'s static step list against the
Python tuples and never looks at the plugin registry or the DOM, so porting
quicklook leaves it green with a dead cascade. The guard this group was counting
on has to be BUILT, not merely satisfied. This group:

1. implements `quicklook_freq_only` — the header collapses to the frequency
   alone, dropping the CPU name (the TUI's own `freq_only` branch);
2. implements `hide_quicklook` — `AppShell` hides the whole block, the last
   notch before the top row crops;
3. removes both `notApplicable` flags and the comment that explains them.

4. adds the assertion that was missing all along: no step may be marked
   `notApplicable` for a plugin the JS registry actually renders. That turns the
   file into a real bidirectional guard — today it makes the two removals
   mandatory, and in future it goes red the day someone flags a step for a
   plugin that is on screen.

## 8. Per-plugin parity

The authority for each is its `render_curses_v5.py`.

### 8.1 `mpp` — `mpp/render_curses_v5.py` (58 lines)

Collection, `_key` = `engine_id`. Title row `MPP`, then one row per engine:
the name left-justified in 8 and the type right-justified in 5 (one cell in
the TUI), the load as `NN.N%` or `N/A` when null, and a `N sess` cell that
v4 **omits entirely** when the session count is zero. The load is the only
coloured value, from `_levels[engine_id].load`. An empty collection renders
nothing (the renderer returns `[]`).

### 8.2 `npu` — `npu/render_curses_v5.py` (106 lines)

Scalar in effect: the renderer shows **the first NPU only**, v4 parity, even
when the payload carries several. Four lines: the name truncated to 17
chars as the header; the load percentage — or the frequency percentage when
`load` is null — followed by the `current/max` frequency range; `mem:`; and
`temperature:`, which honours `--fahrenheit` like `sensors` does. `N/A` for
every missing value, in the TUI's own width.

### 8.3 `percpu` — `percpu/render_curses_v5.py` (160 lines)

Collection, `_key` = `cpu_number`, rendered as the TUI's transposed grid:
columns are the OS-specific stat fields (`_os_headers()`), rows are cores.
Top-N by `total` descending when there are more cores than
`max_cpu_display` (§5.1), then one mean row for the rest. **No tier colour
anywhere**: v5 `percpu` publishes no field-level alert and the system-wide
`cpu` plugin is the source of CPU alerts. Title, `total` column and row
labels follow §5.2.

### 8.4 `quicklook` — `quicklook/render_curses_v5.py` (224 lines)

Scalar. In order:

1. **The header** — the CPU name (`cpu_name`) and its frequency
   (`cpu_hz_current` / `cpu_hz`), or the frequency alone under
   `quicklook_freq_only` (§7). Absent when the payload carries neither.
2. **The bars** — `stats_list` decides which of `cpu`, `mem`, `swap`,
   `load`, `gpu_mem`, `gpu_proc` are drawn and in which order (§4).
3. **The per-core view** — one bar per core when the payload carries
   `percpu`, capped by `max_cpu_display`, sorted by `total` descending when
   the cap bites, plus the `percpu_other` mean row the model publishes for
   the hidden ones.

An empty payload renders nothing in the WebUI. (The TUI renderer returns a
bare `CPU` header row for an empty payload — the same shape G9-7 fixed in
`raid`/`smart`. It is left alone here: the fix belongs with the other five
blocks in the tracking issue from §2, and changing it in this group would
ship a sixth unreviewed TUI change.)

## 9. Registry, layout, degradation

- Four registry entries in `js/v5/plugins/index.js`, in `TOP_SLOT` order:
  `quicklook` first, then `cpu`, `percpu`, `npu`, `mpp`, then the existing
  rest. `test_every_slot_orders_its_plugins_like_the_tui` reads the real
  tuple and covers it unchanged.
- Shapes: `quicklook` scalar, `npu` collection with `required: ["npu_id"]`
  (the component shows the first item), `mpp` collection
  (`required: ["engine_id"]`), `percpu` collection
  (`required: ["cpu_number"]`).
- The three hardcoded registry lists in `tests/test_webui_v5_render.py`
  grow from 21 to 25 names.
- `quicklook` is the widest new block; the top row's cascade already has
  its two steps (§7). The other three hide as whole blocks, like every
  other top-slot plugin.

## 10. Tests

| Level | What |
|---|---|
| Render (per plugin) | a populated payload and an empty one; `mpp` a null load and a zero session count; `npu` a second NPU that must NOT render, a null load falling back to the frequency percentage, `--fahrenheit`; `percpu` the top-N cut with its mean row, and both quicklook states (§5.2); `quicklook` each bar in `stats_list`, the per-core view, the header with and without `freq_only` |
| Bars | the fill's width equals the percentage, the tier class is on the fill, and a `prominent` value still renders its badge |
| `max_cpu_display` | a config value other than 4 changes what BOTH surfaces show — the test that makes the key non-inert |
| Degradation | the drift test passes with both steps live and neither flagged `notApplicable`; a narrow top row collapses the quicklook header to the frequency, then hides the block |
| `full_quicklook` | with the server flag set, the six blocks are hidden and `load`/`percpu` are not |
| TUI | `percpu`'s new tests for `max_cpu_display` and for the quicklook interaction; the existing suites unchanged |

## 11. Risks

| Risk | Mitigation |
|---|---|
| The bar becomes a component-local invention that the next bar block re-invents | §4 fixes the three-part shape and puts the CSS in `css/v5.css`, not in a scoped block |
| `percpu`'s two new behaviours are conflated | §5.1 and §5.2 are separate decisions with separate tests; one can be true without the other |
| The quicklook state reaches `percpu` by a different route on each surface, and the two drift | §5.3 names one source of truth — the rendered plugin list — and both surfaces already expose it |
| The cascade's two steps are wired but never exercised | §7's drift test plus a render test at a width that forces each notch |
| `full_quicklook` and the horizontal cascade fight over the same blocks | §6: `full_quicklook` hides through the same mechanism the cascade uses, and is applied first |

## 12. Success criteria

1. The nine `TOP_SLOT` plugins all render in the WebUI, in the TUI's order.
2. Each of the four new blocks matches its `render_curses_v5.py` on the
   cases in §10, with the terminal open beside the browser.
3. `[percpu] max_cpu_display=2` visibly changes both surfaces.
4. `--full-quicklook` gives the browser the same six hidden blocks as the
   terminal.
5. `tests/test_webui_v5_degrade_drift.py` passes with no `notApplicable`
   step left.
6. The full suite is green and `make pre-commit` is clean.
7. Owed afterwards: a browser smoke of the four blocks (a many-core box, a
   machine with no NPU/MPP, `--full-quicklook`, a narrow viewport, both
   themes).
