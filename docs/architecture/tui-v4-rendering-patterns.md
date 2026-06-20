# TUI v4 Rendering Patterns — Phase 1 Plugins

Reference catalogue of `msg_curse()` output patterns for the five plugins migrated in
Phase 1: cpu, mem, load, network, percpu.

Purpose: this document is the visual-parity contract for the v5 generic curses renderer.
It describes what v4 *does*; it does not prescribe v5 design.

---

## cpu

**Source:** `glances/plugins/cpu/__init__.py::msg_curse`

**Guard:** returns empty if `not self.stats`, `args.percpu` is set, or plugin is disabled.

**Header line example:**
```
CPU   12.3%   idle  87.1%   ctx_sw  1.2K
```

**Field table:**

| field | label | format | alignment | total width | color rule |
|---|---|---|---|---|---|
| (title) | `CPU` | `{:8}` | left | 8 | `TITLE` |
| total | *(none)* | `{:5.1f}%` | right | 6 | `get_views(key='total', option='decoration')` |
| idle | `idle` | `{:4.1f}%` via `{:>8}` label + `{:4.1f}%` value | right | 8+5 | optional=`get_views(key='idle', option='optional')` |
| ctx_switches | `ctx_sw` | `curse_add_stat('ctx_switches', width=15, header='  ')` → `{:8}` label + `{:5}K/s` value | — | 15 | `get_views(key='ctx_switches', option='decoration')` |

**Line 2 (user/idle + irq + interrupts):**

| field | label | format | width | color rule |
|---|---|---|---|---|
| user (or idle on Windows) | `user` | `curse_add_stat('user', width=15)` | 15 | decoration from views |
| irq | `irq` | `curse_add_stat('irq', width=14, header='  ')` | 14 | decoration from views |
| interrupts | `inter` | `curse_add_stat('interrupts', width=15, header='  ')` | 15 | decoration from views |

**Line 3 (system/core + nice + sw_int/ctx_sw):**

| field | label | format | width | color rule |
|---|---|---|---|---|
| system (or core on Windows) | `system` | `curse_add_stat('system', width=15)` | 15 | decoration from views |
| nice | `nice` | `curse_add_stat('nice', width=14, header='  ')` | 14 | decoration from views |
| soft_interrupts (or ctx_switches fallback) | `sw_int` | `curse_add_stat('soft_interrupts', width=15, header='  ')` | 15 | decoration from views |

**Line 4 (iowait/dpc + steal + guest/syscalls):**

| field | label | format | width | color rule |
|---|---|---|---|---|
| iowait (or dpc on Windows) | `iowait` | `curse_add_stat('iowait', width=15)` | 15 | decoration from views |
| steal | `steal` | `curse_add_stat('steal', width=14, header='  ')` | 14 | decoration from views |
| guest (Linux) or syscalls (non-Linux/non-macOS) | `guest` | `curse_add_stat('guest', width=14, header='  ')` | 14 | decoration from views |

**`curse_add_stat` layout (width=N):**
- label cell: `header + '{:{width}}'.format(key_name, width=N-7)` — left-aligned, padded
- value cell: `'{:5.1f}%'` for percent fields; `'{:>5}K'` for number+`min_symbol` fields (via `auto_unit`)
- Both cells inherit the same `optional` flag; value cell gets `decoration` from views

**Layout notes:** 4-line block; `CPU` title left-padded to 8; total is a bare `{:5.1f}%`
(no label) directly after the title on line 1; all other fields use `curse_add_stat`.
Lines 2–4 start with `curse_new_line()`.

**Conditional behaviour:**
- Hidden entirely when `args.percpu` is True (percpu takes priority).
- `idle` shown only when `'user' in self.stats` (i.e. not Windows; `idle_tag=False`).
- Line 2 shows `user` on Unix/Linux, `idle` on Windows.
- Line 3 shows `system` on Unix/Linux, `core` on Windows.
- Line 4 shows `iowait` on Linux, `dpc` on Windows.
- `guest` shown only on Linux; `syscalls` shown on non-Linux/non-macOS.
- All rate fields (`ctx_switches`, `interrupts`, `soft_interrupts`, `syscalls`) are
  `optional=True` — hidden when terminal is narrow.

✅ **v5 renderer:** `glances/plugins/cpu/render_curses_v5.py`

---

## mem

**Source:** `glances/plugins/mem/__init__.py::msg_curse`

**Guard:** returns empty if `not self.stats` or plugin is disabled.

**Header line example:**
```
MEM ↑  74.2%   active  5.3G
```

**Field table:**

| field | label | format | alignment | total width | color rule |
|---|---|---|---|---|---|
| (title) | `MEM` | `'{}'.format('MEM')` | left | 3 | `TITLE` |
| trend | *(space + arrow)* | `' {:2}'.format(trend_msg(...))` | left | 3 | `DEFAULT` |
| percent | *(none)* | `'{:>7.1%}'.format(percent/100)` | right | 7 | `get_views(key='percent', option='decoration')` |
| active | `active` | `curse_add_stat('active', width=16, header='  ')` | — | 16 | decoration from views |

**Line 2 (total + inactive):**

| field | label | format | width | color rule |
|---|---|---|---|---|
| total | `total` | `curse_add_stat('total', width=15)` | 15 | DEFAULT |
| inactive | `inacti` | `curse_add_stat('inactive', width=16, header='  ')` | 16 | DEFAULT |

