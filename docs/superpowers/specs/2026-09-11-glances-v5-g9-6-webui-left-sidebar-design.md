# G9-6 — v5 WebUI left sidebar, batch 1 (`diskio`, `fs`, `sensors`, `wifi`) and the `network` retrofit: Design

**Status:** approved (2026-09-11)
**Sub-project of:** G9 (see the G9-1 spec §2.1 for the decomposition)
**Predecessors:** `2026-09-05-glances-v5-g9-1-webui-serving-design.md`, `2026-09-06-glances-v5-g9-2-webui-foundation-design.md`, `2026-09-06-glances-v5-g9-3-webui-scaling-design.md`, `2026-09-06-glances-v5-g9-4-webui-plugins-design.md`, `2026-09-11-glances-v5-g9-5-webui-layout-header-design.md`

---

## 1. Goals

After G9-5 the v5 WebUI has a page skeleton and eleven plugins. The `left`
slot holds `network` alone, and `network` itself is not at TUI parity: G9-3
ported it before G9-4's D1 made strict TUI parity the rule.

G9-6:

1. **Ports four left-sidebar collections** — `diskio`, `fs`, `sensors`,
   `wifi` — at strict TUI parity.
2. **Brings `network` to TUI parity** before four more collections copy its
   shape: `is_up`, `hide_zero`, `alias`, cycle-1 rows, bits per second.
3. **Fixes the collection title convention** (D6): the title takes the TUI
   header row's first cell, as G9-5 A1 did for scalar blocks.
4. **Splits the WebUI render tests out of `tests/test_webserver_v5.py`** and
   the fixtures out of the render probe, before this group adds to both (D4).

## 2. Out of scope

- **The rest of `LEFT_SLOT`** — `ports`, `connections`, `irq`, `folders`,
  `raid`, `smart`: G9-7.
- **The TUI's vertical fit and `N/M` truncation counter.** The browser page
  scrolls under the sticky footer. Without a configuration file the
  maintainer's machine publishes 86 disks and 81 filesystems; the shipped
  `conf/glances.conf` filters them (`[diskio] hide=loop.*,/dev/loop.*`,
  `[fs] hide=/boot.*,.*/snap.*`).
- **`--diskio-iops`, `--diskio-latency`, `--network-cumul`, `--network-sum`** —
  not implemented by the v5 TUI renderers either (their TODOs).
- **`[network] hide_no_up` / `hide_no_ip`** (present in the shipped
  configuration) — the v5 TUI renderer skips a down interface unconditionally
  (`glances/plugins/network/render_curses_v5.py:133`); the WebUI mirrors the
  renderer, not the configuration key.
- **The other formatters' tie rounding** — `formatPercent` and `formatCount`
  (`toFixed(1)`), `PluginLoad.vue`'s `toFixed(2)` and `gpuValue()`'s
  `Math.round` diverge from Python on exact ties exactly as §7.3 describes
  (`52.25` → `52.3%` in the WebUI, `52.2%` in the TUI). Reported, not fixed:
  each can adopt `toFixedHalfEven` in a later group.
- **`--disable-unicode` for the battery trend glyphs** — v4 ignores it too
  (`glances/plugins/sensors/__init__.py:255-259`, `unicode_message()` called
  without `args`), and so does the v5 TUI (`sensors/render_curses_v5.py:58-66`).

## 3. Decisions taken before design (2026-09-11)

