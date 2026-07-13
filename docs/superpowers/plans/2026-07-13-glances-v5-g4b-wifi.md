# Glances v5 — wifi plugin port (G4B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the v4 `wifi` plugin to the v5 asyncio architecture — a per-interface collection reading `/proc/net/wireless`, with INVERTED (`<=`) signal-quality alert levels mirroring v4 `get_alert`.

**Architecture:** A collection plugin (`model_v5.py::PluginModel`, `IS_COLLECTION=True`, primary key `ssid`) whose `_grab_stats()` reads `/proc/net/wireless` in a worker thread (existence-guarded) and yields one dict per wireless interface. Because signal is negative dBm (lower = worse) and the v5 config reader rejects negative thresholds, alert levels are computed in an explicit `_derived_parameters()` override (like sensors) that reads `[wifi]` careful/warning/critical directly and applies the engine's `low` direction. A dedicated `render_curses_v5.py` mirrors v4 `msg_curse()` (a `WIFI`/`dBm` header then one coloured row per interface, sorted by ssid).

**Tech Stack:** Python, /proc/net/wireless, asyncio (to_thread), curses renderer v5, pytest

## Global Constraints

- **Mirror v4**: read the v4 `msg_curse()` + grabber before writing the renderer/model; divergent "clean generic" layouts are regressions.
- **LEFT sidebar width budget = 34 chars, separators included**: `col1 + 1 + col2 + 1 + … ≤ 34`; overshooting clips the rightmost column.
- **Reuse v4 grabber** via `asyncio.to_thread`, guarded on `/proc/net/wireless` existence (wifi has no external grabber class — the small `/proc` parse is ported into the model; no rewrite of its logic).
- **Empty registry / empty stats must stay valid** (no wireless interface → empty collection, not a crash).
- **Alerts fire on `warning`+ only**; `careful` is colour-only (blue in TUI, collapsed to ok by the alert engine).
- **`prominent: False`** on `quality_level` → coloured text, no background highlight (sensors parity).
- **No dead code** — do NOT port the v4 `self._thread` / `exit()` scaffolding (never used in v4).
- **Do not touch `NEWS.rst`** during development (release-time only).
- **No commits/push/PR** — stage only (`git add`), never `git commit`.
- Tests: `.venv/bin/python -m pytest`; lint `ruff check` + `ruff format`.

---

## Key implementation finding (levels path — decided, not open)

The v5 threshold engine **natively supports** `watch_direction: "low"` with a `<=`
comparison (`glances/plugins/plugin/thresholds_v5.py::compute_level`, lines 76–79:
`if direction == "low" and value <= threshold: return level`).

**However, the native base-class path cannot be used for wifi**, because the config
reader `read_thresholds()` treats every **negative** config value as "absent"
(`thresholds_v5.py` line 146: `if fvalue >= 0:` — the feature that lets users disable
a level with `careful=-1`). Wifi's thresholds are inherently negative dBm
(`careful=-65`, `warning=-75`, `critical=-85`), so the native reader would silently
discard all three and, with no `default_thresholds` to fall back on, compute **no
level at all** — a regression versus v4 where these thresholds drive the colour.

**Chosen path (mirror sensors):** an explicit `_derived_parameters()` override that
reads `[wifi]` careful/warning/critical directly (negatives preserved) and delegates
the comparison to the engine via `compute_level(quality_level, thresholds, "low")` —
reusing the tested `low`/`<=` logic while bypassing the negative-rejecting reader.
This is verified by **Task 2**, which asserts the four inverted bands. The native
`watch_direction: "low"` mechanism is documented here as intentionally NOT wired for
the config-read reason above.

---

## File Structure

```
glances/plugins/wifi/
  __init__.py            (v4 — untouched; kept for v4 runtime)
  model_v5.py            (NEW — PluginModel, grabber, inverted levels)
  render_curses_v5.py    (NEW — WIFI/dBm header + per-interface rows)
tests/
  test_plugin_wifi_v5.py               (NEW — model: identity/fields/grab/levels/EMITS_ALERTS)
  test_plugin_wifi_render_curses_v5.py (NEW — renderer: header/rows/skip/width-budget)
docs/aoa/wifi.rst        (verify/light-touch; already in docs/aoa/index.rst — do NOT re-add)
conf/glances.conf        ([wifi] careful/warning/critical already shipped — verify only)
```

