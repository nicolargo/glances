# Glances v5 TUI — per-plugin show/hide hotkeys (Phase 2.X-a)

**Date:** 2026-09-21
**Branch:** `develop-v5`, on top of `168d339` (WebUI right-column fit, G9 closed)
**Group:** Phase 2.X — TUI interactive surface
(`docs/architecture/glances-v5-architecture-decisions.md` §10)
**Closes:** gap #2 of the ten that matter
(`docs/architecture/glances-v5-v4-parity-inventory.md` — "Les 10 écarts qui comptent")

---

## 1. Scope

The SHOW/HIDE family of v4 hotkeys: the keys that make one plugin — or one
layout slot — disappear from the terminal and come back. Nothing else from
Phase 2.X. No process cursor, no kill, no nice, no filter: those are 2.X-b and
they are what the *other* half of the SHOW/HIDE table depends on (§3.3).

---

## 2. The count in the roadmap is wrong, and the inventory is why

§10 of `…decisions.md` says **"The 23 per-plugin show/hide toggles"**. That
figure comes from Part 3 of the parity inventory, which tabulates 24 rows in
its SHOW/HIDE section, one of them (`4`) already ported.

Read against the v4 dispatch table itself
(`glances/outputs/glances_curses.py:41-98`) the figure does not hold:

- **`C` (`switch: disable_cloud`, `glances_curses.py:58`) is absent from Part 3
  entirely.** Not listed in SHOW/HIDE, not in MISCELLANEOUS, not anywhere — I
  grepped the whole section. The inventory's own summary claims to tabulate
  "54 real entries" from `_hotkeys`; `C` is one of the 54 and it was dropped.
- **`r` (`switch: disable_smart`, `glances_curses.py:84`) is a show/hide
  toggle filed under MISCELLANEOUS**, because the inventory row is
  (correctly) preoccupied with a v4 documentation bug — v4's in-app help and
  `docs/cmds.rst` both label `r` "Reset history" while the code binds it to
  SMART visibility. Whatever the label, the behaviour is a visibility toggle
  and it belongs to this chantier.
- **`e` (extended process stats) sits in SHOW/HIDE but is not one.** It is
  `_handle_process_extended` (`glances_curses.py:345-351`), which sets
  `enable_process_extended` *and* `disable_cursor` — it decorates the
  cursor-selected process. With no cursor in v5 there is nothing to extend.
  It is 2.X-b work.

So the real scope of this chantier is **24 keys**, not 23: the 24 SHOW/HIDE
rows, minus `4` (ported), minus `e` (2.X-b), plus `C` (missed) and `r`
(misfiled).

**This spec does not fix the inventory.** Part 3 is a dated snapshot with its
own provenance; amending it is a separate, and larger, correction pass. The
discrepancy is recorded here and in §9 so the next reader of §10 does not
re-derive it.

## 3. The 24 keys

### 3.1 Plain per-plugin toggles (19)

Each is one v4 `switch` on a `disable_<plugin>` arg, and maps to exactly one
v5 registry plugin name.

| Key | v4 switch (`glances_curses.py`) | v5 plugin | v5 slot |
|---|---|---|---|
| `A` | `disable_amps` :54 | `amps` | right |
| `C` | `disable_cloud` :58 | `cloud` | header |
| `d` | `disable_diskio` :59 | `diskio` | left |
| `D` | `disable_containers` :60 | `containers` | right |
| `G` | `disable_gpu` :66 | `gpu` | top |
| `I` | `disable_ip` :69 | `ip` | header |
| `K` | `disable_connections` :72 | `connections` | left |
| `l` | `disable_alert` :73 | `alert` | right |
| `n` | `disable_network` :77 | `network` | left |
| `N` | `disable_now` :78 | `now` | header |
| `P` | `disable_ports` :81 | `ports` | left |
| `Q` | `enable_irq` :83 **(inverted)** | `irq` | left |
| `r` | `disable_smart` :84 | `smart` | left |
| `R` | `disable_raid` :85 | `raid` | left |
| `s` | `disable_sensors` :86 | `sensors` | left |
| `V` | `disable_vms` :92 | `vms` | right |
| `W` | `disable_wifi` :94 | `wifi` | left |
| `7` | `disable_npu` :50 | `npu` | top |
| `8` | `disable_mpp` :51 | `mpp` | top |

Slots are `curses_renderer_v5.py:60-85` (`HEADER_SLOT` :62, `TOP_SLOT` :63,
`LEFT_SLOT` :64, `RIGHT_SLOT` :77).

### 3.2 Compound and structural toggles (5)

