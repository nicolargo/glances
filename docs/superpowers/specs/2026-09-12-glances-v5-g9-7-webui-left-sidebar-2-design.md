# G9-7 — v5 WebUI left sidebar, batch 2 (`ports`, `connections`, `irq`, `folders`, `raid`, `smart`): Design

**Status:** approved (2026-09-12)
**Sub-project of:** G9 (see the G9-1 spec §2.1 for the decomposition)
**Predecessors:** `2026-09-06-glances-v5-g9-4-webui-plugins-design.md`,
`2026-09-11-glances-v5-g9-5-webui-layout-header-design.md`,
`2026-09-11-glances-v5-g9-6-webui-left-sidebar-design.md`,
`2026-09-12-glances-v5-webui-horizontal-degradation-design.md`

---

## 1. Goals

After G9-6 the `left` slot holds five of `LEFT_SLOT`'s eleven plugins
(`network`, `wifi`, `diskio`, `fs`, `sensors`). G9-7 ports the remaining six
and **closes the left column**:

1. `ports`, `connections`, `irq`, `folders`, `raid`, `smart` at strict TUI
   parity, each mirroring its `render_curses_v5.py`.
2. A **shared collection shell** (`CollectionBlock.vue`) extracted before the
   five new collection components copy the boilerplate a sixth time, and the
   five existing ones migrated onto it at iso-behaviour.
3. One v4 **non-regression fix** surfaced by the design: an empty `raid` or
   `smart` collection currently paints a bare header row in the v5 TUI where
   v4 paints nothing (§8).

`LEFT_SLOT` order after this group — unchanged, it is already the TUI's:

    network, ports, wifi, connections, diskio, fs, irq, folders, raid, smart, sensors

## 2. Out of scope

- **Splitting `tests/test_webui_v5_render.py` (1410 lines) and
  `tests/fixtures/webui_render_fixtures.js` (561 lines).** Recommended by the
  G9-6 review; the maintainer deferred it (D1). The new fixtures and
  assertions land in those files.
- **The `ch` / font-stack question** (G9-6 §2 and the `.gl-truncate` note in `css/v5.css`).
  Decided, and the decision is *do nothing* — see D2.
- **Formatter tie rounding** for `formatPercent` / `formatCount` /
  `PluginLoad`'s `toFixed(2)` (G9-6 §2), and the sensors `_levels[label]`
  last-write-wins defect. Both still reported, not fixed.
- **Vertical degradation / truncation counters.** The TUI's `item_start`
  "N/M" counter (`Row.item_start`) has no WebUI
  counterpart: the page scrolls, it does not fit rows to a height.
- **`connections`' disabled-probe latch** (`4591a6f5`, develop). Already
  carried by the model; the WebUI only reads the resulting `*_enabled` flags.

## 3. Decisions taken before design (2026-09-12)

| # | Decision | Consequence |
|---|---|---|
| D1 | **Scope: the six blocks + the shared collection shell.** No test-file split | §4 is a task 0 refactor pinned by the existing render tests; §2 keeps the split as a standing recommendation |
| D2 | **Do not touch `--gl-font`.** `ch` caps stay, documented as approximate | On Linux/Chrome `1ch` ≈ 0.83 rendered characters. Since G9-6 §13 put every left table at `width: 100%`, a cap only decides *how much of a long name shows*, never the block's width — so the inaccuracy is cosmetic, not structural |
| D3 | **`raid` and `smart` render one `<tbody>` per item, and sub-lines keep the TUI's `└─` / `├─` glyphs** verbatim | §5.5, §5.6. The grouping gives each array/device a styling and keying anchor; the glyphs keep the WebUI readable against the terminal side by side |
| D4 | **Strict TUI parity on headers**: `ports` renders **no header row at all** (identified by `aria-label` only), `folders` renders `<th>FOLDERS</th>` plus an empty `<th>` for its size column | Extends G9-6 D6 ("a loaded collection's title is its first `<th>`") to the two blocks that have no full header row in the TUI. `ports`' missing title is the documented continuity with `network` above it (`ports/render_curses_v5.py` module docstring, `test_no_title_row_deliberate_do_not_fix`) |
| D5 | **Labels come from the schema** (G9-4 D2, G9-6 D5, carried over) | §6 adds the missing `short_name`s and switches the `irq`, `raid` and `connections` TUI renderers to `field_label()` |
| D6 | **Fix the empty-collection divergence** in `raid` and `smart` | §8. Both TUI renderers return `[]` on an empty collection (v4 parity), both `test_empty_returns_header_only` tests are inverted, and the WebUI renders nothing |
| D7 | **Approach A for the shell**: a component with slots, not a declarative table and not a composable | §4. A declarative `columns`/`rows` shell would need an escape hatch for each of `ports` (no header), `raid`/`smart` (two levels) and `folders` (`?` prefix) on the day it shipped |

