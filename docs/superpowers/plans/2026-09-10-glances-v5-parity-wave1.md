# Glances v5 — parity wave 1 (implementation plan)

**Spec**: `docs/superpowers/specs/2026-09-10-glances-v5-parity-wave1-design.md` —
read it for the decisions each task applies; it is the binding authority.
**Branch**: `develop-v5`.

Seven tasks (Task 7 was added mid-wave, see its own section). Tasks 1, 3 and 5 all add to `GlancesPluginBase.__init__`, so they run
in order and each must be built on what the previous one left in that file.

---

## Global constraints

- **Never commit, never push.** Stage with `git add` and stop; the maintainer
  commits personally.
- **TDD**: the failing test comes first, run it, confirm it fails for the right
  reason, then implement.
- **No change to default behaviour.** Every key here is opt-in and ships absent
  or commented in `conf/glances.conf`. The only new thing an unconfigured user
  can ever see is the WARNING of Task 1, which requires a stale key to fire.
- **Layers**: filtering and thresholds in `model_v5.py` / `base_v5.py`;
  renderers only read what the payload carries.
- **The payload is a contract**: a per-item field must be declared in
  `fields_description`, and must not appear and disappear between cycles.
- Do not touch `NEWS.rst`. Do not touch `conf/glances.conf` unless a task says so.
- Match the file's existing style (type hints, `ClassVar`, docstring tone).
  Ruff line length 120. Add tests to existing test files where one exists.
- Run the targeted tests plus the full suite once. `tests/test_restful.py::TestGlances::test_051_cors_credentials_disabled_for_wildcard_in_list`
  is known-flaky here (it passes in isolation) — ignore it if it is the only failure.

---

## Task 1 — WARNING on an unrecognised threshold key

Applies spec §3.

**Files**: `glances/plugins/plugin/base_v5.py`, `tests/test_plugin_base_v5.py`
(or the existing base-class test file — find it, do not create a second one).

**What to build**

In `GlancesPluginBase.__init__`, after the fields are indexed, call a new
`_warn_unknown_threshold_keys()` that:

1. Reads the plugin's own config section. Nothing else is inspected.
2. Keeps only *threshold keys*: a key equal to `careful` / `warning` /
   `critical`, or ending in `_careful` / `_warning` / `_critical`.
3. Builds the accepted names:
   `{schema.get("threshold_field", name) for name, schema in fields with watched: True}`
   — reuse the existing `_threshold_key()` helper rather than restating the rule.
4. A threshold key is **recognised** when, after stripping the level suffix, the
   remainder is empty (the bare `careful` form) or **ends with** one of the
   accepted names. The suffix test is what makes `wlan0_bytes_recv_warning` and
   `/home_percent_careful` work without parsing the primary key.
5. Logs one `logger.warning` per unrecognised key, naming the section, the key,
   and the sorted accepted names.

Config keys are lower-cased by v5's config layer; compare lower-cased.

**Tests** (each must fail before the implementation)

- `[network] rx_warning=0.7` → exactly one WARNING, and its message contains
  `rx_warning` and `bytes_recv`.
- `[network] wlan0_bytes_recv_warning=0.7` → no warning.
- `[fs] /home_percent_careful=50` → no warning (primary key containing `/`).
- `[network] careful=50` (bare form) → no warning.
- `[network] hide_zero=True`, `[network] show=eth.*` → no warning (not threshold keys).
- A plugin with no watched field and `[<plugin>] warning=1` → one warning.

**Verify**: the base-class test file, plus `python -m pytest tests/ -q` for
plugins whose shipped `conf/glances.conf` section might now warn — **if any
shipped section produces a warning, that is a finding to report, not a test to
adjust**: it would mean `conf/glances.conf` documents a key v5 does not accept.

---

## Task 2 — the two dead CLI options

Applies spec §4.

**Files**: `glances/main_v5.py`, `glances/plugins/network/render_curses_v5.py`,
`tests/test_main_v5.py` (or the existing CLI test file),
`tests/test_plugin_network_render_curses_v5.py`.