| Key | v4 | Reaches | Note |
|---|---|---|---|
| `f` | `_handle_fs_stats` :361-363 | `fs` **and** `folders` | One key, two plugins, flipped together. |
| `z` | `_handle_disable_process` :387-392 | `processlist`, `programlist`, `processcount` | v4 also calls `glances_processes.disable()` — see §6.3. |
| `2` | `switch: disable_left_sidebar` :45 | the whole LEFT slot | v4 checks the flag at layout time (:928), not per plugin. |
| `3` | `switch: disable_quicklook` :46 | `quicklook` | A plain toggle; listed here only because `4` interacts with it (§6.4). |
| `5` | `_handle_top_menu` :343-348 | the whole TOP slot | v4 expands over `_top` (:110), flipping each `disable_<p>`. |

`3` is mechanically a §3.1 toggle. It is tabulated here because full-quicklook
(`4`, already ported) hides TOP siblings through a *different* mechanism and
the two must be shown to compose (§6.4).

### 3.3 Explicitly deferred to 2.X-b

`e` — extended stats for the cursor-selected process. No cursor exists
(`glances_curses_v5.py` has no `cursor_position`, confirmed by the inventory's
own grep). Binding `e` to anything now would be inventing behaviour.

---

## 4. What v5 has today

### 4.1 The hotkey table

`_HOTKEYS` (`glances_curses_v5.py:151-169`) is data-driven with three action
kinds — `sort`, `switch` (toggle a `ViewState` boolean), `action` (a named
verb). 15 keys. `_handle_key` (:277-342) dispatches; the `h` overlay is
generated from this same table, so a new entry documents itself and the two
cannot drift. The overlay already scrolls (`_handle_help_key`, `j`/`k`), so
24 new rows need no new overlay mechanism.

`ViewState` (:107-127) holds only booleans: `show_percpu`,
`process_short_name`, `programs`, `show_help`.

### 4.2 Plugin hiding in the renderer

`build_frame` (`curses_renderer_v5.py:1252-1272`) already skips plugins by
view key — but as **seven hardcoded `if` statements**, one per plugin:

```python
if view and view.get("hide_quicklook") and plugin_name == "quicklook":
    continue
if view and view.get("hide_memswap") and plugin_name == "memswap":
    continue
# … hide_gpu, hide_cloud, hide_now, hide_ip, hide_uptime
```

Those seven keys are **not a user-facing mechanism**. They are owned by the two
automatic width-degradation cascades: `_DEGRADE_STEPS`
(`glances_curses_v5.py:66-74`, the TOP row) and `_HEADER_DEGRADE_STEPS`
(:91-98, the header banner). The `view` dict is rebuilt from scratch every
cycle by `_build_view` (:820-839) and the cascade writes into it during the
fit loop.

This is the single most important fact in the design: **the cascade and the
user are two different authorities writing hide decisions, and the cascade
rewrites its keys every frame.**

---

## 5. Design

### 5.1 D1 — a separate namespace, union semantics

`ViewState` gains one field:

```python
hidden_plugins: set[str] = field(default_factory=set)
```

`_build_view` publishes it as `view["user_hidden"] = frozenset(...)`.

`build_frame` hides a plugin when **either** authority says so:

```python
if plugin_name in view.get("user_hidden", frozenset()):
    continue
if view.get(f"hide_{plugin_name}"):
    continue
```

Why not one key. If the user toggle wrote `hide_gpu`, the cascade's frame-by-
frame rewrite of that same key would either clobber the user's choice or
strand it: a gpu hidden by width pressure at step (g) and then *un*-hidden by
the user would flip back the next time the fit loop ran, and a user-hidden gpu
would make the cascade believe it had already spent step (g). Two namespaces,
union at the read site, and neither authority can corrupt the other.

Union is also the honest semantics: "hidden because I said so" and "hidden
because there is no room" are both hidden, and a user un-hiding a block cannot
conjure width that does not exist.

### 5.2 D2 — the `if` chain becomes one lookup

The second line above (`view.get(f"hide_{plugin_name}")`) subsumes all seven
existing `if` statements exactly — same keys, same truth test, same `continue`.
It is a strict generalisation: it also makes every *other* plugin cascade-
hideable, which costs nothing today (no cascade step names them) and removes
the edit that a future cascade step would otherwise need.

This is the only change this chantier makes to `build_frame`'s control flow.
The per-plugin comments that currently justify each `if` (the header
degradation rationale) move to the `_HEADER_DEGRADE_STEPS` table, which is
where they belong — they document the cascade, not the renderer.

### 5.3 D3 — a fourth action kind, `hide`

