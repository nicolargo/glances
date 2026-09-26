# Glances v5 — the stats history store

**Date:** 2026-09-26
**Branch:** `develop-v5`, on top of `bb4a4c6` (sensors reads `[hddtemp]`)
**Group:** v4 feature parity backlog
(`docs/architecture/glances-v5-architecture-decisions.md` §10, "CLI — the
options still missing": `--disable-history` "needs a feature v5 does not have")
**Unblocks, later and out of scope here:** trend arrows, the `S` /
`--sparkline` quicklook mode, the graph exporter.

---

## 1. Scope

v5 keeps only the latest sample of every plugin. v4 also keeps a short
in-memory time series for a chosen set of fields, and five consumers read it.
This chantier builds the **store** and wires the **two API consumers**. The
three display and export consumers get their own chantiers. The maintainer
chose this scope on 2026-09-26, together with the three decisions in §5.1,
§5.3 and §5.5.

In scope:

- `HistoryStoreV5`: bounded ring buffers in memory, fed once per plugin cycle.
- The `history: True` schema key, redefined to mean "historise this field"
  (§5.1), set on the fields that v4's `items_history_list` names (§4).
- `[global] history_size` (default 1200, `0` disables) and `--disable-history`.
- `GET /api/5/{plugin}/history`, in a columnar v5 shape (§5.5).
- The MCP resource `glances://stats/{plugin}/history`. It currently returns
  `{}` and logs a WARNING (`mcp_adapter_v5.py:102`).

Out of scope, each unblocked by this chantier:

| Consumer | v4 reference | Why it waits |
|---|---|---|
| Trend arrows ↑↓ next to MEM, SWAP and LOAD in the TUI | `mem/__init__.py:304`, `memswap/__init__.py:166`, `load/__init__.py:157` → `get_trend()` (`plugins/plugin/model.py:413`) | Not asked for in this round. **Not in the parity inventory at all** (Part 3 lists hotkeys, and this is not one), so §7 adds it to the backlog. |
| `S` / `--sparkline` quicklook mode | `quicklook/__init__.py:292-370` | Set aside by the maintainer on 2026-09-25. |
| Graph exporter, `--export-graph-path` | `exports/glances_graph/__init__.py:87` → `get_export_history()` | Phase 3 (all remaining exporters). |
| min/max/mean (`mmm`) | `plugins/plugin/model.py:195-290`, on `cpu.total`, `load.min1`, `mem.percent` | A different mechanism (§5.1). Separate parity chantier, §7. |

---

## 2. What v4 does

**Declaration.** Each plugin has a module-level `items_history_list`: a list of
`{name, description, y_unit}` entries, separate from `fields_description`
(for example `mem/__init__.py:115`).

**Recording.** After every update, `update_stats_history()`
(`plugins/plugin/model.py:347-378`) reads `get_export()`. For a scalar plugin it
appends `(datetime.now(UTC), value)` under the field name. For a collection it
does the same for each item, under `"<pk_value>_<field>"`
(`nativestr(l_export[item_name]) + '_' + nativestr(i['name'])`). The buffer
is a Python `list`, trimmed with `pop(0)` once it reaches `history_size`
(`attribute.py:106-111`). That is O(n) per append, on every field of every
plugin.

**Size.** `[global] history_size`. The code defaults to 28800
(`plugins/plugin/model.py:728`). The shipped `glances.conf` sets 1200
("~1h with the default refresh rate", `conf/glances.conf:12-14`). A value of
`0`, or `--disable-history`, turns history off (`main.py:890-893`).

**Reading.**

- REST: `/api/4/{plugin}/history[/{nb}]` returns `{key: [[iso, value], …]}`.
  `/api/4/{plugin}/{item}/history[/{nb}]` returns one list, where `item` is
  the flattened key (`glances_restful_api.py:556-564`, `:1043`, `:1202`).
- MCP: `glances://stats/{plugin}/history` serialises `get_raw_history()`
  (`glances_mcp.py:253-270`).

**Defects that should not be carried over.**

1. The flattened key is ambiguous. `"sda1_read_bytes"` could be item `sda1`
   with field `read_bytes`, or item `sda1_read` with field `bytes`. Interface,
   disk and mount-point names can all contain `_`, and a mount point can
   contain `/` as well, which is why v4's item route cannot address an fs
   series at all.
2. Series never go away. An interface that disappears keeps its key until
   restart, frozen at its last value.
3. Each point is a `(datetime, value)` tuple, so the timestamp is repeated in
   every series of the same cycle. A `datetime` is about 48 bytes, the tuple
   about 56 more.

---

## 3. What v5 has today

- `StatsStoreV5` (`stats_store_v5.py`) holds the latest payload of each
  plugin. Writes go through an `asyncio.Lock`, reads take no lock. It keeps
  no history, by design.
- `GlancesPluginBase.update()` (`base_v5.py:439-468`) runs grab → transform →
  `store.set()` and commits the rate snapshot only when the cycle succeeds.
- `fields_description` already accepts a `history` key. Architecture §3.2
  documents it as "whether min/max/mean statistics are computed for this
  field. Replaces v4 `mmm`". **Nothing reads it.** It is set on
  `cpu.total`, `cpu.system` and `cpu.user` only.
- `[alerts] history_size` exists. It sizes the **alert** ring buffer
  (`alerts_v5.py:169`), which is unrelated. §5.4 keeps the two apart.
- `/api/5/{plugin}/{field}/history` is listed as "deferred" in architecture
  §4.6.

---

## 4. Which fields are historised

The set is **v4's `items_history_list`, mapped to v5 field names**. Nothing
is added.

| Plugin | v4 `items_history_list` | v5 fields with `history: True` | Notes |
|---|---|---|---|
| cpu | `user`, `system` | `user`, `system` | `total` loses the flag it carries today. It was set for the `mmm` meaning (§5.1) and returns with the `mmm` chantier. |
| percpu | `user`, `system` | `user`, `system` | Collection, keyed by `cpu_number`. |
| load | `min1`, `min5`, `min15` | same | |
| mem | `percent` | `percent` | |
| memswap | `percent` | `percent` | |
| processcount | `total`, `running`, `sleeping`, `thread` | same | |
| quicklook | `cpu`, `percpu`, `mem`, `swap`, `load`, `gpu_mem`, `gpu_proc` | `cpu`, `mem`, `swap`, `load`, `gpu_mem`, `gpu_proc` | **`percpu` is left out**: its value is a list of per-core dicts, not a number (D3). The per-core series already exist in the `percpu` plugin. Which one the sparkline reads is decided in the sparkline chantier. |
| network | `bytes_recv_rate_per_sec`, `bytes_sent_rate_per_sec` | `bytes_recv`, `bytes_sent` | v5 replaces the counter with its rate in place. |
| diskio | `read_bytes_rate_per_sec`, `write_bytes_rate_per_sec` | `read_bytes`, `write_bytes` | Same as network. |
| fs | `percent` | `percent` | Keyed by `mnt_point`, which may contain `/` (defect 1). |
| gpu | `proc`, `mem` | `proc`, `mem` | |
| npu | `freq`, `load`, `mem` | same | |
| mpp | `load` | `load` | |
| containers | `cpu_percent` | `cpu_percent` | Keyed by `name`. |
| vms | `memory_usage` | `memory_usage` | Keyed by `name`. |

v4's `description` and `y_unit` are not copied. v5 already carries both in
`fields_description` (`description`, `unit`), which `/api/5/{plugin}/info`
serves, so a second copy would drift.

---

## 5. Design

### 5.1 D1 — `history` means "historise this field"; `mmm` is separate (maintainer decision)

In v4 these are two independent mechanisms. `items_history_list` feeds the
time series. `mmm: True` makes the plugin publish `<field>_min`, `_max` and
`_mean`, computed from a separate 28800-sample list of its own
(`plugins/plugin/model.py:261-264`). Architecture §3.2 merged the two into
one key. The merge was never implemented, and it would couple two things
with different contracts: `mmm` adds fields to the REST and export payload,
while history adds none.

Decision: `history: True` in `fields_description` replaces
`items_history_list`. `mmm` becomes its own parity chantier (§7), with its
own key when it is designed. §3.2 of the architecture document is corrected
in the same push.

Declaring history in the schema, rather than in a second list, means the
field's name, unit and description are declared once, and a test can check
every declaration against the payload (D3).

### 5.2 D2 — one store, fed by the plugin after a successful publish

`glances/history_v5.py` holds `HistoryStoreV5`. It is created once in
`main_v5.assemble`, or not created at all when history is disabled (§5.4).
It reaches the plugins as an attribute, `plugin.history`, which `assemble`
sets after construction. The base `__init__` initialises it to `None`.

*Changed while implementing, 2026-09-26.* The first draft passed the store
as a constructor argument, `__init__(store, config, history=None)`. That
would have meant changing 22 signatures, because 22 plugins override
`__init__(store, config)`. The attribute has the same default and costs the
same `is not None` test per cycle.

`update()` records right after `await self.store.set(...)`, inside the same
`try`:

```python
await self.store.set(self.plugin_name, self._build_store_payload())
if self._history is not None and self._history_fields:
    self._history.record(self.plugin_name, self._stats, self._history_fields, self._primary_key)
```

Three properties come from recording at this point:

- **What was recorded is what REST served.** Values are post-transform:
  rates are already per second and `None` on cycle 1, and show/hide filters
  have already been applied. `hidden` items (`hide_zero`) **are** recorded,
  because they are hidden from display only, not from the payload.
- **A failed cycle records nothing**, like `_raw_previous`.
- **The scheduler does not change.** It cannot tell a failed cycle from a
  good one, because `update()` swallows the exception.

`record()` is synchronous. It never awaits, so a REST handler running on the
same event loop can never see a half-written cycle.

`_history_fields` is computed once in `__init__` from `fields_description`,
the same way as `_rate_fields` and `_watched_fields`.

### 5.3 D3 — layout: one time axis per plugin, one aligned ring buffer per series

```text
HistoryStoreV5
  _plugins: {plugin_name: _PluginHistory}

_PluginHistory
  timestamps: deque[float]                  # maxlen = history_size, epoch seconds (UTC)
  series:     {field: {item: deque[float | None]}}
              # scalar plugin: item is None
              # collection:    item is the primary-key value, as a string
  idle:       {(field, item): int}          # consecutive cycles without a value
```

- **One time axis per plugin.** Every series of a plugin is sampled in the
  same cycle, so the timestamp is stored once. This fixes defect 3. Each
  plugin has its own axis because each plugin has its own refresh period
  (`[<plugin>] refresh`).
- **Timestamps are wall clock**, `time.time()` taken inside `record()`.
  Using `_cycle_ts` would be wrong here: it is `time.monotonic()`, which is
  correct for rates and meaningless to a client.
- **Series stay aligned with their axis.** A series first seen after the
  axis already has points is left-padded with `None` up to the axis length.
  A known series absent from this cycle gets a `None` appended. So index `i`
  of every series of a plugin belongs to `timestamps[i]`.
- **Series expire** (fixes defect 2). `idle` counts consecutive cycles
  without a value. When it reaches `history_size`, every point the series
  holds is `None`, and the series is removed. An interface that comes back
  later starts a new series, padded with `None`, which is what the data says.
- **Only numbers are recorded.** A declared value that is not `int`, `float`
  or `None` is skipped, with a DEBUG log. A `bool` counts as not a number. A
  unit test also walks every plugin's `fields_description` and fails if a
  field marked `history: True` is not numeric in that plugin's test payload.
  This test is what keeps `quicklook.percpu` (a list) out.
- **`deque(maxlen=history_size)`** drops the oldest point in O(1), unlike
  v4's `pop(0)`.

**Memory.** A slot in a deque is 8 bytes plus the float object (24 bytes; the
`None` and the small ints are shared). That is about 32 bytes per point.

| Host | Series | Points (×1200) | Approximate RAM |
|---|---:|---:|---:|
| Laptop: 8 cores, 2 NICs, 2 disks, 4 fs, 1 GPU | ≈ 50 | 60 k | ≈ 2 MB |
| Server: 64 cores, 8 NICs, 12 disks, 20 fs, 30 containers | ≈ 250 | 300 k | ≈ 10 MB |

The server row is dominated by `percpu` (128 series). v4 stores every point
as a `(datetime, value)` tuple (about 130 bytes), so v5 uses about a quarter
of v4's memory for the same series. `array('d')` with NaN would cut this to
8 bytes per point, at the cost of hand-written ring indexing. That is not
worth it at these sizes. The measurement in §8 (`bench_v4_v5.py`) is the
check.

### 5.4 D4 — configuration: `[global] history_size`, `--disable-history`

- `[global] history_size`, an integer, **default 1200**. That is the value
  the shipped `glances.conf` and v4's disable check both use
  (`main.py:892`). v4's code default of 28800 is not carried over: at 2 s per
  cycle it is 16 hours per series, and nobody asked for that in v5.
- `history_size = 0` or `--disable-history` means no store is created. The
  plugins receive `history=None`, and recording costs one `is not None` test
  per cycle.
- A negative value, or one that is not an integer, logs a WARNING and falls
  back to 1200. `[global] refresh` falls back silently
  (`scheduler_v5._config_refresh`). History warns instead, because a window
  that has quietly gone back to its default is hard to notice.
- `[alerts] history_size` is unrelated and unchanged. The comment in
  `conf/glances.conf` next to `[global] history_size` gains one line saying
  so, because the two identical key names are a real trap.
- `--disable-history` goes into `/api/5/args` as a boolean display
  preference. The frozen key set in `test_routes_v5.py` gains it, which is
  the point of that test.

### 5.5 D5 — `GET /api/5/{plugin}/history`: columnar, nested by field then item (maintainer decision)

```text
GET /api/5/{plugin}/history
GET /api/5/{plugin}/history?nb=60
GET /api/5/{plugin}/history?field=bytes_recv
GET /api/5/{plugin}/history?field=bytes_recv&item=eth0
```

Scalar plugin:

```json
{
  "timestamps": [1790000000.0, 1790000002.0],
  "series": { "percent": [41.2, 41.5] }
}
```

Collection plugin, nested by field, then by the raw primary-key value:

```json
{
  "timestamps": [1790000000.0, 1790000002.0],
  "series": {
    "bytes_recv": { "eth0": [null, 1532.0], "wlan0": [null, 0.0] },
    "bytes_sent": { "eth0": [null, 812.5], "wlan0": [null, 0.0] }
  }
}
```

- **Nesting instead of a `"eth0.bytes_recv"` key.** The question put to the
  maintainer offered a flat key as an example. Writing this section showed
  that any separator collides with some item name (defect 1: `/` in mount
  points, `.` in container names). Nesting by field, then item, needs no
  separator. The payload is still columnar with one shared time vector, as
  decided.
- **Filters are query parameters, not path segments.** `item` can be `/home`.
  This replaces v4's `/{plugin}/{item}/history`, which could not address an
  fs series at all.
- `nb` returns the last `nb` points; `0` or absent returns all of them. The
  timestamps and every series are sliced together.
- **Status codes.** An unknown plugin returns 404, like the other plugin
  routes. An unknown `field` or `item` also returns 404. A plugin with no
  history field, a plugin that has not published yet, and history disabled
  all return `200 {"timestamps": [], "series": {}}`. A client that needs to
  tell those apart reads `/info` or `/args`.
- **Authentication and security.** The same router, middleware and password
  gate as every `/api/5` route. The data is the same kind the client can
  already GET from `/api/5/{plugin}`, just over time. Nothing is redacted.
- **Rupture with v4.** The shape differs, and there is no ISO string per
  point. This is documented for the 5.0.0 release notes (§7).

The route is declared before `/{plugin_name}` in `routes_v5.py`. The paths
differ in depth anyway, so declaring it first is only a precaution.

### 5.6 D6 — MCP returns the same shape

`McpPluginView.get_raw_history(item=None, nb=0)` returns the D5 payload,
built by the same helper as the route. It no longer returns `{}` with a
WARNING. The throttled WARNING and the `_warned` set are removed, along with
the three places that document the gap: the module docstring, architecture
§11.3 (the table row), and §11.4 ("Known v5 gaps").

`glances_mcp.py` is shared with v4 and **does not change**. It serialises
whatever `get_raw_history` returns, and the D5 dict is plain JSON. The
resource therefore returns the v5 shape under v5 and the v4 shape under v4,
in line with the decision already recorded for alerts (§11.5, "v5-native
schema, no translation").

---

## 6. Divergences from v4, recorded

| # | v4 | v5 | Why |
|---|---|---|---|
| 1 | `items_history_list`, a second list per plugin | `history: True` in `fields_description` | One declaration per field (D1). |
| 2 | `{"eth0_bytes_recv": [[iso, v], …]}` | `{timestamps, series: {field: {item: […]}}}` | Unambiguous keys, one time vector (D5). Maintainer decision. |
| 3 | `/{plugin}/history/{nb}`, `/{plugin}/{item}/history[/{nb}]` | `/{plugin}/history?nb=&field=&item=` | Path segments cannot carry `/home` (D5). |
| 4 | Series never expire | A series expires once all its points are `None` | D3. |
| 5 | Code default 28800 | Default 1200 | The shipped conf value (D4). |
| 6 | `quicklook.percpu` historised as a list of dicts | Not historised | Only numbers are recorded (D3). The per-core series live in `percpu`. |
| 7 | Timestamps as `datetime`, ISO in JSON | Epoch seconds (float, UTC) | Compact, and what a plotting client consumes directly. |

---

## 7. Documentation and backlog changes in the same push

- Architecture §3.2: redefine `history`; `mmm` is noted as a separate
  pending mechanism.
- Architecture §4.6: `/api/5/{plugin}/history` moves from "deferred" to the
  route table.
- Architecture §11.3 and §11.4: the MCP history row and gap are closed.
- Architecture §10, parity backlog:
  - The CLI row: `--disable-history` moves to shipped.
  - **New row: trend arrows** (mem, memswap, load), now unblocked. v4
    reference `get_trend()`. Not in the parity inventory.
  - **New row: `mmm` min/max/mean** on `cpu.total`, `load.min1` and
    `mem.percent`. Absent from v5's payload.
  - The `S` row (2.X-c, "blocked") becomes "unblocked, set aside by the
    maintainer".
- `conf/glances.conf`: the comment on `[global] history_size` (0 disables it,
  and it is not `[alerts] history_size`).
- Release notes material: divergences 2, 3 and 5 are breaking for API
  clients.

---

## 8. Test strategy

- **`tests/test_history_v5.py`, the store alone:**
  - Scalar and collection recording.
  - Alignment: a late series is left-padded, an absent series gets `None`
    appended.
  - Expiry after exactly `history_size` idle cycles, and not one cycle
    earlier.
  - `maxlen` eviction.
  - `nb` slicing, applied to the timestamps and every series together.
  - Values that are not numbers, including `bool`, are skipped.
  - `record()` contains no `await`: an AST check, in the same spirit as the
    purity tests of `_handle_key`.
- **The plugin pipeline**, in the base tests:
  - A failed cycle records nothing.
  - `history=None` records nothing and raises nothing.
  - Recorded values equal what `get_api_payload()` serves for the same cycle.
- **Schema contract:** every field marked `history: True` in every plugin is
  numeric in that plugin's test payload. The §4 mapping is pinned as a table,
  so a flag added or dropped later is a deliberate test edit.
- **Routes:** the shape for a scalar and for a collection, `nb`, `field`,
  `item` with a `/` in it, 404 on an unknown plugin, field or item, 200 empty
  when history is disabled or on cycle 0, and behind auth when
  `[outputs] password` is set.
- **MCP:** the resource returns the D5 shape, and the WARNING is gone.
- **CLI and config:** `--disable-history` and `history_size = 0` each mean
  no store is created. An invalid value falls back to 1200 with a WARNING.
  `/api/5/args` carries the new key.
- **Footprint:** `make bench-v4-v5`, run before and after. The RAM delta is
  reported in the commit message and compared against the §5.3 estimate.

---

## 9. Shipping

One chantier, two commits:

1. **The store and its feed:** `history_v5.py`, the base hook, the schema
   flags from §4, the config and the CLI.
2. **The consumers:** the REST route, the MCP adapter, and the documentation
   from §7.

The first commit changes no visible behaviour. With nothing reading the
store, it only costs memory, which is what the §8 benchmark measures before
the API makes the data visible.

---

## 10. Open questions for the maintainer

None block the design.

1. **Is `history_size` per plugin?** v4 has only the global key. A plugin
   whose refresh period differs from the others covers a different time
   span with the same number of points. The alternative is a window
   expressed in seconds. Proposal: keep v4's global count, and revisit with
   the sparkline, the first consumer that draws a fixed width.
2. **Should history be exported?** v4 exposes `get_export_history()` only
   for the graph exporter. Proposal: decide in Phase 3 together with the
   exporter, as a `HistoryStoreV5` read method rather than a plugin method.
