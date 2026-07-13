# Glances v5 — G4B design (raid + smart + wifi + ip + CVE-2026-35587)

**Date:** 2026-07-13
**Phase:** 2, group **G4B** (execution order G0→G1→G2→G3→G4A→**G4B**→G5→G6→G7)
**Status:** design (approved decisions baked in; awaiting spec review before plans)

## 1. Goal & scope

Port four v4 plugins to the Glances v5 asyncio architecture, mirroring v4
behaviour (per the "TUI v5 must mirror v4" rule), and integrate the
**CVE-2026-35587 SSRF mitigation** into the `ip` port (same group, per the
Phase 2 design §4.1 and architecture decisions §CVE-2026-35587, severity
*high*).

Plugins: `raid`, `smart`, `wifi`, `ip`. Each is independent; this single
design doc covers all four, with **one execution plan per plugin** (the port
pattern is mechanical and proven in G4A; separate plans keep the review
checkpoints crisp — especially for the security-bearing `ip` plugin).

## 2. Global constraints (apply to every task)

- **Mirror v4**: read the v4 `msg_curse()` + grabber before writing each
  renderer/model; divergent "clean generic" layouts are regressions.
- **LEFT sidebar width budget = 34 chars, separators included.** The curses
  painter inserts a one-space separator between adjacent cells, so
  `col1 + 1 + col2 + 1 + col3 … ≤ 34`. Overshooting clips the rightmost
  column (the sensors unit bug, 2026-07-13). Budget every renderer up-front.
- **Reuse v4 grabbers** via `asyncio.to_thread` (no rewrite of pymdstat /
  pySMART / /proc parsing). Guard each grabber independently.
- **Empty registry / empty stats must stay valid** (a plugin whose hardware
  is absent yields an empty collection, not a crash).
- **Alerts fire on `warning`+ only**; `careful` is colour-only (v5 engine
  already collapses sub-warning levels — see alerts_v5). `prominent: False`
  on watched fields → coloured text, no background highlight (sensors parity).
- **No dead code**, no speculative config keys, surgical edits.
- **Do not touch `NEWS.rst`** during development (release-time only). The CVE
  entry is added by the maintainer at release.
- **No commits/push/PR** — stage only.
- Tests: `.venv/bin/python -m pytest`; lint `ruff check` + `ruff format`.

## 3. Common porting pattern (from G4A)

Each plugin provides, under `glances/plugins/<name>/`:

- `model_v5.py::PluginModel(GlancesPluginBase[...])` — `plugin_name`,
  `IS_COLLECTION`, `fields_description`, `_grab_stats()` (async, wraps the v4
  grabber in `asyncio.to_thread`), and — where colouring/alerts apply — an
  override of `_derived_parameters()` building `self._levels`.
- `render_curses_v5.py::render(payload, fields_desc=None, view=None)
  -> list[Row]` — a `TITLE` header row then per-item rows, using
  `Cell`/`Row`/`ColorRole`/`_LEVEL_TO_ROLE`/`title_role` from
  `glances.outputs.curses_renderer_v5`.
- `tests/test_plugin_<name>_v5.py` and
  `tests/test_plugin_<name>_render_curses_v5.py`.

Collection payload shape (base `_build_store_payload`):
`{"data": [...], **metadata, "_levels": {...}}`. Scalar shape:
`{**stats, **metadata, "_levels": {...}}`.

## 4. Per-plugin design

### 4.1 raid (collection)

- **Grabber**: `pymdstat.MdStat().get_stats()['arrays']` (Linux, `/proc/mdstat`),
  wrapped in `to_thread`, guarded on `ImportError` (plugin yields empty) and
  on runtime failure (returns empty; base keeps last good stats).
- **Shape**: v4 keys arrays by name in a dict. v5 collection needs a flat
  list of dicts, so **inject the array name as the `name` field** (primary
  key). Per-array fields: `name`(pk), `type`, `status`, `used`, `available`,
  `components`(internal), `config`(internal).