| # | Decision | Consequence |
|---|---|---|
| D1 | **Scope: `diskio`, `fs`, `sensors`, `wifi`** | Registry order in `left` becomes `network, wifi, diskio, fs, sensors` — `LEFT_SLOT` filtered to the registry; the existing drift guard covers it unchanged |
| D2 | **Full `network` retrofit** | `is_up`, `hidden`, `alias`, null-rate rows, bits/s with `--byte`, and D6 |
| D3 | **Name cells capped at the TUI's name width; the ellipsis falls on the TUI's side** | 18ch with a **leading** ellipsis for `network`, `diskio`, `fs` (the TUI keeps the tail: `"_" + name[-17:]`); 19ch for `sensors` and 26ch for `wifi` with a **trailing** ellipsis (the TUI keeps the head) — **amended 2026-09-12, see §13: both become `calc(27ch + var(--gl-gap))`**. Full text in `title`. **Amends** G9-4 §8.4 and the `.gl-truncate` comment in `css/v5.css` ("never copy a terminal character count") — for left-sidebar name cells only, by the maintainer's explicit choice |
| D4 | **Task 0 moves tests and fixtures without modifying them** | See §9.1 |
| D5 | **Labels from the schema** (G9-4 D2, carried over) | New `short_name`s; the `diskio`, `fs`, `wifi` TUI renderers read `field_label()` — §6 |
| D6 | **A loaded collection's title is its first `<th>`**, as in the TUI header row (`DISK I/O │ R/s │ W/s`); the `<h2>` renders only while loading or erroring | G9-5 A1 extended to collections. `network` loses its `interface` column header and `network.interface_name.short_name` is removed. An empty collection renders its title and headers with no row, as the TUI paints its header row; `network`'s "no interface" text goes |

## 4. Measured inputs

Read from the repository and from a running v5 server on 2026-09-11, not
assumed.

### 4.1 TUI renderers

| Plugin | Title + headers | Rows skipped | Order | Name | Value text | Tier from |
|---|---|---|---|---|---|---|
| `network` (`render_curses_v5.py:96-164`) | `NETWORK` + `field_label(bytes_recv)` + `field_label(bytes_sent)` | `is_up is False`, `hidden is True`, either rate `None` | payload | `alias or interface_name`, `"_" + tail` beyond 18 | `_format_rate()`: ×8, K/M/G/T at 1024, one decimal, suffix `b`; sub-K `int(value)` + `b`. `view["byte"]`: no ×8, no suffix | `bytes_recv` / `bytes_sent` |
| `diskio` (`:80-133`) | `DISK I/O` + **literal** `R/s`, `W/s` | `hidden is True`, either rate `None`, empty name | `sorted(key=str(disk_name))` | `alias or disk_name`, `"_" + tail` beyond 18 | `_format_byte_rate()`: `1.4M`; sub-K `int(value)` + `B` | `read_bytes` / `write_bytes` |
| `fs` (`:73-123`) | `FILE SYS` + **literal** `Used`‖`Free` + `Total` | empty `mnt_point` | `sorted(key=str(mnt_point))` | `alias or mnt_point`, `"_" + tail` beyond 18 | `format_value(unit=bytes)` → `_auto_unit()`; `-` for `None` | **`percent`**, on the used/free cell only; `Total` uncoloured |
| `sensors` (`:96-128`) | `SENSORS` only, one cell | battery with value in `([], None, "")`; a value neither numeric nor a sentinel | payload (server sorts with `natural_keys`, `model_v5.py:198`) | `label`, head kept, cut at 19 | §8.5 | `_levels[label].value` |
| `wifi` (`:57-96`) | `WIFI` + **literal** `dBm` | `ssid` in `("", None)`; non-numeric `quality_level` | `sorted(key=str(ssid))` | `ssid`, head kept, cut at 26 | `f"{quality_level:.0f}"` | `_levels[ssid].quality_level` |

The painter skips a block with **zero rows** (`curses_renderer_v5.py:1484-1489`);
all five renderers always return their header row, so an empty collection
shows its header in the TUI.

### 4.2 What `/api/5` actually serves

Measured against `python -m glances.main_v5 -s` with `[network] alias=lo:Loopback`:

- `network` items carry `is_up`, `hidden` and, for `lo`, `alias: "Loopback"`.
  `hidden` and `alias` are base metadata fields declared `internal: True`
  (`glances/plugins/plugin/base_v5.py:63-84`), which `_project(keep_internal=True)`
  keeps for REST and MCP.