## 4. `CollectionBlock.vue` — the shared collection shell

Every collection component written since G9-3 repeats the same twelve lines:
the `<article class="gl-plugin">` root with its `aria-label` and its
"keep this comment inside the root" note, the `<h2>` title shown only while
loading or erroring, the error paragraph, the `loading…` paragraph, and the
`<table class="gl-table">` wrapper. `PluginDiskio.vue`, `PluginFs.vue`,
`PluginNetwork.vue`, `PluginSensors.vue` and `PluginWifi.vue` carry five
copies of it; G9-7 would make ten.

### 4.1 Interface

```
props:
  payload   Object|null   the plugin payload, null while loading
  error     String|undef  the service layer's error message
  title     String        the block's title (e.g. "RAID disks"), used by the
                          loading/error <h2>; a loaded block's title is a <th>
                          supplied by the #head slot (G9-6 D6)
  ariaLabel String        defaults to `title`; `ports` passes "PORTS" while
                          rendering no visible title at all (D4)

slots:
  #head     optional — the <tr> of <th>s that goes inside <thead>.
            Omitted by `ports`: the shell then renders no <thead> (D4).
  #body     required — one or more <tbody> elements. Flat blocks pass one;
            `raid` and `smart` pass one per item (D3).
```

The shell owns: the root element and its `aria-label`, the loading/error
states, the `<table class="gl-table">`, and `<thead>` when `#head` is
supplied. It owns **no** cell, no width, no colour: those stay in the plugin
component, where the TUI parity argument for each of them lives.

`#body` taking `<tbody>` elements rather than `<tr>`s is what lets `raid` and
`smart` group per item without the shell knowing anything about hierarchy.
Flat components wrap their `v-for` in a single `<tbody>` — one extra line
against a shell that could never express two levels.

### 4.2 Task 0: migrate the five existing components

Iso-behaviour, no assertion changed — the precedent is G9-6 task 0 (moving
tests without modifying them). The existing render tests and the
`gl-plugin` / `data-plugin` drift checks are the pin. Each component keeps
its `<style scoped>` `--gl-name-width`, its props (including the two
deliberately-unused `serverArgs` / `degrade` declarations and their comments),
and its cells verbatim.

The "keep this comment INSIDE the root" hazard moves into the shell: the shell
is the component that now owns the root node, so the note belongs there once
instead of five times.

## 5. Per-plugin parity

Each sub-section is the contract the component must reproduce; the
authority is the plugin's `render_curses_v5.py`, named in each heading.

### 5.1 `ports` — `ports/render_curses_v5.py`

- **Shape:** collection, `_key` = `indice`. **No header row** (D4), no
  `<thead>`, `aria-label="PORTS"`.
- **Rows:** payload order (the TUI does not sort). An item with neither
  `url` nor `host` is **skipped** — it cannot be scanned.
- **Name cell:** `description`, capped at `25ch` (`_NAME_MAX_WIDTH`), trailing
  ellipsis (the TUI keeps the head: `str(...)[:25]`), full text in `title`.