```python
"n": {"hide": ("network",), "group": "SHOW/HIDE", "desc": "Show/hide network stats"},
"f": {"hide": ("fs", "folders"), "group": "SHOW/HIDE", "desc": "Show/hide filesystem and folders"},
```

Always a tuple, so the compound keys of §3.2 are not a special case. Dispatch
toggles the whole tuple as one unit, keyed on the *first* name so a compound
key never lands half-hidden:

```python
if "hide" in action:
    names = action["hide"]
    if names[0] in self._view.hidden_plugins:
        self._view.hidden_plugins.difference_update(names)
    else:
        self._view.hidden_plugins.update(names)
    return "changed"
```

`"changed"` (not `"repaint"`) — it mutates the stats view, like every other
switch.

### 5.4 D4 — slots are expanded at press time, not carried as slot state

`2` and `5` bind to `hide` tuples holding the slot's plugin names:
`LEFT_SLOT` (`curses_renderer_v5.py:64`) and `TOP_SLOT` (:63), imported, not
retyped.

v4 does this for `5` already (`_handle_top_menu` expands over `_top`) and does
*not* for `2` (a layout-time flag). Expanding both is the v5 choice, for one
reason: v5's `hidden_plugins` is the single place a block's visibility is
decided, and a parallel `hidden_slots` would need its own read site in
`build_frame`, its own interaction rule with `hidden_plugins`, and its own
answer to "what does `n` do after `2`". Expansion needs none of that —
after `2`, `n` un-hides network alone, which is what a user pressing it means.

The cost, stated plainly: `2` then `n` then `2` leaves network visible and the
rest of the sidebar hidden, where v4 would restore the whole sidebar. That is
the v4 behaviour of `5` (whose expansion has the same property) applied to `2`
as well — consistency between the two structural keys, bought at the price of
exact `2` fidelity. **Maintainer's call; §9 Q1.**

### 5.5 D5 — the two inverted keys stay inverted in *meaning*, not in state

`Q` is `enable_irq` in v4: irq is opt-in, so the key enables rather than
disables. In v5 the *state* is uniformly "hidden or not", so `Q` is an
ordinary toggle over `("irq",)`. The asymmetry survives only in the starting
value — see §6.1, which is where the real problem lives.

`r` binds to `("smart",)`, following the v4 **code**, not the v4 docs. The
docs bug is v4's and out of scope; the v5 help overlay will read
"Show/hide SMART stats", which is what the key does.

---

## 6. Divergences from v4 forced by v5's architecture

These are not choices. They fall out of decisions already taken, and each one
needs to be visible in the release notes.

### 6.1 A config-disabled plugin cannot be revealed by a hotkey

`discover_plugins` (`main_v5.py:370-390`) does not instantiate a plugin whose
`[<plugin>] disable` is true — deliberately, and documented there: `ports`
builds its scan list and starts a thread in `__init__`, so gating later "would
be too late". Such a plugin is absent from the registry
(`main_v5.py:674`), publishes nothing to the store, and has no `fields_by_plugin`
entry.

So a hotkey for it has nothing to show. This bites hardest on `Q`/`irq`,
whose v4 semantics are precisely "reveal the opt-in module": in v4 irq is
collected and display-gated; in v5, off means absent.

The same applies to anything switched off by `--disable-plugin` / `[<p>] disable`.

**Decision: the hotkey is bound unconditionally and is a no-op on an absent
plugin.** The alternative — binding keys from the live registry — makes the
help overlay's contents vary by configuration and makes a key silently
unbound, which is worse than a key that visibly does nothing. Runtime
re-enable is issue #3548's problem and `discover_plugin_classes`
(`main_v5.py:336-346`) already exists as its entry point; when it lands, `Q`
becomes correct with no change here.

### 6.2 Hiding a right-column plugin returns its rows to the others

`_fit_right_column` (`glances_curses_v5.py:712-760`) counts items via
`count(name)`, which returns `0` for a block not in `frame.right`. A plugin
hidden by §5.1 is filtered before the plan is computed, so `plan_right_column`
redistributes its budget to the survivors automatically.

This is a v5 *improvement* over v4 (which has no vertical budget at all), it
needs no code, and it must be tested — it is exactly the kind of emergent
behaviour that a later refactor breaks silently.

### 6.3 `z` does not stop the process engine

v4's `_handle_disable_process` calls `glances_processes.disable()`, halting
collection. In v5 the same engine singleton is shared with the REST API and
the WebUI: a TUI keypress that stopped collection would blank `/api/5/processlist`
for every other consumer.

**`z` hides the three process blocks in the TUI and nothing else.** The CPU
saving v4 gets is not reproduced. Recorded as a deliberate v5 divergence.