**`--disable-unicode`** — the consumer already exists
(`glances_curses_v5.py:203,252`), and `main_v5.py:659` already reads
`getattr(args, "disable_unicode", False)`. Only the `add_argument` is missing.
Declare it (store_true), with v4's help text as the model (`main.py:655-658`).

**`--byte`** — v4 semantics (`network/__init__.py:273`): bits per second with a
`b` unit suffix by default; bytes per second and no `b` with `--byte`. The value
is already in the view dict (`main_v5.py:658`). Give the network renderer the
optional third parameter the other renderers already use
(`def render(payload, fields_desc, view=None)`, cf.
`glances/plugins/mem/render_curses_v5.py:89`) and honour `view["byte"]` in the
rate formatter. Remove the `TODO(G2+)` line about `--byte` — leave the rest of
that TODO if it names other unfinished things.

Scope is `network` only: `containers` already honours `--byte` in v5, `diskio`
shows bytes in both versions.

**Tests**

- The parser declares `--disable-unicode` and it reaches the TUI constructor as
  `True`.
- A network payload renders `b`-suffixed bit rates with no view and with
  `view={"byte": False}`, and byte-per-second values with `view={"byte": True}`.

---

## Task 3 — `hide_zero` + `hide_threshold_bytes`, generic

Applies spec §5.1. Builds on Task 1's additions to `base_v5.__init__`.

**Files**: `glances/plugins/plugin/base_v5.py`,
`glances/plugins/network/model_v5.py`, `glances/plugins/diskio/model_v5.py`,
`glances/plugins/network/render_curses_v5.py`,
`glances/plugins/diskio/render_curses_v5.py`, and the matching test files.

**What to build**

- `HIDE_ZERO_FIELDS: ClassVar[list[str]] = []` on `GlancesPluginBase`.
  `network` declares `["bytes_recv", "bytes_sent"]`; `diskio` declares its two
  byte-rate fields (`read_bytes`, `write_bytes` — v5 keeps the base names,
  `rate: True` replaces the value in place).
- `base_v5` reads `[<plugin>] hide_zero` (bool, default `False`) and
  `hide_threshold_bytes` (int, default `0`) once, at construction.
- Sticky state per primary-key value and field: a field starts hidden and is
  un-hidden for good the first time its value is **strictly greater** than
  `hide_threshold_bytes` (v4 `cc5e2bab` — `>`, never `>=`). `None` never
  un-hides anything.
- Publish ONE row-level boolean per item: a declared field `hidden`
  (`internal: True`, `exportable: False`), `True` only when **every**
  `HIDE_ZERO_FIELDS` entry of that item is still hidden. This is the deliberate
  divergence from v4 recorded in spec §5.1 — put a comment saying so, citing the
  spec, so the next reader does not "fix" it back to per-field.
- With `hide_zero` off, `hidden` is always `False`.
- The item stays in the payload. Only the renderers skip a row whose `hidden`
  is `True`.

**Tests**

- Stickiness: a cycle above the threshold un-hides, and a later cycle back at 0
  keeps the row visible.
- Boundary: a value exactly equal to `hide_threshold_bytes` does NOT un-hide.
- Row rule: one field moving keeps the row visible while the other stays at 0.
- `None` rates (first sample) leave the row hidden.
- `hide_zero=False` (default) hides nothing, whatever the values.
- The renderers skip a hidden row and keep the others.
- The payload still carries the hidden item (REST/history unaffected).

---

## Task 4 — `hide_no_up`, `hide_no_ip`, `[fs] allow`, `[fs] free_space`

Applies spec §5.2, §5.3, §5.4.

**Files**: `glances/plugins/network/model_v5.py`,
`glances/plugins/fs/model_v5.py`, `glances/plugins/fs/render_curses_v5.py`,
`glances/main_v5.py`, and the matching test files.

- **`hide_no_up` / `hide_no_ip`** (network, both default `False`): filter at
  collection time, exactly as v4 `network/__init__.py:164-173` — `hide_no_up`
  drops interfaces whose psutil status is not up; `hide_no_ip` drops those with
  no address of a family other than `AF_LINK`. These two DO drop the item from
  the payload (v4 parity — unlike `hidden` of Task 3).
