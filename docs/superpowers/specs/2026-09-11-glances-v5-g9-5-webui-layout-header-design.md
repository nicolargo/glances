# G9-5 — v5 WebUI page skeleton and header plugins: Design

**Status:** approved (2026-09-11); amended after the maintainer's smoke test, same day — see §14
**Sub-project of:** G9 (see the G9-1 spec §2.1 for the decomposition)
**Predecessors:** `2026-09-05-glances-v5-g9-1-webui-serving-design.md`, `2026-09-06-glances-v5-g9-2-webui-foundation-design.md`, `2026-09-06-glances-v5-g9-3-webui-scaling-design.md`, `2026-09-06-glances-v5-g9-4-webui-plugins-design.md`

---

## 1. Goals

After G9-4 the v5 WebUI renders six plugins as one flat `flex-wrap` run of
blocks (`AppShell.vue`, `.gl-plugins`). The TUI has a page structure — a
header line, a top row, a left and a right column — and the 28 remaining
ports have nowhere to land until the browser has one too.

G9-5 builds that structure and fills its first slot:

1. **The page skeleton** — header / top / left / right zones mirroring the
   TUI v5 slots, with the alert list staying in the footer.
2. **The header plugins** — `system`, `ip`, `uptime`, `cloud`, `now`: five
   one-line blocks, cheap enough that the skeleton is what gets tested.
3. **`/api/5/all/info`** — one schema request at page load instead of one per
   plugin. G9-4's closing report (E6) asked for it to open the next group:
   6 concurrent `/info` requests today, ~34 at full port, on the one path with
   no retry.
4. **Disabled plugins disappear** instead of loading forever (§6).

## 2. Out of scope

- **Width-driven hiding of blocks.** The TUI degrades its header in a cascade
  (`_HEADER_DEGRADE_STEPS`, `glances/outputs/glances_curses_v5.py:87-94`); the
  browser does not reproduce it (D3). Still deferred, as in G9-3 and G9-4.
- **`[outputs] left_menu`.** Absent from v5, the TUI included (parity
  inventory, `docs/architecture/glances-v5-v4-parity-inventory.md:378`). Stays
  in the parity backlog.
