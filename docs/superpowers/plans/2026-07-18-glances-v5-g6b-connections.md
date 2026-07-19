# Glances v5 — connections plugin port (G6B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the v4 `connections` plugin (TCP connection-state counters + Netfilter conntrack) to the v5 asyncio architecture as a **scalar** plugin — the only scalar of the G6B group — disabled by default (CPU-heavy), with exactly one watched field (`nf_conntrack_percent`), per-cycle (non-latching) per-source feature flags, and the approved `terminated`/`initiated` bug fix.

**Architecture:** A scalar plugin (`model_v5.py::PluginModel`, `IS_COLLECTION=False`, no primary key) whose `_grab_stats()` self-gates on `[connections] disable` (default `True`, mirroring the established `npu`/`vms` pattern — v5's `discover_plugins` has no generic per-plugin disable plumbing) and, when enabled, wraps two independent v4 collection steps in `asyncio.to_thread`: `psutil.net_connections(kind="tcp")` (state counters) and two `/proc/sys/net/netfilter/nf_conntrack_*` reads (conntrack). Each source owns a **per-cycle local** enabled flag, created fresh at the top of every collection and discarded at the end of it — never an instance attribute. A source that fails is marked disabled **for that cycle's payload only** and is retried on the next cycle, exactly as v4 does (v4's `update()` opens with `stats = self.get_init_value()`, a fresh copy of `stats_init_value`, so both flags reset to `True` every cycle). This is what lets a transient failure self-heal — the concrete case being `nf_conntrack` loaded after Glances starts. The base class's standard numeric-threshold path watches only `nf_conntrack_percent` (ladder `nf_conntrack_percent_careful|warning|critical`, defaults 70/80/90 — already shipped in `conf/glances.conf`); the four connection-state counters carry no thresholds, matching v4. A dedicated `render_curses_v5.py` mirrors v4 `msg_curse()`: a `TCP CONNECTIONS` title, then `Listen`/`Initiated`/`Established`/`Terminated` rows (each skipped when its key is absent), then a `Tracked` row (`count/max`) — the only coloured row, driven by the `nf_conntrack_percent` level — rendered in the LEFT sidebar (`connections` is already in `LEFT_SLOT`, no orchestrator change needed).

**Tech Stack:** Python, psutil (`net_connections`), `/proc` reads, asyncio (`to_thread`), curses renderer v5, pytest

## Global Constraints

- **Mirror v4**: read `glances/plugins/connections/__init__.py` (`update()`, `update_for_net_connections_method`, `update_for_nf_conntrack_method`, `msg_curse`) before writing the model/renderer; divergent "clean generic" layouts are regressions.
- **LEFT sidebar, 34-char budget.** `connections` is already listed in `LEFT_SLOT` in `curses_renderer_v5.py` — no layout/orchestrator change is needed.
- **Empty / disabled must stay valid** — no crash. Disabled-by-default → empty payload (`{}`), not an exception. Absent conntrack files (or `nf_conntrack_max == 0`) → valid payload missing only the affected fields, never a crash.
- **`nf_conntrack_percent` is the only watched field** (ladder `nf_conntrack_percent_careful|warning|critical`, defaults 70/80/90). The four state counters (`LISTEN`, `ESTABLISHED`, `initiated`, `terminated`) carry **no** thresholds — v4 parity.
- **`EMITS_ALERTS = True`.**
- **Plugin titles/column headers are ALWAYS `ColorRole.HEADER`** — never colour a header from `_levels`. `title_role` does not exist in v5; do not reintroduce it.
- **Per-cycle feature flags, retry every cycle** (v4 parity): a failing source is reported disabled in that cycle's payload only, and is retried on the next cycle. The flags must be **local to the collection call**, never instance attributes that persist — a sticky flag would permanently kill the plugin on a transient failure.
- **Approved bug fix**: v4 `glances/plugins/connections/__init__.py:123` iterates `self.initiated_states` a second time instead of `self.terminated_states`, so v4's `terminated` is silently a copy of `initiated` and `terminated_states` (lines 79–86) is dead code. v5 iterates `terminated_states` for the `terminated` aggregate — the true fix, guarded by a dedicated test.
- **No dead code** — do not port v4's individual `SYN_SENT`/`SYN_RECV`/per-terminated-substate fields into `fields_description`; only the aggregated `initiated`/`terminated` counters are declared and stored (v4 kept the substates in `fields_description` but never rendered them — that's the dead code this port drops).
- **Do not touch `NEWS.rst`** during development (release-time only).
- **Do not modify `glances/plugins/plugin/base_v5.py`.**
- **No commits/push/PR** — stage only (`git add`), never `git commit`.
- Tests: `.venv/bin/python -m pytest`; lint `.venv/bin/python -m ruff check` + `.venv/bin/python -m ruff format`.

---

## Key implementation findings (decided, not open)

1. **Disabled-by-default has no v5 plumbing**, exactly as established for `npu`/`vms`. `[connections] disable=True` already ships in `conf/glances.conf` (documented there as "consumes lots of CPU"). The model self-gates in `_grab_stats`: `str(self.config.get("connections", "disable", "True")).strip().lower() in ("false", "0", "no")`. Disabled → `_grab_stats()` returns `{}` without touching `psutil` or `/proc` at all.
2. **Declared fields are narrower than v4's `fields_description`.** v4 declares `LISTEN`, `ESTABLISHED`, `SYN_SENT`, `SYN_RECV`, `initiated`, `terminated`, `nf_conntrack_count`, `nf_conntrack_max`, `nf_conntrack_percent` — but `msg_curse` only ever displays the two status counters plus the two *aggregates* (`initiated`, `terminated`); `SYN_SENT`/`SYN_RECV` are computed into `stats` but never read anywhere else. The design's field list (§5.1) omits them. v5 computes the `initiated`/`terminated` sums directly from the connection list (one pass with `sum(1 for c in connections if c.status in ...)`) without ever storing the individual sub-state counts — simpler, fewer fields, no dead data.
3. **Sidebar row width formula is v4-*style*, not v4's literal arithmetic.** v4's `msg_curse` computes each value cell's width as `max_width - len(label) + 2` against a *dynamically supplied* `max_width` from the painter. v5 fixes the LEFT-sidebar budget at a constant 34 chars (matching `wifi`/`diskio`), and the v5 painter (unlike v4's raw `curse_add_line` concatenation) automatically inserts one separator space between adjacent cells (see `curses_renderer_v5.py` `PluginBlock.width` docstring). Reproducing the *shape* v4 produces on screen (label at its natural width, value right-flushed to the edge of the row) inside that fixed budget gives `value_width = 34 - len(label) - 1` (the `-1` absorbs the painter's separator) so that `len(label) + 1(separator) + value_width == 34` exactly for every row — this is the "reproduce the widths" instruction applied to a fixed-budget renderer instead of v4's dynamic one.
4. **Defensive `nf_conntrack_max == 0` guard is a deliberate, minimal addition beyond literal v4 parity.** v4 divides `nf_conntrack_count * 100 / nf_conntrack_max` unconditionally once both proc reads succeed — a `nf_conntrack_max == 0` value (never seen in practice, but not impossible on an unusual kernel) would raise `ZeroDivisionError`, silently swallowed by the base's outer `try/except` in `update()`, losing the *entire* cycle's stats for a plugin that otherwise collected fine. The design's explicit invariant ("must yield a valid payload, not a crash") justifies a one-line guard (`if stats.get("nf_conntrack_max"): ...`) that only *skips assigning* `nf_conntrack_percent` for that pathological case — it does not change `nf_conntrack_enabled`, does not touch any other field, and is covered by `test_nf_conntrack_max_zero_no_crash_no_percent` in Task 1.

---

## File Structure

```
glances/plugins/connections/
  __init__.py            (v4 — untouched; kept for v4 runtime)
  model_v5.py            (NEW — PluginModel: self-gate, per-cycle source flags, _collect, fields)
  render_curses_v5.py    (NEW — TCP CONNECTIONS title + Listen/Initiated/Established/Terminated + Tracked)
tests/
  test_plugin_connections_v5.py               (NEW — model: identity/fields/gate/retry/bugfix/thresholds/export)
  test_plugin_connections_render_curses_v5.py (NEW — renderer: title/rows/skip/tracked/colour/widths)
docs/aoa/connections.rst  (update for v5)
conf/glances.conf         ([connections] disable=True + nf_conntrack_percent_* already shipped — verify only)
```

---

### Task 1 — Model: identity, fields, self-gate, per-cycle source flags, bug fix, thresholds

**Files:** `glances/plugins/connections/model_v5.py`, `tests/test_plugin_connections_v5.py`

**Interfaces:**
- Consumes: `StatsStoreV5`, `GlancesConfigV5`, `psutil.net_connections(kind="tcp")`, `psutil.CONN_*` status constants, `/proc/sys/net/netfilter/nf_conntrack_{count,max}`.
- Produces: `PluginModel` (`plugin_name="connections"`, `IS_COLLECTION=False`, `EMITS_ALERTS=True`); payload `{"net_connections_enabled":…, "nf_conntrack_enabled":…, "LISTEN":…, "ESTABLISHED":…, "initiated":…, "terminated":…, "nf_conntrack_count":…, "nf_conntrack_max":…, "nf_conntrack_percent":…, "time_since_update":…, "_levels":{...}}` (any field may be absent when its source is disabled or a value is unavailable). Class attributes consumed by tests: `PluginModel.status_list`, `PluginModel.initiated_states`, `PluginModel.terminated_states`, `PluginModel.conntrack_paths`.

fields_description (9 fields; only `nf_conntrack_percent` is watched). Note the two `*_enabled` descriptions state the per-cycle semantic explicitly — a reader of the REST schema must not read them as latched:

```python
fields_description: ClassVar[dict[str, dict[str, Any]]] = {
    "net_connections_enabled": {
        "description": (
            "Whether `psutil.net_connections()` succeeded during THIS cycle "
            "(re-evaluated every cycle — a failure is not latched)."
        ),
        "unit": "bool",
    },
    "nf_conntrack_enabled": {
        "description": (
            "Whether the Netfilter conntrack /proc counters were readable during "
            "THIS cycle (re-evaluated every cycle — a failure is not latched)."
        ),
        "unit": "bool",
    },
    "LISTEN": {
        "description": "Number of TCP connections in LISTEN state.",
        "unit": "number",
    },
    "ESTABLISHED": {
        "description": "Number of TCP connections in ESTABLISHED state.",
        "unit": "number",
    },
    "initiated": {
        "description": "Number of TCP connections initiated (SYN_SENT + SYN_RECV).",
        "unit": "number",
    },
    "terminated": {
        "description": (
            "Number of TCP connections terminated (FIN_WAIT1, FIN_WAIT2, TIME_WAIT, "
            "CLOSE, CLOSE_WAIT, LAST_ACK)."
        ),
        "unit": "number",
    },
    "nf_conntrack_count": {
        "description": "Number of tracked connections.",
        "unit": "number",
    },
    "nf_conntrack_max": {
        "description": "Maximum number of tracked connections.",
        "unit": "number",
    },
    "nf_conntrack_percent": {
        "description": "Percentage of tracked connections (nf_conntrack_count / nf_conntrack_max * 100).",
        "unit": "percent",
        "watched": True,
        "watch_direction": "high",
        "prominent": True,
        "default_thresholds": {"careful": 70.0, "warning": 80.0, "critical": 90.0},
    },
}
```

Model body (self-gate mirrors `npu`/`vms`; the two collectors mutate a local `stats` dict and **return a bool** saying whether they succeeded this cycle; `_collect` holds those booleans as locals and writes them into the payload — there is deliberately **no** `self._*_enabled` attribute, so nothing can latch across cycles):

```python
class PluginModel(GlancesPluginBase[dict]):
    plugin_name: ClassVar[str] = "connections"
    IS_COLLECTION: ClassVar[bool] = False
    EMITS_ALERTS: ClassVar[bool] = True

    status_list: ClassVar[list[str]] = [psutil.CONN_LISTEN, psutil.CONN_ESTABLISHED]
    initiated_states: ClassVar[list[str]] = [psutil.CONN_SYN_SENT, psutil.CONN_SYN_RECV]
    terminated_states: ClassVar[list[str]] = [
        psutil.CONN_FIN_WAIT1,
        psutil.CONN_FIN_WAIT2,
        psutil.CONN_TIME_WAIT,
        psutil.CONN_CLOSE,
        psutil.CONN_CLOSE_WAIT,
        psutil.CONN_LAST_ACK,
    ]
    conntrack_paths: ClassVar[dict[str, str]] = {
        "nf_conntrack_count": "/proc/sys/net/netfilter/nf_conntrack_count",
        "nf_conntrack_max": "/proc/sys/net/netfilter/nf_conntrack_max",
    }

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {...}  # as above

    def _is_enabled(self) -> bool:
        # Mirror v4 [connections] disable=True default (CPU-heavy).
        raw = self.config.get("connections", "disable", "True")
        return str(raw).strip().lower() in ("false", "0", "no")

    def _collect_net_connections(self, stats: dict[str, Any]) -> bool:
        """Fill the connection-state counters. Return False if unavailable.

        The return value is the caller's per-cycle flag — nothing is
        stored on `self`, so the next cycle tries again (v4 parity).
        """
        try:
            connections = psutil.net_connections(kind="tcp")
        except Exception as exc:  # noqa: BLE001 — retried next cycle, never latched
            logger.warning("connections: net_connections() failed this cycle (%s)", exc)
            return False

        for status in self.status_list:
            stats[status] = len([c for c in connections if c.status == status])
        stats["initiated"] = sum(1 for c in connections if c.status in self.initiated_states)
        # Approved bug fix vs v4 (__init__.py:123): iterate terminated_states,
        # not initiated_states, so `terminated` is a real, distinct count.
        stats["terminated"] = sum(1 for c in connections if c.status in self.terminated_states)
        return True

    def _collect_nf_conntrack(self, stats: dict[str, Any]) -> bool:
        """Fill the conntrack counters. Return False if unreadable.

        Same per-cycle contract as `_collect_net_connections`: a missing
        `/proc` entry today does not prevent a read tomorrow (the
        `nf_conntrack` module may be loaded after Glances starts).
        """
        for field_name, path in self.conntrack_paths.items():
            try:
                with open(path) as f:
                    stats[field_name] = float(f.readline().rstrip("\n"))
            except (OSError, FileNotFoundError) as exc:
                logger.warning("connections: conntrack read failed this cycle (%s)", exc)
                return False
        # Defensive: nf_conntrack_max == 0 would raise ZeroDivisionError and
        # lose the whole cycle (see Key Finding 4). Skip the percent field
        # only; the two raw counters and nf_conntrack_enabled are unaffected.
        if stats.get("nf_conntrack_max"):
            stats["nf_conntrack_percent"] = stats["nf_conntrack_count"] * 100 / stats["nf_conntrack_max"]
        return True

    def _collect(self) -> dict[str, Any]:
        # Both flags are LOCALS, recreated on every call. Do not hoist them
        # onto `self` — see the module docstring.
        stats: dict[str, Any] = {}
        net_connections_enabled = self._collect_net_connections(stats)
        nf_conntrack_enabled = self._collect_nf_conntrack(stats)
        stats["net_connections_enabled"] = net_connections_enabled
        stats["nf_conntrack_enabled"] = nf_conntrack_enabled
        return stats

    async def _grab_stats(self) -> dict:
        if not self._is_enabled():
            return {}
        return await asyncio.to_thread(self._collect)
```

Steps:
- [ ] Write `tests/test_plugin_connections_v5.py` with `store`/`config`/`_config_with` fixtures copied verbatim from `tests/test_plugin_mem_v5.py` (lines 49–68: `store()` → `StatsStoreV5()`; `config(tmp_path, monkeypatch)` → plain `GlancesConfigV5()` with `SYSTEM_CONFIG_PATH` redirected; `_config_with(tmp_path, monkeypatch, body)` writing an XDG `glances.conf`). Add a `FakeConn = namedtuple("FakeConn", ["status"])` helper and:
  - `test_plugin_identity` — `plugin_name == "connections"`, `IS_COLLECTION is False`, `EMITS_ALERTS is True`.
  - `test_fields_description_keys` — `set(PluginModel.fields_description.keys()) == {"net_connections_enabled", "nf_conntrack_enabled", "LISTEN", "ESTABLISHED", "initiated", "terminated", "nf_conntrack_count", "nf_conntrack_max", "nf_conntrack_percent"}`.
  - `test_only_nf_conntrack_percent_is_watched` — `[k for k, v in PluginModel.fields_description.items() if v.get("watched")] == ["nf_conntrack_percent"]`.
  - `test_nf_conntrack_percent_default_thresholds` — `PluginModel.fields_description["nf_conntrack_percent"]["default_thresholds"] == {"careful": 70.0, "warning": 80.0, "critical": 90.0}`.
- [ ] Run: `.venv/bin/python -m pytest tests/test_plugin_connections_v5.py::test_plugin_identity -v` → expect **FAIL** (module missing).
- [ ] Write COMPLETE `glances/plugins/connections/model_v5.py`: SPDX header (2026), module docstring describing the plugin (scalar, disabled by default, two independent sources) and carrying these two non-obvious points a reader would otherwise "fix": (a) *"The two `*_enabled` flags are deliberately per-cycle locals, not instance state: a source that fails is retried on the next cycle so a transient failure self-heals (e.g. `nf_conntrack` loaded after Glances starts). Do not hoist them onto `self`."* and (b) the approved `terminated`/`terminated_states` bug fix vs. v4 `__init__.py:123`. Then `from __future__ import annotations`, imports (`asyncio`, `logging`, `typing.Any`/`ClassVar`, `psutil`, `GlancesPluginBase`), `logger = logging.getLogger(__name__)`, the `fields_description`, and the class body above.
- [ ] Run: `.venv/bin/python -m pytest tests/test_plugin_connections_v5.py -v` → expect **PASS**.
- [ ] Add the guard test locking the approved bug fix:
  ```python
  def test_initiated_and_terminated_states_are_distinct():
      assert PluginModel.initiated_states != PluginModel.terminated_states
      assert set(PluginModel.initiated_states).isdisjoint(set(PluginModel.terminated_states))
  ```
- [ ] Add the functional guard proving `terminated` is computed from `terminated_states`:
  ```python
  async def test_terminated_computed_from_terminated_states_not_initiated(store, config, monkeypatch):
      plugin = PluginModel(store, config)
      monkeypatch.setattr(plugin, "_is_enabled", lambda: True)
      conns = [
          FakeConn(psutil.CONN_LISTEN),
          FakeConn(psutil.CONN_LISTEN),
          FakeConn(psutil.CONN_ESTABLISHED),
          FakeConn(psutil.CONN_SYN_SENT),
          FakeConn(psutil.CONN_TIME_WAIT),
          FakeConn(psutil.CONN_TIME_WAIT),
          FakeConn(psutil.CONN_CLOSE_WAIT),
      ]
      with patch("glances.plugins.connections.model_v5.psutil.net_connections", return_value=conns):
          stats = await plugin._grab_stats()
      assert stats["LISTEN"] == 2
      assert stats["ESTABLISHED"] == 1
      assert stats["initiated"] == 1  # one SYN_SENT
      assert stats["terminated"] == 3  # two TIME_WAIT + one CLOSE_WAIT
      assert stats["terminated"] != stats["initiated"]
  ```
- [ ] Run: `.venv/bin/python -m pytest tests/test_plugin_connections_v5.py -v` → expect **PASS**.
- [ ] Add the disabled-by-default tests:
  ```python
  async def test_disabled_by_default_returns_empty(store, config):
      plugin = PluginModel(store, config)
      with patch("glances.plugins.connections.model_v5.psutil.net_connections") as mock_nc:
          assert await plugin._grab_stats() == {}
      mock_nc.assert_not_called()

  async def test_enabled_via_config_collects(tmp_path, monkeypatch, store):
      config = _config_with(tmp_path, monkeypatch, "[connections]\ndisable=False\n")
      plugin = PluginModel(store, config)
      with patch("glances.plugins.connections.model_v5.psutil.net_connections", return_value=[]):
          stats = await plugin._grab_stats()
      assert stats["net_connections_enabled"] is True
      assert stats["LISTEN"] == 0
  ```
- [ ] Add the per-cycle retry guard tests (the core §5.1 requirement — these are precisely the assertions a future "don't retry a known-broken call" optimisation would silently break, so they must be explicit about the recovery):
  ```python
  async def test_net_connections_failure_is_retried_next_cycle(tmp_path, monkeypatch, store):
      config = _config_with(tmp_path, monkeypatch, "[connections]\ndisable=False\n")
      plugin = PluginModel(store, config)

      with patch(
          "glances.plugins.connections.model_v5.psutil.net_connections", side_effect=OSError("boom")
      ) as mock_nc:
          stats1 = await plugin._grab_stats()
      assert stats1["net_connections_enabled"] is False
      assert "LISTEN" not in stats1
      assert mock_nc.call_count == 1

      # Second cycle: the call must be retried and, now that it works, the
      # plugin must fully recover. A latched flag would fail all three
      # assertions below.
      with patch(
          "glances.plugins.connections.model_v5.psutil.net_connections",
          return_value=[FakeConn(psutil.CONN_LISTEN)],
      ) as mock_nc2:
          stats2 = await plugin._grab_stats()
      assert mock_nc2.call_count == 1
      assert stats2["net_connections_enabled"] is True
      assert stats2["LISTEN"] == 1

  async def test_nf_conntrack_failure_is_retried_next_cycle(tmp_path, monkeypatch, store):
      """The real-world case: the nf_conntrack module is loaded AFTER
      Glances starts. v4 recovers; v5 must too."""
      config = _config_with(tmp_path, monkeypatch, "[connections]\ndisable=False\n")
      plugin = PluginModel(store, config)
      count_file = tmp_path / "count"
      max_file = tmp_path / "max"
      plugin.conntrack_paths = {"nf_conntrack_count": str(count_file), "nf_conntrack_max": str(max_file)}

      with patch("glances.plugins.connections.model_v5.psutil.net_connections", return_value=[]):
          stats1 = await plugin._grab_stats()
      assert stats1["nf_conntrack_enabled"] is False
      assert "nf_conntrack_count" not in stats1

      # The conntrack counters appear (module loaded) — next cycle must
      # pick them up.
      count_file.write_text("10\n")
      max_file.write_text("100\n")
      with patch("glances.plugins.connections.model_v5.psutil.net_connections", return_value=[]):
          stats2 = await plugin._grab_stats()
      assert stats2["nf_conntrack_enabled"] is True
      assert stats2["nf_conntrack_count"] == 10.0
      assert stats2["nf_conntrack_percent"] == 10.0

  def test_enabled_flags_are_not_instance_state(store, config):
      """Structural guard: the flags must live only in the payload, never
      on the instance — an attribute is how a latch would creep back in."""
      plugin = PluginModel(store, config)
      assert not hasattr(plugin, "_net_connections_enabled")
      assert not hasattr(plugin, "_nf_conntrack_enabled")
  ```
- [ ] Run: `.venv/bin/python -m pytest tests/test_plugin_connections_v5.py -v` → expect **PASS**.
- [ ] Add the empty/absent-conntrack and zero-max guard tests (Key Finding 4; "must yield a valid payload, not a crash"):
  ```python
  async def test_absent_conntrack_files_yield_valid_payload(tmp_path, monkeypatch, store):
      config = _config_with(tmp_path, monkeypatch, "[connections]\ndisable=False\n")
      plugin = PluginModel(store, config)
      plugin.conntrack_paths = {
          "nf_conntrack_count": str(tmp_path / "nope_count"),
          "nf_conntrack_max": str(tmp_path / "nope_max"),
      }
      with patch("glances.plugins.connections.model_v5.psutil.net_connections", return_value=[]):
          stats = await plugin._grab_stats()  # must not raise
      assert stats["nf_conntrack_enabled"] is False
      assert "nf_conntrack_percent" not in stats

  async def test_nf_conntrack_max_zero_no_crash_no_percent(tmp_path, monkeypatch, store):
      config = _config_with(tmp_path, monkeypatch, "[connections]\ndisable=False\n")
      plugin = PluginModel(store, config)
      count_file = tmp_path / "count"
      max_file = tmp_path / "max"
      count_file.write_text("10\n")
      max_file.write_text("0\n")
      plugin.conntrack_paths = {"nf_conntrack_count": str(count_file), "nf_conntrack_max": str(max_file)}
      with patch("glances.plugins.connections.model_v5.psutil.net_connections", return_value=[]):
          stats = await plugin._grab_stats()  # must not raise ZeroDivisionError
      assert stats["nf_conntrack_enabled"] is True
      assert stats["nf_conntrack_max"] == 0.0
      assert "nf_conntrack_percent" not in stats
  ```
- [ ] Run: `.venv/bin/python -m pytest tests/test_plugin_connections_v5.py -v` → expect **PASS**.
- [ ] Add the threshold-ladder test (parametrized like `tests/test_plugin_mem_v5.py::test_default_thresholds_drive_percent_level`), driving `nf_conntrack_percent` via real files through the **full** `update()` pipeline:
  ```python
  @pytest.mark.parametrize(
      "count, max_, expected_level",
      [
          (10, 100, "ok"),
          (70, 100, "careful"),
          (80, 100, "warning"),
          (90, 100, "critical"),
          (99, 100, "critical"),
      ],
  )
  async def test_nf_conntrack_percent_default_thresholds_drive_level(
      tmp_path, monkeypatch, store, count, max_, expected_level
  ):
      config = _config_with(tmp_path, monkeypatch, "[connections]\ndisable=False\n")
      plugin = PluginModel(store, config)
      count_file = tmp_path / "count"
      max_file = tmp_path / "max"
      count_file.write_text(f"{count}\n")
      max_file.write_text(f"{max_}\n")
      plugin.conntrack_paths = {"nf_conntrack_count": str(count_file), "nf_conntrack_max": str(max_file)}
      with patch("glances.plugins.connections.model_v5.psutil.net_connections", return_value=[]):
          await plugin.update()
      entry = store.get("connections")["_levels"]["nf_conntrack_percent"]
      assert entry["level"] == expected_level
      assert entry["prominent"] is True

  async def test_only_nf_conntrack_percent_is_levelled(tmp_path, monkeypatch, store):
      config = _config_with(tmp_path, monkeypatch, "[connections]\ndisable=False\n")
      plugin = PluginModel(store, config)
      count_file = tmp_path / "count"
      max_file = tmp_path / "max"
      count_file.write_text("10\n")
      max_file.write_text("100\n")
      plugin.conntrack_paths = {"nf_conntrack_count": str(count_file), "nf_conntrack_max": str(max_file)}
      with patch(
          "glances.plugins.connections.model_v5.psutil.net_connections",
          return_value=[FakeConn(psutil.CONN_LISTEN)],
      ):
          await plugin.update()
      levels = store.get("connections")["_levels"]
      assert list(levels.keys()) == ["nf_conntrack_percent"]
  ```
- [ ] Run: `.venv/bin/python -m pytest tests/test_plugin_connections_v5.py -v` → expect **PASS**.
- [ ] Add the export test (mirrors `tests/test_plugin_mem_v5.py::test_get_export_strips_internals`):
  ```python
  async def test_get_export_strips_internals(tmp_path, monkeypatch, store):
      config = _config_with(tmp_path, monkeypatch, "[connections]\ndisable=False\n")
      plugin = PluginModel(store, config)
      with patch(
          "glances.plugins.connections.model_v5.psutil.net_connections",
          return_value=[FakeConn(psutil.CONN_LISTEN)],
      ):
          await plugin.update()
      exported = plugin.get_export()
      assert "_levels" not in exported
      assert "time_since_update" not in exported
      assert exported["LISTEN"] == 1
  ```
- [ ] Run: `.venv/bin/python -m pytest tests/test_plugin_connections_v5.py -v` → expect **PASS** (full file, no failures).
- [ ] `.venv/bin/python -m ruff check glances/plugins/connections/model_v5.py tests/test_plugin_connections_v5.py && .venv/bin/python -m ruff format glances/plugins/connections/model_v5.py tests/test_plugin_connections_v5.py`.
- [ ] `git add glances/plugins/connections/model_v5.py tests/test_plugin_connections_v5.py` — then STOP (no commit).

---

### Task 2 — Curses renderer (`TCP CONNECTIONS` title + Listen/Initiated/Established/Terminated + Tracked)

**Files:** `glances/plugins/connections/render_curses_v5.py`, `tests/test_plugin_connections_render_curses_v5.py`

**Interfaces:**
- Consumes: scalar payload `{"net_connections_enabled":…, "nf_conntrack_enabled":…, "LISTEN":…, "ESTABLISHED":…, "initiated":…, "terminated":…, "nf_conntrack_count":…, "nf_conntrack_max":…, "_levels": {"nf_conntrack_percent": {"level":…, "prominent":…}}}` (any key may be absent).
- Produces: `render(payload, fields_desc=None, view=None) -> list[Row]` — `[]` when nothing to show; otherwise a title `Row`, then one `Row` per present state counter in fixed order, then an optional `Tracked` `Row`.

Layout (mirror v4 `msg_curse`, `glances/plugins/connections/__init__.py` lines 190–229; see Key Finding 4 for the width-formula rationale):

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the connections plugin.

Mirrors v4 `connections.msg_curse()`
(`glances/plugins/connections/__init__.py::msg_curse`): a `TCP CONNECTIONS`
title, then one row per connection-state counter in a fixed order
(`Listen`, `Initiated`, `Established`, `Terminated` — each skipped when its
key is absent from the payload), then a `Tracked` row (`count/max`) when
Netfilter conntrack is enabled and both values are present — the ONLY
coloured row, driven by the `nf_conntrack_percent` level.

Reference layout (LEFT sidebar):

    TCP CONNECTIONS
    Listen                                   3
    Initiated                                0
    Established                             12
    Terminated                             204
    Tracked                            512/1024

Width formula (see plan Key Finding 3): v4 computes each value cell's
width as `max_width - len(label) + 2` against a dynamically-supplied
`max_width`. v5 fixes the LEFT-sidebar budget at 34 chars (matching
`wifi`/`diskio`) and the v5 painter auto-inserts one separator space
between adjacent cells (unlike v4's raw concatenation), so the value
width here is `34 - len(label) - 1` — this keeps
`len(label) + 1(separator) + value_width == 34` exactly, reproducing
v4's on-screen shape (label at its natural width, value flushed to the
row's right edge) inside the fixed v5 budget.
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row

_LEFT_SIDEBAR_MAX_WIDTH = 34

# Fixed v4 display order (glances/plugins/connections/__init__.py:205).
_ROW_ORDER: tuple[tuple[str, str], ...] = (
    ("LISTEN", "Listen"),
    ("initiated", "Initiated"),
    ("ESTABLISHED", "Established"),
    ("terminated", "Terminated"),
)


def _stat_row(label: str, value: Any, color: ColorRole = ColorRole.DEFAULT) -> Row:
    """One (label, right-flushed value) row filling the 34-char budget
    exactly: `len(label) + 1 (painter separator) + value_width == 34`.
    """
    value_width = _LEFT_SIDEBAR_MAX_WIDTH - len(label) - 1
    return Row(cells=[Cell(text=label), Cell(text=str(value).rjust(value_width), color=color)])


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]] | None = None, view: dict | None = None) -> list[Row]:
    if not isinstance(payload, dict) or not payload:
        return []

    net_enabled = bool(payload.get("net_connections_enabled"))
    nf_enabled = bool(payload.get("nf_conntrack_enabled"))
    if not net_enabled and not nf_enabled:
        return []

    rows: list[Row] = [Row(cells=[Cell(text="TCP CONNECTIONS", color=ColorRole.HEADER, bold=True)])]

    if net_enabled:
        for key, label in _ROW_ORDER:
            if key not in payload:
                continue
            rows.append(_stat_row(label, payload[key]))

    if nf_enabled and payload.get("nf_conntrack_count") is not None and payload.get("nf_conntrack_max") is not None:
        levels = payload.get("_levels")
        levels = levels if isinstance(levels, dict) else {}
        level = levels.get("nf_conntrack_percent", {}).get("level")
        role = _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)
        value_text = f"{payload['nf_conntrack_count']:.0f}/{payload['nf_conntrack_max']:.0f}"
        rows.append(_stat_row("Tracked", value_text, color=role))

    return rows