- **fields_description** (authored — v4 has none):
  - `name`: primary_key.
  - `type`: internal, watched False (RAID level, e.g. `raid1`; `None`→`UNKNOWN`).
  - `status`: internal, watched False (`active`/`inactive`).
  - `used`: watched False (int|None).
  - `available`: watched False (int|None).
  - `components`: internal, watched False (dict name→role).
  - `config`: internal, watched False (layout string `UU`/`U_`).
- **Levels** (`_derived_parameters` override, mirrors v4 `raid_alert`):
  per array, on a synthetic watched key (use `status` field for the level
  index): `type == raid0` → `ok`; `status == inactive` → `critical`;
  `used is None or available is None` → no level (DEFAULT); `used < available`
  → `warning`; else `ok`. `_levels = {name: {"status": {"level", "prominent"}}}`.
- **EMITS_ALERTS = True** (decision 2026-07-13: degraded/inactive RAID is a
  real incident → feed alert history + action. **This is a deliberate
  enhancement over v4**, which was colour-only. warning=degraded,
  critical=inactive both alert; there is no careful tier here.)
- **Renderer** (`RAID disks` header, Used/Avail cols; budget ≤ 34):
  - Header: `RAID disks`(name col) + `Used`(rjust) + `Avail`(rjust).
  - Per array: `f"{TYPE} {name}"` (name col), then Used/Avail cells coloured
    by the array level. raid0+active → Used=`len(components)`, Avail=`-`.
    active non-raid0 → Used=`used`, Avail=`available`.
  - `inactive` → sub-line `└─ Status inactive` (coloured) + one line per
    sorted component `   ├─/└─ disk {role}: {name}`.
  - degraded (non-raid0, `used < available`) → `└─ Degraded mode` (coloured)
    + if `len(config) < 17`: `   └─ {config with '_'→'A'}`.
  - Fix the name/value column widths so `name + 1 + used + 1 + avail ≤ 34`
    (mirror fs: name = 34 − 1 − 7 − 1 − 7 = 18).
- **Config**: none.

### 4.2 smart (collection)

- **Grabber**: `get_smart_data(hide_attributes)` (module-level v4 helper using
  `pySMART.DeviceList`), wrapped in `to_thread`, guarded on `ImportError`.
  **Root required**: if `not is_admin()`, the plugin yields empty (mirror v4
  `disable`). No `snmp`.
- **Shape reconciliation** (v4's per-device dict uses *numeric attribute
  keys*, which the flat v5 field filter would strip). Reshape each device to:
  `{"name": DeviceName (pk), "attributes": [ {name, key, raw, value, ...}, … ]}`.
  The grab flattens v4's numeric-keyed attrs into the `attributes` list
  (sorted by the v4 numeric order). `_remove_parameters` filters only
  top-level item keys, so the nested `attributes` list passes through intact.
- **fields_description** (authored):
  - `name`: primary_key (DeviceName, e.g. `/dev/sda Samsung SSD 850`).
  - `attributes`: internal, watched False (list of attribute dicts).
- **Levels**: none. **EMITS_ALERTS = False** (v4 has no smart colouring/alerts;
  `worst`/`threshold`/`when_failed` are captured but never decorated).
- **Renderer** (`SMART disks`):
  - Header `SMART disks`.
  - Per device: name line (truncated to the block width).
  - Per attribute (from `attributes`): ` {name (`_`→space)}` (name col) +
    value rjust 8. Value = `auto_unit(raw)` when key ∈ `LARGE_VALUE_KEYS`
    else `str(raw)`; `None`→`""`.
  - Budget the widths ≤ 34.
- **Config**: `hide_attributes` (comma-separated; attributes whose `.name`
  matches are dropped at grab time).

### 4.3 wifi (collection)

- **Grabber**: read `/proc/net/wireless` (Linux; existence-guarded), wrapped
  in `to_thread`. Skip the two header lines; parse each interface line.
  **Do NOT port the dead thread scaffolding** (`self._thread`/`exit()`) —
  it is never used in v4.
- **Shape**: list of dicts, one per interface. Fields: `ssid`(pk — actually
  the interface name, `:` stripped), `quality_link`, `quality_level`.
