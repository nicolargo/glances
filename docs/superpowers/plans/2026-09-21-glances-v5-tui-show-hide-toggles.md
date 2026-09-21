# Glances v5 TUI — per-plugin show/hide hotkeys (Phase 2.X-a) — Implementation

**Spec:** `docs/superpowers/specs/2026-09-21-glances-v5-tui-show-hide-toggles-design.md`
**Branch:** `develop-v5`, on top of `168d339`
**Status:** implemented 2026-09-21.

---

## Tasks

- [x] **T1 — `ViewState.hidden_plugins`.** One `set[str]` field, defaulted via
  `dataclasses.field`. Its docstring states why it is a namespace of its own
  and not a `hide_<plugin>` key. → verify: `test_build_view_publishes_the_user_hide_set`.

- [x] **T2 — 24 `_HOTKEYS` entries, a fourth action kind `hide`.** Value is
  always a tuple of plugin names, so compound (`f`, `z`) and slot-wide (`2`,
  `5`) keys are not special cases. `2`/`5` import `LEFT_SLOT`/`TOP_SLOT`
  rather than retyping them. `_HOTKEYS`'s annotation widens to
  `dict[str, dict[str, Any]]` (the values are no longer all `str`).
  → verify: `test_show_hide_family_covers_the_v4_keys`,
  `test_hide_key_toggles_its_plugins_on_and_off` (24 cases).

- [x] **T3 — dispatch.** A `hide` branch in `_handle_key`, keyed on the
  tuple's FIRST member so a compound key never lands half-hidden. Returns
  `"changed"` like the other view switches.
  → verify: `test_compound_key_never_lands_half_hidden`,
  `test_slot_keys_cover_their_whole_slot`.

- [x] **T4 — publish.** `_build_view` exports
  `view["user_hidden"] = frozenset(...)` — a copy, because the fit loops
  mutate `view` freely.

- [x] **T5 — the renderer reads the union.** In `build_frame`, the seven
  hardcoded `if view.get("hide_<plugin>") and plugin_name == "<plugin>"`
  statements collapse to one `view.get(f"hide_{plugin_name}")` lookup, and a
  `user_hidden` membership test joins it. Verified by grep that no other
  `hide_*` view key collides with a plugin name (`hide_ip_location`,
  `hide_os_info`, `hide_public_info`, `hide_zero`, `hide_no_up`, `hide_no_ip`,
  `hide_threshold_bytes`, `hide_attributes` — none is a plugin).
  → verify: `test_cascade_hide_keys_still_skip_their_block` (one case per
  key, so the generalisation is proven equivalent), and the two mutation runs
  below.

- [x] **T6 — help overlay.** `_HELP_GROUPS` gains `"SHOW/HIDE"`. No other
  change: `_help_lines` generates from `_HOTKEYS` and the overlay already
  scrolls.
  → verify: `test_hide_keys_are_documented_in_the_help_overlay`.

- [x] **T7 — drift guards.** Every `hide` tuple names a plugin that exists in
  one of the four slots; no key carries two action kinds.
  → `test_every_hide_key_names_a_real_plugin`,
  `test_hide_keys_do_not_collide_with_the_rest_of_the_table`.

- [x] **T8 — the roadmap.** §10 of `glances-v5-architecture-decisions.md`:
  the show/hide line struck through, the count corrected 23 → 24 with the two
  inventory defects named, `F` moved to the data-type group. Part 3 of the
  parity inventory deliberately NOT amended (spec §2).

---

## Tests touched, and why

Four existing tests changed, all for reasons the change causes:

| Test | Why |
|---|---|
| `test_tui_v5_handle_key_quit` | asserted `z` was unmapped; `z` is now SHOW/HIDE processes. Re-pointed at `y`, which neither v4 nor v5 binds and which the remaining 2.X groups will not claim. |
| `test_tui_v5_paint_help_renders_title_and_keys` | asserts on overlay CONTENT at 80×24. The document grew to 33 rows (55 in the single-column fallback 80 columns forces), so the tail scrolled off. Given 40×100, and it now also asserts the `SHOW/HIDE` group is there. |
| `test_tui_v5_help_shows_doc_link` | same, 30 → 40 rows. |
| `test_tui_v5_help_shows_color_binding` | same, 30 → 40 rows. |

`test_tui_v5_help_shows_config_file` needed nothing: its line is at the top of
the document.

**46 tests added** (24 of them the parametrized key sweep).

---

## Verification performed

**Unit.** `3643 passed, 2 skipped` for the whole suite
(`tests/`, less `test_perf.py` — known flaky under load — and
`test_restful.py` / `test_xmlrpc.py` / `test_webui.py`, which need a live
server on 61234/61235 and fail identically on the untouched baseline).
Baseline before the change: `3597 passed`.

**Mutation.** The new tests were checked to actually bite, not merely pass:

| Mutation | Result |
|---|---|
| delete the `user_hidden` guard in `build_frame` | 6 failed |
| delete the `hide_{plugin_name}` guard in `build_frame` | 15 failed |
| key the compound flip on `names[-1]` instead of `names[0]` | `test_compound_key_never_lands_half_hidden` failed |

**Lint.** `ruff check glances/ tests/` clean; `ruff format` applied.

**Live.** Two runs against real plugins and a real store:

1. A pty + terminal-emulator run of `python -m glances.main_v5`, driving real
   keypresses: `n`, `d`, `f`, `2`, `z`, `h` each hide and restore their blocks.
2. A headless frame-level run (real `discover_plugins`, real `StatsStoreV5`):
   `5` empties the TOP slot, `2` empties the LEFT slot, `n`/`d`/`z`/`I` each
   remove exactly their plugin.

Run 2 exists because run 1 reported a false failure on `5`: the emulator
mis-replays ncurses' optimised diff output. `_paint` does call
`stdscr.erase()`; nothing is wrong with the repaint.

---

## Found while working, NOT fixed here

- **`setup_logging` (`main_v5.py:318-328`) logs to stderr, which in TUI mode is
  the terminal itself.** Every WARNING scrolls the curses display and corrupts
  it — visibly, with text bleeding across columns. v4 avoids this
  (`glances/logger.py:58-60`: a file handler, console level `CRITICAL`). This
  is pre-existing, unrelated to this chantier, and is what made the first two
  smoke runs unreadable until the child's stderr was redirected. Worth its own
  fix.
- At 80 columns the help overlay falls back to a single column because the
  longest description — `4`'s, "Full quicklook (hide cpu/mem/load)", 34 chars
  — does not leave room for two. Pre-existing; the 24 new keys make the
  resulting document much taller (55 rows). It scrolls, so it is legible, but
  shortening a few descriptions would let 80×24 hold two columns again.

---

## Divergences from v4, as the spec predicted

All three shipped as designed and are release-note material:

1. A config-disabled plugin is never instantiated in v5, so its hotkey is a
   visible no-op — `Q`/`irq` most of all, since irq is opt-in in v4 (spec §6.1).
2. `z` hides the three process blocks but does not stop the shared
   `glances_processes` engine, which v5 shares with the REST API and the
   WebUI (spec §6.3).
3. `2` is expanded to its slot members, so `2` then `n` then `2` leaves
   network visible and the rest of the sidebar hidden. v4 would restore the
   whole sidebar; v4's own `5` already behaves the way v5's `2` now does
   (spec §5.4, Q1).