```

Steps:
- [ ] Write `tests/test_plugin_connections_render_curses_v5.py` with a `_payload(**over)` factory returning a valid base payload (`net_connections_enabled=True, nf_conntrack_enabled=True, LISTEN=3, ESTABLISHED=12, initiated=0, terminated=204, nf_conntrack_count=512, nf_conntrack_max=1024, _levels={"nf_conntrack_percent": {"level": "ok", "prominent": True}}`, overridable via `**over`) and a `_flat(rows)` helper (`" ".join(c.text for r in rows for c in r.cells)`). Add:
  - `test_empty_payload_returns_nothing` — `render({}) == []`.
  - `test_both_sources_disabled_returns_nothing` — `_payload(net_connections_enabled=False, nf_conntrack_enabled=False)` → `render(...) == []`.
  - `test_title_row_is_header_and_bold` — `rows = render(_payload())`; `rows[0].cells[0].text == "TCP CONNECTIONS"`, `.color == ColorRole.HEADER`, `.bold is True`.
  - `test_rows_in_fixed_order` — `rows = render(_payload())`; the labels of `rows[1:5]` (stripped) are `["Listen", "Initiated", "Established", "Terminated"]` in that exact order.
  - `test_missing_key_row_is_skipped` — `payload = _payload(); del payload["terminated"]`; `render(payload)` → no row's label is `"Terminated"`.
  - `test_net_connections_disabled_hides_state_rows` — `_payload(net_connections_enabled=False)` → none of `Listen/Initiated/Established/Terminated` appear in `_flat(render(...))`, but the title and Tracked row still do.
  - `test_tracked_row_shown_when_enabled_and_present` — `render(_payload())` → a row whose first cell stripped is `"Tracked"` and whose second cell text stripped is `"512/1024"`.
  - `test_tracked_row_hidden_when_conntrack_disabled` — `_payload(nf_conntrack_enabled=False)` → `"Tracked"` not in `_flat(...)`.
  - `test_tracked_row_hidden_when_count_missing` — `payload = _payload(); del payload["nf_conntrack_count"]` → `"Tracked"` not in `_flat(render(payload))`.
  - `test_tracked_row_hidden_when_max_missing` — same with `nf_conntrack_max` deleted.
  - `test_tracked_row_colour_reflects_level` — `_payload(_levels={"nf_conntrack_percent": {"level": "warning", "prominent": True}})`; the Tracked row's value cell `.color == ColorRole.WARNING`.
  - `test_state_rows_never_coloured` — `_payload(_levels={"nf_conntrack_percent": {"level": "critical", "prominent": True}})`; every row except the title and Tracked has both cells `.color == ColorRole.DEFAULT`.
  - `test_row_width_matches_34_char_budget` — for every data row (rows 1..N, excluding the title), `len(row.cells[0].text) + len(row.cells[1].text) == 33` (34 minus the painter's 1-space separator — see Key Finding 3).
- [ ] Run: `.venv/bin/python -m pytest tests/test_plugin_connections_render_curses_v5.py::test_title_row_is_header_and_bold -v` → expect **FAIL** (module missing).
- [ ] Write COMPLETE `glances/plugins/connections/render_curses_v5.py` exactly as shown above.
- [ ] Run: `.venv/bin/python -m pytest tests/test_plugin_connections_render_curses_v5.py -v` → expect **PASS**.
- [ ] `.venv/bin/python -m ruff check glances/plugins/connections/render_curses_v5.py tests/test_plugin_connections_render_curses_v5.py && .venv/bin/python -m ruff format glances/plugins/connections/render_curses_v5.py tests/test_plugin_connections_render_curses_v5.py`.
- [ ] `git add glances/plugins/connections/render_curses_v5.py tests/test_plugin_connections_render_curses_v5.py` — then STOP (no commit).

---

### Task 3 — Config verification + docs + full-suite green

**Files:** `conf/glances.conf` (verify only), `docs/aoa/connections.rst`

**Interfaces:** none new — verification and documentation.

Steps:
- [ ] Verify `conf/glances.conf` `[connections]` section (already present, lines 376–383) ships `disable=True` and `nf_conntrack_percent_careful=70` / `nf_conntrack_percent_warning=80` / `nf_conntrack_percent_critical=90` — confirmed present, matching the model's `default_thresholds`. Do NOT re-add or change these; only touch the file if a diff shows a key genuinely missing.
- [ ] Read `docs/aoa/connections.rst`. Append a v5 note (mirroring the `.. note::` block G6A added to `docs/aoa/vms.rst`) directly after the existing `.. code-block:: ini` example, stating: the plugin is **disabled by default** (CPU-heavy); only `nf_conntrack_percent` carries thresholds/alerts (`EMITS_ALERTS=True`) — the `Listen`/`Initiated`/`Established`/`Terminated` counters are informational only, never alerted on; `Initiated` and `Terminated` are independent aggregates (SYN_SENT+SYN_RECV vs. the six terminating states) — do not describe them as related beyond both being TCP-state aggregates; and Netfilter conntrack (and its `Tracked` row) is entirely optional — absent on hosts without `nf_conntrack`, in which case only the four state rows render. Example block to insert:
  ```rst
  .. note::

      The ``connections`` plugin is **disabled by default** (``disable=True``)
      because scanning the full connection table is CPU-heavy. Only
      ``nf_conntrack_percent`` carries thresholds/alerts (default
      careful/warning/critical: 70/80/90%); the ``Listen``, ``Initiated``,
      ``Established`` and ``Terminated`` counters are informational only and
      are never alerted on. ``Initiated`` (SYN_SENT + SYN_RECV) and
      ``Terminated`` (FIN_WAIT1, FIN_WAIT2, TIME_WAIT, CLOSE, CLOSE_WAIT,
      LAST_ACK) are independent aggregates. Netfilter conntrack tracking
      (the ``Tracked`` row) is optional and only shown when the
      ``/proc/sys/net/netfilter/nf_conntrack_*`` counters are readable on
      the host.
  ```
- [ ] Run the v5 connections test set: `.venv/bin/python -m pytest tests/test_plugin_connections_v5.py tests/test_plugin_connections_render_curses_v5.py -v` → expect **PASS**.
- [ ] Run the full suite to confirm no regression: `.venv/bin/python -m pytest -q` → expect **PASS** (green, count increased only by the new connections tests; a single pre-existing unrelated failure `tests/test_actions_sanitize.py::TestSecurePopen::test_pipe` may remain — it references none of the connections modules).
- [ ] `.venv/bin/python -m ruff check glances/plugins/connections/ tests/test_plugin_connections_v5.py tests/test_plugin_connections_render_curses_v5.py && .venv/bin/python -m ruff format --check glances/plugins/connections/ tests/test_plugin_connections_v5.py tests/test_plugin_connections_render_curses_v5.py`.
- [ ] `git add glances/plugins/connections/ tests/test_plugin_connections_v5.py tests/test_plugin_connections_render_curses_v5.py docs/aoa/connections.rst` (include `conf/glances.conf` only if it was edited) — then STOP (no commit).

---

## Final self-check (design §5.1 / §6 coverage map)

| Spec requirement | Task |
| --- | --- |
| `PluginModel` scalar, no primary key, `EMITS_ALERTS=True` | Task 1 |
| Fields: enabled flags, LISTEN/ESTABLISHED, initiated, terminated, nf_conntrack_count/max/percent | Task 1 |
| Only `nf_conntrack_percent` watched (ladder 70/80/90, config keys `nf_conntrack_percent_{careful,warning,critical}`) | Task 1 |
| State counters carry no thresholds | Task 1 (`test_only_nf_conntrack_percent_is_levelled`) |
| `_grab_stats()` wraps `psutil.net_connections()` + two `/proc` reads in `asyncio.to_thread` | Task 1 |
| Feature flags retry every cycle (v4 parity), never latched | Task 1 (`test_net_connections_failure_is_retried_next_cycle`, `test_nf_conntrack_failure_is_retried_next_cycle`, `test_enabled_flags_are_not_instance_state`) |
| Approved bug fix: `terminated` computed from `terminated_states`, distinct from `initiated_states` | Task 1 (`test_initiated_and_terminated_states_are_distinct`, `test_terminated_computed_from_terminated_states_not_initiated`) |
| Render: title `TCP CONNECTIONS`; Listen/Initiated/Established/Terminated fixed order, skip absent | Task 2 |
| Render: Tracked row (`count/max`) only coloured row, gated on conntrack enabled + both present | Task 2 |
| LEFT sidebar, 34-char budget, no orchestrator change (`connections` already in `LEFT_SLOT`) | Task 2 (Key Finding 3) |
| Empty/absent conntrack → valid payload, not a crash | Task 1 (`test_absent_conntrack_files_yield_valid_payload`, `test_nf_conntrack_max_zero_no_crash_no_percent`) |
| Docs `docs/aoa/connections.rst` updated for v5 | Task 3 |
| Config `[connections]` (disable/thresholds) already shipped — verify | Task 3 |
| Tests: identity/fields, gate, retry guards, bug-fix guard, thresholds, export, renderer rows/skip/colour/width | Tasks 1–2 |