- **fields_description** (from v4):
  - `ssid`: primary_key.
  - `quality_link`: watched False, unit `dBm`.
  - `quality_level`: watched True, `watch_direction: "low"`, unit `dBm`,
    `prominent: False` (coloured text, no background). **Alert field.**
- **Levels** (`_derived_parameters` override — **INVERTED direction**, v4
  `get_alert` parity): signal is negative dBm, lower = worse, so the
  comparison is `<=`. Read careful/warning/critical from `[wifi]`
  (defaults −65/−75/−85). Per interface:
  `value <= critical → critical`; `value <= warning → warning`;
  `value <= careful → careful`; else `ok`. `TypeError/KeyError → no level`.
  `_levels = {ssid: {"quality_level": {"level", "prominent"}}}`.
  - If the v5 threshold engine natively supports `watch_direction: "low"`
    with a `<=` comparison, use it instead of the override (verify during
    implementation; sensors used an explicit override — reuse that shape if
    the engine lacks a low direction).
- **EMITS_ALERTS = True** (v4 alerts on `quality_level`). `careful` collapses
  to `ok` in the alert engine (warning+ rule) but stays blue in the TUI.
- **Renderer** (`WIFI` + `dBm`): header `WIFI`(name col) + `dBm`(rjust 7).
  Per interface (sorted by ssid): skip `ssid in ('', None)` or
  `quality_level is None` (issues #1151/#1973); name col + `quality_level`
  rjust 7 coloured by level. Budget ≤ 34.
- **Config**: `careful=-65`, `warning=-75`, `critical=-85` (already shipped).

### 4.4 ip (scalar)

- **Private IP grabber**: `get_ip_address()` from `glances.globals` (psutil;
  first up non-`lo` AF_INET iface) → `address`, `mask`; `mask_cidr` via
  `ip_to_cidr`. Wrapped in `to_thread`. `gateway` field kept in schema but
  **left unpopulated** (v4 parity — v4 declares it but never sets it).
- **Public IP** — replace the v4 `threading.Thread` with an **in-model cadenced
  fetch** (cleaner in the asyncio model): the plugin tracks
  `self._last_public_fetch_ts` and `self._public_cache`. On each `update()`
  (at `[ip] refresh`, 60s), if public is enabled and
  `elapsed ≥ public_refresh_interval` (300s), run the *guarded* fetch in
  `to_thread`; otherwise reuse the cache. No standalone thread, no `exit()`
  teardown needed.
- **fields_description** (from v4): `address`, `mask`, `mask_cidr`(number),
  `gateway`, `public_address`, `public_info_human`. Scalar (no primary_key).
- **Renderer** (inline single Row, `optional` segments — collapses on narrow
  terminals): `IP `(TITLE) + `address` + `/{mask_cidr}`; if `public_address`:
  ` Pub `(TITLE) + public address; if `public_info_human`: ` {…}`. Guard
  `UnicodeEncodeError/KeyError` around the public segment (issue #1469).
- **`--hide-public-info`** parity: mask `a.b.c.d`→`a.b.*.*` on
  `public_address` before storing (display-only, as in v4).
- **Config** (`[ip]`): `public_api` (URL), `public_username`,
  `public_password`, `public_field` (list), `public_template`,
  `public_refresh_interval` (300), `public_disabled`, **+ new
  `public_api_allow_internal` (default false)** — see §5.

## 5. CVE-2026-35587 — SSRF mitigation (ip)

**Vulnerability**: `[ip] public_api` is a fully config-controlled URL passed
straight to `urllib.urlopen`; `public_username`/`public_password` are attached
as HTTP Basic-Auth to whatever host it points at. An operator (or a config
injected via env/overlay) can aim it at loopback / link-local / RFC1918 /
cloud-metadata endpoints (e.g. `http://169.254.169.254/…`) and exfiltrate
internal responses and/or forwarded credentials.

The local v4 file already has **scheme validation only** (http/https). v5 must
add the remaining two controls and the opt-out key.

**Mitigation (all three controls, wired in the `ip` port):**

1. **Scheme allowlist** — `urlparse(public_api).scheme in ('http', 'https')`,
   else disable public IP + `logger.warning`. (Port the existing v4 check.)
2. **Internal-IP rejection with DNS resolution** (decision 2026-07-13:
   resolve + check, robust against DNS-based SSRF). At **fetch time**, resolve
   the URL host via `socket.getaddrinfo` and, for **every** resolved address,
   reject if `ipaddress.ip_address(a)` is `is_loopback`, `is_link_local`
   (covers metadata `169.254.169.254`), `is_private` (RFC1918 + others), or
   `is_reserved` — **unless `public_api_allow_internal=true`**. A rejected host
   → skip the request, `logger.warning` once, leave `public_address` empty.
   Resolving per fetch (every 300s) also defeats DNS-rebinding (the check and
   the request see the same resolution only if we connect to a checked IP; see
   note below).
3. **Credential non-forwarding** — subsumed by (2): a blocked host means *no
   request is made at all*, so `public_username`/`public_password` can never
   reach an internal host. Credentials are only ever attached on the path
   where the resolved IPs all passed the check.

**New config key**: `public_api_allow_internal` (default `false`, shipped
**commented** in `conf/glances.conf` → behaviour unchanged for existing
users). Documented in `docs/aoa/ip.rst`.

**Helper**: `_public_api_allowed(url: str, allow_internal: bool) -> bool`
performing scheme + resolve + category check; unit-tested in isolation with
representative hosts (`http://169.254.169.254`, `http://127.0.0.1`,
`http://10.0.0.5`, `http://example.com` mocked to a public IP, `file://…`,
a hostname mocked via `getaddrinfo` to resolve to `169.254.169.254`).

**Rebinding note**: full TOCTOU-proof protection would require pinning the
checked IP into the connection (custom opener). That is out of scope for G4B
(the architecture text asks for scheme + category + credential controls); the
per-fetch resolution closes the config-driven and DNS-alias vectors, which is
the specified bar. A pinned-connection hardening can follow as a separate
security task if desired — flagged, not silently dropped.

## 6. Testing strategy

Per plugin: identity/fields tests; grab-merge + partial-failure; renderer
layout (header + rows) + width-budget assertion (`col-sum + separators ≤ 34`,
the sensors-bug regression guard); level/threshold tests where applicable.

- raid: level mapping (raid0/inactive/degraded/None), degraded sub-line,
  inactive component sub-lines, EMITS_ALERTS True.
- smart: attribute reshape (numeric keys → `attributes` list), hide_attributes
  filtering, root-absent → empty, LARGE_VALUE_KEYS auto_unit, EMITS_ALERTS
  False.
- wifi: inverted level thresholds (`<=`, all four bands), skip empty
  ssid/None, EMITS_ALERTS True, careful colour-only.
- ip: private grab, mask_cidr, inline renderer segments, `--hide-public-info`
  masking, cadenced public fetch (cache reuse before interval), **SSRF helper
  unit tests** (scheme reject, loopback/link-local/private/reserved reject,
  metadata reject, allow_internal opt-in, DNS-alias-to-internal reject,
  credentials never sent to blocked host).

## 7. Deliberate divergences from v4 (documented)

1. **raid raises alerts** (EMITS_ALERTS True) — v4 was colour-only. Chosen
   enhancement; degraded/inactive → alert history + action.
2. **ip public fetch** uses an in-model cadenced `to_thread` instead of a
   standalone `threading.Thread` — fits the asyncio scheduler, removes the
   thread lifecycle/`exit()` teardown.
3. **wifi** drops the dead `self._thread`/`exit()` scaffolding (never used in
   v4).
4. **ip SSRF**: adds internal-IP rejection (DNS-resolved) + credential
   non-forwarding + `public_api_allow_internal`; v4 had scheme-check only.

## 8. Out of scope

- SNMP input method (unimplemented in v4 for all four).
- `ip` gateway population (v4 declares but never sets it).
- TOCTOU-pinned-connection SSRF hardening (flagged in §5, separate task).
- Any `NEWS.rst` entry (maintainer, release-time).