---

### Task 1 — Model: identity, fields_description, `/proc/net/wireless` grabber

**Files:** `glances/plugins/wifi/model_v5.py`, `tests/test_plugin_wifi_v5.py`

**Interfaces:**
- Consumes: `StatsStoreV5`, `GlancesConfigV5`, `/proc/net/wireless`.
- Produces: `PluginModel` (`plugin_name="wifi"`, `IS_COLLECTION=True`, primary key `ssid`); `_grab_stats()` returning `list[dict]` with fields `ssid`, `quality_link`, `quality_level`.

Grabber notes (mirror v4 `_get_wireless_stats`, drop the dead thread scaffolding):
- Module constant `WIRELESS_FILE = "/proc/net/wireless"`.
- `_collect()` (sync, runs in a worker thread): if the file does not exist → return `[]`. Otherwise `open()` the file **inside** try/except (Snap confinement rule), skip the **two** header lines, then per remaining line: `parts = line.split()`; append `{"ssid": parts[0][:-1], "quality_link": float(parts[2]), "quality_level": float(parts[3])}`. Guard `PermissionError`/`FileNotFoundError`/`IndexError`/`ValueError` → log debug, return what was parsed so far (empty on open failure).
- `_grab_stats()` = `await asyncio.to_thread(self._collect)`.

fields_description (from v4):
```python
fields_description: ClassVar[dict[str, dict[str, Any]]] = {
    "ssid": {
        "description": "Wi-Fi network name (interface name).",
        "unit": "string",
        "primary_key": True,
    },
    "quality_link": {
        "description": "Signal quality level.",
        "unit": "dBm",
        "watched": False,
    },
    "quality_level": {
        "description": "Signal strength level.",
        "unit": "dBm",
        "watched": True,
        "watch_direction": "low",
        "prominent": False,
    },
}
```

Steps:
- [ ] Write `tests/test_plugin_wifi_v5.py` with `store` + `config` fixtures (copy the sensors test fixtures: `store()` → `StatsStoreV5()`; `config(tmp_path, monkeypatch)` → monkeypatch `GlancesConfigV5.SYSTEM_CONFIG_PATH` then `GlancesConfigV5()`). Add:
  - `test_plugin_identity` — `plugin_name == "wifi"`, `IS_COLLECTION is True`, `_primary_key == "ssid"`.
  - `test_fields_description_flags` — `fd["ssid"]["primary_key"] is True`; `fd["quality_level"]["watched"] is True`; `fd["quality_level"]["watch_direction"] == "low"`; `fd["quality_level"].get("prominent") is False`; `fd["quality_link"].get("watched", False) is False`.
- [ ] Run: `.venv/bin/python -m pytest tests/test_plugin_wifi_v5.py::test_plugin_identity -v` → expect **FAIL** (module missing).
- [ ] Write COMPLETE `glances/plugins/wifi/model_v5.py`: SPDX header, `from __future__ import annotations`, imports (`asyncio`, `logging`, `os`, `typing`), `from glances.plugins.plugin.base_v5 import GlancesPluginBase`. Constant `WIRELESS_FILE`. Class `PluginModel(GlancesPluginBase[list])` with the `fields_description` above, `_collect()`, `_grab_stats()`. Use `os.path.exists(WIRELESS_FILE)` at grab time (not import time — hardware can appear/disappear; empty-registry rule).
- [ ] Add `test_grab_parses_and_skips_two_header_lines` — monkeypatch `_collect` NOT; instead write a temp file and monkeypatch `WIRELESS_FILE`/patch `os.path.exists` + `open`. Simpler: monkeypatch `model_v5.WIRELESS_FILE` to a `tmp_path` file containing the two v4 header lines + two interface lines (`wlp2s0: 0000   51.  -59.  -256 …` and `wlan1: 0000   60.  -50.  -256 …`), await `_grab_stats()`, assert two rows, `ssid` == `"wlp2s0"`/`"wlan1"` (trailing `:` stripped), `quality_link == 51.0`, `quality_level == -59.0`.
- [ ] Add `test_grab_missing_file_returns_empty` — point `WIRELESS_FILE` at a non-existent path, assert `await _grab_stats() == []`.
- [ ] Run: `.venv/bin/python -m pytest tests/test_plugin_wifi_v5.py -v` → expect **PASS**.
- [ ] `ruff check glances/plugins/wifi/model_v5.py tests/test_plugin_wifi_v5.py && ruff format glances/plugins/wifi/model_v5.py tests/test_plugin_wifi_v5.py`.
- [ ] `git add glances/plugins/wifi/model_v5.py tests/test_plugin_wifi_v5.py` — then STOP (no commit).