- `diskio` items carry `hidden`.
- `fs` publishes the **envelope-level** `free_space` metadata
  (`fs/model_v5.py:113-115`) — the config key merged with `--fs-free-space`.
- `sensors` items carry `type`, `unit`, `status` (internal, kept);
  `_key` is `label`.
- `wifi`: `{ssid, quality_link, quality_level}`, `_levels[ssid].quality_level`.
- `/api/5/args` serves `byte`, `fahrenheit`, `fs_free_space`,
  `disable_unicode`, `meangpu` (`routes_v5.py:174-177`, redacted namespace).
- `/api/5/all/info`: `network` is the only one of the five with `short_name`s.

## 5. Row rules (`rows.js`)

A new pure module, `glances/outputs/static/js/v5/rows.js`, testable under
`node --test` (same reason `layout.js` is not in `plugins/index.js`). It holds
only what has at least two callers:

- **`displayName(item, keyField)`** — `item.alias` when it is a non-empty
  string, otherwise `String(item[keyField] ?? "")`. Callers: `network`,
  `diskio`, `fs`.
- **`byText(field)`** — a comparator reproducing Python's
  `sorted(key=lambda it: str(it.get(field, "")))`: code-point order
  (`"B" < "a"`), **not** `localeCompare`. `Array.prototype.sort` is stable, as
  Python's `sorted` is. Callers: `diskio`, `fs`, `wifi`.

Each component applies its own skip rules from §4.1 in a computed `rows`; a
rule used by one component stays in that component.

## 6. Labels (D5)

| Model | Field | New `short_name` |
|---|---|---|
| `diskio` | `read_bytes` / `write_bytes` | `R/s` / `W/s` |
| `fs` | `used` / `free` / `size` | `Used` / `Free` / `Total` |
| `wifi` | `quality_level` | `dBm` |
| `network` | `interface_name` | **removed** (`"interface"`, D6) — and the comment block above it that justifies it (`network/model_v5.py:66-73`) is rewritten to drop that justification |

The `diskio`, `fs` and `wifi` renderers replace their literals with
`field_label(fields_desc.get(key, {}), key, prefer_short=True)`, following
`network/render_curses_v5.py:104-116`. The block titles (`DISK I/O`,
`FILE SYS`, `WIFI`, `SENSORS`, `NETWORK`) stay literals in both outputs: they
are block tags, not field labels (G9-5 §7.3).

Blast radius, measured: 12 assertions on these strings in
`tests/test_plugin_diskio_render_curses_v5.py`,
`tests/test_plugin_fs_render_curses_v5.py` and
`tests/test_plugin_wifi_render_curses_v5.py`. `short_name` has no other
consumer (`field_label()` at `curses_renderer_v5.py:243`, the cpu renderer,
the WebUI).

**Amended while planning (2026-09-11).** An earlier draft said those three
files "must pass without modification". They cannot: the `diskio` and `fs`
fixtures are hand-written schema subsets with no `short_name`, and the `wifi`
tests call `render(payload)` with no schema at all, so a renderer reading
`field_label()` would print `read_bytes`, `used`, `quality_level`. Production
always passes the plugin's real schema (`curses_renderer_v5.py:1459`). The
three files therefore switch their schema source to
`PluginModel.fields_description` — the G9-4 precedent for `load` and `gpu`
(`tests/test_plugin_gpu_render_curses_v5.py:16-24`) — and **not one assertion
changes**. That is the non-regression gate: a changed or deleted assertion in
those files is a failure of this group.

`sensors`' value column has no header in the TUI; it needs no schema change.

## 7. Formatting (`format.js`)

### 7.1 `formatBytes` — sub-K truncation

Python's `_auto_unit()` (`glances/outputs/curses_formatters_v5.py`) and
`diskio`'s `_format_byte_rate()` print `int(value)` below 1024; `formatBytes`
uses `Math.round`. It becomes `Math.trunc`. With the tie rule of §7.3,
`formatBytes` then equals `_format_byte_rate()` and
`format_value(unit=bytes)` for every value below 1 PiB (the Python functions
stop at `T`, `formatBytes` goes on to `P`), so both components use it
unchanged.