- **Runtime plugin toggling (#3548).** `pluginslist` is read once per page load
  (§6).
- **`system`'s "Disconnected from" line** — client mode, Phase 3.
- **Fixing `--hide-public-info`'s API exposure** — reported in §11, not fixed.
- **Splitting `tests/fixtures/webui_render_probe.js`** (E6 recommendation) —
  it grows again here; the split stays a recommendation.
- **Retiring the v4 Vue app** — Phase 4.

## 3. Decisions taken before design (2026-09-11)

| # | Decision | Consequence |
|---|---|---|
| D1 | **Scope: skeleton + header + `/api/5/all/info`** | The top row, sidebars and `processlist` wait for G9-6+; every later port lands in a slot that already exists |
| D2 | **Layout reference: the TUI v5 slots, alerts kept in the footer** | `cloud` sits in the header's right group (TUI), not on its own row (v4 WebUI). The footer stays a vertical alert list, per the project's UI principle, rather than the TUI's `alert` block in `RIGHT_SLOT` |
| D3 | **Narrow viewport: CSS only, nothing hidden** | Zones wrap and stack, long strings truncate with an ellipsis and keep their full text in `title`. Follows G9-4 §8.4: *a browser truncates with the layout; a terminal truncates with a slice* |
| D4 | **The slot lives in the JS registry** (`slot` attribute per entry, order = registry order) | A second copy of the TUI's tuples, guarded by a drift test (§10) — see §4 for the two rejected alternatives |
| D5 | **The G9-2 top bar ("Glances · refresh Ns") is removed**; the refresh cadence moves to the footer | The header zone replaces the bar; the page name is already in `<title>` |
| D6 | **Visibility = registry ∩ `/api/5/pluginslist`**, read once at mount | A disabled plugin is not rendered; a failed read degrades to today's behaviour |

## 4. Where the slot truth lives (D4)

Three options were weighed.

- **A — `slot` in `plugins/index.js`. Chosen.** No API, no Python file
  touched, no TUI risk. The cost is a second copy of
  `HEADER_SLOT_LEFT`/`HEADER_SLOT_RIGHT`/`TOP_SLOT`/`LEFT_SLOT`/`RIGHT_SLOT`
  (`glances/outputs/curses_renderer_v5.py:58-80`), so drift is caught by a
  test, not prevented by construction.
- **B — move the tuples to a neutral `glances/outputs/layout_v5.py` and serve
  them on `/api/5/layout`.** A single source for both renderers, and it would
  have made a future `left_menu` apply to both at once. Measured blast radius:
  one production importer (`glances_curses_v5.py:36`) and three test files,
  two of which monkeypatch `curses_renderer_v5.TOP_SLOT`
  (`tests/test_curses_renderer_v5.py:1565`, `:1614`) — feasible with a
  by-name re-import. Not chosen by the maintainer.
- **C — a `DISPLAY_SLOT` class attribute plus a rank on every `model_v5.py`.**
  34 model files, and an integer rank replacing an ordered list — the shape
  G9-3's final review already rejected for `priority`. Too wide for this group.

**Whoever revisits D4** (for instance when `left_menu` is ported) should start
from B: its blast radius is measured above.

## 5. Measured inputs

Read from the repository on 2026-09-11, not assumed:

| Plugin | Shape | TUI renderer | Empty/guard rule | Notes |
|---|---|---|---|---|
| `system` | scalar | `hostname` (HEADER role) + `hr_name` | no `hostname` → `[]` | `hr_name` already applies `[system] system_info_msg` server-side (`model_v5.py:114-122`) |
| `ip` | scalar | `IP` + `address/mask_cidr`; `Pub` + `public_address` (masked with `--hide-public-info`) + `public_info_human` | no cell → `[]` | `mask_cidr` `None` → bare address (`render_curses_v5.py:53`) |
| `uptime` | scalar | `Uptime:` + `format_value(seconds)` | `seconds is None` → `[]` | formatter `format_seconds`, `curses_formatters_v5.py:66-80` |
| `now` | scalar | `custom` | empty `custom` → `[]` | `iso` is REST-only |
| `cloud` | scalar | `platform` (HEADER, bold) + ` {type} instance {name} ({region})`, `Unknown` fallback | no `platform` or no `name` → `[]` (#2485) | `DISABLED_BY_DEFAULT = True` (`model_v5.py:100`) |

Three facts that shape the design:

- **A disabled plugin is never instantiated** (`glances/main_v5.py:372`), so
  it never appears in `/api/5/all`. `fetchAll()` (`api.js`) reads an absent
  plugin as *loading*. Today `--disable-plugin gpu` leaves `gpu` on
  "loading…" forever; `cloud`, disabled by default, would do the same for
  most users.
- **`/api/5/all` skips empty payloads** (`routes_v5.py`, `all_stats`). `cloud`
  on a non-cloud host publishes `{}` and is therefore absent from `/all` for
  the process lifetime — indistinguishable from cycle 0.
- **`/api/5/all/limits` is the precedent for a batch route**: declared before
  its dynamic `/{plugin_name}/…` twin, with `all` already in
  `_RESERVED_NAMES`.

## 6. Data flow

### 6.1 The registry

Each `PLUGINS` entry in `glances/outputs/static/js/v5/plugins/index.js` gains
`slot`, one of `header-left`, `header-right`, `top`, `left`, `right`. Order
within a slot is registry order, so the registry is reordered to follow the
TUI tuples:

| Slot | Entries, in order |
|---|---|
| `header-left` | `system`, `ip` |
| `header-right` | `uptime`, `cloud`, `now` |
| `top` | `cpu`, `gpu`, `mem`, `memswap`, `load` |
| `left` | `network` |
| `right` | — |

There is **no fallback slot**. The TUI's `slot_for()` sends an unknown plugin
to `left`; in the registry a missing or misspelled `slot` would silently drop
a block from every zone, so the drift test (§10) fails on it instead.

### 6.2 Page load

`AppShell.mounted` issues four requests, whatever the number of plugins
(today: `2 + N`):

| Request | Purpose | On failure |
|---|---|---|
| `api/5/config` | refresh cadence + theme (unchanged) | defaults |
| `api/5/args` | `serverArgs` (unchanged) | `{}` |
| `api/5/all/info` **(new)** | every plugin's schema in one request | `{}` — field names as labels |
| `api/5/pluginslist` **(newly used)**, via `resolvePluginNames()` in `api.js` | the plugins actually instantiated | `null` — render the whole registry, as today |

`labels.js`: `resolveLabels(pluginName)` is **replaced** by
`resolveAllLabels()`, which returns `{plugin: {field: label}}` with the same
`short_name` → `label` → field-name precedence. The per-plugin function would
have no caller left, so it is removed, and its tests move to the new function.

### 6.3 Visibility

A new pure module, `glances/outputs/static/js/v5/layout.js`, exports two
functions:

- `visiblePlugins(registry, names)` — `registry.filter(p => names.includes(p.name))`,
  order preserved; the whole registry when `names` is `null` (the
  `pluginslist` read failed).
- `groupBySlot(entries)` — `{slot: [entries…]}` in registry order, for §6.4.

Not in `plugins/index.js`: that module imports `.vue` files, which
`node --test` cannot load, so nothing in it is unit-testable. `fetchAll()`
receives the visible entries only.

**Documented limitation:** `pluginslist` is read once. When #3548 makes a
plugin toggleable at runtime, a newly enabled plugin appears after a page
reload. The comment at the call site says so.

### 6.4 Rendering

`AppShell` groups the visible entries by `slot` into
`<section data-slot="…">` containers; an empty slot renders no container.
The two header groups sit inside one header zone. Props are unchanged:
`payload`, `error`, `labels`, `serverArgs`, and `data-plugin` still falls
through onto each component's single root (G9-4 §6).

### 6.5 Server

`GET /api/5/all/info` in `glances/routes_v5.py` returns
`{name: plugin.fields_description}` for every registered plugin, declared
before `/{plugin_name}/info` with the same comment `/all/limits` carries. The
route table in the module docstring gains the row. `/api/5/<plugin>/info`
stays: it is part of the API contract.

## 7. The five header components

### 7.1 Common shape

- **One root `<span>`**, so `data-plugin` lands on it. No `<article>` and no
  `<h2>`: these are one-line blocks, not panels.
- **The four props are declared** (G9-4 D5), `serverArgs` included.
- **States:**

| State | Rendering |
|---|---|
| `error` | the message, `gl-level-critical`, visible — an error is never hidden, same as every other component |
| no payload, or the guard field missing | the root stays in the DOM, hidden with `v-show` |

Consequently the five registry entries declare `required: []`: a missing guard
field is the component's hide rule, not a shape error for `validate()` to
turn into a visible message. The scalar-object shape check still applies.

Hiding rather than removing the root keeps `data-plugin` findable by the probe
and means the header's `column-gap` does not count an invisible block. It also
matches the TUI, where the same conditions return `[]`. The two cases of §5 —
cycle 0 and `cloud`'s permanent `{}` — both render nothing, as in the TUI.

### 7.2 Components

| Component | Rendering (mirrors `render_curses_v5.py`) | Hidden when |
|---|---|---|
| `PluginSystem.vue` | `hostname` (`gl-header`) + `hr_name` (`gl-truncate`, full text in `title`) | no `hostname` |
| `PluginIp.vue` | `IP` + `address/mask_cidr` (bare `address` if `mask_cidr` is `null`); `Pub` + `public_address`, masked `a.b.*.*` when `serverArgs.hide_public_info`; `public_info_human` (`gl-truncate`, `title`) | no address at all |
| `PluginUptime.vue` | `Uptime:` + `formatSeconds(seconds)` | `seconds` is `null` |
| `PluginNow.vue` | `custom` | `custom` empty |
| `PluginCloud.vue` | `platform` (`gl-header`, bold) + `{type} instance {name} ({region})`, `Unknown` for a missing part | no `platform` or no `name` |

`ip`'s `title` attribute carries the geolocation string only — never the
public address, which would bypass the mask on hover.

### 7.3 Labels

`IP`, `Pub` and `Uptime:` are literals, as they are in the TUI renderers. They
are block tags, not field labels (`address`'s label is not "IP"), and the TUI
does not read them through `field_label()`. G9-4's D2 (the schema as the
single label source) does not apply; **decided, not deferred**, like `gpu`'s
`mem` exception (G9-4 §9).

### 7.4 Formatting

`formatSeconds(value)` in `format.js` mirrors `format_seconds`
(`glances/outputs/curses_formatters_v5.py:66-80`) exactly: `int(float(value))`
truncation, then `Ns` below 60, `NmSSs` below an hour, `NhMMm` below a day,
`NdHHh` beyond; a non-numeric value returns `""`.

## 8. CSS skeleton

`AppShell` stacks four zones: header, top, body (left + right), footer. A
`1px solid var(--gl-border)` rule separates them. Tokens only — the existing
colour-literal rule keeps applying.

| Zone | CSS | TUI equivalent |
|---|---|---|
| header | flex, `flex-wrap`, `column-gap: 3ch`; the `header-right` group has `margin-left: auto` | `_HEADER_GAP = 3`; right group right-aligned (`_paint_header`) |
| top | flex, `flex-wrap`, `justify-content: space-between` | first block flush left, last flush right, gaps distributed (`_paint_top_row`) |
| body | grid `max-content 1fr`; one column below `48rem` (left above right) | left and right side by side |
| left / right | flex column | stacked blocks |
| footer | alert list (unchanged) + `refresh Ns` cadence on the right (D5); sticky at the viewport's bottom edge — amended, see §14 A6 | — |

**`.gl-truncate`**, global in `css/v5.css`: `overflow: hidden;
text-overflow: ellipsis; white-space: nowrap; min-width: 0`. `min-width: 0` is
load-bearing — a flex item otherwise refuses to shrink below its content and
the ellipsis never triggers. Global for the same reason as `.gl-muted`: a
scoped copy matches only the component that declares it. It is also the fix
G9-4 §8.4 names for `gpu`'s title, should the smoke test call for it.

**`48rem` corresponds to no TUI rule.** It is the browser's own threshold, held
in one `@media` rule so it can be tuned. That is D3 applied: no invented
cascade.

The `.gl-plugins` flex run is removed; the `.gl-topbar` is removed (D5).

## 9. Failure modes

| Condition | Behaviour |
|---|---|
| `/api/5/all/info` unreachable | field names as labels; a value is never blanked |
| `/api/5/pluginslist` unreachable | the whole registry renders (today's behaviour) |
| A header plugin not yet published, or `{}` forever | hidden block (§7.1) |
| `/api/5/all` fails | every visible block shows its error, header included |
| A registry entry without a valid `slot` | test failure (§10); no fallback at runtime |
| `serverArgs` unreachable | `{}` — public address shown unmasked, as when the flag is off |

## 10. Testing

- **`node --test`:**
  - `formatSeconds`: 0, 59, 60, 3599, 3600, 86399, 86400, a float truncated
    (`61.9` → `1m01s`), a non-numeric value → `""`.
  - `visiblePlugins`: intersection, order preserved, `null` → whole registry.
  - `groupBySlot`: registry order kept within a slot, an unused slot absent.
  - `resolveAllLabels`: precedence, one fetch, failure → `{}`.
- **pytest, route:** `/api/5/all/info` returns `fields_description` keyed by
  every registered plugin; `all` is not captured as a plugin name; an empty
  registry returns `{}`.
- **Render probe — the drift guard** (the test D4 depends on): for each
  `[data-slot]`, the DOM order of `data-plugin` equals the matching Python
  tuple filtered to the registry's plugin names (`header-left` ↔
  `HEADER_SLOT_LEFT`, `header-right` ↔ `HEADER_SLOT_RIGHT`, `top` ↔
  `TOP_SLOT`, `left` ↔ `LEFT_SLOT`, `right` ↔ `RIGHT_SLOT`), and every
  registry plugin appears in exactly one slot. The Python side imports the
  tuples from `glances.outputs.curses_renderer_v5` — it must never restate
  them.
- **Render probe — behaviour:**
  - `cloud` absent from `pluginslist` → absent from the DOM; `pluginslist`
    failing → the whole registry renders.
  - `system` with `hr_name`; `ip` complete, without `mask_cidr`, masked via
    `hide_public_info`, and with no address (hidden); `uptime`; `now`; `cloud`
    complete and with `name` missing (hidden).
  - the refresh cadence renders in the footer.
  - the probe's `/info` stubs become one `/all/info` stub; `pluginslist` gets
    per-scenario answers like `ARGS_FIXTURES`.
- **The probe must support `v-show`:** its `FakeElement` needs a `style`
  object so tests can assert `display: none`.
- **Binding non-regression:** no TUI Python file changes, so no
  `tests/test_*render_curses_v5.py` and no `tests/test_curses_renderer_v5.py`
  may change; `public/glances.js` and `public/browser.js` stay byte-identical;
  `make pre-commit` passes.
- **Manual UI smoke test, owed to the maintainer:** a narrow viewport, a long
  `hr_name`, a long IP geolocation string, both themes — and G9-4's owed
  `gpu` title check, which `.gl-truncate` may now resolve.

## 11. Reported, not fixed: `--hide-public-info` does not reach the API

The flag masks the public address at display time only — in the TUI
(`glances/plugins/ip/render_curses_v5.py:60`), in v4, and in this group's
`PluginIp.vue`. `/api/5/ip` and `/api/5/all` serve `public_address` in clear.
For anyone reading the API, a client-side mask protects nothing.

It belongs to the API layer, not the WebUI, and v4 behaves the same way, so it
is out of this group's scope. **Follow-up:** open an issue that decides whether
the flag should filter the REST/MCP payload (the conditional-filtering pattern
of `as_dict_secure()`), with the default-behaviour impact assessed.

## 12. Risks

| Risk | Mitigation |
|---|---|
| The JS registry drifts from the TUI tuples (the price of D4) | The drift guard fails the suite (§10) |
| `pluginslist` is stale once #3548 lands | Comment at the call site; a reload picks it up |
| `--hide-public-info` gives a false sense of privacy | §11 issue |
| The probe keeps growing (631 lines before this group) | Not split here; E6's recommendation stands |
| `v-show` is new to the probe's fake DOM | A dedicated `style` assertion, so a probe that ignores `style` cannot pass a hidden-block test by accident |

## 13. Deliverables

New: `PluginSystem.vue`, `PluginIp.vue`, `PluginUptime.vue`, `PluginNow.vue`,
`PluginCloud.vue`; `layout.js` (`visiblePlugins`, `groupBySlot`) and
`tests/js/layout.test.mjs`; `formatSeconds`; `resolveAllLabels`;
`.gl-truncate`; `GET /api/5/all/info`.

Modified: `plugins/index.js` (`slot`, order, five entries), `AppShell.vue`
(zones, `pluginslist`, batch labels, footer cadence, top bar removed),
`labels.js`, `api.js` (`resolvePluginNames()`), `css/v5.css`,
`routes_v5.py`, `tests/fixtures/webui_render_probe.js`,
`tests/test_webserver_v5.py`, `tests/test_routes_v5.py`,
`tests/js/labels.test.mjs`, `tests/js/format.test.mjs`, and the rebuilt
`public/glances5.js` (kept separable, per the G9-1 constraint).

Unchanged, and deliberately so: every TUI Python file, `levels.js`,
`columns.js`, `fetchAll()`'s one-request-per-tick contract.

Release-notes items (never written to `NEWS.rst` during development):

- The v5 WebUI page follows the TUI layout: header, top row, left and right
  columns, alerts in the footer.
- The v5 WebUI shows `system`, `ip`, `uptime`, `cloud` and `now`.
- A plugin disabled on the server no longer shows as loading in the v5 WebUI.
- New route `GET /api/5/all/info`.
- The v5 WebUI top bar is gone; the refresh cadence moved to the footer.

## 14. Amendments after the maintainer's smoke test (2026-09-11)

The group passed its final whole-group review; the maintainer's browser smoke
test then produced six change requests. Each was designed in chat, approved,
implemented test-first, and checked with headless-Chrome screenshots of a real
v5 server (dark and light themes, 720 and 1500 px, an overflowing 260 px
window, and captures seconds apart with changing values). **Where this section
and an earlier one disagree, this section wins.**

| # | Request | Decision | Amends |
|---|---|---|---|
| A1 | Right-align the value column of `swap` and `load` like `gpu` — extended by the maintainer to `mem` and `cpu` | Once a payload exists, a scalar plugin's title and its value are the **first (dt, dd) pair of column 1**, as on the TUI's line 1 (`MEM 53.2% \| active 5.8G`, `CPU 4.5% \| idle 95.5% \| ctx_sw 6.7K`). Every column then has four lines. The `<h2>` title row renders only while loading or erroring. `load`'s `4core` takes the default colour, like the TUI's plain cell | G9-4 §8.1-§8.3 title rows; the G9-3 `mem` layout |
| A2 | `prominent` must look like the TUI | A filled **badge**: the tier colour as background, `--gl-prominent-fg` (= `var(--gl-bg)`) as text — ≥ 5.0:1 on all eight tier/theme pairs, where a fixed black drops to 3.2:1. `--gl-prominent-bg` is removed. In the alert footer only the **level word** carries the badge, like the TUI's LEVEL cell | G9-2 §5.1 R3 — **amended**. The filled background remains a second channel, but it is now painted in the tier colour, so R3 holds for the **shipped** themes only: a user theme whose tier colour is close to `--gl-bg` loses the hue and the badge together (the old grey highlight had its own token). The text colour is set inside each tier's badge rule, so it never depends on rule order |
| A3 | Limit the badge to the text | Table cells carry the tier on a `<span>` around the formatted value; the `<td>` keeps only `gl-num`. Grid values get `justify-self: end`, so a `<dd>` shrinks to its text | G9-3's cell binding in `PluginNetwork.vue` / `PluginGpu.vue` |
| A4 | `gpu` sat lower than its neighbours | `.gl-plugin-title h2 { margin: 0; font-size: inherit }` — every title is text-sized, like the TUI and like a loaded scalar `<dt>` title | — |
| A5 | Block widths must not follow the values | A width **floor on the grid column**: `.gl-stat-grid dl` is `auto minmax(7ch, auto)` (worst case of formatPercent/Bytes/Count and a load average), `dl.gl-col-rate` is 9ch for formatRate columns (`memswap`). Never a `min-width` on the `<dd>`: it would widen the badge again | §8 (no floor) |
| A6 | The footer at the bottom of the screen | **Sticky** (maintainer's choice over "after the content"): `.gl-app` is at least `100vh`, the footer is pushed down with `margin-top: auto` and stays at the viewport's bottom edge on an opaque background with a separator | §8 footer row |

### 14.1 Conventions every later port inherits

- A scalar plugin with a title value puts the title and that value as the
  first pair of its first column; the `<h2>` is for the loading/error state
  only.
- A collection component binds `cellClassFor(...)` on a `<span>` inside the
  cell, never on the `<td>`.
- A scalar column holding rates takes `class="gl-col-rate"`.

### 14.2 Costs, stated

- A loaded scalar title is a `<dt>`, no longer a heading element — a heading
  is not allowed inside `<dt>`. Screen-reader navigation by heading loses
  those four titles.
- The probe's `pluginValueClasses` no longer carries the tier of a table value
  (it lives on the inner `<span>`); `pluginTableCells` is the output that
  observes it.
- The CSS behaviours (A2, A4, A5, A6) are asserted by source-level regex
  tests in `tests/test_webui_v5_tokens.py`: the render probe has no layout
  engine. The screenshots above are the behavioural evidence.
- A content-heavy page scrolls under a footer that is always visible. Its alert
  list is capped at `40vh` and scrolls inside the footer: uncapped, a footer
  taller than the viewport slid off its top edge and hid the NEWEST alerts
  (independent review of these amendments, measured in headless Chrome).
- A loaded scalar `<article>` carries `aria-label` (`MEM`, `SWAP`, `LOAD`,
  `CPU`) to compensate for the lost heading.
- `--gl-prominent-bg` was removed although G9-2 §5.2 treats token names as an
  interface; harmless before the first v5 release, but it belongs in the
  release changelog (§14.4).

### 14.3 Tests added

`test_a_scalar_title_is_the_first_pair_of_its_first_column`,
`test_a_scalar_plugin_keeps_its_title_while_loading`,
`test_a_prominent_alert_badges_its_level_word_only`,
`test_a_table_value_carries_its_tier_on_the_text_not_the_cell`,
`test_only_a_column_of_rates_takes_the_wider_floor`
(`tests/test_webserver_v5.py`); `test_a_prominent_value_is_a_badge_in_its_tier_colour`,
`test_a_plugin_title_has_the_text_size_and_no_margin`,
`test_a_value_column_has_a_width_floor_on_the_grid_not_the_cell`,
`test_the_footer_sticks_to_the_bottom_of_the_viewport`,
`test_the_sticky_footer_caps_its_alert_list`
(`tests/test_webui_v5_tokens.py`); after the independent review of these
amendments, `test_a_loaded_scalar_plugin_still_names_itself_for_assistive_technology`
(`tests/test_webserver_v5.py`).

### 14.4 Release-notes additions

- Scalar plugin titles and their value share the value column, matching the TUI.
- Prominent values render as tier-coloured badges, in the TUI's style.
- Plugin blocks keep a stable width as values change.
- The alert footer stays at the bottom of the window.
