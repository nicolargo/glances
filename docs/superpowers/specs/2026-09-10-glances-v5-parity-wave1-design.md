# Glances v5 — parity wave 1: threshold-key warning, dead CLI options, display filters

**Date**: 2026-09-10 · **Branch**: `develop-v5` · **Origin**: the v4 → v5 parity
inventory (`docs/architecture/glances-v5-v4-parity-inventory.md`) and the
maintainer's arbitration on its four highest-value gaps.

## 1. Scope

Four maintainer decisions, taken on the inventory's findings:

| # | Inventory finding | Decision |
|---|---|---|
| 1 | Threshold keys renamed, one family re-scaled | **Keep the v5 names.** No v4 aliases. Emit a startup WARNING on any unrecognised threshold key. |
| 2 | The interactive TUI is missing (15 keys against v4's 62) | **Put it in the development plan** as an owned group. No implementation in this wave. |
| 6 | Two v5 options declared but dead (`--disable-unicode`, `--byte`) | **Fix both.** |
| 7 | Display filters lost (`hide_zero`, `hide_threshold_bytes`, `hide_no_up`, `hide_no_ip`, `[fs] allow`, `[fs] free_space`, generic `alias`) | **Re-implement all of them.** |

Findings 3 (`--bind` default), 4 (`-s` / `-w`) and 5 (the `<...>_log` family)
received no instruction and are **out of scope**: 3 and 4 are release-note items
with no code to write, 5 stays in the parity backlog table.

## 2. Non-negotiable constraints

- **No change to default behaviour.** Every key in this wave is opt-in and
  ships absent or commented in `conf/glances.conf`. An unconfigured user must
  see exactly what they see today — with one deliberate exception: the startup
  WARNING of §3, which fires only for a user who *has* a stale threshold key.
- **Layers**: filtering and threshold logic belong to `model_v5.py` /
  `base_v5.py`; renderers only read what the payload carries.
- **The payload is a contract**: a field's presence must not flicker between
  cycles. A new per-item field is declared in `fields_description` or it does
  not exist.
- Work is **staged, never committed**.

## 3. Finding 1 — WARNING on an unrecognised threshold key

### 3.1 Why a warning and not an alias

v5 renamed `[network] rx_*`/`tx_*` → `bytes_recv_*`/`bytes_sent_*` (and moved
them from percent to a ratio in `[0,1]` via `normalize_by`),
`[processlist] cpu_*`/`mem_*` → `cpu_percent_*`/`memory_percent_*`, and
`[fs] <mnt>_careful` → `<mnt>_percent_careful`. The v4 spellings are silently
ignored today: a user's thresholds simply stop applying, with nothing in the
logs. Accepting both spellings would freeze the v4 vocabulary into v5 forever;
the maintainer chose the rename, so the cost to pay is **telling the user**.

### 3.2 What counts as a threshold key

In a plugin's config section, a key is a *threshold key* when it is exactly
`careful` / `warning` / `critical`, or ends with `_careful` / `_warning` /
`_critical`. Nothing else is examined — action keys (`<level>_action`,
`_action_repeat`), `disable`, `refresh`, `show`, `hide`, `alias`, `list` and
every plugin-specific key are out of scope for this check.

### 3.3 What counts as recognised

For a plugin, the set of accepted threshold names is
`{schema.get("threshold_field", field_name) for every field with watched: True}`
— the same set `_threshold_key()` already computes in `base_v5.py`.

A threshold key is recognised when, after stripping the level suffix, the
remainder is either empty (the bare `careful` form, which applies to any watched
field of the plugin) or **ends with one of the accepted names**, so that both
supported shapes pass:

- `<field>_<level>` — `bytes_recv_warning`
- `<pk>_<field>_<level>` — `wlan0_bytes_recv_warning`, `/home_percent_careful`

The suffix test is what makes primary keys containing `_` or `/` work without
having to parse them.

### 3.4 Where it lives

`GlancesPluginBase.__init__`, once per plugin, at construction — the only place
that has both the config section and `fields_description`. One WARNING per
unrecognised key, naming the section, the key, and the accepted threshold names
for that plugin. A plugin with no watched field and a threshold key in its
section is warned too (every key is unrecognised there).

Note the pre-existing v5 behaviour that config keys are lower-cased: the check
compares lower-cased names, and a primary key whose real case differs is not the
subject of this check.

### 3.5 Deliberately not done

No rename map ("did you mean `bytes_recv_warning`?"). A per-plugin map would
have to encode v4 history that is already ambiguous across plugins — `cpu` and
`mem` are *valid* threshold names for `containers` and `vms` while being stale
ones for `processlist`. Listing the plugin's accepted names is unambiguous and
cannot be wrong.

## 4. Finding 6 — the two dead options

### 4.1 `--disable-unicode`

The consumer already exists: `glances_curses_v5.py:203,252` takes
`disable_unicode` and sets `self._unicode`. `main_v5.py:659` passes it with
`getattr(args, "disable_unicode", False)`. Only the parser declaration is
missing, so the value is always `False`. The fix is the `add_argument` call, and
a test that the flag reaches the TUI.

### 4.2 `--byte`

`main_v5.py:237` declares it and `main_v5.py:658` puts it in the view dict, but
`network/render_curses_v5.py` hardcodes bits per second and carries the open
`TODO(G2+)`. v4 semantics (`network/__init__.py:273`): default is bits per
second with a `b` unit suffix; with `--byte`, bytes per second and no `b`.

Scope is `network` only — v4's other `--byte` consumer is `containers`, already
honoured in v5. `diskio` displays bytes in both versions.

## 5. Finding 7 — the display filters

### 5.1 `hide_zero` + `hide_threshold_bytes` (generic)

v4 (`plugins/plugin/model.py:643-657`) keeps a **sticky, per-field** hidden flag:
a field starts hidden, and the first cycle whose value is strictly greater than
`hide_threshold_bytes` un-hides it **for the rest of the process's life**. The
renderers then drop a row only when *all* of the plugin's `hide_zero_fields`
are still hidden (`network/__init__.py:328`, `diskio/__init__.py:259`).

v5 design:

- `HIDE_ZERO_FIELDS: ClassVar[list[str]] = []` on the plugin class. `network`
  declares `["bytes_recv", "bytes_sent"]`, `diskio` its two byte-rate fields
  (v5 keeps the base names — `rate: True` replaces the value in place).
- `base_v5` reads `[<plugin>] hide_zero` (bool, default `False`) and
  `hide_threshold_bytes` (int, default `0`) once, at construction.
- The sticky state lives in the model, keyed by primary-key value then field.
  A value of `None` (a rate with no previous sample) never un-hides anything.
- **Divergence from v4, deliberate**: v5 publishes ONE row-level boolean per
  item, a declared field `hidden` (`internal: True`, `exportable: False`),
  already reduced with the "all fields still hidden" rule. Both v4 consumers
  compute that same `all(...)`, and a single boolean keeps the WebUI, the TUI
  and any future renderer from re-deriving it three ways. The per-field detail
  is not published.
- With `hide_zero` off (the default), `hidden` is always `False`.
- The item is **never dropped from the payload**: rates, history and the REST
  API keep seeing every interface. Only the renderers skip a hidden row.

The three v4 fixes that this port must carry: strict `>` and not `>=`
(v4 `cc5e2bab`), `network` must actually read `hide_threshold_bytes`
(v4 `d88f9d98`), and a row stays visible while any of its fields is
(v4 `ff80c903`, structural here).

### 5.2 `hide_no_up` / `hide_no_ip` (network)

v4 filters at collection time (`network/__init__.py:164-173`): `hide_no_up`
drops interfaces whose `psutil` status is not up; `hide_no_ip` drops those with
no address of a family other than `AF_LINK`. Both default to `False`. Same place
in v5: `network/model_v5.py::_collect`, before anything else. These two DO drop
the item — v4 parity, and an interface that is down carries no meaningful rate.

### 5.3 `[fs] allow`

v4 (`fs/__init__.py:160-170`): a comma-separated list of extra filesystem types
to include, on top of the built-in list, for logical mounts (#448). Same
semantics in `fs/model_v5.py`.

### 5.4 `[fs] free_space`

v4 exposes it three ways: the config key `[fs] free_space`, the CLI option
`--fs-free-space` (`main.py:644`), and the TUI hotkey `F`. It switches the fs
block from "used space" to "free space".

This wave implements the config key and the CLI option, and the renderer
behaviour. **The hotkey `F` is deferred** to the TUI group of §6 with the other
21 toggles — a single hotkey has no home in v5 until that group builds the
toggle surface, and shipping one key alone would be the third different way of
doing the same thing.

### 5.5 Generic `alias`

v4 loads `[<plugin>] alias=<key>:<Name>,...` in the **base class**
(`model.py:1075-1087`), so it exists for every plugin, and uses it in three
places: the item's published `alias` field (`network`, `diskio`, `fs`), the
`show`/`hide` display filters, which match the alias as well as the raw name
(`model.py:1044,1059`), and the name sort (`model.py:453,461`).

v5 design:

- Parsed once in `base_v5.__init__`, next to the `show`/`hide` filters.
- Applied to **collection plugins** on the primary-key value, publishing a
  declared per-item field `alias` (string, `internal: True`) when a match
  exists. The primary key itself is never rewritten — `_levels`, the per-item
  threshold overrides and the rate matching are all keyed on it.
- The `show` / `hide` filters match against the alias too (v4 parity).
- Renderers that print a name column (`network`, `diskio`, `fs`) display the
  alias when present.
- **`sensors` is not touched**: it has its own richer alias (label and
  `label_type` forms, `sensors/model_v5.py:194-214`) that the generic one does
  not cover. Its section-level behaviour is unchanged.
- The name sort is left as it is: no v5 collection renderer sorts on a name the
  generic alias would change today. Recorded here so the next person does not
  read the omission as an oversight.

## 6. Finding 2 — the TUI group goes into the development plan

No code in this wave. The roadmap in
`docs/architecture/glances-v5-architecture-decisions.md` §10 gains an owned
group covering the whole interactive surface the inventory found missing:

- process management: selection cursor (`UP`/`DOWN`), `k` kill, `+`/`-` nice,
  `ENTER`/`E` filter, `e` extended stats, `M` min/max reset;
- the 23 per-plugin show/hide toggles, including `F` (fs free space) deferred
  from §5.4;
- the 9 missing data-type toggles (`b`/`B`, `%`, `S`, …);
- `F5` / `Ctrl-R` forced refresh and the sort-navigation arrows.

The exhaustive key-by-key list is Part 3 of the parity inventory; the roadmap
entry points at it rather than duplicating it.

## 7. Test strategy

Every item is covered by a test that fails before the change:

- §3: a stale `[network] rx_warning` produces exactly one WARNING naming the
  accepted names; a valid `wlan0_bytes_recv_warning` and a valid
  `/home_percent_careful` produce none; a non-threshold key produces none.
- §4: `--disable-unicode` reaches the TUI; a network payload renders `b`-suffixed
  bits by default and byte-per-second values with `--byte`.
- §5.1: stickiness (a burst un-hides for good), strict `>` at the threshold
  boundary, the row-level `all(...)` rule, `None` never un-hides, and
  `hide_zero=False` hiding nothing.
- §5.2/§5.3: the filters drop exactly what v4 drops.
- §5.4: the fs payload/renderer switches to free space.
- §5.5: alias published, `show`/`hide` matching the alias, `sensors` untouched.