**Visible outside this group:** `memswap`'s `formatRate()` sub-K rates
(`855.6` → `855B/s`, was `856B/s`) — now equal to the TUI's
`format_bytespers()`. Integer byte counts (`mem`, `memswap` totals) are
unaffected.

### 7.2 `formatNetworkRate(bytesPerSecond, byte)`

Mirrors `network/render_curses_v5.py::_format_rate()`:

| Input | `byte` false (default) | `byte` true (`--byte`) |
|---|---|---|
| `100` | `800b` | `100` |
| `1048576` | `8.0Mb` | `1.0M` |
| non-numeric | `-` | `-` |

`byte` is `serverArgs.byte`.

### 7.3 Half-even rounding on exact ties

Python formats floats with correct rounding, **half-to-even on an exact
tie**; `Number.prototype.toFixed` and `Math.round` round an exact tie up.
The two outputs diverge on real values: `1280` bytes is `1.25K` exactly
(Python `1.2K`, JS `1.3K`), and a sensor at `42.5` (Python `42`, JS `43`).

One helper, **`toFixedHalfEven(value, digits)`**, serves `formatBytes`'s
one-decimal branch and a new **`formatFixed0(value)`** (used by `sensors` and
`wifi`). It is exported so the cases below can be tested on it directly: the
false-tie case (`0.15`) cannot be reached through `formatBytes`, whose values
below 1024 never take the one-decimal branch. Requirements:

- A tie is detected **exactly**, on the double's exact decimal expansion —
  never on `x * 10 ** digits`, which rounds: `0.15 * 10 === 1.5` in floating
  point although `0.15` is stored as `0.1499999999999999944…`.
- Mandatory cases on `toFixedHalfEven`: `(0.15, 1) → "0.1"`,
  `(1.25, 1) → "1.2"`, `(1.35, 1) → "1.4"` (not a tie, stored above),
  `(42.5, 0) → "42"`, `(43.5, 0) → "44"`, `(0.5, 0) → "0"`,
  `(-54.5, 0) → "-54"`, `(-54.4, 0) → "-54"`; and `formatBytes(1280) → "1.2K"`.
  Every expected string was checked against CPython's `f"{x:.{d}f}"` on
  2026-09-11; `toFixed` disagrees on four of them (`1.3`, `43`, `1`, `-55`).
- `formatFixed0` returns `"-"` for a non-number, like every `format.js`
  function; its callers skip such rows before formatting anyway (§4.1).

**Visible outside this group:** `mem`/`memswap` values landing on an exact
one-decimal tie (e.g. `1.25G` → `1.2G`, was `1.3G`) — now equal to the TUI.

## 8. Components

### 8.1 Common shape

```html
<article class="gl-plugin" aria-label="DISK I/O">
  <div v-if="error || !payload" class="gl-plugin-title"><h2 class="gl-header">DISK I/O</h2></div>
  <p v-if="error" class="gl-level-critical">…</p>
  <p v-else-if="!payload" class="gl-muted">loading…</p>
  <table v-else>
    <thead><tr><th class="gl-header">DISK I/O</th><th class="gl-header gl-num">R/s</th>…</tr></thead>
    <tbody>
      <tr v-for="item in rows" :key="item[keyField]">
        <td><span class="gl-name gl-truncate-start" :title="name"><bdi>{{ name }}</bdi></span></td>
        <td class="gl-num"><span :class="cellClassFor(payload, item, field)">{{ value }}</span></td>
      </tr>
    </tbody>
  </table>
</article>
```

- **D6:** the `<h2>` renders only while loading or erroring; once loaded the
  title is the first `<th>`. `aria-label` on the `<article>` compensates for
  the lost heading, as G9-5 §14.2 does for scalar blocks.
- **The name cap lives on a block `<span>` inside the cell**, never on the
  `<td>`: `max-width` on a table cell in automatic table layout is not
  reliably honoured.