- **Status cell:** right-aligned (`gl-num`), coloured by
  `cellClassFor(payload, item, "status")` — i.e. `_levels[indice].status`,
  which the model publishes for every scannable item **including the healthy
  `"ok"` tier** (green, v4's `OK` decoration). `prominent` is always false.
- **Status text**, mirroring `_status_if_url` / `_status_if_host`:

  | Item kind | Condition | Text |
  |---|---|---|
  | has `url` | `status` is a number | `Code <status>` |
  | has `url` | `status` is null | `Scanning` |
  | has `url` | otherwise | `String(status)` — the scanner writes `"Error"` |
  | has `host` | `host` is null | `None` |
  | has `host` | `status` is null | `Scanning` |
  | has `host` | `status === true` | `Open` |
  | has `host` | `status == 0` (covers `false` and `0`) | `Timeout` |
  | has `host` | otherwise | `<status * 1000 → .0f>ms` |

  The RTT uses `formatFixed0(status * 1000)` so the half-even tie rule matches
  Python's `f"{…:.0f}"`. JS `typeof status === "number"` must not swallow the
  boolean case: `true` is checked first, and `status == 0` must match both
  `0` and `false` exactly as Python's `status == 0` does.

### 5.2 `connections` — `connections/render_curses_v5.py`

- **Shape:** **scalar**, not a collection. It renders with the existing
  `gl-stat-grid` + `<dl>` pattern, like `PluginLoad.vue`: the title
  `TCP CONNECTIONS` is the first `<dt>`, whose `<dd>` is empty (the TUI's
  title line carries no value).
- **Whole block hidden** when neither `net_connections_enabled` nor
  `nf_conntrack_enabled` is true — the component renders nothing, as the TUI
  returns `[]`.
- **Rows** when `net_connections_enabled`, in this fixed order, each skipped
  when its key is **absent** from the payload (absent, not null):
  `LISTEN`, `initiated`, `ESTABLISHED`, `terminated`. Labels from the schema
  (§6). Values plain integers, no colour.
- **`Tracked` row** when `nf_conntrack_enabled` and both
  `nf_conntrack_count` and `nf_conntrack_max` are non-null:
  `<count .0f>/<max .0f>`, the **only** coloured row, from
  `scalarLevel(payload, "nf_conntrack_percent")` via `levelClass`.
- Registry `spec`: `{ shape: "scalar", required: [] }` — every field is
  conditional, so nothing can be required.

### 5.3 `irq` — `irq/render_curses_v5.py`

- **Shape:** collection, `_key` = `irq_line`. Header row: the title `IRQ`
  then the schema label for `irq_rate` (§6).
- **Ranking lives in the component**, as it does in the TUI renderer: the
  model deliberately publishes *every* IRQ line (a documented v4 divergence
  for exporters), so the component sorts by `irq_rate` descending with
  `(item.irq_rate ?? 0)` — a null rate sorts last instead of throwing — and
  keeps the first **5** (`_TOP_N`).
  The sort must be stable like Python's `sorted`, which `Array.prototype.sort`
  is; ties therefore keep payload order on both sides.
- **Name cell:** `irq_line`, cap `24ch`, trailing ellipsis.
- **Rate cell:** `formatFixed0(irq_rate)` right-aligned, `-` when null
  (cycle 1) — `formatFixed0` already returns `-`. No colour: `irq` publishes
  no `_levels`.

### 5.4 `folders` — `folders/render_curses_v5.py`

- **Shape:** collection, `_key` = `path`. Header row: `<th>FOLDERS</th>`
  plus an empty `<th class="gl-num">` (D4).
- **Rows:** payload order. Name cell = `path`, cap `24ch`, **leading**
  ellipsis — the TUI keeps the tail (`"_" + path[-23:]`), so the WebUI uses
  the G9-6 `gl-truncate-start` treatment (`direction: rtl` plus the
  load-bearing `<bdi>`), not the literal `_` prefix.
- **Size cell:** `formatBytes(size)` (the TUI's
  `format_value(value, {"unit": "bytes"})`), `-` when null.
- **`errno != 0`:** the text is prefixed with `?` and the cell is rendered
  **bold with no tier colour** — v4's `curses.A_BOLD`. The model emits no
  `_levels` entry for a broken folder (no alert, no history, no action), so
  `cellClassFor` returns `""` and the component adds its own bold class. The
  `?` must not be produced by the formatter: it is a rendering decision, and
  conflating the two is how the TUI version ended up with a `?` eating one of
  its nine columns.
- Otherwise coloured by `_levels[path].size`.

### 5.5 `raid` — `raid/render_curses_v5.py`

- **Shape:** collection, `_key` = `name`. Header row: `RAID disks`, then the
  schema labels for `used` and `available` (§6).
- **One `<tbody>` per array** (D3), sorted by `String(name)` with `byText`
  — the TUI's `sorted(items, key=lambda it: str(it.get("name", "")))`.
  An item with no `name` is skipped.
- **Name cell:** `` `${String(type ?? "UNKNOWN").toUpperCase()} ${name}` ``,
  cap `18ch`, trailing ellipsis. `type` null renders `UNKNOWN`, v4 parity.
- **Value cells**, both coloured from `_levels[name].status`:

  | Case | Used | Avail |
  |---|---|---|
  | `type === "raid0"` and `status === "active"` | `Object.keys(components).length` | `-` |
  | `status === "active"` | `used` | `available` |
  | otherwise | *empty* | *empty* |

  The "otherwise" row keeps two empty `<td class="gl-num">` cells rather
  than a `colspan` on the name: the TUI paints a single cell there, and both
  render identically, but empty cells keep the three-column grid — a
  `colspan` would let a long array name spread under `Used`/`Avail`.

- **Sub-lines** — rows inside the same `<tbody>`, one cell with
  `colspan="3"`, glyphs verbatim:
  - `status === "inactive"` → `└─ Status inactive`, coloured like the array,
    then one line per component, keys sorted ascending:
    `   ├─ disk <role>: <component>` for every line but the last, which uses
    `└─`.
  - `type !== "raid0"` and `used != null` and `available != null` and
    `used < available` → `└─ Degraded mode`, coloured, then — only when
    `String(config).length < 17` — `   └─ <config with every "_" replaced by
    "A">`.
  - The two are **not** exclusive: an inactive array that is also degraded
    emits both groups, in that order, exactly as the renderer does.

### 5.6 `smart` — `smart/render_curses_v5.py`

- **Shape:** collection, `_key` = `name`. Header row: `SMART disks` alone
  (the TUI has no value header). No colour anywhere: v4 `smart` is
  display-only (`EMITS_ALERTS = False`, no watched field).
- **One `<tbody>` per device** (D3), payload order: a device row whose single
  cell is `name` capped at `34ch`, then one row per entry of
  `device.attributes`.
- **Attribute name:** `" " + String(name).replace(/_/g, " ")`, capped at
  `25ch` — the leading space is the TUI's indent and stays, so the cap
  counts it. The device row's single cell takes `colspan="2"`.
- **Attribute value:** right-aligned on the `8ch` column;
  `raw === null` → empty string; `attr.key ∈ LARGE_VALUE_KEYS` →
  `formatAutoUnit(raw)` (§7); otherwise `String(raw)`.
- **`LARGE_VALUE_KEYS` is a Python constant** (`glances/plugins/smart/__init__.py`):
  six keys, `bytesWritten`, `bytesRead`, `dataUnitsRead`, `dataUnitsWritten`,
  `hostReadCommands`, `hostWriteCommands`. The component needs the same set,
  so it is **copied into JS with a drift test** that imports the Python
  frozenset and compares it 1:1 — the `degrade.js` /
  `test_webui_v5_degrade_drift.py` precedent, for the same reason: a silent
  divergence here changes displayed numbers, not layout.

## 6. Schema labels (D5)

None of the six plugins declares a `short_name` today; their TUI renderers
hardcode the header strings. Every label that is *displayed* moves into the
schema, and the TUI renderer reads it through `field_label()` — so the TUI and
the WebUI cannot drift, which is the whole point of G9-4 D2.

| Plugin | Field | `short_name` | Renderer change |
|---|---|---|---|
| `irq` | `irq_rate` | `Rate/s` | header cell reads `field_label()` |
| `raid` | `used` | `Used` | header cell reads `field_label()` |
| `raid` | `available` | `Avail` | header cell reads `field_label()` |
| `connections` | `LISTEN` | `Listen` | `_ROW_ORDER` keeps the field order, labels come from `field_label()` |
| `connections` | `initiated` | `Initiated` | idem |
| `connections` | `ESTABLISHED` | `Established` | idem |
| `connections` | `terminated` | `Terminated` | idem |
| `connections` | `nf_conntrack_count` | `Tracked` | the `Tracked` row's label |

`ports`, `folders` and `smart` display **no** field label (no column header,
D4) and get no `short_name`. Block titles (`FOLDERS`, `RAID disks`,
`SMART disks`, `IRQ`, `TCP CONNECTIONS`) are not field labels: they stay
literals on both sides, as in every block ported so far.

The five TUI renderers touched here keep their pinned tests; a label moving
into the schema must leave every assertion line unchanged (G9-6 task 0's
precedent — when a TUI test uses a hand-written schema subset instead of
`PluginModel.fields_description`, switch the fixture, not the assertions).

## 7. `formatAutoUnit` — a second, different auto-unit

`smart` is the first WebUI consumer of v4's `glances.globals.auto_unit`, which
is **not** the algorithm `formatBytes` mirrors. `formatBytes` reproduces
`_auto_unit` from `curses_formatters_v5.py` (divide while `>= 1024`, one
decimal from 1K up, `int()` below). `auto_unit` differs on every axis:

- it divides by the largest prefix whose quotient is `> 1` (not `>= 1024`);
- its precision is variable: 2 decimals when the quotient is `<= 9.995`,
  1 when `< 99.95`, 0 above — except `K`, always 0;
- `0` returns the string `"0"`;
- below `1K` it returns `{:.0f}` for an int and `{:.2f}` for a float;
- `None` returns `-`.

A new `formatAutoUnit(value)` in `format.js` mirrors it, with unit tests
driven by the docstring's own cases (`613421788 → 585M`,
`5307033647 → 4.94G`, `44968414685 → 41.9G`, `838471403472 → 781G`,
`9683209690677 → 8.81T`, `1073741824 → 1024M`, `1181116006 → 1.10G`).
`low_precision` and the non-default `min_symbol` / `none_symbol` arguments are
**not** ported: `smart` calls `auto_unit(raw)` with none of them, and an
unused parameter is dead code.