---

### Task 2 — Inverted alert levels (`_derived_parameters` override) + EMITS_ALERTS

**Files:** `glances/plugins/wifi/model_v5.py`, `tests/test_plugin_wifi_v5.py`

**Interfaces:**
- Consumes: `[wifi]` config `careful`/`warning`/`critical` (defaults `-65`/`-75`/`-85`), `self._stats` (list of interface dicts).
- Produces: `self._levels = {ssid: {"quality_level": {"level", "prominent"}}}`; class attr `EMITS_ALERTS = True`.

Level rules (v4 `get_alert` parity — INVERTED, `<=`):
- Read `careful`/`warning`/`critical` from `[wifi]` as float, defaults `-65`/`-75`/`-85`. Wrap the reads in try/except `TypeError`/`KeyError`/`ValueError`.
- Per interface: skip if `quality_level` is not a number → **no level entry** (renderer stays DEFAULT). Else `level = compute_level(quality_level, {"careful": c, "warning": w, "critical": cr}, "low")` — which returns `critical` when `value <= critical`, `warning` when `value <= warning`, `careful` when `value <= careful`, else `ok`.
- `prominent` read from the `quality_level` field schema (`bool(self.fields_description["quality_level"].get("prominent", False))`) — single source of truth, mirrors sensors.
- On any threshold-read exception → skip that interface (no level).

Reference shape: `glances/plugins/sensors/model_v5.py::_derived_parameters` (lines 269–290) and `_resolve_level`; reuse `compute_level` from `glances.plugins.plugin.thresholds_v5` for the actual comparison instead of inlining the `<=` ladder.

Steps:
- [ ] Add a `_cfg_with(tmp_path, monkeypatch, body)` helper to `tests/test_plugin_wifi_v5.py` (copy from the sensors test: writes an XDG-discovered `glances.conf`), and a `_levels(p, rows)` driver (`p._stats = rows; p._derived_parameters(); return p._levels`). Add level tests using the **default** thresholds (plain `config` fixture, `[wifi]` absent → defaults −65/−75/−85):
  - `test_level_critical` — `quality_level=-90` → `lv["wlp2s0"]["quality_level"]["level"] == "critical"` (−90 <= −85).
  - `test_level_warning` — `-80` → `"warning"` (−80 <= −75, not <= −85).
  - `test_level_careful` — `-70` → `"careful"` (−70 <= −65, not <= −75).
  - `test_level_ok` — `-50` → `"ok"` (−50 > −65).
  - `test_level_prominent_false` — assert `lv[...]["quality_level"]["prominent"] is False` (mirrors schema).