- **Tier on the inner `<span>`**, never on the `<td>` (G9-5 §14.1).
- **The row key is the raw primary key**, hardcoded per component (the
  comment in `PluginNetwork.vue:23-25` explains why `payload._key` is not used).
  `_levels` stays keyed by that raw value, never by `alias` (§4.1).
- **All four props declared**, `serverArgs` included (G9-4 §5).
- **`.gl-num` is unchanged**: its 9ch floor is wider than the TUI's 7-column
  values, an accepted width difference.
- **Registry `spec.required`:** `["disk_name"]`, `["mnt_point"]`, `["label"]`,
  `["ssid"]`; `network` keeps `["interface_name"]`.

### 8.2 CSS (`css/v5.css`, global)

- `.gl-name { display: block; max-width: var(--gl-name-width); }` plus the
  `.gl-truncate` properties. Each component sets `--gl-name-width` in its
  scoped style: `18ch` (`network`, `diskio`, `fs`), and
  `calc(27ch + var(--gl-gap))` for `sensors` and `wifi` (§13; was `19ch` and
  `26ch`).
- `.gl-truncate-start` — the leading ellipsis: `direction: rtl` on the
  `<span>`, the text isolated in a `<bdi>` so a leading `/` does not reorder.
  Checked with headless-Chrome screenshots at Task 2 (§11).
- The `.gl-truncate` comment is amended to state D3's exception.

### 8.3 `PluginNetwork.vue` (retrofit)

| Aspect | Rendering |
|---|---|
| Headers | `NETWORK` · `labelFor(bytes_recv)` · `labelFor(bytes_sent)` |
| Rows | skip `is_up === false`, `hidden === true`, `bytes_recv == null`, `bytes_sent == null`; payload order |
| Name | `displayName(item, "interface_name")`, 18ch, leading ellipsis |
| Values | `formatNetworkRate(v, !!serverArgs.byte)` |
| Tier | `bytes_recv` / `bytes_sent` |

The "no interface" paragraph is removed (D6).

### 8.4 `PluginDiskio.vue`, `PluginFs.vue`, `PluginWifi.vue`

| Component | Headers | Rows | Name | Values | Tier |
|---|---|---|---|---|---|
| `PluginDiskio` | `DISK I/O` · `R/s` · `W/s` | skip `hidden`, null `read_bytes`/`write_bytes`, empty name; `byText("disk_name")` | `displayName`, 18ch, leading | `formatBytes` | `read_bytes` / `write_bytes` |
| `PluginFs` | `FILE SYS` · `Used`‖`Free` · `Total` | skip empty `mnt_point`; `byText("mnt_point")` | `displayName`, 18ch, leading | `formatBytes(used‖free)`, `formatBytes(size)` | **`percent`** on the used/free cell; `Total` none |
| `PluginWifi` | `WIFI` · `dBm` | skip `ssid` `""`/`null`, non-numeric `quality_level`; `byText("ssid")` | `ssid`, `calc(27ch + var(--gl-gap))` (§13), trailing | `formatFixed0(quality_level)` | `quality_level` |

`fs`'s switch reads **`payload.free_space`**, which selects both the field and
its label. It does not read `serverArgs.fs_free_space`: that misses a
`[fs] free_space` set in the configuration, which the model has already
merged (§4.2).

### 8.5 `PluginSensors.vue`

- **Headers:** `SENSORS` then an empty `<th>`. The TUI header row has one
  cell; an empty `<th>` rather than `colspan` keeps the header aligned column
  by column with the probe's `pluginColumnHeaders` / `pluginColumnClasses`.
- **Rows:** payload order. Skip a `battery` row whose value is `[]`, `null`
  or `""`; skip a value that is neither a number nor a sentinel.