`1.10G` is load-bearing: the trailing zero means the result is a fixed-decimal
string, so `toFixed`, not `toFixedHalfEven`'s integer path, and never a
`Number` round-trip that would print `1.1G`.

## 8. The empty-collection fix (D6)

v4's `raid.msg_curse()` and `smart.msg_curse()` both open with
`if not self.stats or self.is_disabled(): return ret`. The v5 renderers
instead build `rows = [header]` and return it before looking at the payload,
and the painter only drops a block with **zero** rows
(`curses_renderer_v5.py`: "Skip empty blocks"). Since an empty collection is
still published (`base_v5.update()` always calls `store.set`), a user who
enables `raid` on a box with no array — or `smart` without the privileges
pySMART needs — gets a bare `RAID disks  Used  Avail` / `SMART disks` header
in the v5 TUI where v4 shows nothing. Both plugins ship `disable=True`
(`conf/glances.conf`), which is why no smoke test caught it.

Fix: in both renderers, return `[]` when the payload is not a dict or its
`data` is not a non-empty list — the header row is built only once there is at
least one item to put under it. `test_empty_returns_header_only` in
`tests/test_plugin_raid_render_curses_v5.py` and
`tests/test_plugin_smart_render_curses_v5.py` is inverted (renamed to say what
v4 does) rather than deleted, so the parity claim stays pinned.