**Line 3 (available/used + buffers):**

| field | label | format | width | color rule |
|---|---|---|---|---|
| available (or used if not available) | `avail` (or `used`) | `curse_add_stat('available', width=15)` | 15 | DEFAULT |
| buffers | `buffer` | `curse_add_stat('buffers', width=16, header='  ')` | 16 | DEFAULT |

**Line 4 (free + cached):**

| field | label | format | width | color rule |
|---|---|---|---|---|
| free | `free` | `curse_add_stat('free', width=15)` | 15 | DEFAULT |
| cached | `cached` | `curse_add_stat('cached', width=16, header='  ')` | 16 | DEFAULT |

**`curse_add_stat` for bytes fields:** `unit='bytes'`, `min_symbol='K'` → value rendered
via `auto_unit(int(value))` with no unit suffix (bytes has no entry in `fields_unit_short`).
Template: `'{:>5}'` (integer path via `min_symbol`).

**Layout notes:** 4-line block; `MEM` title immediately followed by 2-char trend indicator
then 7-char right-aligned percentage; two-column grid from line 2 onward (15 + 16 chars).
`percent` is formatted as `{:>7.1%}` (Python's `%` format, i.e. value × 100 with `%` suffix)
but the stat is already divided by 100 before formatting: `self.stats['percent'] / 100`.

**Color logic:** `percent` decoration comes from `get_alert_log(used, maximum=total)` set in
`update_views()`; thresholds follow the standard CAREFUL/WARNING/CRITICAL ladder.
All byte fields are `DEFAULT` (no threshold configured for them).

**Conditional behaviour:**
- Line 3 shows `available` when `self.available` is True (Linux/macOS), otherwise `used`.
- `active`, `inactive`, `buffers`, `cached` are `optional=True` — hidden on narrow terminals.

✅ **v5 renderer:** `glances/plugins/mem/render_curses_v5.py`

---

## memswap

**Source:** `glances/plugins/memswap/__init__.py::msg_curse`

**Guard:** returns empty if `not self.stats` or plugin is disabled.

**Expected v4-equivalent output:**

```
SWAP   25.0%
total          16.0G
used            4.0G
free           12.0G
```

**Header field table:**

| field | label | format | width | color rule |
|---|---|---|---|---|
| (title) | `SWAP` | `'{:4}'.format('SWAP')` | 4 | `TITLE` |
| trend arrow | `↑/↓/` | `'{:2}'.format(trend_msg(...))` | 2 | `DEFAULT` |
| percent | `25.0%` | `'{:>6.1%}'.format(percent / 100)` | 6 | `get_views(key='percent', option='decoration')` |

**Body rows** (lines 2-4): each row is `curse_add_stat(<field>, width=15)` — single label/value pair, label left-aligned, value right-aligned, total row width 15 chars.

| Line | Field | Notes |
|---|---|---|
| 2 | `total` | Total swap memory |
| 3 | `used` | Used swap memory |
| 4 | `free` | Free swap memory |

**Color logic:** `percent` decoration comes from `get_alert_log(used, maximum=total)` — standard CAREFUL/WARNING/CRITICAL ladder.

**Conditional behaviour:** the plugin is hidden when the system has no swap configured (psutil raises on `swap_memory()` — see Illumos/OpenBSD issues #1767, #2719).

✅ **v5 renderer:** `glances/plugins/memswap/render_curses_v5.py`
(Added in G4-memswap. Trend arrow not yet ported — same status as `mem`/`load`.)

---

## fs

**Source:** `glances/plugins/fs/__init__.py::msg_curse`

**Guard:** returns empty if `not self.stats`, plugin disabled, or
`max_width` is `None` (logs a debug message).

**Expected v4-equivalent output (default — used + total):**

```
FILE SYS              Used   Total
/                   125.0G  500.0G
/home               512.0G    1.0T
```

**`name_max_width` computation:** `max_width - 13`

**Header field table:**

| field | label | format | alignment | width | notes |
|---|---|---|---|---|---|
| (title) | `FILE SYS` | `'{:{width}}'.format('FILE SYS', width=name_max_width)` | left | name_max_width | `TITLE` |
| Used / Free | `Used` or `Free` | `'{:>8}'.format(...)` | right | 8 | depends on `--fs-free-space` flag |
| Total | `Total` | `'{:>7}'.format('Total')` | right | 7 | `DEFAULT` |

**Per-filesystem row:**

| field | format | alignment | width | color rule |
|---|---|---|---|---|
| mnt_point | concatenated `mnt (device_short)` when room, else truncated with leading `_` | left | name_max_width | `DEFAULT` |
| used / free | `auto_unit(value)` right-padded to 7 | right | 7 | `get_alert(used, max=size)` |
| total | `auto_unit(size)` right-padded to 7 | right | 7 | `DEFAULT` |

**Sort order:** mountpoint ascending (`operator.itemgetter('mnt_point')`).

**Color logic:** the `used` cell carries the alert decoration computed
from `get_alert(current=size-free, maximum=size, header=mnt_point)` —
standard CAREFUL/WARNING/CRITICAL ladder. Read-only mounts (`ro` in
options) skip the alert in v4 (issue #3143); v5 keeps the alert
universal — operators can suppress via the show/hide filters.

**Conditional behaviour:**
- `--fs-free-space`: header shows `Free`, row value shows `auto_unit(free)`
  instead of `auto_unit(used)`.
- Mountpoints whose alias / show / hide filters reject them are skipped.

✅ **v5 renderer:** `glances/plugins/fs/render_curses_v5.py`
(Added in G4-fs. Default mode only — ``--fs-free-space`` toggle and
the optional ``(device)`` suffix on mountpoints are deferred to a
later phase pending CLI / max_width plumbing.)

---

## diskio

**Source:** `glances/plugins/diskio/__init__.py::msg_curse`

**Guard:** returns empty if `not self.stats`, plugin disabled, or
`max_width` is `None` (logs a debug message).

**Expected v4-equivalent output (default — byte rates):**

```
DISK I/O              R/s     W/s
nvme0n1              100B     50B
sda                   1.4M   732K
```

**`name_max_width` computation:** `max_width - 13`

**Header field table (default mode):**

| field | label | format | alignment | width | notes |
|---|---|---|---|---|---|
| (title) | `DISK I/O` | `'{:{width}}'.format('DISK I/O', width=name_max_width)` | left | name_max_width | `TITLE` |
| read | `R/s` | `'{:>8}'.format('R/s')` | right | 8 | `DEFAULT` |
| write | `W/s` | `'{:>7}'.format('W/s')` | right | 7 | `DEFAULT` |

Header variants (controlled by `args`):

| mode | labels shown |
|---|---|
| default (rate) | `R/s` + `W/s` |
| `--diskio-iops` | `IOR/s` + `IOW/s` |
| `--diskio-latency` | `ms/opR` + `ms/opW` |

**Per-disk row:**

| field | format | alignment | width | color rule |
|---|---|---|---|---|
| disk_name | left-padded, tail-truncated with `_` when too long | left | name_max_width | `DEFAULT` |
| read | `auto_unit(read_bytes_rate_per_sec)` (no `/s` suffix — header carries it) | right | 7 | `get_views(item=disk, key='read_bytes', option='decoration')` |
| write | same for write_bytes | right | 7 | `get_views(item=disk, key='write_bytes', option='decoration')` |

**Sort order:** disk name ascending (`sorted_stats()`).

**Color logic:** `read_bytes` / `write_bytes` decorations come from
``get_alert(bytes, header='rx', action_key=disk_name)`` and the ``tx``
variant. v4 thresholds are configurable but ship with no defaults —
v5 keeps this opt-in semantic via ``strict_thresholds=True`` so a
legacy ``[diskio] careful=50`` cannot bleed onto per-disk rates.

**Conditional behaviour:**
- Disks whose name starts with ``ram`` are hidden unless
  ``--diskio-show-ramfs`` is passed (issue #714). Not implemented in
  v5 G4 — operators can use the show/hide regex filters.
- ``--diskio-iops`` / ``--diskio-latency`` alt modes deferred to a
  later phase pending args plumbing through ``render()``.
- v4 hides disks that never had non-zero traffic
  (``hide_zero_fields`` per-view). v5 keeps zero-traffic disks
  visible — operators can filter via ``[diskio] hide=`` regex.

✅ **v5 renderer:** `glances/plugins/diskio/render_curses_v5.py`
(Added in G4-diskio. Default rate mode only; alt modes deferred.)

---

## load

**Source:** `glances/plugins/load/__init__.py::msg_curse`

**Guard:** returns empty if `not self.stats`, `self.stats == {}`, or plugin is disabled.

**Header line example:**
```
LOAD ↑  4core
1 min   0.72
5 min   1.45
15 min  1.23
```

**Field table:**

| field | label | format | alignment | width | color rule |
|---|---|---|---|---|---|
| (title) | `LOAD` | `'{:4}'.format('LOAD')` | left | 4 | `TITLE` |
| trend | *(space + arrow)* | `' {:1}'.format(trend_msg(...))` | left | 2 | `DEFAULT` |
| cpucore | *(none)* | `'{:3}core'.format(int(cpucore))`  | left | 7 | `DEFAULT` |
| min1 | `1 min` | `'{:7}'.format('1 min')` + `f'{load:>6.2f}'` (or `f'{load:>5.1f}%'` in Irix mode) | right | 7+6 | `get_views(key='min1', option='decoration')` |
| min5 | `5 min` | same pattern | right | 7+6 | `get_views(key='min5', option='decoration')` |
| min15 | `15 min` | `'{:7}'.format('15 min')` + value | right | 7+6 | `get_views(key='min15', option='decoration')` |

**Layout notes:** header (title + trend + core count) on line 1; each load average on its
own line via `curse_new_line()`. Label cell is 7 chars left-aligned; value cell is 6 chars
right-aligned (`>6.2f`). No two-column layout — single column.

**Irix mode:** when `args.disable_irix` is set and `log_core() != 0`, load values are
divided by `log_core()` and multiplied by 100, then formatted as `{:>5.1f}%` (5 chars + `%`).

**Color logic:** `get_views(key='minN', option='decoration')` maps to
CAREFUL/WARNING/CRITICAL thresholds based on load vs. core count ratio. `min1` trend
drives the trend arrow.

**Conditional behaviour:**
- `cpucore` segment only shown when `'cpucore' in self.stats and self.stats['cpucore'] > 0`.
- Irix-mode formatting only when `args.disable_irix` and cores > 0.

✅ **v5 renderer:** `glances/plugins/load/render_curses_v5.py`

---

## network

**Source:** `glances/plugins/network/__init__.py::msg_curse`

**Guard:** returns empty if `not self.stats`, plugin disabled, or `max_width` is `None`
(logs a debug message in that case).

**Header line example (default — rate, two columns):**
```
NETWORK          Rx/s    Tx/s
eth0             1.2Mb   256Kb
lo                  0       0
```

**`name_max_width` computation:** `max_width - 12`

**Header field table:**

| field | label | format | alignment | width | notes |
|---|---|---|---|---|---|
| (title) | `NETWORK` | `'{:{width}}'.format('NETWORK', width=name_max_width)` | left | name_max_width | `TITLE` |
| Rx/s header | `Rx/s` | `'{:>7}'.format('Rx/s')` | right | 7 | `DEFAULT` |
| Tx/s header | `Tx/s` | `'{:>7}'.format('Tx/s')` | right | 7 | `DEFAULT` |

Header variants (controlled by `args`):

| mode | labels shown |
|---|---|
| default (rate, two cols) | `Rx/s` + `Tx/s` |
| `--network-cumul` (cumulative, two cols) | `Rx` + `Tx` |
| `--network-sum` (rate, one col) | `Rx+Tx/s` (width 14) |
| `--network-cumul --network-sum` | `Rx+Tx` (width 14) |

**Per-interface row:**

| field | format | alignment | width | color rule |
|---|---|---|---|---|
| if_name | `'{:{width}}'.format(if_name, width=name_max_width)` | left | name_max_width | `DEFAULT` |
| rx (rate or cumul) | `f'{rx:>7}'` | right | 7 | `get_views(item=if_key, key='bytes_recv', option='decoration')` |
| tx (rate or cumul) | `f'{tx:>7}'` | right | 7 | `get_views(item=if_key, key='bytes_sent', option='decoration')` |
| ax (sum mode) | `f'{ax:>14}'` | right | 14 | `DEFAULT` |

**Rate/unit computation:**
- Default (bits): `to_bit=8`, `unit='b'` — multiply bytes by 8, append `'b'`
- `--byte` flag: `to_bit=1`, `unit=''` — display raw bytes, no suffix
- Value formatted via `self.auto_unit(int(value * to_bit)) + unit` → e.g. `1.2Mb`, `256Kb`

**Interface name truncation:** if `len(if_name) > name_max_width`, truncated to
`'_' + if_name[-(name_max_width-1):]`.

**Layout notes:** one header line + one line per active interface.
Each interface row starts with `curse_new_line()`.
Total row width = `name_max_width + 14` (two 7-char columns) or `name_max_width + 14`
(one 14-char column in sum mode).

**Color logic:** `bytes_recv` and `bytes_sent` decorations come from views thresholds
(CAREFUL/WARNING/CRITICAL) set against configured interface speed limits.

**Conditional behaviour:**
- Interfaces with `is_up == False` are skipped (issue #765).
- Interfaces where both `bytes_recv_rate_per_sec` and `bytes_sent_rate_per_sec` are hidden
  (all-zero, `hide_zero=True`) are skipped (issue #1787).
- Interfaces with no first-measurement rate yet (`rates is None`) are skipped.
- `--network-cumul`: shows total bytes transferred instead of per-second rate.
- `--network-sum`: collapses Rx+Tx into a single 14-char column.
- `--byte`: displays bytes instead of bits.

✅ **v5 renderer:** `glances/plugins/network/render_curses_v5.py`
(G1 ships the default rate-bits-2col mode only — ``--byte``,
``--network-cumul`` and ``--network-sum`` deferred to G2+ pending
``max_width`` / ``args`` plumbing through ``render()``.)

---

## percpu

**Source:** `glances/plugins/percpu/__init__.py::msg_curse`

**Note:** This plugin's layout differs fundamentally from the others — it renders a
transposed table (fields as rows, CPU cores as columns) rather than a single-entity
block. The description below uses prose + representative examples.

**Guard:** returns empty if `not self.stats`, `not args.percpu` (plugin is hidden when
`args.percpu` is False), or plugin is disabled.

**Representative output (Linux, 4 cores, quicklook disabled):**

```
CPU    user  system iowait    idle     irq    nice   steal   guest
CPU0   12.5%   3.2%   0.5%  83.8%    0.0%   0.0%    0.0%    0.0%
CPU1    8.1%   2.0%   0.1%  89.8%    0.0%   0.0%    0.0%    0.0%
CPU2   15.0%   4.5%   1.2%  79.3%    0.0%   0.0%    0.0%    0.0%
CPU3    6.3%   1.8%   0.0%  91.9%    0.0%   0.0%    0.0%    0.0%
CPU*    9.9%   2.8%   0.4%  86.2%   ...
```

**Header construction:**

1. Base header list from OS (method `define_headers_from_os()`):
   - Linux: `['user', 'system', 'iowait', 'idle', 'irq', 'nice', 'steal', 'guest']`
   - macOS: `['user', 'system', 'idle', 'nice']`
   - BSD: `['user', 'system', 'idle', 'irq', 'nice']`
   - Windows: `['user', 'system', 'dpc', 'interrupt']`

2. If quicklook is disabled: prepend `'total'` to the header list and output title
   `'{:5}'.format('CPU')` as `TITLE`.

3. Header row: for each stat name in header list: `f'{stat:>7}'` — right-aligned, 7 chars.

**Per-CPU row:**

| element | format | width | color rule |
|---|---|---|---|
| CPU id label (quicklook disabled) | `f'CPU{id:1} '` (id < 10) or `f'{id:4} '` (id ≥ 10) | 5 | `DEFAULT` |
| each stat value | `f'{value:6.1f}%'` | 7 (6+`%`) | `get_alert(value, header=stat_name)` |

**Overflow row (`CPU*`):**
- Shown only when `len(self.stats) > max_cpu_display` (default: 4).
- Label: `'CPU* '` (5 chars).
- Values: mean of all non-displayed CPUs for each stat, same `{:6.1f}%` format and same
  `get_alert` color rule.

**Layout notes:**
- `max_cpu_display` is configurable (default: 4).
- When more CPUs exist than `max_cpu_display`, the top-N by `total` are shown plus the
  overflow summary row.
- Each CPU row starts with `curse_new_line()`.
- When quicklook is enabled, the `CPU` title column and `total` column are omitted — percpu
  acts as a pure supplementary view.

**Color logic:** `get_alert(value, header=stat_name)` — uses the stat name as the alert
key, mapping to CAREFUL/WARNING/CRITICAL thresholds configured for each CPU field.

**Conditional behaviour:**
- Only active when `args.percpu` is True; cpu plugin hides itself in that case.
- `max_cpu_display` can be overridden in `glances.conf` under `[percpu] max_cpu_display`.
- The set of columns shown is OS-dependent (see header construction above).

✅ **v5 renderer:** `glances/plugins/percpu/render_curses_v5.py`
(G1 ships the quicklook-disabled mode — ``CPU`` title + ``total`` column
always present. Quicklook-enabled toggle deferred to G2+.)

---

## quicklook

**Source:** `glances/plugins/quicklook/__init__.py::msg_curse`

**Note:** This is a v5-native composite (Phase 2 G2), not a generic-rendered
plugin. The model re-collects its own stats and ships a dedicated pure
renderer; the v4 behaviour below is the visual-parity contract.

**Guard (v4):** returns empty if `not self.stats` or plugin is disabled.

**Representative output (compact mode):**

```
Intel Core i7-8550U 2.00/4.00GHz
CPU  [|||||         45.0%]
MEM  [|||||||       62.0%]
LOAD [||            18.0%]
```

**Representative output (per-core mode, `--percpu`, > 4 cores):**

```
CPU0 [||||||||      78.0%]
CPU1 [||||          41.0%]
CPU2 [|||           33.0%]
CPU3 [||            20.0%]
CPU* [|||           29.0%]
```

**Bar layout:** each metric is a label cell (`{:<4}` + space), a bold `[`
bracket cell, the bar string, and a bold `]` bracket cell. The bar string
is produced by the **pure v4 helper** `glances.outputs.glances_bars.Bar`
(`bar_char="|"`), reused verbatim — it returns e.g. `"|||||    45.0%"`.

**Bar width (v5):**
- **Compact mode** (not `full_quicklook`), header present: bars **justify to
  the header line width** — every bar row's painter-width equals the header
  row's, floored to keep the inner bar usable on very short headers
  (`_MIN_BAR_TOTAL`). When the header is replaced by `"Frequency"` (cascade
  step d) the header shrinks, so every bar row shrinks with it.
- **Compact mode, no header** (no `cpu_hz_current`): falls back to the default
  compact column width.
- **Full mode** (`full_quicklook`): bars use `view["quicklook_width"]`
  (`max(20, max_x-8)`), unchanged — they span (almost) the whole terminal and
  do not justify to a header.

**Color logic:** bar colour = the field's alert level from
`payload["_levels"][key]["level"]` mapped through
`curses_renderer_v5._LEVEL_TO_ROLE` (`_role_for`). In per-core mode every
row uses the aggregate `cpu` level.

**Optional header row:** `<cpu_name> <cur>/<max>GHz` (or `<cur>GHz` when max
is unknown), shown only when `cpu_hz_current` is present. Name painted as
`HEADER`. Mirrors v4 `msg_curse` lines 211–228.

**v5 model:** `glances/plugins/quicklook/model_v5.py`

- Scalar composite (`IS_COLLECTION = False`). Watched percent fields
  `cpu` / `mem` / `swap` / `load`, plus the per-core list `percpu` and the
  CPU metadata `cpu_name` / `cpu_hz_current` / `cpu_hz` / `cpu_log_core` /
  `cpu_phys_core`.
- `cpu` and `percpu` come from the v5-native shared sampler
  `glances.cpu_sampler_v5.sampler` (`get_aggregate` / `get_per_core`),
  exactly like the `cpu` / `percpu` plugins. `mem` / `swap` / `load` and
  the CPU metadata come from `psutil` (each call independently guarded,
  `_collect_sync` run via `asyncio.to_thread`). **No import from any v4
  plugin module.**
- `load` is the 15-min average normalised by logical core count
  (`load15 / cpu_log_core * 100`). `mem` is plain
  `(total - available) / total` (no ZFS arc adjustment — see scope cuts).

**Internal fields reach the renderer:** `percpu`, `cpu_name`, `cpu_hz*` and
the core counts are declared `internal: True, watched: False`. They are
excluded from level computation and from the generic renderer, but remain
present in the payload handed to `render_curses_v5.render`.

**view contract:** the renderer reads three keys seeded by
`TuiV5._build_view(max_x)` (`glances/outputs/glances_curses_v5.py`):

| key | type | meaning |
|---|---|---|
| `view["percpu"]` | bool | replace the CPU bar with per-core bars |
| `view["full_quicklook"]` | bool | full-width mode (wider bars) |
| `view["quicklook_width"]` | int | target bar cell width (`max(20, max_x-8)` in full mode, else compact column width) |

**Per-core mode** (`_per_cpu_rows`): show the top 4 cores by `total`
(`_DEFAULT_MAX_CPU_DISPLAY`), then a `CPU*` row whose value is the **mean of
the hidden / overflow cores** (not the displayed ones) — exact v4 Bar-path
parity (`__init__.py` lines 322–324).

**full-quicklook:** the `4` hotkey toggles `TuiV5._full_quicklook`;
`build_frame` then hides the TOP-slot siblings in
`curses_renderer_v5._FULL_QUICKLOOK_HIDDEN` = `{cpu, npu, mpp, gpu, mem,
memswap}` (exact v4 `enable_fullquicklook` parity — `load` and `percpu`
stay visible). The CLI flags `--full-quicklook` / `--percpu` seed the
initial `_full_quicklook` / `_percpu` state.

**Explicit scope cuts (G2):**
- **No GPU** section — deferred to G4A with the gpu plugin.
- **No sparkline** — no v5 history store yet; bars only.
- **No ZFS** arc adjustment on `mem` — plain `(total-available)/total`.

✅ **v5 renderer:** `glances/plugins/quicklook/render_curses_v5.py`

---

## processcount

**Source:** `glances/plugins/processcount/__init__.py::msg_curse`

**Layout:**

```
TASKS 215 (1452 thr), 3 run, 195 slp, 17 oth   Threads sorted automatically
                                                by cpu_percent
```

**Header construction:**
- Title: `'TASKS'` (`TITLE` decoration).
- Total: `'{:>4}'.format(processcount['total'])`.
- Threads (when `'thread'` in stats): ` ({} thr),`.
- Running / Sleeping: ` {} run,` / ` {} slp,`.
- Other: ` {} oth ` where `other = total - running - sleeping`.

**Sort line:**
- Drives off `args.programs` ("Programs" / "Threads") and
  `glances_processes.sort_key` (mapped through `sort_for_human`).
- Adds " sorted automatically" when `glances_processes.auto_sort` is True.

**Conditional behaviour:**
- `args.disable_process` short-circuits with the single line
  ``PROCESSES DISABLED (press 'z' to display)``.
- `glances_processes.process_filter` (when set) prepends a multi-line
  ``Processes filter: <expr> on column <key>`` header with a hint
  ``('ENTER' to edit, 'E' to reset)``.

✅ **v5 renderer:** `glances/plugins/processcount/render_curses_v5.py`
(Added in G4-processlist. Sort indicator and filter UI deferred — v5
hardcodes engine sort to `cpu_percent`; argv/config plumbing comes
with G5.)

---

## processlist

**Source:** `glances/plugins/processlist/__init__.py::msg_curse`

**Layout (excerpt — header + top rows):**

```
CPU%  MEM%      PID USER       THR  NI S Command
78.4   3.1     1234 alice        4   0 S python3 myscript.py
12.5   3.1      512 root         2   0 S sshd
 0.5   0.2       42 bob          1   0 S htop
```

**Header construction:**
- Each column header is produced by `msg_curse_header_common(field, label, …)`
  with the `layout_header` width tokens (e.g. `'cpu': '{:<6} '`, `'mem': '{:<5} '`,
  `'pid': '{:>{width}} '`).
- Active sort column is decorated with `SORT`; the rest get `DEFAULT`.
- v4 conditionally shows VIRT/RES (memory_info), TIME+, R/s/W/s and CPU
  core columns depending on `disable_stats` + `disable_virtual_memory`.

**Per-process row:**

| element | format | color rule |
|---|---|---|
| CPU% | `{:<6.1f}` (or `{:<6.0f}` when no-digit) | `get_alert(cpu_percent, header='cpu_percent')` |
| MEM% | `{:<5.1f}` | `get_alert(memory_percent, header='memory_percent')` |
| PID | `{:>{width}}` (width = `_max_pid_size`) | `DEFAULT` |
| USER | `{:<10}` (truncated, trailing `+` on overflow) | `DEFAULT` |
| THR | `{:<3}` | `DEFAULT` |
| NI | `{:>3}` | `DEFAULT` |
| S | `{:>1}` | `DEFAULT` |
| Command | `{}` (joined cmdline, fallback `[name]`) | `DEFAULT` |

**Conditional behaviour:**
- `args.programs` swaps the per-thread list for an aggregated
  per-program view (sums of cpu_percent / memory_percent etc.).
- `args.enable_process_extended` and `cursor_position` highlight one
  process and append a multi-line extended block (open files, threads,
  TCP/UDP, swap, mean/min/max).
- The list is pre-sorted by the engine via `sort_stats(processlist,
  sorted_by=sort_key, reverse=sort_reverse)`.

✅ **v5 renderer:** `glances/plugins/processlist/render_curses_v5.py`
(Added in G4-processlist. Layout: `CPU% MEM% VIRT RES PID USER THR
NI S R/s W/s Command` — full v4 default column set. Categorical
thresholds wired for `status` and `nice` via
`status_<level>=<csv>` / `nice_<level>=<csv>` in `[processlist]`.
Command rendering ports v4's `split_cmdline`: path + **bold** cmd +
arguments. Top-20 rows, engine sort hardcoded to `cpu_percent` desc,
no extended view, no programs aggregation, no filter UI — these
come back with the v5 argv/config plumbing in G5.)

### Responsive columns (`view["proclist_width"]`)

v5-specific behaviour with no v4 helper equivalent: the processlist lives in
the RIGHT sidebar, and on a narrow terminal the full 12-fixed-column prefix
crowds out the flexible `Command` column. The renderer drops low-priority
fixed columns until `Command` is readable again.

**The `view["proclist_width"]` contract:** the painter tells the renderer the
exact width it will be painted at — the right-sidebar paint width. It is
seeded by `TuiV5._fit_proclist_width` (`glances/outputs/glances_curses_v5.py`)
as:

```
view["proclist_width"] = max_x - _sidebar_split(frame, max_x) - _SIDEBAR_SEPARATOR_GAP
```

This mirrors the `_paint` geometry exactly (`right_x = left_width +
_SIDEBAR_SEPARATOR_GAP`). `left_width` depends only on `frame.left` natural
widths — never on processlist's own columns — so one extra rebuild settles the
value (no oscillation). `_fit_proclist_width` is a no-op (and skips the
rebuild) when no processlist block is present, so the rest of the layout and
wide terminals are unaffected.

**Drop cascade (`_DROP_ORDER`, a→h):** columns are dropped one at a time, in
this fixed maintainer-spec order, until `Command` fits:

| step | column |
|---|---|
| (a) | VIRT |
| (b) | TIME+ |
| (c) | RES |
| (d) | USER |
| (e) | PID |
| (f) | THR |
| (g) | S |
| (h) | NI |

**Never dropped:** `CPU%`, `MEM%`, `R/s`, `W/s`, `Command`. These always
survive — `CPU%`/`MEM%` are the primary signal, `R/s`/`W/s` the IO pair, and
`Command` is the flexible column the whole cascade protects.

**Drop rule (`_visible_fixed_keys`):** drop columns in `_DROP_ORDER` until the
space left for `Command` is at least `_MIN_COMMAND_WIDTH` (= 8) characters, or
all droppable columns are gone. The space accounts for the painter's
inter-cell separators and the dynamic PID width (`_pid_width`, which scales
with the widest PID).

**Header + rows stay consistent:** the visible-column set is computed once per
`render` call, then both the header row and every data row are filtered through
the same `active_set` (`_filter_fixed`). So the header and the rows always drop
the *same* columns and stay aligned.

**Default (no width) keeps all columns:** when `view["proclist_width"]` is
absent or not an `int` (export, tests, callers that pass no `view`), the
renderer keeps all 12 fixed columns — byte-identical to the historical output
(locked by `test_no_width_keeps_all_columns`). No regression for non-TUI
consumers.

**Measure-driven, not threshold-driven:** the visible set is computed from the
*real* right-sidebar width, not a hard-coded column-count breakpoint. Crucially
`_fit_proclist_width` runs at **both** `_build_fitted_frame` return points — the
early return (TOP row already fits, wide terminal) and the post-cascade return
— so the processlist is fitted to its sidebar width even when the TOP row never
needed degrading.

✅ **v5 renderer:** `glances/plugins/processlist/render_curses_v5.py`
(`_DROP_ORDER`, `_FIXED_COL_KEYS`, `_MIN_COMMAND_WIDTH`,
`_visible_fixed_keys`, `_filter_fixed`). Width seeded by
`glances/outputs/glances_curses_v5.py::_fit_proclist_width`.

---

## system

**Source:** `glances/plugins/system/__init__.py::msg_curse`

**Guard:** returns empty if `not self.stats` or plugin is disabled.

**Layout:**

```
hostname  Linux Ubuntu 22.04 LTS
```

Single line: hostname rendered as `TITLE`, followed by a space-padded
`hr_name` (human-readable OS description) as an `optional` segment
(hidden on narrow terminals). In client mode, a connection-status
prefix (`Connected to` / `SNMP from` / `Disconnected from`) is
prepended with an `OK` or `CRITICAL` decoration.

**Conditional behaviour:**
- Client mode adds a connection-status prefix (`args.client`).
- `hr_name` segment is `optional=True` — hidden on narrow terminals.

> ✅ v5: `glances/plugins/system/render_curses_v5.py` (Phase 2 G1). Header line painted by `glances_curses_v5._paint_header`.

---

## uptime

**Source:** `glances/plugins/uptime/__init__.py::msg_curse`

**Guard:** returns empty if `not self.stats` or plugin is disabled.

**Layout:**

```
Uptime: 3 days, 4:12:07
```

Single `DEFAULT`-decorated line: literal prefix `'Uptime: '` followed
by the pre-formatted uptime string returned by the model.

> ✅ v5: `glances/plugins/uptime/render_curses_v5.py` (Phase 2 G1). Header line painted by `glances_curses_v5._paint_header`.

---

## now

**Source:** `glances/plugins/now/__init__.py::msg_curse`

**Guard:** returns empty if `not self.stats` or plugin is disabled.

**Layout:**

```
2024-03-15 14:23:05 UTC
```

Single `DEFAULT`-decorated line: `stats['custom']` formatted to
exactly 23 characters (`'{:23}'.format(...)`) — fixed-width to pad
cleanly against the right edge of the header row.

> ✅ v5: `glances/plugins/now/render_curses_v5.py` (Phase 2 G1). Left-sidebar block.

---

## TOP-row responsive degradation

v5-specific layout behaviour (no v4 equivalent helper, but it reproduces the v4
*visual outcome*: the TOP plugin row never lets curses clip the rightmost block,
LOAD). Implemented in `glances/outputs/glances_curses_v5.py`.

**Problem:** the TOP slot stacks several blocks side by side (quicklook, cpu,
mem, memswap, load…). On a narrow terminal their combined natural width exceeds
`max_x`; the painter would collapse the inter-block gaps to `_TOP_GAP_MIN` and
curses would clip the last block (LOAD). The degradation cascade drops detail
from the *less important* blocks first so LOAD always survives.

**view flags** (seeded with defaults that preserve today's wide-terminal output
byte-for-byte — no regression):

| key | type | default | meaning |
|---|---|---|---|
| `view["cpu_cols"]` | int | `3` | CPU grid columns to render (`3`→`2`→`1`) |
| `view["mem_cols"]` | int | `2` | MEM grid columns to render (`2`→`1`) |
| `view["quicklook_freq_only"]` | bool | `False` | quicklook header shows `"Frequency"` instead of the CPU name; compact bars shrink to match |
| `view["hide_quicklook"]` | bool | `False` | `build_frame` skips the quicklook block |
| `view["hide_memswap"]` | bool | `False` | `build_frame` skips the memswap (swap) block |

**Cascade order (`_DEGRADE_STEPS`):** an ordered list applied one notch at a
time until the row fits. Drop the least-important detail first; hide a whole
block only as a last resort. `cpu_cols=1` subsumes the col-3 drop, so (b)
(`cpu_cols=2`) is tried before (c) (`cpu_cols=1`):

| step | mutation | effect |
|---|---|---|
| (a) | `mem_cols = 1` | hide MEM's 2nd column |
| (b) | `cpu_cols = 2` | hide CPU's 3rd column |
| (c) | `cpu_cols = 1` | hide CPU's 2nd column |
| (d) | `quicklook_freq_only = True` | replace the CPU name with `"Frequency"` and shrink the quicklook block |
| (e) | `hide_quicklook = True` | hide the quicklook block |
| (f) | `hide_memswap = True` | hide the swap block |
| (g) | _planned (G4A)_ `hide_gpu = True` | hide the gpu block — the very last resort, once the gpu plugin joins the TOP row |

> **Planned (G4A — gpu):** the gpu plugin will insert into the TOP row. The cascade must then extend with step **(g)** `hide_gpu` _after_ (f), and `build_frame` must gain a matching `hide_gpu` guard (mirroring `hide_quicklook` / `hide_memswap`). Not added yet — it would be dead code without the gpu plugin.

**Fit rule (`_top_fits`):** mirrors the painter's own layout test exactly — the
TOP row fits iff

```
sum(block.width for block in frame.top) + (n - 1) * _TOP_GAP_MIN <= max_x
```

where `n` is the number of TOP blocks and `_TOP_GAP_MIN` (= `1`) is the minimum
inter-block gap. An empty TOP row trivially fits.

**The loop (`_build_fitted_frame`):**
1. Build the per-cycle `view` (`_build_view(max_x)`) and the frame
   (`_frame_for_view(view)`).
2. If `full_quicklook` is active, or the frame already fits (`_top_fits`),
   return it as-is — wide terminals take this early return and do exactly one
   `build_frame` call, byte-identical to today.
3. Otherwise walk `_DEGRADE_STEPS`, setting one flag at a time, rebuilding the
   frame (`_frame_for_view`) and re-measuring after each step; stop as soon as
   `_top_fits` is satisfied (or all steps are exhausted).

`full_quicklook` mode is exempt from the cascade: it already owns the whole
width via its own sibling-hiding (`_FULL_QUICKLOOK_HIDDEN`).

**Measure-driven, not threshold-driven:** the cascade keys on the *real*
`PluginBlock.width` of the rebuilt frame, not on fixed column-count thresholds.
Because the natural widths include the CPU brand-name length, the cascade adapts
automatically to a long CPU name (a wide quicklook header pushes the row over
`max_x` sooner) rather than triggering at a hard-coded width. `build_frame` is
pure and cheap, so calling it a handful of times per paint cycle to measure is
negligible at the 2 s refresh rate (wide terminals call it once).

**Cost:** up to 7 `build_frame` calls on a too-narrow cycle (1 initial + 6
cascade steps); exactly 1 on a wide terminal.

**Residual limit:** the cascade guarantees a fit for any realistic terminal
width, but since cpu/mem/load are never hidden (LOAD is intentionally
protected), a terminal narrower than the fully-degraded row — `cpu` (1 col) +
`mem` (1 col) + `load`, below ~38 cols, far under any real terminal — will
still let curses clip.

✅ **v5 painter:** `glances/outputs/glances_curses_v5.py`
(`_DEGRADE_STEPS`, `_build_fitted_frame`, `_top_fits`, `_frame_for_view`,
`_build_view`, `_TOP_GAP_MIN`). Per-flag rendering lives in
`glances/plugins/cpu/render_curses_v5.py` (`cpu_cols`),
`glances/plugins/mem/render_curses_v5.py` (`mem_cols`),
`glances/plugins/quicklook/render_curses_v5.py` (`quicklook_freq_only` +
justify), and `glances/outputs/curses_renderer_v5.py::build_frame`
(`hide_quicklook` / `hide_memswap`).