- **Name:** `label`, `calc(27ch + var(--gl-gap))` (§13), trailing ellipsis.
- **Value** (mirrors `_value_text()`):
  1. a sentinel `ERR`/`SLP`/`UNK`/`NOS` renders verbatim;
  2. with `serverArgs.fahrenheit` and a `type` other than `battery` /
     `fan_speed`: `formatFixed0(toFahrenheit(value)) + "F"`, no trend;
  3. otherwise `formatFixed0(value) + unit`, plus for a `battery` a trend from
     `status`: starts with `Charg` → `↑`, `Discharg` → `↓`, `Full` → `✓`,
     anything else → nothing.
- **Tier:** `cellClassFor(payload, item, "value")` (`_key` is `label`).

## 9. Testing

### 9.1 Task 0 — the move

- `tests/test_webserver_v5.py` from `_BUNDLE_PATH` (line 576) to the end moves,
  as one block with its helpers and imports, to
  `tests/test_webui_v5_render.py`. `test_the_v5_bundle_is_served` (HTTP only)
  stays.
- The fixture constants of `tests/fixtures/webui_render_probe.js`
  (`ALERT_FIXTURES`, `INFO_FIXTURES`, `SERVER_PLUGINS`,
  `PLUGINSLIST_FIXTURES`, `ALL_UNREACHABLE_SCENARIOS`, the `*_FIXTURE`
  constants, `ARGS_FIXTURES`, `ALL_FIXTURES`) move to
  `tests/fixtures/webui_render_fixtures.js`, loaded with `require()` (the probe
  is CommonJS).
- **Nothing else changes** — no rename, no reformat, no docstring edit beyond
  the file names the probe's header comment and the moved docstrings cite.
  Imports `tests/test_webserver_v5.py` no longer uses after the move are
  removed (ruff F401), and only those.
- **Evidence:** the collected test ids are identical before and after
  (`pytest --collect-only -q`, ids compared modulo the file name), and the
  probe's stdout is **byte-identical for every scenario** in `ALL_FIXTURES`,
  `PLUGINSLIST_FIXTURES` and `ARGS_FIXTURES`, captured before and after.

### 9.2 `node --test`

- `format.test.mjs`: §7.1 (`855.6 → "855B"`), §7.2 table, §7.3 mandatory
  cases on `toFixedHalfEven` and `formatBytes(1280)`, `formatFixed0` on a
  non-number → `"-"`.
- `rows.test.mjs`: `displayName` (alias wins; empty alias → key; missing key
  → `""`); `byText` (`"B"` before `"a"`, `"sda"` before `"sdb"`, stability).

### 9.3 pytest

- **TUI:** the three renderer test files of §6 green with their schema source
  switched to `PluginModel.fields_description` and every assertion unchanged
  (§6 amendment); one schema pin per model, like `test_network_schema_declares_the_tui_short_names`, which
  itself **changes**: its `interface` assertion becomes an assertion that
  `interface_name` declares no `short_name`.
- **Tokens** (`tests/test_webui_v5_tokens.py`, source-level regex, G9-5 §14.2):
  `.gl-name` uses `max-width: var(--gl-name-width)`; `.gl-truncate-start`
  sets `direction: rtl`.

### 9.4 Render probe

A new probe output, `pluginNameCells`, keyed by `data-plugin`: for each name
`<span class~="gl-name">`, its text, class list, `title`, and whether it holds a
`<bdi>`.

| Plugin | Scenarios and assertions |
|---|---|
| `network` | a down interface, a `hidden` one and a null-rate one are absent; `alias` shown, `title` = alias; `1048576` → `8.0Mb`; with `byte` → `1.0M`; headers `NETWORK`, `Rx/s`, `Tx/s`; no `<h2>` once loaded, `aria-label` present; empty `data` → headers, no `<tr>` in `<tbody>`; leading-ellipsis classes + `<bdi>` |
| `diskio` | rows sorted by raw name; `hidden` and null-rate rows absent; alias shown; tier on the `<span>` from `read_bytes` |
| `fs` | sorted by mount point; `free_space: false` → `Used` + used values, `true` → `Free` + free values; `percent`'s tier on the used/free `<span>`, none on `Total` |
| `wifi` | sorted by ssid; empty ssid and non-numeric level absent; `dBm` header; `-54.5` → `-54`; trailing-ellipsis class, no `<bdi>` |
| `sensors` | payload order kept; `fahrenheit` converts a `temperature_core` row and leaves `battery` and `fan_speed` alone; `↑`/`↓`/`✓`; `ERR` verbatim; an empty battery row absent; tier from `_levels[label].value`; `42.5` → `42` |