- [ ] Run: `.venv/bin/python -m pytest tests/test_plugin_wifi_v5.py::test_level_critical -v` → expect **FAIL** (`_levels` empty; base `_derived_parameters` can't read negative thresholds).
- [ ] Add to `model_v5.py`: `EMITS_ALERTS: ClassVar[bool] = True`; import `compute_level`; implement `_derived_parameters()` (override, does NOT call super) building `self._levels` per the rules above; a `_read_thresholds()` helper returning `(careful, warning, critical)` from config with the −65/−75/−85 defaults.
- [ ] Run: `.venv/bin/python -m pytest tests/test_plugin_wifi_v5.py -v` → expect **PASS**.
- [ ] Add `test_level_from_config_overrides_defaults` — `_cfg_with(..., "[wifi]\ncareful=-60\nwarning=-70\ncritical=-80\n")`; assert `-75` → `"warning"` (−75 <= −70) and `-55` → `"ok"`. Verifies the **negative** config values are honoured (the whole reason for the override).
- [ ] Add `test_level_none_skipped` — `quality_level=None` → ssid absent from `_levels`.
- [ ] Add `test_careful_is_colour_only` — assert `PluginModel.EMITS_ALERTS is True` AND that a `careful` level is produced (renderer colours it) but note in a comment that the alert engine collapses careful→ok (warning+ rule); the level value here is exactly `"careful"`.
- [ ] Add `test_emits_alerts_true` — `assert PluginModel.EMITS_ALERTS is True`.
- [ ] Run: `.venv/bin/python -m pytest tests/test_plugin_wifi_v5.py -v` → expect **PASS**.
- [ ] `ruff check` + `ruff format` the two files.
- [ ] `git add glances/plugins/wifi/model_v5.py tests/test_plugin_wifi_v5.py` — then STOP (no commit).

---

### Task 3 — Curses renderer (`WIFI` + `dBm`, per-interface rows, width budget)

**Files:** `glances/plugins/wifi/render_curses_v5.py`, `tests/test_plugin_wifi_render_curses_v5.py`

**Interfaces:**
- Consumes: collection payload `{"data": [...], "_levels": {ssid: {"quality_level": {...}}}}`.
- Produces: `render(payload, fields_desc=None, view=None) -> list[Row]` — header row (`WIFI` + `dBm`) then one row per interface.

Layout (mirror v4 `msg_curse`, lines 187–212; mirror sensors `render_curses_v5.py`):
- Constants: `_NAME_MAX_WIDTH = 26`, `_VALUE_COL_WIDTH = 7`, `_LEFT_SIDEBAR_MAX_WIDTH = 34` (`26 + 1 + 7 == 34`).
- Header `Row`: `Cell(text="WIFI".ljust(_NAME_MAX_WIDTH), color=title_role(payload), bold=True)` + `Cell(text="dBm".rjust(_VALUE_COL_WIDTH), color=title_role(payload), bold=True)`.
- Guard: `payload` not a dict, or `data` not a list → return header only.
- Iterate `sorted(items, key=lambda r: str(r.get("ssid", "")))`. **Skip** rows where `ssid in ("", None)` or `quality_level is None` (issues #1151/#1973).
- Per row: `Cell(text=_format_name(ssid))` (ljust/truncate to `_NAME_MAX_WIDTH`) + `Cell(text=f"{quality_level:.0f}".rjust(_VALUE_COL_WIDTH), color=role, prominent=prominent)` where `(role, prominent)` come from a `_level_role(levels, ssid)` helper (copy sensors' `_level_role`, reading `levels[ssid]["quality_level"]`).
- Use `_LEVEL_TO_ROLE`, `Cell`, `ColorRole`, `Row`, `title_role` from `glances.outputs.curses_renderer_v5`.

Steps:
- [ ] Write `tests/test_plugin_wifi_render_curses_v5.py` with `_payload(rows, levels=None)`, `_flat(rows)`, `_wifi(ssid, link, level)` helpers (mirror the sensors render test). Add:
  - `test_empty_returns_header_only` — `render(_payload([]))` → `"WIFI"` in flat, `len(rows) == 1`.
  - `test_header_and_one_row` — one interface → `"WIFI"`, `"dBm"`, ssid, and the signal number present.
  - `test_rows_sorted_by_ssid` — pass `wlan1` then `wlan0`; assert `wlan0` row precedes `wlan1`.
  - `test_skip_empty_ssid` — `ssid=""` row omitted.
  - `test_skip_none_quality_level` — `quality_level=None` row omitted.
  - `test_level_colour_applied` — `_levels={"wlan0": {"quality_level": {"level": "critical", "prominent": False}}}`; value cell `.color.value == "critical"` and `.prominent is False`.
  - `test_row_fits_left_sidebar_budget` — `assert _NAME_MAX_WIDTH + 1 + _VALUE_COL_WIDTH <= _LEFT_SIDEBAR_MAX_WIDTH`; and for a concrete rendered row `len(label_cell.text) + 1 + len(value_cell.text) <= _LEFT_SIDEBAR_MAX_WIDTH`.
- [ ] Run: `.venv/bin/python -m pytest tests/test_plugin_wifi_render_curses_v5.py::test_header_and_one_row -v` → expect **FAIL** (module missing).
- [ ] Write COMPLETE `glances/plugins/wifi/render_curses_v5.py` per the layout above (SPDX header, module docstring documenting the 26+1+7=34 budget, `_format_name`, `_level_role`, `render`).
- [ ] Run: `.venv/bin/python -m pytest tests/test_plugin_wifi_render_curses_v5.py -v` → expect **PASS**.
- [ ] `ruff check` + `ruff format` the two files.
- [ ] `git add glances/plugins/wifi/render_curses_v5.py tests/test_plugin_wifi_render_curses_v5.py` — then STOP (no commit).

---

### Task 4 — Config verification + docs + full-suite green

**Files:** `conf/glances.conf` (verify only), `docs/aoa/wifi.rst`

**Interfaces:** none new — verification and documentation.

Steps:
- [ ] Verify `conf/glances.conf` `[wifi]` already ships `careful=-65` / `warning=-75` / `critical=-85` (confirmed present at lines 373–379 — do NOT re-add). Only add if a diff shows them missing.
- [ ] Read `docs/aoa/wifi.rst`. It already documents the negative-dBm thresholds and matches v5 behaviour. Confirm `wifi` is already listed in `docs/aoa/index.rst` (do NOT re-add). Make a light-touch edit ONLY if something is now inaccurate for v5 (e.g. the `disable=False` line if the v5 disable mechanism differs); otherwise leave unchanged and note "no doc change warranted — v5 mirrors v4".
- [ ] Run the whole v5 wifi test set: `.venv/bin/python -m pytest tests/test_plugin_wifi_v5.py tests/test_plugin_wifi_render_curses_v5.py -v` → expect **PASS**.
- [ ] Run the full suite to confirm no regression: `.venv/bin/python -m pytest -q` → expect **PASS** (green, count unchanged aside from the new wifi tests).
- [ ] `ruff check glances/plugins/wifi/ tests/test_plugin_wifi_v5.py tests/test_plugin_wifi_render_curses_v5.py && ruff format --check glances/plugins/wifi/ tests/test_plugin_wifi_v5.py tests/test_plugin_wifi_render_curses_v5.py`.
- [ ] `git add glances/plugins/wifi/ tests/test_plugin_wifi_v5.py tests/test_plugin_wifi_render_curses_v5.py docs/aoa/wifi.rst` (include `conf/glances.conf` only if it was edited) — then STOP (no commit).

---

## Final self-check (spec §4.3 coverage map)

| §4.3 requirement | Task |
| --- | --- |
| Grabber `/proc/net/wireless`, existence-guarded, `to_thread`, skip 2 header lines | Task 1 |
| Drop dead `self._thread`/`exit()` scaffolding | Task 1 (never ported) |
| Shape: list of dicts; `ssid` (pk, `:` stripped), `quality_link`, `quality_level` | Task 1 |
| fields_description (ssid pk; quality_link watched False dBm; quality_level watched True / low / dBm / prominent False) | Task 1 |
| Inverted `<=` levels from `[wifi]` (defaults −65/−75/−85), four bands, TypeError/KeyError→no level | Task 2 |
| `_levels = {ssid: {"quality_level": {level, prominent:False}}}` | Task 2 |
| Native `watch_direction:"low"` decision (NOT usable — negative-config reject; override chosen) | Key finding + Task 2 |
| `EMITS_ALERTS = True`; careful colour-only (collapses to ok in alert engine) | Task 2 |
| Renderer `WIFI`+`dBm`, sorted by ssid, skip empty/None (#1151/#1973), budget ≤ 34 | Task 3 |
| Config `[wifi]` thresholds already shipped — verify | Task 4 |
| Docs `wifi.rst` (already in index) — docs task | Task 4 |
| Tests: identity/fields, grab parse, inverted bands, skip empty/None, EMITS_ALERTS, careful colour-only, width budget | Tasks 1–3 |