### 6.4 `3` and `4` compose by union, and that is the correct reading

Full-quicklook (`4`) hides TOP siblings through `_FULL_QUICKLOOK_HIDDEN`
(`curses_renderer_v5.py:91`, applied :1253) — a third authority, untouched by
this design. `3` puts `quicklook` in `hidden_plugins`.

Pressing `4` then `3` therefore yields: every other TOP block hidden by
full-quicklook, quicklook hidden by the user — an empty TOP row. No special
case.

**Amended 2026-09-22.** When this was written `_FULL_QUICKLOOK_HIDDEN` was v4's
six-plugin set, leaving `load` and `percpu` on the row, and v4 reached the same
end state by the same route. The maintainer has since widened `4` to hide every
TOP sibling (`…decisions.md` §10, "Reversed decision — full quicklook"), so the
union above now empties the row one key earlier and v4 no longer matches. The
composition rule itself is unchanged.

### 6.5 The WebUI is not affected

v4's show/hide keys are terminal-only, and v5's WebUI has no keyboard surface.
`user_hidden` lives in `ViewState`, which the REST layer never reads. Out of
scope, deliberately: a browser-side visibility control is a WebUI feature, not
a parity gap.

### 6.6 Toggles do not persist

v4 does not persist them across restarts either. `--disable-plugin` and
`[<p>] disable` remain the persistent mechanism. No new config key.

---

## 7. Test strategy

Unit, at the two seams the design creates.

**`_handle_key` dispatch** (`tests/test_curses_v5.py`) — for each of the 24
keys: pressing it adds the right names to `hidden_plugins`; pressing it again
removes exactly those; the return is `"changed"`. A compound key (`f`) flips
both names together and never lands half-hidden. `2`/`5` cover their whole
slot tuple.

**`build_frame` filtering** (`tests/test_curses_renderer_v5.py`) — a name in
`user_hidden` produces no block in any slot; the seven cascade keys still hide
what they hid before the `if` chain was generalised (one test per key, so the
generalisation is proven equivalent and not merely plausible); user and
cascade compose by union, in both orders.

**Drift guard** — a test asserting every `"hide"` tuple in `_HOTKEYS` names
only plugins that exist in `HEADER_SLOT ∪ TOP_SLOT ∪ LEFT_SLOT ∪ RIGHT_SLOT`.
This is what catches a typo'd or renamed plugin name, which would otherwise
be a key that silently does nothing — the exact failure mode §6.1 makes
tolerable and therefore invisible.

**Budget interaction** (`tests/test_curses_renderer_v5.py`) — hiding
`containers` raises the quota `plan_right_column` gives `processlist`. Guards
§6.2.

**Help overlay** — the generated overlay lists a `SHOW/HIDE` group containing
all 24 keys, and `_HELP_GROUPS` (`glances_curses_v5.py:172`) orders it.

No new fixture file. No browser test.

---

## 8. Out of scope

Process management (`e`, `k`, `+`/`-`, `ENTER`/`E`, `M`, arrows) — 2.X-b.
The data-type toggles (`b`, `B`, `L`, `F`, `S`, `T`, `U`, `0`, `6`) — 2.X-c;
`F` is named in §10 of `…decisions.md` as belonging to "the 23", but it
changes what `fs` *displays*, not whether it displays, and it has no home
until 2.X-c. Fixing Part 3 of the parity inventory. Any WebUI change. Any
change to the degradation cascades' step lists.

---

## 9. Open questions for the maintainer

**Q1 — `2` (left sidebar).** §5.4 expands it to the slot's plugins, so a
subsequent single-plugin toggle acts on one plugin rather than restoring the
whole sidebar. v4 keeps `2` as an indivisible layout flag. Expansion, or a
faithful indivisible `2`?

**Q2 — `z` and `disable_cursor`.** §6.3 drops the engine stop. Confirm that
TUI-only hiding is the wanted behaviour, given the REST/WebUI sharing.

**Q3 — the inventory correction.** `C` missing and `r` misfiled (§2) are real
defects in Part 3. Fix them in a separate pass, or amend §10's "23" in place
as part of this chantier?

---

## 10. Predicted divergences to verify in the live smoke test

1. `Q` on a default config does nothing visible (irq is opt-in and absent) —
   §6.1, expected, not a bug.
2. `2` on a narrow terminal may not widen the right column, because
   `_sidebar_split` (:911) reacts to block widths, not to slot emptiness.
   Verify what an empty LEFT slot actually does to the split.
3. Hiding the last block of the TOP row changes `_body_geometry` (:849) and
   moves the body up by two rows, not one (block height + gap).