The existing slot-order drift guard covers the four new registry entries
without modification. Fixture values avoid unintended ties (§7.3).

### 9.5 Binding non-regression

- No TUI Python file changes beyond the three renderers and four models of §6,
  and no TUI test file beyond the schema-source switch of §6's amendment.
- `public/glances.js` and `public/browser.js` byte-identical.
- The full suite green (`test_restful` test_050/051 is flaky by construction —
  re-run before diagnosing).
- `make pre-commit` passes, or its failures are shown to predate the group
  (§11).

### 9.6 Owed to the maintainer

Manual browser smoke: long mount point and long disk alias (leading ellipsis),
long sensor label (trailing), `--byte`, `--fahrenheit`, `--fs-free-space`, a
battery, both themes, a narrow viewport.

## 10. Tasks

| # | Task | Verified by |
|---|---|---|
| 0 | The move (§9.1) | §9.1 evidence |
| 1 | `format.js`: §7.1-§7.3 | §9.2 |
| 2 | `rows.js`; `.gl-name`, `.gl-truncate-start`; headless-Chrome check of the leading ellipsis | §9.2, §9.3 tokens, screenshots |
| 3 | §6: `short_name`s and the three TUI renderers | §9.3 |
| 4 | `network` retrofit (§8.3) + `pluginNameCells` | §9.4 `network` |
| 5 | `diskio` + `fs` (components, registry entries) | §9.4 |
| 6 | `wifi` + `sensors` | §9.4 |
| 7 | Close: screenshots of all five blocks (dark/light, 720/1500 px), §9.5 | §9.5 |

Every task touching a component rebuilds `public/glances5.js`: the probe runs
against the bundle. After every task, `git status --short` is checked for
files a subagent unstaged.

## 11. Risks

| Risk | Mitigation |
|---|---|
| The `rtl` + `<bdi>` leading ellipsis renders wrong in a browser | **Spiked in headless Chrome while planning (2026-09-11): it works** — `/var/snap/firefox/common/host-hunspell` in 18ch reads `…mmon/host-hunspell`, `/` and `/boot/efi` keep their slash at the start. The `<bdi>` is load-bearing: without it `/boot/efi` renders `boot/efi/`. Chrome's default `th { text-align: center }` must be overridden. Firefox is not verified (not installed). Task 2 re-checks against the real `v5.css`; **if that fails, stop and ask the maintainer** |
| The tie detector reports false ties | Exact detection is a requirement (§7.3); `0.15 → "0.1"` is mandatory |
| Task 0 loses a test or a fixture | Collected ids and per-scenario probe output compared (§9.1) |
| `make pre-commit` already fails `check-shebang-scripts-are-executable` on 5 test files from develop backports | Re-checked at the start of the group; reported, not fixed here |
| A subagent unstages the maintainer's files | `git status --short` after every task |
| D3 reintroduces terminal widths the earlier specs rejected | Scoped to left-sidebar name cells; the `.gl-truncate` comment records the exception |

## 12. Deliverables

**New:** `PluginDiskio.vue`, `PluginFs.vue`, `PluginWifi.vue`,
`PluginSensors.vue`; `rows.js` and `tests/js/rows.test.mjs`;
`formatNetworkRate`, `toFixedHalfEven`, `formatFixed0`; `.gl-name`,
`.gl-truncate-start`;
`tests/test_webui_v5_render.py`; `tests/fixtures/webui_render_fixtures.js`.