The WebUI components then render nothing for an empty collection, which is
what the other nine left-column blocks already do.

## 9. Registry, widths, degradation

- **Registry:** six new entries in `js/v5/plugins/index.js`, each in its
  `LEFT_SLOT` position. `test_every_slot_orders_its_plugins_like_the_tui`
  covers the order with no change. Shapes: `connections` scalar, the other
  five collections; `required` lists only a field that is always present —
  `ports` `["indice"]`, `irq` `["irq_line"]`, `folders` `["path"]`,
  `raid` `["name"]`, `smart` `["name"]`, `connections` `[]`.
- **Widths:** each component sets `--gl-name-width` in its scoped style to its
  TUI name cap — `ports` 25ch, `irq` 24ch, `folders` 24ch, `raid` 18ch,
  `smart` 25ch. Since G9-6 §13 every left table is `width: 100%` and the body
  grid sizes the column to the widest block, so these caps change only how
  much of a long name shows. Blocks with one value column (all but `raid`)
  will therefore show more characters of a name than `network` does — the
  consequence the maintainer chose in §13.
- **Horizontal degradation:** left-column blocks are hidden as a whole, never
  shrunk. The six components declare the unused `degrade` and `serverArgs`
  props with the existing comment (an undeclared prop becomes a DOM
  attribute), and nothing is added to `degrade.js`.

