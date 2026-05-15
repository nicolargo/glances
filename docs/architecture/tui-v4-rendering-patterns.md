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