- **`[fs] allow`**: a comma-separated list of extra filesystem types to include
  on top of the built-in list (v4 `fs/__init__.py:160-170`, issue #448).
- **`[fs] free_space`**: switches the fs block from used space to free space.
  Implement the config key, the CLI option `--fs-free-space` (v4
  `main.py:644`, config fallback at `main.py:832`) and the renderer behaviour
  (v4 `fs/__init__.py:298,318` is the display reference). The renderer takes the
  optional `view` third parameter, like the other renderers.
  **The hotkey `F` is out of scope** — spec §5.4 defers it to the TUI group.

**Tests**: each filter drops exactly what v4 drops and nothing else; the default
(key absent) changes nothing; the fs block shows free space under the config key
and under the CLI option, and used space without them.

---

## Task 5 — generic `alias`

Applies spec §5.5. Builds on Tasks 1 and 3 in `base_v5.__init__`.

**Files**: `glances/plugins/plugin/base_v5.py`, the `network`, `diskio` and `fs`
renderers, and the matching test files.

- Parse `[<plugin>] alias=<key>:<Name>,...` once in `base_v5.__init__`, next to
  the `show`/`hide` filters. Lower-cased keys, v4 `model.py:1075-1081`.
- For collection plugins, publish a declared per-item field `alias` (string,
  `internal: True`) when the item's primary-key value has a match. **Never
  rewrite the primary key** — `_levels`, the per-item threshold overrides and
  the rate matching are all keyed on it.
- The `show` / `hide` filters must match the alias as well as the raw value
  (v4 `model.py:1044,1059`).
- `network`, `diskio` and `fs` renderers display the alias when present.
- **Do not touch `sensors`**: it has its own richer alias handling
  (`sensors/model_v5.py:194-214`) that the generic one does not cover.
- The name sort is deliberately left alone (spec §5.5).

**Tests**: alias published for a matching item and absent otherwise; the primary
key unchanged in the payload and in `_levels`; `hide=<alias>` hides the item;
the three renderers print the alias; a `sensors` alias still works exactly as
before.

---

## Task 6 — documentation: the TUI group and the closed gaps

Applies spec §6. **Documentation only — no code, no tests.**

**Files**: `docs/architecture/glances-v5-architecture-decisions.md`,
`docs/architecture/glances-v5-v4-parity-inventory.md`.

1. Add an owned group to the §10 roadmap covering the whole interactive TUI
   surface listed in spec §6 (process management, the 23 show/hide toggles
   including the `F` deferred by spec §5.4, the 9 data-type toggles, `F5` /
   `Ctrl-R`, the sort arrows). Point at Part 3 of the parity inventory for the
   key-by-key list instead of duplicating it. Follow the shape of the existing
   phase entries.
2. In the *v4 feature parity backlog* table, mark what this wave closes: the
   `hide_zero` row, the display-filters row, and the threshold-rename row (which
   becomes "decided: rename kept, WARNING added"). Remove a row only when the
   wave actually closed it; otherwise narrow its wording to what is left.
3. **Add the two backlog rows the new `conf/glances.conf` comments point at.**
   Task 7 commented keys out with "known gap, see §10", and the review found that
   pointer currently dangles — §10's table has no row for either:
   - **`percpu` has no threshold colouring in v5** — it declares no watched field
     (`percpu/model_v5.py:19-22`), while v4 colours each core's user/system/iowait
     from `[percpu] user_*` etc. The docstring there justifies the choice by v4's
     lack of `'log': True`, which is about *alerting*, not *colouring* — quote that
     distinction in the row so the next reader does not re-derive it.
   - **`diskio` lost the latency family** — `[diskio] rx_latency_*` / `tx_latency_*`
     have no v5 equivalent (`diskio/model_v5.py:23-25`).
   Do NOT record a `sensors` gap: the wave established that `sensors` resolves its
   own threshold tiers (`<type>_<level>` and `<type>_<label>_<level>`) and those keys
   work. What deserves a line — in §3's threshold-warning material, not the backlog
   — is that a plugin resolving thresholds itself declares its key shapes through
   `GlancesPluginBase._recognises_threshold_key()`, or the startup warning will
   false-positive on it, as it did on `sensors` before the hook existed.
4. In the parity inventory, update the status of every line this wave changed
   (the `⚠️ partiel` / `❌ absent` cells for `--disable-unicode`, `--byte`,
   `hide_zero`, `hide_threshold_bytes`, `hide_no_up`, `hide_no_ip`, `[fs] allow`,
   `[fs] free_space`, `alias`), and re-run the counts in its "Synthèse" table so
   the totals stay true. Add a dated line saying which wave changed them.

---

## Task 7 — make the shipped `conf/glances.conf` v5-correct

**Added mid-wave**, after Task 1's WARNING surfaced the real state of the shipped
config. This task is the reason the wave exists — do not skip it.

**What Task 1 revealed** (verified by the controller against the shipped file):
the config Glances v5 ships declares, **uncommented**, threshold keys that v5
silently ignores. A default v5 install today runs *without* the thresholds its
own configuration file documents:

| Section | Live keys in `conf/glances.conf` | v5 state |
|---|---|---|
| `[network]` | `rx_careful/warning/critical`, `tx_*` (conf:333-338) | v5 accepts `bytes_recv_*` / `bytes_sent_*`, **as a ratio in `[0,1]`**, not a percent (`network/model_v5.py:75-96`) |
| `[processlist]` | `cpu_careful/warning/critical`, `mem_*` | v5 accepts `cpu_percent_*` / `memory_percent_*` (same percent scale) |
| `[percpu]` | `user_*`, `iowait_*`, `system_*` | v5 `percpu` declares **no watched field at all** — the per-core cells are never threshold-coloured (`percpu/model_v5.py:19-27`) |
| `[diskio]` | `rx_latency_*`, `tx_latency_*` | the latency family was removed from v5 by decision (`diskio/model_v5.py:23-25`) |
| `[sensors]` | `temperature_core_careful/warning/critical` | v5 sensors watches a single generic `value` field (`sensors/model_v5.py:94-99`); the v4 per-type key shape is not accepted |

**Files**: `conf/glances.conf` only. No code, no tests — the assertion that the
shipped conf produces no warning belongs to Task 1's test suite, which already
covers the mechanism; add a test there ONLY if none pins "the shipped conf emits
no unrecognised-threshold warning".

**What to do**

1. **Rename what has a v5 equivalent**, keeping the same intent:
   - `[network]`: `rx_*` → `bytes_recv_*` and `tx_*` → `bytes_sent_*`, **and convert
     the values from percent to ratio** (`70` → `0.7`, `80` → `0.8`, `90` → `0.9`)
     — v5 compares the rate against link capacity through
     `normalize_by: bytes_speed_rate_per_sec`. Getting this wrong silently sets
     thresholds 100× too high, so state the conversion in a comment above the keys.
   - `[processlist]`: `cpu_*` → `cpu_percent_*`, `mem_*` → `memory_percent_*`
     (values unchanged — same percent scale).
2. **Comment out what v5 has no equivalent for**, each with a one-line reason and
   a pointer to the parity backlog, so a reader knows it is a known gap and not
   an oversight:
   - `[percpu]` `user_*` / `iowait_*` / `system_*` — v5 percpu has no watched field.
   - `[diskio]` `rx_latency_*` / `tx_latency_*` — family removed in v5.
   - `[sensors]` `temperature_core_*` — v5 has no per-type threshold key.
3. Change **nothing else** in the file. Do not reflow, do not reorder, do not
   touch other sections' comments.

**Verify**: instantiate every discovered plugin class against the shipped
`conf/glances.conf` and confirm **zero** unrecognised-threshold warnings. Do it
with a handler attached to the `glances.plugins.plugin.base_v5` logger AFTER the
imports — importing `glances.main_v5` / `glances.config_v5` reconfigures the root
logger, and a naively-added `StreamHandler` will silently show nothing (that is
exactly how Task 1's report got the wrong answer). Cross-check against
`~/.local/share/glances/glances.log`.

---

## Done bar

- [ ] Tasks 1-5 and 7 implemented, each with tests that fail before and pass after.
- [ ] `python -m pytest tests/ -q` green (bar the known-flaky test_051).
- [ ] `make pre-commit` run at the end on the staged index.
- [ ] Task 6's documentation matches what was actually built.
- [ ] Everything **staged, not committed**.