**Modified:** `PluginNetwork.vue`; `plugins/index.js` (four entries, `left`
order); `format.js` (`formatBytes`); `css/v5.css`;
`glances/plugins/{diskio,fs,wifi}/render_curses_v5.py`;
`glances/plugins/{diskio,fs,wifi,network}/model_v5.py`;
`tests/test_plugin_{diskio,fs,wifi}_render_curses_v5.py` (schema source only);
`tests/test_webserver_v5.py` (the moved block removed);
`tests/fixtures/webui_render_probe.js`; `tests/js/format.test.mjs`;
`tests/test_webui_v5_tokens.py`; the rebuilt `public/glances5.js`.

**Unchanged, deliberately:** every other TUI Python file and TUI test file,
`levels.js`, `columns.js`, `layout.js`, `api.js`, `AppShell.vue`, `fetchAll()`'s
one-request-per-tick contract.

**Release-notes items** (never written to `NEWS.rst` during development):

- The v5 WebUI shows `diskio`, `fs`, `sensors` and `wifi` in the left column.
- The v5 WebUI `network` block matches the TUI: bits per second (bytes with
  `--byte`), interface aliases, `hide_zero`, down interfaces hidden.
- Collection block titles sit in the table header row, as in the TUI; the
  `network` block no longer has an `interface` column header.
- Long disk, mount point and interface names are shortened from the start,
  sensor and wifi names from the end; the full displayed name (the alias when
  one is set) is in the tooltip.
- Byte sizes, byte and bit rates, sensor and Wi-Fi values round like the TUI:
  sub-kilobyte values truncate (`855B/s`), exact ties round to even (`1.2K`
  for 1280 bytes). Percentages, counters, load and GPU values do not yet (§2).
- `/api/5/diskio/info`, `/fs/info`, `/wifi/info` declare `short_name`s;
  `/api/5/network/info` no longer declares one for `interface_name`.
- The left-column blocks share one width budget (§13).

## 13. Amendment (2026-09-12): one width budget for the left column

After the maintainer's smoke test: **every block of the left column must have
the same width**, `network` being the reference. `wifi` and `sensors` have two
columns where `network`, `diskio` and `fs` have three, so their name cap
becomes the three-column budget:

```css
--gl-name-width: calc(27ch + var(--gl-gap));   /* 18ch + the 9ch value column + its gap */
```

D3's TUI widths (`26ch` for `wifi`, `19ch` for `sensors`) are replaced by this;
`18ch` for the three-column blocks is unchanged. The maintainer chose this over
stretching the tables (`​.gl-table { width: 100% }`), which was the other option
put to him.

**Measured in headless Chrome** (`.superpowers/sdd/2026-09-11-glances-v5-g9-6-webui-left-sidebar/width-probe/w.html`):

| Block | Width |
|---|---|
| `network`, 18ch, a name at the cap | 277.4px |
| `wifi`, new cap, a long ssid | 277.4px |
| `sensors`, new cap, a long label | 277.4px |
| `wifi`, new cap, only `wlp0s20f3` | 155.7px |
| `wifi`, 26ch (before), only `wlp0s20f3` | 155.7px |

**The limitation, and what closed it.** A table column shrinks to its content,
so the caps equalise the **maximum** width, not the rendered one. The screenshot
taken after the change showed `sensors` reaching `network`'s right edge while
`wifi` (one 9-character ssid, 156px) and `diskio` (short device names, 228px)
stayed narrow against `network`'s 278px. Shown that evidence, the maintainer
added the rule he had first declined:

```css
.gl-table { width: 100%; }
```

Each table then fills the column the body grid already sizes to the widest
block, so the widths are equal whatever the content, and G9-7's six new blocks
inherit it with no per-component budget. The raised caps stay: they decide how
much of a long name is shown, and the leftover width falls between the name and
the values. Pinned by `test_every_collection_table_fills_the_left_column`
(`tests/test_webui_v5_tokens.py`).
- The empty `network` block shows its header row instead of "no interface".
- The `sensors` block honours `--fahrenheit` and shows battery trend arrows;
  the `fs` block honours `--fs-free-space`.