## 10. Tests

| Level | What |
|---|---|
| Shell | `CollectionBlock` renders the loading `<h2>`, the error paragraph, a `<thead>` only when `#head` is supplied, and the `aria-label` fallback to `title` |
| Render (per plugin) | a populated payload, an empty collection (renders nothing), and the plugin's own edge cases: `ports` each of the 8 status branches and the skipped item, `connections` each `*_enabled` combination, `irq` the top-5 cut and a null rate, `folders` the `errno` row, `raid` raid0/active/inactive/degraded and inactive+degraded together, `smart` a device with a `LARGE_VALUE_KEYS` attribute and a null raw |
| Drift | `LARGE_VALUE_KEYS` JS copy vs the Python frozenset |
| Formatter | `formatAutoUnit` against `auto_unit`'s docstring cases, plus `0`, a sub-1K int, a sub-1K float and `null` |
| TUI | the five renderers switched to `field_label()` keep their assertions; `raid` / `smart` empty-payload tests inverted |
| Schema | the new `short_name`s appear in `/api/5/all/info`, the single request `resolveAllLabels()` reads |

Fixtures go in `tests/fixtures/webui_render_fixtures.js`, assertions in
`tests/test_webui_v5_render.py` (D1 — no split). Collection fixtures must use
real schema shapes, not hand-written subsets.

## 11. Risks

| Risk | Mitigation |
|---|---|
| The task 0 migration silently changes a rendered block | The existing render tests are the pin and must pass **unmodified**; any assertion that needs touching means the migration is not iso-behaviour |
| `formatAutoUnit` is confused with `formatBytes` by a later component | §7 states the difference in `format.js` next to both functions, and the docstring cases are the test |
| `ports`' truthiness branches ported loosely (`status == 0` vs `false`, `true` before `typeof number`) | Each of the 8 branches gets its own assertion (§10) |
| `raid`'s two sub-line groups treated as exclusive | A fixture with an inactive **and** degraded array |
| A `<tbody>` per item is read as a styling hook and gets a border | No style is added in this group; the blocks must look exactly like the flat ones |

## 12. Success criteria

1. The eleven `LEFT_SLOT` plugins all render in the WebUI, in the TUI's order.
2. Each of the six new blocks matches its `render_curses_v5.py` on the cases
   listed in §10, with the terminal open beside the browser.
3. The five migrated components' render tests pass with no assertion changed.
4. `raid` and `smart` with an empty collection paint nothing, in both surfaces.
5. The full suite is green and `make pre-commit` is clean.
6. Owed to the maintainer afterwards: a browser smoke of the six blocks
   (long names on both ellipsis sides, a broken folder, an inactive/degraded
   array, a `smart` device, both themes, narrow viewport) — plus the two
   smokes still owed from G9-6 and the degradation group.
