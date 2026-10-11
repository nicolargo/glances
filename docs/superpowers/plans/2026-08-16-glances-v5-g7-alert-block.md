# G7 — Alert block rendering (Glances v5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the v5 alert block from a variable-width sentence log into an aligned, incident-oriented column record that degrades gracefully on narrow terminals.

**Architecture:** The alert engine stays a transition state machine. Incidents are *derived at render time* by walking the bounded history and reconciling it against a new read-only accessor over the engine's unbounded per-tuple state. The renderer then emits a fixed column grid whose only elastic column is the alert target.

**Tech Stack:** Python 3.9+, `curses` via the v5 `Row`/`Cell`/`ColorRole` primitives, pytest.

**Spec:** `docs/superpowers/specs/2026-08-01-glances-v5-g7-alert-design.md` (approved 2026-08-16, option **C**). Section references below (§n) point at it.

## Global Constraints

- **Never commit, never push, never open a PR.** Every task ends with `git add` only. The maintainer reviews the staged diff and commits personally. Never add a `Co-Authored-By` trailer.
- **Never touch `NEWS.rst`.** Release-note material is recorded in spec §14; the maintainer writes the changelog at release time.
- `GET /api/5/alert` must stay **byte-identical**. No task adds, removes or renames a field of the event dict built by `GlancesAlerts._build_event`.
- No new configuration key. No new key binding. No new dependency.
- No new `ColorRole`. The available roles are `DEFAULT`, `OK`, `CAREFUL`, `WARNING`, `CRITICAL`, `HEADER` (`glances/outputs/curses_renderer_v5.py:110-116`).
- `careful` never enters the alert history — that is `_alert_level`'s job (`glances/alerts_v5.py:72`) and no task changes it.
- Existing behaviour that must survive every task: empty history collapses to a **single** header-styled line, `ALERT (initializing)` during warmup and `ALERT (no alert detected)` once settled.
- Run the whole suite with `python -m pytest tests/ -q` before staging any task. At the end of the last task run `make pre-commit` (≈23 hooks; `make lint && make format` is not enough), and restage afterwards because gitleaks scans the index.
- The v5 server/TUI entry point is `python -m glances.main_v5`, **not** `python -m glances`.

---

## File Structure

| File | Responsibility | Tasks |
|---|---|---|
| `glances/alerts_v5.py` | + `get_ongoing()`, read-only view over `_state` | 1 |
| `glances/outputs/curses_renderer_v5.py` | incident derivation, formatters, the column grid, `build_frame` wiring | 2, 3, 5, 6 |
| `glances/outputs/glances_curses_v5.py` | publish `right_width` and `unicode` into `view`, pass `alerts_ongoing` | 4, 5, 6 |
| `glances/plugins/processlist/render_curses_v5.py` | read the renamed width key | 4 |
| `glances/main_v5.py` | forward `--disable-unicode` to the TUI | 5 |
| `conf/glances.conf` | document the `[alerts]` section | 7 |
| `tests/test_alerts_v5.py` | engine accessor tests | 1 |
| `tests/test_curses_renderer_v5.py` | derivation, formatters, grid golden tests | 2, 3, 6 |
| `tests/test_curses_v5.py` | TUI wiring tests | 4, 5, 6 |
| `tests/test_config_v5.py` | `[alerts]` defaults still parse | 7 |

Task order is a dependency order. Tasks 1–4 each produce something consumed by task 6; nothing is left unused at the end of the plan.

---

### Task 1: Read-only ongoing accessor on the alert engine

Spec §5.6. The history is a `deque(maxlen=200)`; `_state` is unbounded and holds the committed level per `(plugin, key, field)`. An alert still active whose transitions have aged out of the ring is invisible today. This accessor is the authority the renderer will use for "what is active right now".

**Files:**
- Modify: `glances/alerts_v5.py` — add a method next to `get_history()` (`:144`)
- Test: `tests/test_alerts_v5.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `GlancesAlerts.get_ongoing() -> dict[tuple[str, str | None, str], str]`. Keys are exactly the `_state` keys, `(plugin_name, key, field_name)`, built at `alerts_v5.py:221` — the same triple the history event exposes as its `plugin` / `key` / `field` values, so a renderer can join the two without coercion. Values are the committed level, always one of `"warning"` / `"critical"`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_alerts_v5.py`. Reuse whatever engine fixture the file already uses for ingestion tests — read the top of the file first and follow that pattern rather than inventing a new one. The tests below assume a helper that drives `ingest_plugin` to a committed level; if the file names it differently, use its name.

```python
def test_get_ongoing_is_empty_before_any_alert(alerts_engine):
    """No committed non-ok level → no ongoing entry."""
    assert alerts_engine.get_ongoing() == {}


def test_get_ongoing_reports_committed_non_ok_levels(alerts_engine):
    """A committed warning shows up keyed by (plugin, key, field)."""
    alerts_engine._state[("mem", None, "percent")] = _AlertState(
        committed_level="warning", has_committed=True
    )
    assert alerts_engine.get_ongoing() == {("mem", None, "percent"): "warning"}


def test_get_ongoing_omits_ok_tuples(alerts_engine):
    """Recovered tuples are dropped, not reported with level 'ok'."""
    alerts_engine._state[("mem", None, "percent")] = _AlertState(
        committed_level="ok", has_committed=True
    )
    alerts_engine._state[("fs", "/", "percent")] = _AlertState(
        committed_level="critical", has_committed=True
    )
    assert alerts_engine.get_ongoing() == {("fs", "/", "percent"): "critical"}


def test_get_ongoing_survives_history_eviction(alerts_engine):
    """The whole point: an active alert whose events aged out is still reported.

    `_state` is unbounded while `_history` is a bounded deque, so clearing the
    history must not change what `get_ongoing()` reports.
    """
    alerts_engine._state[("cpu", None, "total")] = _AlertState(
        committed_level="critical", has_committed=True
    )
    alerts_engine._history.clear()
    assert alerts_engine.get_ongoing() == {("cpu", None, "total"): "critical"}


def test_get_ongoing_does_not_mutate_state(alerts_engine):
    """Read-only: calling it twice yields equal results and leaves _state alone."""
    alerts_engine._state[("mem", None, "percent")] = _AlertState(
        committed_level="warning", has_committed=True
    )
    before = dict(alerts_engine._state)
    first = alerts_engine.get_ongoing()
    second = alerts_engine.get_ongoing()
    assert first == second
    assert alerts_engine._state == before


def test_get_ongoing_returns_a_copy(alerts_engine):
    """Mutating the returned dict must not corrupt the engine."""
    alerts_engine._state[("mem", None, "percent")] = _AlertState(
        committed_level="warning", has_committed=True
    )
    alerts_engine.get_ongoing()[("bogus", None, "x")] = "critical"
    assert ("bogus", None, "x") not in alerts_engine._state
```

Add `_AlertState` to the module's existing import from `glances.alerts_v5` at the top of the test file.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_alerts_v5.py -k get_ongoing -v`
Expected: FAIL with `AttributeError: 'GlancesAlerts' object has no attribute 'get_ongoing'`.

- [ ] **Step 3: Implement the accessor**

In `glances/alerts_v5.py`, immediately after `get_history()`:

```python
    def get_ongoing(self) -> dict[tuple[str, str | None, str], str]:
        """Return the currently non-``ok`` committed levels, keyed by tuple.

        A read-only view over ``_state``. Unlike ``get_history()`` — a bounded
        ring buffer — ``_state`` keeps one entry per watched
        ``(plugin, key, field)`` for the lifetime of the process, so an alert
        that has been active long enough for its transitions to age out of the
        history is still reported here.

        The TUI uses this as the authority on what is active; the history only
        supplies the chronology (when an incident opened, which levels it went
        through). Returns a fresh dict — callers may mutate it freely.

        Never called from the ingest path, and it writes nothing: the alert
        engine's observable behaviour is unchanged by its existence.
        """
        return {
            state_key: state.committed_level
            for state_key, state in self._state.items()
            if state.committed_level != "ok"
        }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_alerts_v5.py -v`
Expected: PASS, including every pre-existing test in the file.

- [ ] **Step 5: Verify the REST payload is untouched**

Run: `python -m pytest tests/test_routes_v5.py tests/test_api.py -q`
Expected: PASS. `get_ongoing` is not wired to any route; `/api/5/alert` still returns `get_history()` raw (`glances/routes_v5.py:122`).

- [ ] **Step 6: Stage**

```bash
git add glances/alerts_v5.py tests/test_alerts_v5.py
```

---

### Task 2: Incident derivation from the transition log

Spec §5.6. Pure function, no I/O, no rendering. This is the algorithmic heart of the change and is worth its own review gate.

**Files:**
- Modify: `glances/outputs/curses_renderer_v5.py` — add above `render_alert_block` (`:521`)
- Test: `tests/test_curses_renderer_v5.py`

**Interfaces:**
- Consumes: `GlancesAlerts.get_ongoing()`'s return type from Task 1.
- Produces: `_LEVEL_ORDER: dict[str, int]` and

  ```python
  _derive_incidents(
      history: list[dict[str, Any]],
      ongoing: dict[tuple[str, Any, str], str] | None = None,
  ) -> list[dict[str, Any]]
  ```

  Each returned incident is:

  ```python
  {
      "plugin": str,
      "key": Any,          # the primary-key value, or None for a scalar plugin
      "field": str,
      "level": str,        # highest level reached during the incident
      "begin": str | None, # ISO timestamp of the opening transition, None if unknown
      "end": str | None,   # ISO timestamp of the closing transition, None while ongoing
      "ongoing": bool,
      "partial": bool,     # True when `begin` is a lower bound, not the real start
      "prominent": bool,
  }
  ```

  Returned already sorted: ongoing first, then reverse-chronological by `begin` within each group (§5.3).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_curses_renderer_v5.py`, under the existing `# --- alert block` banner. Add `_derive_incidents` to the module import at the top of the file.

```python
def _evt(ts, plugin, field, level, previous="ok", key=None, prominent=False, is_initial=False):
    """Minimal alert event, shaped like GlancesAlerts._build_event's output."""
    return {
        "ts": ts,
        "plugin": plugin,
        "key": key,
        "field": field,
        "level": level,
        "previous_level": previous,
        "value": 1.0,
        "prominent": prominent,
        "is_initial": is_initial,
        "hostname": "h",
    }


def test_derive_incidents_single_open_incident():
    """One entry transition, still active → one ongoing incident."""
    history = [_evt("2026-08-16T10:00:00+00:00", "mem", "percent", "warning")]
    ongoing = {("mem", None, "percent"): "warning"}
    incidents = _derive_incidents(history, ongoing)
    assert len(incidents) == 1
    inc = incidents[0]
    assert inc["plugin"] == "mem"
    assert inc["field"] == "percent"
    assert inc["level"] == "warning"
    assert inc["begin"] == "2026-08-16T10:00:00+00:00"
    assert inc["end"] is None
    assert inc["ongoing"] is True
    assert inc["partial"] is False


def test_derive_incidents_escalation_keeps_one_row_at_max_level():
    """warning → critical is ONE incident whose level is the peak reached."""
    history = [
        _evt("2026-08-16T10:00:00+00:00", "cpu", "total", "warning"),
        _evt("2026-08-16T10:02:00+00:00", "cpu", "total", "critical", previous="warning"),
    ]
    incidents = _derive_incidents(history, {("cpu", None, "total"): "critical"})
    assert len(incidents) == 1
    assert incidents[0]["level"] == "critical"
    assert incidents[0]["begin"] == "2026-08-16T10:00:00+00:00"


def test_derive_incidents_deescalation_keeps_the_peak_level():
    """critical → warning, still active: the journal keeps CRITICAL (v4 parity §2.6)."""
    history = [
        _evt("2026-08-16T10:00:00+00:00", "cpu", "total", "critical"),
        _evt("2026-08-16T10:05:00+00:00", "cpu", "total", "warning", previous="critical"),
    ]
    incidents = _derive_incidents(history, {("cpu", None, "total"): "warning"})
    assert len(incidents) == 1
    assert incidents[0]["level"] == "critical"
    assert incidents[0]["ongoing"] is True


def test_derive_incidents_resolution_closes_the_row_instead_of_adding_one():
    """The `→ ok` transition must NOT occupy a row of its own (§5.4)."""
    history = [
        _evt("2026-08-16T10:00:00+00:00", "mem", "percent", "warning"),
        _evt("2026-08-16T10:03:00+00:00", "mem", "percent", "ok", previous="warning"),
    ]
    incidents = _derive_incidents(history, {})
    assert len(incidents) == 1
    assert incidents[0]["ongoing"] is False
    assert incidents[0]["begin"] == "2026-08-16T10:00:00+00:00"
    assert incidents[0]["end"] == "2026-08-16T10:03:00+00:00"


def test_derive_incidents_same_tuple_twice_gives_two_rows():
    """One row per INCIDENT, not per tuple: alert, recover, alert again = 2."""
    history = [
        _evt("2026-08-16T10:00:00+00:00", "mem", "percent", "warning"),
        _evt("2026-08-16T10:03:00+00:00", "mem", "percent", "ok", previous="warning"),
        _evt("2026-08-16T10:10:00+00:00", "mem", "percent", "warning"),
    ]
    incidents = _derive_incidents(history, {("mem", None, "percent"): "warning"})
    assert len(incidents) == 2
    assert [i["ongoing"] for i in incidents] == [True, False]
    assert incidents[0]["begin"] == "2026-08-16T10:10:00+00:00"
    assert incidents[1]["end"] == "2026-08-16T10:03:00+00:00"


def test_derive_incidents_evicted_opener_is_marked_partial():
    """First surviving event has previous_level != ok → the incident started earlier."""
    history = [
        _evt("2026-08-16T10:02:00+00:00", "cpu", "total", "critical", previous="warning"),
    ]
    incidents = _derive_incidents(history, {("cpu", None, "total"): "critical"})
    assert len(incidents) == 1
    assert incidents[0]["partial"] is True
    assert incidents[0]["begin"] == "2026-08-16T10:02:00+00:00"


def test_derive_incidents_is_initial_is_not_partial():
    """An `is_initial` event IS the start — Glances just found the system already hot."""
    history = [
        _evt("2026-08-16T10:00:00+00:00", "cpu", "total", "critical", previous="ok", is_initial=True),
    ]
    incidents = _derive_incidents(history, {("cpu", None, "total"): "critical"})
    assert incidents[0]["partial"] is False


def test_derive_incidents_fully_evicted_ongoing_tuple_is_synthesized():
    """Engine says active, history has nothing → still a row, with no begin."""
    incidents = _derive_incidents([], {("cpu", None, "total"): "critical"})
    assert len(incidents) == 1
    inc = incidents[0]
    assert inc["plugin"] == "cpu"
    assert inc["field"] == "total"
    assert inc["level"] == "critical"
    assert inc["begin"] is None
    assert inc["ongoing"] is True
    assert inc["partial"] is True


def test_derive_incidents_history_says_open_but_engine_says_recovered():
    """Defensive: the engine is the authority, so the incident is closed."""
    history = [_evt("2026-08-16T10:00:00+00:00", "mem", "percent", "warning")]
    incidents = _derive_incidents(history, {})
    assert incidents[0]["ongoing"] is False
    assert incidents[0]["end"] is None


def test_derive_incidents_ongoing_level_wins_when_higher_than_history():
    """Engine escalated but the escalation event was evicted → show the engine's level."""
    history = [_evt("2026-08-16T10:00:00+00:00", "cpu", "total", "warning")]
    incidents = _derive_incidents(history, {("cpu", None, "total"): "critical"})
    assert incidents[0]["level"] == "critical"


def test_derive_incidents_sorts_ongoing_first_then_newest_first():
    """§5.3: a long-running ongoing incident must not sink below newer resolved ones."""
    history = [
        _evt("2026-08-16T09:00:00+00:00", "cpu", "total", "critical"),
        _evt("2026-08-16T10:00:00+00:00", "mem", "percent", "warning"),
        _evt("2026-08-16T10:01:00+00:00", "mem", "percent", "ok", previous="warning"),
        _evt("2026-08-16T11:00:00+00:00", "fs", "percent", "warning", key="/"),
        _evt("2026-08-16T11:01:00+00:00", "fs", "percent", "ok", previous="warning", key="/"),
    ]
    incidents = _derive_incidents(history, {("cpu", None, "total"): "critical"})
    assert [(i["plugin"], i["ongoing"]) for i in incidents] == [
        ("cpu", True),
        ("fs", False),
        ("mem", False),
    ]


def test_derive_incidents_keeps_prominent_if_any_transition_had_it():
    """`prominent` must survive the collapse — the G6B defect class (§11)."""
    history = [
        _evt("2026-08-16T10:00:00+00:00", "cpu", "total", "warning", prominent=False),
        _evt("2026-08-16T10:02:00+00:00", "cpu", "total", "critical", previous="warning", prominent=True),
    ]
    incidents = _derive_incidents(history, {("cpu", None, "total"): "critical"})
    assert incidents[0]["prominent"] is True


def test_derive_incidents_distinguishes_keys_of_the_same_plugin():
    """fs[/] and fs[/home] are different tuples, hence different incidents."""
    history = [
        _evt("2026-08-16T10:00:00+00:00", "fs", "percent", "warning", key="/"),
        _evt("2026-08-16T10:01:00+00:00", "fs", "percent", "warning", key="/home"),
    ]
    incidents = _derive_incidents(
        history,
        {("fs", "/", "percent"): "warning", ("fs", "/home", "percent"): "warning"},
    )
    assert len(incidents) == 2
    assert {i["key"] for i in incidents} == {"/", "/home"}


def test_derive_incidents_no_ongoing_argument_defaults_to_history_only():
    """`ongoing=None` → derive purely from the history (export / direct calls)."""
    history = [_evt("2026-08-16T10:00:00+00:00", "mem", "percent", "warning")]
    incidents = _derive_incidents(history)
    assert len(incidents) == 1
    assert incidents[0]["ongoing"] is True
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_curses_renderer_v5.py -k derive_incidents -v`
Expected: FAIL at import — `cannot import name '_derive_incidents'`.

- [ ] **Step 3: Implement the derivation**

In `glances/outputs/curses_renderer_v5.py`, immediately above `render_alert_block`:

```python
# Severity ranking, used to keep an incident's level monotonic: once an
# incident has reached `critical` it keeps reporting `critical` even if it
# later de-escalates. v4 parity — `GlancesEvent.update()` assigns `state`
# only on CRITICAL (design §2.6).
_LEVEL_ORDER: dict[str, int] = {"ok": 0, "careful": 1, "warning": 2, "critical": 3}


def _derive_incidents(
    history: list[dict[str, Any]],
    ongoing: dict[tuple[str, Any, str], str] | None = None,
) -> list[dict[str, Any]]:
    """Collapse a transition log into incidents (design §5.6).

    The alert engine records level *transitions*; the block shows *incidents*.
    An incident opens on the first transition to a non-``ok`` level for a
    ``(plugin, key, field)`` tuple and closes on its transition back to
    ``ok``. Escalations mutate the open incident, they never open a new one —
    that is the "one row per incident" rule (§5.4).

    ``ongoing`` is ``GlancesAlerts.get_ongoing()``. It is the AUTHORITY on
    what is still active: the history is a bounded ring buffer, so an alert
    can outlive its own transitions. Passing ``None`` falls back to deriving
    "ongoing" from the history alone, which is what direct callers (export,
    tests) want.

    Returns incidents already sorted: ongoing first, newest first within each
    group (§5.3), so a long-running alert cannot sink out of the visible
    window behind newer resolved ones.
    """
    open_by_tuple: dict[tuple[str, Any, str], dict[str, Any]] = {}
    incidents: list[dict[str, Any]] = []

    for evt in history:
        state_key = (str(evt.get("plugin", "")), evt.get("key"), str(evt.get("field", "")))
        level = str(evt.get("level", ""))
        ts = str(evt.get("ts", "")) or None
        if level == "ok":
            closed = open_by_tuple.pop(state_key, None)
            if closed is not None:
                closed["end"] = ts
                closed["ongoing"] = False
            continue
        incident = open_by_tuple.get(state_key)
        if incident is None:
            # A first surviving transition that did not come from `ok` means
            # the opening transition has been evicted from the ring buffer:
            # `begin` is then a lower bound, not the real start. An
            # `is_initial` event is exempt — it IS the start, Glances simply
            # found the system already in that state at boot.
            previous = str(evt.get("previous_level", "ok"))
            partial = previous != "ok" and not bool(evt.get("is_initial", False))
            incident = {
                "plugin": state_key[0],
                "key": state_key[1],
                "field": state_key[2],
                "level": level,
                "begin": ts,
                "end": None,
                "ongoing": True,
                "partial": partial,
                "prominent": bool(evt.get("prominent", False)),
            }
            open_by_tuple[state_key] = incident
            incidents.append(incident)
            continue
        if _LEVEL_ORDER.get(level, 0) > _LEVEL_ORDER.get(incident["level"], 0):
            incident["level"] = level
        incident["prominent"] = incident["prominent"] or bool(evt.get("prominent", False))

    if ongoing is not None:
        for state_key, incident in open_by_tuple.items():
            committed = ongoing.get(state_key)
            if committed is None:
                # The engine says recovered but no `→ ok` event survives.
                # Trust the engine and close the incident with an unknown end.
                incident["ongoing"] = False
            elif _LEVEL_ORDER.get(committed, 0) > _LEVEL_ORDER.get(incident["level"], 0):
                incident["level"] = committed
        # Tuples the engine reports active but the history no longer covers at
        # all. Without this the block would silently drop a live alert.
        for state_key, committed in ongoing.items():
            if state_key in open_by_tuple:
                continue
            incidents.append(
                {
                    "plugin": state_key[0],
                    "key": state_key[1],
                    "field": state_key[2],
                    "level": committed,
                    "begin": None,
                    "end": None,
                    "ongoing": True,
                    "partial": True,
                    "prominent": False,
                }
            )

    # Two stable passes: chronological within a group, then ongoing on top.
    incidents.sort(key=lambda i: i["begin"] or "", reverse=True)
    incidents.sort(key=lambda i: 0 if i["ongoing"] else 1)
    return incidents
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_curses_renderer_v5.py -k derive_incidents -v`
Expected: PASS, 14 tests.

- [ ] **Step 5: Run the full renderer suite**

Run: `python -m pytest tests/test_curses_renderer_v5.py -q`
Expected: PASS. `_derive_incidents` is not wired into `render_alert_block` yet, so no existing test changes behaviour.

- [ ] **Step 6: Stage**

```bash
git add glances/outputs/curses_renderer_v5.py tests/test_curses_renderer_v5.py
```

---

### Task 3: Compact duration and fixed-width time formatters

Spec §6.4 and §6.2. `str(timedelta)` produces `0:02:04` — six to eight columns that read as a clock, not an elapsed time (§3.1.3). `_format_alert_time` produces 14 characters for an event from another day, which no fixed grid can absorb.

**Files:**
- Modify: `glances/outputs/curses_renderer_v5.py` — `_format_alert_time` (`:473`), `_format_alert_duration` (`:493`)
- Test: `tests/test_curses_renderer_v5.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `_format_alert_time(ts: str, now: datetime | None = None) -> str` — unchanged signature, new output contract: at most 8 characters.
  - `_format_duration_compact(seconds: float) -> str` — new.
  - `_incident_duration(incident: dict[str, Any], now: datetime | None = None) -> str | None` — new; returns the rendered duration for an incident, `>`-prefixed when `partial`, `None` when it cannot be computed.
  - `_format_alert_duration` is **deleted**; Task 6 removes its last caller in the same plan, and Task 3 removes its last caller now (nothing else uses it — verify with the grep in Step 5).

- [ ] **Step 1: Update the existing formatter tests and add the new ones**

Two existing tests assert the old contract and must be rewritten — this is the approved divergence recorded in spec §6.2 and §14. Replace `test_format_alert_time_other_day_includes_date` and every `test_format_alert_duration_*` test with the following. Keep `test_format_alert_time_same_day_returns_hms_local`, `test_format_alert_time_naive_utc_is_handled` and `test_format_alert_time_malformed_falls_back` exactly as they are.

```python
def test_format_alert_time_other_day_returns_month_day_within_8_columns():
    """Another day → `MM-DD`, not the old 14-char `MM-DD HH:MM:SS`.

    Approved divergence (design §6.2): the fixed grid gives TIME 8 columns and
    the DURATION column now carries the age (`2d04h`), so the full timestamp
    is redundant.
    """
    from datetime import datetime, timezone

    from glances.outputs.curses_renderer_v5 import _format_alert_time

    now_utc = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    result = _format_alert_time("2026-08-14T09:30:00+00:00", now=now_utc)
    assert len(result) <= 8
    assert result == "08-14"


def test_format_duration_compact_seconds():
    from glances.outputs.curses_renderer_v5 import _format_duration_compact

    assert _format_duration_compact(0) == "0s"
    assert _format_duration_compact(43) == "43s"
    assert _format_duration_compact(59.9) == "59s"


def test_format_duration_compact_minutes():
    from glances.outputs.curses_renderer_v5 import _format_duration_compact

    assert _format_duration_compact(60) == "1m00s"
    assert _format_duration_compact(178) == "2m58s"


def test_format_duration_compact_hours():
    from glances.outputs.curses_renderer_v5 import _format_duration_compact

    assert _format_duration_compact(3600) == "1h00m"
    assert _format_duration_compact(4380) == "1h13m"


def test_format_duration_compact_days():
    from glances.outputs.curses_renderer_v5 import _format_duration_compact

    assert _format_duration_compact(86400) == "1d00h"
    assert _format_duration_compact(187200) == "2d04h"


def test_format_duration_compact_never_exceeds_eight_columns():
    """The DURATION column is 8 wide; nothing plausible may overflow it."""
    from glances.outputs.curses_renderer_v5 import _format_duration_compact

    assert len(_format_duration_compact(999 * 86400)) <= 8


def test_incident_duration_ongoing_measures_from_begin_to_now():
    from datetime import datetime, timezone

    from glances.outputs.curses_renderer_v5 import _incident_duration

    now = datetime(2026, 8, 16, 10, 3, 0, tzinfo=timezone.utc)
    incident = {"begin": "2026-08-16T10:00:00+00:00", "end": None, "ongoing": True, "partial": False}
    assert _incident_duration(incident, now=now) == "3m00s"


def test_incident_duration_closed_measures_begin_to_end():
    """A resolved incident freezes its duration — it must not keep ticking."""
    from datetime import datetime, timezone

    from glances.outputs.curses_renderer_v5 import _incident_duration

    now = datetime(2026, 8, 16, 23, 0, 0, tzinfo=timezone.utc)
    incident = {
        "begin": "2026-08-16T10:00:00+00:00",
        "end": "2026-08-16T10:00:43+00:00",
        "ongoing": False,
        "partial": False,
    }
    assert _incident_duration(incident, now=now) == "43s"


def test_incident_duration_partial_is_prefixed_with_a_lower_bound_marker():
    """Opener evicted → the duration is a floor, and says so."""
    from datetime import datetime, timezone

    from glances.outputs.curses_renderer_v5 import _incident_duration

    now = datetime(2026, 8, 16, 10, 3, 0, tzinfo=timezone.utc)
    incident = {"begin": "2026-08-16T10:00:00+00:00", "end": None, "ongoing": True, "partial": True}
    assert _incident_duration(incident, now=now) == ">3m00s"


def test_incident_duration_unknown_begin_returns_none():
    from glances.outputs.curses_renderer_v5 import _incident_duration

    incident = {"begin": None, "end": None, "ongoing": True, "partial": True}
    assert _incident_duration(incident) is None


def test_incident_duration_malformed_begin_returns_none():
    from glances.outputs.curses_renderer_v5 import _incident_duration

    incident = {"begin": "not-a-timestamp", "end": None, "ongoing": True, "partial": False}
    assert _incident_duration(incident) is None


def test_incident_duration_future_begin_returns_none():
    """Clock skew must not print a negative duration."""
    from datetime import datetime, timezone

    from glances.outputs.curses_renderer_v5 import _incident_duration

    now = datetime(2026, 8, 16, 10, 0, 0, tzinfo=timezone.utc)
    incident = {"begin": "2026-08-16T11:00:00+00:00", "end": None, "ongoing": True, "partial": False}
    assert _incident_duration(incident, now=now) is None


def test_incident_duration_naive_begin_assumed_utc():
    from datetime import datetime, timezone

    from glances.outputs.curses_renderer_v5 import _incident_duration

    now = datetime(2026, 8, 16, 10, 1, 0, tzinfo=timezone.utc)
    incident = {"begin": "2026-08-16T10:00:00", "end": None, "ongoing": True, "partial": False}
    assert _incident_duration(incident, now=now) == "1m00s"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_curses_renderer_v5.py -k "format_duration_compact or incident_duration or format_alert_time" -v`
Expected: FAIL — `cannot import name '_format_duration_compact'`, plus the rewritten `_format_alert_time` test failing on the old 14-character output.

- [ ] **Step 3: Implement the formatters**

Replace the body of `_format_alert_time` so the other-day branch returns `MM-DD`:

```python
    if local_dt.date() == now_local.date():
        return local_dt.strftime("%H:%M:%S")
    # Another day: `MM-DD` keeps the column at 8 characters. The full
    # timestamp used to be printed here, but the grid's DURATION column now
    # carries the age (design §6.2), so the hour is redundant.
    return local_dt.strftime("%m-%d")
```

Delete `_format_alert_duration` entirely and put these two functions in its place:

```python
def _format_duration_compact(seconds: float) -> str:
    """Elapsed time in at most 8 columns (design §6.4).

    ``43s`` / ``2m58s`` / ``1h13m`` / ``2d04h``. Replaces ``str(timedelta)``,
    whose ``0:02:04`` reads as a clock rather than an elapsed time and whose
    width is unpredictable. Sub-second precision is dropped so the value does
    not jitter between refreshes.
    """
    total = int(max(0.0, seconds))
    if total < 60:
        return f"{total}s"
    if total < 3600:
        return f"{total // 60}m{total % 60:02d}s"
    if total < 86400:
        return f"{total // 3600}h{(total % 3600) // 60:02d}m"
    return f"{total // 86400}d{(total % 86400) // 3600:02d}h"


def _incident_duration(incident: dict[str, Any], now: datetime | None = None) -> str | None:
    """Rendered duration of one incident, or ``None`` when it cannot be known.

    Ongoing incidents measure from ``begin`` to now; resolved ones from
    ``begin`` to ``end``, so a resolved row freezes instead of ticking. A
    ``partial`` incident — one whose opening transition has aged out of the
    history — is prefixed ``>`` because its duration is a lower bound.

    Returns ``None`` for an unknown, malformed or future ``begin`` (clock
    skew): the caller then leaves the column blank rather than printing
    something false. Never raises — the renderer must not crash on a
    malformed event.
    """
    begin_raw = incident.get("begin")
    if not begin_raw:
        return None
    try:
        begin = datetime.fromisoformat(str(begin_raw))
    except (ValueError, TypeError):
        return None
    if begin.tzinfo is None:
        begin = begin.replace(tzinfo=timezone.utc)

    end_raw = incident.get("end")
    end: datetime | None = None
    if end_raw:
        try:
            end = datetime.fromisoformat(str(end_raw))
        except (ValueError, TypeError):
            end = None
        if end is not None and end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
    if end is None:
        end = now or datetime.now(tz=timezone.utc)

    elapsed = (end - begin).total_seconds()
    if elapsed < 0:
        return None
    text = _format_duration_compact(elapsed)
    return f">{text}" if incident.get("partial") else text
```

`render_alert_block` still calls `_format_alert_duration` at this point. Replace that one call site with the inline expression below so the module stays importable and the suite stays green; Task 6 rewrites the function wholesale anyway.

```python
            duration = _incident_duration(
                {"begin": str(evt.get("ts", "")), "end": None, "ongoing": True, "partial": False},
                now=now_local,
            )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_curses_renderer_v5.py -q`
Expected: PASS. The two alert-block tests that only assert on substrings (`test_render_alert_block_shows_recent_events`, `test_render_alert_block_truncates_to_limit`) are unaffected by the duration format change.

- [ ] **Step 5: Verify no caller of the deleted function survives**

Run: `grep -rn "_format_alert_duration" glances/ tests/`
Expected: no output.

- [ ] **Step 6: Stage**

```bash
git add glances/outputs/curses_renderer_v5.py tests/test_curses_renderer_v5.py
```

---

### Task 4: Generalise the painted-width hint from processlist to the whole right column

Spec §6.1. `render_alert_block` receives no width, so the frame fitter truncates wherever it lands (§3.1.4). The right column already computes the number the alert block needs — it is just published under a processlist-specific name and behind a processlist-specific guard.

**Files:**
- Modify: `glances/outputs/glances_curses_v5.py:621-640` — `_fit_proclist_width`
- Modify: `glances/plugins/processlist/render_curses_v5.py:356` and its docstring at `:308`
- Modify: `glances/plugins/processlist/render_curses_v5.py:66` — the comment naming the key
- Test: `tests/test_curses_v5.py`, `tests/test_processlist_v5.py` if it exists (check with `ls tests/ | grep processlist`)

**Interfaces:**
- Consumes: nothing.
- Produces: `view["right_width"]` — the painted width in columns of the right sidebar, published on every frame that has a non-empty right column. Same value the old `view["proclist_width"]` carried. `GlancesCursesV5._fit_right_width(view, frame, max_x) -> Frame` replaces `_fit_proclist_width`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_curses_v5.py`. Follow the file's existing pattern for building a TUI instance and a frame — read a nearby test first; the fixture below is illustrative of the assertion, not of the setup. Add `Frame` to the module's imports from `glances.outputs.curses_renderer_v5` if it is not already imported.

```python
def test_right_width_is_published_even_without_a_processlist_block(tui_v5):
    """The alert block always exists, so the width hint must not be gated on
    processlist the way `_fit_proclist_width` was."""
    frame = tui_v5._build_fitted_frame(max_x=100, max_y=40)
    view = tui_v5._build_view(100)
    frame = tui_v5._fit_right_width(view, frame, 100)
    assert isinstance(view["right_width"], int)
    assert view["right_width"] > 0


def test_right_width_is_not_published_when_the_right_column_is_empty(tui_v5):
    view = tui_v5._build_view(100)
    empty = Frame(header=[], top=[], left=[], right=[])
    tui_v5._fit_right_width(view, empty, 100)
    assert "right_width" not in view


def test_proclist_width_key_is_gone(tui_v5):
    """One mechanism, one name."""
    view = tui_v5._build_view(100)
    frame = tui_v5._build_fitted_frame(max_x=100, max_y=40)
    tui_v5._fit_right_width(view, frame, 100)
    assert "proclist_width" not in view
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_curses_v5.py -k right_width -v`
Expected: FAIL — `AttributeError: ... has no attribute '_fit_right_width'`.

- [ ] **Step 3: Rename the method, the key and widen the guard**

In `glances/outputs/glances_curses_v5.py`, replace `_fit_proclist_width` with:

```python
    def _fit_right_width(self, view: dict[str, Any], frame: Frame, max_x: int) -> Frame:
        """Tell the RIGHT-column renderers the width they will be painted at.

        The right sidebar is painted at
        ``right_width = max_x - left_width - _SIDEBAR_SEPARATOR_GAP`` (mirrors
        ``_paint``). Feeding that as ``view["right_width"]`` lets the
        processlist drop low-priority columns to keep ``Command`` readable,
        and lets the alert block pick a grid that fits (design §6.1).

        ``left_width`` depends only on ``frame.left`` natural widths — NOT on
        any right-column renderer's own columns — so a single extra rebuild
        settles the width. The rebuild still fires only when the value
        actually changes (first frame, resize).
        """
        if not frame.right:
            return frame
        left_width = self._sidebar_split(frame, max_x)
        right_width = max(0, max_x - left_width - self._SIDEBAR_SEPARATOR_GAP)
        if right_width and view.get("right_width") != right_width:
            view["right_width"] = right_width
            frame = self._frame_for_view(view)
        return frame
```

Update both call sites at `:591` and `:599` from `self._fit_proclist_width(...)` to `self._fit_right_width(...)`.

In `glances/plugins/processlist/render_curses_v5.py`, change `:356` to:

```python
    available = (view or {}).get("right_width")
```

and update the two comments that name the old key (`:66` and the docstring at `:308`) to say `view["right_width"]`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_curses_v5.py -k right_width -v`
Expected: PASS.

- [ ] **Step 5: Verify the rename is total and the processlist output is unchanged**

Run: `grep -rn "proclist_width" glances/ tests/`
Expected: no output.

Run: `python -m pytest tests/ -q -k "processlist or curses"`
Expected: PASS. The processlist responsive-column tests are the non-regression proof required by spec §11 — the rename must leave their output byte-identical.

- [ ] **Step 6: Stage**

```bash
git add glances/outputs/glances_curses_v5.py glances/plugins/processlist/render_curses_v5.py tests/test_curses_v5.py
```

---

### Task 5: Wire `--disable-unicode` into the v5 view

Spec §6.5. The alert block's glyphs are the first non-ASCII characters the v5 TUI will emit. v4 honours `--disable-unicode`; v5 has no mechanism at all. This task adds the flag path; Task 6 is its only consumer, so the flag is never dead surface at the end of the plan.

**Files:**
- Modify: `glances/outputs/glances_curses_v5.py` — `__init__` (`:181-196`), `_build_view` (`:753-771`)
- Modify: `glances/main_v5.py:467-481` — the `_TuiV5(...)` construction
- Test: `tests/test_curses_v5.py`, `tests/test_main_v5.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `view["unicode"] -> bool` — `True` when Unicode glyphs may be emitted, `False` under `--disable-unicode`. `GlancesCursesV5.__init__` gains a keyword-only-by-convention parameter `disable_unicode: bool = False`, matching the existing `byte` / `fahrenheit` style.

- [ ] **Step 1: Write the failing tests**

As in Task 4, read a nearby test in `tests/test_curses_v5.py` first and build the TUI the way that file already does. `tui_v5` / `tui_v5_factory` below stand for whatever construction helper exists there — do not add a new fixture if one is already available.

```python
def test_view_allows_unicode_by_default(tui_v5):
    assert tui_v5._build_view(100)["unicode"] is True


def test_view_forbids_unicode_when_disable_unicode_is_set(tui_v5_factory):
    """--disable-unicode must reach the renderers, v4 parity."""
    tui = tui_v5_factory(disable_unicode=True)
    assert tui._build_view(100)["unicode"] is False
```

And in `tests/test_main_v5.py`, extend whichever existing test asserts on the `_TuiV5` construction kwargs (search for `full_quicklook` in that file) so it also asserts `disable_unicode` is forwarded from `args`. If no such test exists, add:

```python
def test_assemble_forwards_disable_unicode_to_the_tui(monkeypatch):
    """`--disable-unicode` reaches the TUI, otherwise the alert glyphs ignore it."""
    captured = {}

    class _FakeTui:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("glances.main_v5._TuiV5", _FakeTui)
    args = _tui_args(disable_unicode=True)  # follow the file's existing args helper
    glances.main_v5.assemble(args, config)
    assert captured["disable_unicode"] is True
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_curses_v5.py -k unicode tests/test_main_v5.py -k unicode -v`
Expected: FAIL with `KeyError: 'unicode'` and an unexpected-keyword `TypeError`.

- [ ] **Step 3: Add the parameter and publish it**

In `GlancesCursesV5.__init__`, add the parameter after `byte`:

```python
        byte: bool = False,
        disable_unicode: bool = False,
```

and in the body, next to the other CLI-seeded flags:

```python
        # v4 parity for `--disable-unicode`: when set, renderers must emit
        # pure ASCII. v5 emitted no non-ASCII character at all until the
        # alert block's state glyphs (design §6.5), so this is the first
        # consumer — published as `view["unicode"]` (True = glyphs allowed).
        self._unicode = not bool(disable_unicode)
```

In `_build_view`, next to the other flags:

```python
        view["unicode"] = self._unicode
```

In `glances/main_v5.py`, add to the `_TuiV5(...)` call after `byte=`:

```python
            disable_unicode=getattr(args, "disable_unicode", False),
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_curses_v5.py tests/test_main_v5.py -q`
Expected: PASS.

- [ ] **Step 5: Stage**

```bash
git add glances/outputs/glances_curses_v5.py glances/main_v5.py tests/test_curses_v5.py tests/test_main_v5.py
```

---

### Task 6: The column grid

Spec §5.1–5.4, §6.2, §6.2c, §6.3, §6.5, §10.3. The deliverable of the whole plan: `render_alert_block` stops emitting sentences and emits the incident grid, and the synthesized block stops bypassing the slot sort.

**Files:**
- Modify: `glances/outputs/curses_renderer_v5.py` — `render_alert_block` (`:521`), `build_frame` signature (`:864`) and its tail (`:976-997`)
- Modify: `glances/outputs/glances_curses_v5.py:529-536` — pass `alerts_ongoing`
- Test: `tests/test_curses_renderer_v5.py`, `tests/test_curses_v5.py`

**Interfaces:**
- Consumes: `_derive_incidents` and `_LEVEL_ORDER` (Task 2); `_format_alert_time`, `_incident_duration` (Task 3); `view["right_width"]` (Task 4); `view["unicode"]` (Task 5); `GlancesAlerts.get_ongoing()` (Task 1).
- Produces:

  ```python
  render_alert_block(
      history: list[dict[str, Any]],
      limit: int = 10,
      is_initializing: bool = False,
      now: datetime | None = None,
      ongoing: dict[tuple[str, Any, str], str] | None = None,
      width: int | None = None,
      unicode_ok: bool = True,
  ) -> list[Row]
  ```

  and `build_frame(..., alerts_ongoing: dict[...] | None = None, ...)`. The three new `render_alert_block` parameters are appended after the existing ones so every current positional call keeps working.

**Grid arithmetic — get this right, the golden tests depend on it.** The painter inserts exactly one space between adjacent cells (`PluginBlock.width`, `curses_renderer_v5.py:176-179`). To land the spec's offsets (glyph at 0, `TIME` at 2, `DURATION` at 12, `TARGET` at 22) the `TIME` and `DURATION` cells carry one trailing pad column each:

| Cell | Emitted width | Occupies |
|---|---|---|
| glyph | 1 | 0 |
| `TIME` | 9 (`ljust`, 8 + 1 pad) | 2–10 |
| `DURATION` | 9 (`rjust(8)` + 1 pad) | 12–20 |
| `TARGET` | `T` (`ljust`) | 22 … |
| `LEVEL` | 8 (`rjust`) | last 8 |

Totals: `1+1+9+1+9+1+T+1+8 = 31+T` with `LEVEL`, `22+T` without it, `12+T` without `DURATION` either. With a 12-column floor on `TARGET` that gives the spec's thresholds of 43 and 34 exactly.

- [ ] **Step 1: Write the failing tests**

Replace `test_render_alert_block_shows_recent_events` and `test_render_alert_block_truncates_to_limit` (their substring assertions no longer describe the output) and add the grid tests. Keep both empty-history tests untouched — they are the §11 non-regression guarantee.

```python
def _line(row):
    """Paint one Row the way PluginBlock.width measures it: one space between
    cells unless the cell is glued."""
    out = ""
    for i, cell in enumerate(row.cells):
        if i and not cell.glue:
            out += " "
        out += cell.text
    return out


# Chronological, like the engine's deque: fs alerts and recovers, then
# containers and cpu alert and stay active.
_GRID_HISTORY = [
    _evt("2026-08-16T13:58:40+00:00", "fs", "percent", "warning", key="/"),
    _evt("2026-08-16T13:59:23+00:00", "fs", "percent", "ok", previous="warning", key="/"),
    _evt("2026-08-16T14:01:03+00:00", "containers", "mem_usage", "warning", key="nginx"),
    _evt("2026-08-16T14:02:11+00:00", "cpu", "total", "critical"),
]
_GRID_ONGOING = {
    ("cpu", None, "total"): "critical",
    ("containers", "nginx", "mem_usage"): "warning",
}
_GRID_NOW = datetime(2026, 8, 16, 14, 5, 9, tzinfo=timezone.utc)


def test_render_alert_block_full_grid_columns_are_aligned():
    """Every row lands TIME at 2, DURATION ending at 19, TARGET at 22."""
    rows = render_alert_block(
        _GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61
    )
    data = [_line(r) for r in rows[2:]]
    assert data, "expected data rows below the title and column header"
    for line in data:
        assert line[1] == " "
        assert line[10:12] == "  "
        assert line[20:22] == "  "
    assert len({len(line) for line in data}) == 1


def test_render_alert_block_ongoing_rows_come_first():
    """§5.3 — a resolved incident must never push an ongoing one out of view."""
    rows = render_alert_block(
        _GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61
    )
    data = [_line(r) for r in rows[2:]]
    assert "cpu.total" in data[0]
    assert "containers[nginx].mem_usage" in data[1]
    assert "fs[/].percent" in data[2]


def test_render_alert_block_resolved_incident_takes_one_row_not_two():
    """§5.4 — the `→ ok` transition resolves a row, it does not add one."""
    rows = render_alert_block(
        _GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61
    )
    assert len(rows) == 2 + 3  # title + column header + 3 incidents (4 events)


def test_render_alert_block_glyphs_distinguish_ongoing_from_resolved():
    rows = render_alert_block(
        _GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61
    )
    glyphs = [r.cells[0].text for r in rows[2:]]
    assert glyphs == ["●", "●", "○"]


def test_render_alert_block_ascii_fallback_emits_no_unicode():
    """--disable-unicode → the whole block is pure ASCII (§6.5)."""
    rows = render_alert_block(
        _GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61,
        unicode_ok=False,
    )
    painted = "\n".join(_line(r) for r in rows)
    assert painted.isascii()
    assert [r.cells[0].text for r in rows[2:]] == ["*", "*", "-"]


def test_render_alert_block_glyph_carries_the_level_colour():
    rows = render_alert_block(
        _GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61
    )
    assert rows[2].cells[0].color == ColorRole.CRITICAL
    assert rows[3].cells[0].color == ColorRole.WARNING


def test_render_alert_block_title_counts_ongoing_and_resolved():
    rows = render_alert_block(
        _GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61
    )
    title = _line(rows[0])
    assert title.startswith("ALERTS")
    assert "2 ongoing" in title
    assert "1 resolved" in title
    assert rows[0].cells[0].color == ColorRole.HEADER


def test_render_alert_block_title_is_never_level_coloured():
    """Standing TUI rule: a block title is HEADER, never escalated."""
    rows = render_alert_block(
        _GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61
    )
    assert all(c.color == ColorRole.HEADER for c in rows[0].cells)
    assert all(c.color == ColorRole.HEADER for c in rows[1].cells)


def test_render_alert_block_drops_level_below_43_columns():
    """§6.3 first step — TARGET has a 12-column floor."""
    wide = render_alert_block(
        _GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=43
    )
    narrow = render_alert_block(
        _GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=42
    )
    assert "CRITICAL" in _line(wide[2])
    assert "CRITICAL" not in _line(narrow[2])


def test_render_alert_block_drops_duration_below_34_columns():
    """§6.3 second step."""
    wide = render_alert_block(
        _GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=34
    )
    narrow = render_alert_block(
        _GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=33
    )
    assert _line(wide[2])[12:20].strip()
    assert "cpu.total" in _line(narrow[2])
    assert len(_line(narrow[2])) <= 33


def test_render_alert_block_never_exceeds_the_given_width():
    """§11 — no emitted row may overflow the block at any tested width."""
    for width in (96, 61, 43, 34, 30, 24):
        rows = render_alert_block(
            _GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=width
        )
        for row in rows:
            assert len(_line(row)) <= width, f"overflow at width={width}"


def test_render_alert_block_truncates_target_with_an_ellipsis():
    """59-character target in a 30-column TARGET cell → cut, and visibly so."""
    history = [
        _evt("2026-08-16T14:00:00+00:00", "containers", "memory_usage_percent",
             "warning", key="a-very-long-container-name")
    ]
    ongoing = {("containers", "a-very-long-container-name", "memory_usage_percent"): "warning"}
    rows = render_alert_block(history, limit=10, now=_GRID_NOW, ongoing=ongoing, width=61)
    # cells: glyph, TIME, DURATION, TARGET, LEVEL
    target_cell = rows[2].cells[3]
    assert len(target_cell.text) == 30
    assert target_cell.text.endswith("…")
    assert len(_line(rows[2])) == 61


def test_render_alert_block_ascii_truncation_uses_a_dot():
    """ASCII mode must not leak `…` through the truncation path."""
    history = [
        _evt("2026-08-16T14:00:00+00:00", "containers", "memory_usage_percent",
             "warning", key="a-very-long-container-name")
    ]
    ongoing = {("containers", "a-very-long-container-name", "memory_usage_percent"): "warning"}
    rows = render_alert_block(
        history, limit=10, now=_GRID_NOW, ongoing=ongoing, width=61, unicode_ok=False
    )
    target_cell = rows[2].cells[3]
    assert target_cell.text.endswith(".")
    assert _line(rows[2]).isascii()


def test_render_alert_block_forwards_prominent_onto_the_level_cell():
    """§11 — the G6B defect class must not reappear."""
    history = [_evt("2026-08-16T14:00:00+00:00", "cpu", "total", "critical", prominent=True)]
    rows = render_alert_block(
        history, limit=10, now=_GRID_NOW,
        ongoing={("cpu", None, "total"): "critical"}, width=61,
    )
    assert rows[2].cells[-1].prominent is True


def test_render_alert_block_forwards_prominent_onto_the_glyph_when_level_is_dropped():
    """Narrow terminal: `prominent` moves rather than disappearing."""
    history = [_evt("2026-08-16T14:00:00+00:00", "cpu", "total", "critical", prominent=True)]
    rows = render_alert_block(
        history, limit=10, now=_GRID_NOW,
        ongoing={("cpu", None, "total"): "critical"}, width=36,
    )
    assert rows[2].cells[0].prominent is True


def test_render_alert_block_shows_no_transition_arrow():
    """§3.1.2 — the level text no longer duplicates the colour, and there is
    no `previous → level` sentence any more."""
    rows = render_alert_block(
        _GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61
    )
    painted = "\n".join(_line(r) for r in rows)
    assert "→" not in painted
    assert "ongoing for" not in painted


def test_render_alert_block_limit_counts_incidents_not_events():
    """`limit` is a DATA-row budget; two events of one incident cost one row."""
    rows = render_alert_block(
        _GRID_HISTORY, limit=2, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61
    )
    assert len(rows) == 2 + 2


def test_render_alert_block_limit_zero_emits_the_title_only():
    """The vertical shrink ladder's step (h) — header only."""
    rows = render_alert_block(
        _GRID_HISTORY, limit=0, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=61
    )
    assert len(rows) == 1
    assert _line(rows[0]).startswith("ALERTS")


def test_render_alert_block_without_width_still_aligns():
    """Export / direct calls pass no width: pad TARGET to its natural maximum
    rather than degrading."""
    rows = render_alert_block(
        _GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING
    )
    data = [_line(r) for r in rows[2:]]
    assert len({len(line) for line in data}) == 1


def test_render_alert_block_fully_evicted_ongoing_alert_is_still_shown():
    """The reason `ongoing` exists at all (§5.6)."""
    rows = render_alert_block(
        [], limit=10, now=_GRID_NOW,
        ongoing={("cpu", None, "total"): "critical"}, width=61,
    )
    painted = "\n".join(_line(r) for r in rows)
    assert "cpu.total" in painted
    assert "--:--:--" in painted


def test_render_alert_block_empty_history_and_no_ongoing_still_collapses():
    """§11 — the single-line collapse survives the redesign."""
    rows = render_alert_block([], limit=10, is_initializing=False, ongoing={}, width=61)
    assert len(rows) == 1
    assert rows[0].cells[0].text == "ALERT (no alert detected)"
```

Add `datetime` / `timezone` and `_derive_incidents` to the file's imports if they are not already there.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_curses_renderer_v5.py -k alert_block -v`
Expected: FAIL — `render_alert_block() got an unexpected keyword argument 'ongoing'`.

- [ ] **Step 3: Rewrite `render_alert_block`**

Replace the whole function. Add the padding helper above it:

```python
# Alert grid geometry (design §6.2). The painter puts one space between
# adjacent cells, so the TIME and DURATION cells carry one trailing pad
# column each to land the spec's offsets (TIME at 2, DURATION at 12,
# TARGET at 22).
_ALERT_W_GLYPH = 1
_ALERT_W_TIME = 8
_ALERT_W_DURATION = 8
_ALERT_W_LEVEL = 8
_ALERT_MIN_TARGET = 12
# Block width at or above which the LEVEL / DURATION columns still fit
# without starving TARGET below its floor.
_ALERT_W_WITH_LEVEL = 31 + _ALERT_MIN_TARGET  # 43
_ALERT_W_WITH_DURATION = 22 + _ALERT_MIN_TARGET  # 34
_ALERT_GLYPHS = {
    True: {True: "●", False: "*"},  # ongoing
    False: {True: "○", False: "-"},  # resolved
}
_ALERT_TIME_UNKNOWN = "--:--:--"


def _fit_text(text: str, width: int, *, right: bool = False, ellipsis: str = "") -> str:
    """Pad or truncate ``text`` to exactly ``width`` columns.

    ``ellipsis`` — when non-empty — replaces the tail of a cut string so a
    truncated target reads as truncated. The caller passes ``…`` or ``.``
    depending on ``unicode_ok``; it is a parameter rather than a constant
    precisely so ASCII mode cannot leak a non-ASCII character.

    Guarantees the return value is exactly ``width`` long — the grid depends
    on it.
    """
    if width <= 0:
        return ""
    if len(text) > width:
        cut = width - len(ellipsis)
        text = text[:cut] + ellipsis if ellipsis and cut > 0 else text[:width]
    return text.rjust(width) if right else text.ljust(width)


def render_alert_block(
    history: list[dict[str, Any]],
    limit: int = 10,
    is_initializing: bool = False,
    now: datetime | None = None,
    ongoing: dict[tuple[str, Any, str], str] | None = None,
    width: int | None = None,
    unicode_ok: bool = True,
) -> list[Row]:
    """Render the alert history as an aligned incident grid (design §6).

    The block is a JOURNAL, not a gauge: it answers "what happened", never
    "where are we now" — the owning plugin already shows the live value
    (§5.1). One row per incident, ongoing ones pinned above resolved ones.

    Args:
        history: output of ``GlancesAlerts.get_history()``.
        limit: DATA-row budget (the title and column-header rows are extra).
            ``0`` emits the title alone — the vertical shrink ladder's
            "header only" step.
        is_initializing: ``GlancesAlerts.is_initializing()``.
        now: reference instant, so every row of a frame agrees.
        ongoing: ``GlancesAlerts.get_ongoing()`` — the authority on what is
            still active. ``None`` derives it from the history alone.
        width: painted block width (``view["right_width"]``). ``None`` keeps
            the full grid and sizes TARGET to its natural maximum, which is
            what export and direct callers want.
        unicode_ok: ``False`` under ``--disable-unicode`` — ASCII glyphs and
            an ASCII title rule (§6.5).

    Empty history AND nothing ongoing collapses to a single header-styled
    line, exactly as before the redesign:
    - ``is_initializing=True``  → ``ALERT (initializing)``
    - ``is_initializing=False`` → ``ALERT (no alert detected)``
    """
    incidents = _derive_incidents(history, ongoing)
    if not incidents:
        label = "ALERT (initializing)" if is_initializing else "ALERT (no alert detected)"
        return [Row(cells=[Cell(text=label, color=ColorRole.HEADER)])]

    now_local = (now or datetime.now(tz=timezone.utc)).astimezone()
    n_ongoing = sum(1 for i in incidents if i["ongoing"])
    n_resolved = len(incidents) - n_ongoing

    # Which columns fit. TARGET is the only elastic one and never drops.
    show_level = width is None or width >= _ALERT_W_WITH_LEVEL
    show_duration = width is None or width >= _ALERT_W_WITH_DURATION

    visible = incidents[:limit] if limit > 0 else []

    def target_of(incident: dict[str, Any]) -> str:
        key = incident["key"]
        source = f"{incident['plugin']}[{key}]" if key is not None else incident["plugin"]
        return f"{source}.{incident['field']}"

    if width is None:
        target_width = max((len(target_of(i)) for i in visible), default=_ALERT_MIN_TARGET)
        target_width = max(target_width, _ALERT_MIN_TARGET)
    elif show_level:
        target_width = width - 31
    elif show_duration:
        target_width = width - 22
    else:
        target_width = width - 12
    target_width = max(0, target_width)

    separator = "·" if unicode_ok else "-"
    title = f"ALERTS  {n_ongoing} ongoing {separator} {n_resolved} resolved"
    if width is not None and unicode_ok and width > len(title) + 1:
        title = title + " " + "─" * (width - len(title) - 1)
    elif width is not None and width > len(title) + 1:
        title = title + " " + "-" * (width - len(title) - 1)
    rows: list[Row] = [Row(cells=[Cell(text=title[:width] if width else title, color=ColorRole.HEADER)])]

    if not visible:
        return rows

    header_cells = [Cell(text=" " * _ALERT_W_GLYPH, color=ColorRole.HEADER, bold=True)]
    header_cells.append(Cell(text=_fit_text("TIME", _ALERT_W_TIME + 1), color=ColorRole.HEADER, bold=True))
    if show_duration:
        header_cells.append(
            Cell(text=_fit_text("DURATION", _ALERT_W_DURATION, right=True) + " ", color=ColorRole.HEADER, bold=True)
        )
    header_cells.append(Cell(text=_fit_text("TARGET", target_width), color=ColorRole.HEADER, bold=True))
    if show_level:
        header_cells.append(
            Cell(text=_fit_text("LEVEL", _ALERT_W_LEVEL, right=True), color=ColorRole.HEADER, bold=True)
        )
    rows.append(Row(cells=header_cells))

    for incident in visible:
        is_ongoing = bool(incident["ongoing"])
        level = str(incident["level"])
        role = _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)
        prominent = bool(incident["prominent"])
        begin = incident["begin"]
        ts_text = _format_alert_time(str(begin), now=now_local) if begin else _ALERT_TIME_UNKNOWN
        duration = _incident_duration(incident, now=now_local) or ""

        cells = [
            Cell(
                text=_ALERT_GLYPHS[is_ongoing][unicode_ok],
                color=role,
                # When LEVEL is dropped the glyph is the only cell left that
                # can carry `prominent` — never silently lose the flag.
                prominent=prominent and not show_level,
            ),
            Cell(text=_fit_text(ts_text, _ALERT_W_TIME + 1)),
        ]
        if show_duration:
            cells.append(Cell(text=_fit_text(duration, _ALERT_W_DURATION, right=True) + " "))
        cells.append(
            Cell(text=_fit_text(target_of(incident), target_width, ellipsis="…" if unicode_ok else "."))
        )
        if show_level:
            cells.append(
                Cell(
                    text=_fit_text(level.upper(), _ALERT_W_LEVEL, right=True),
                    color=role,
                    prominent=prominent,
                )
            )
        rows.append(Row(cells=cells))

    return rows
```

- [ ] **Step 4: Run the grid tests**

Run: `python -m pytest tests/test_curses_renderer_v5.py -k alert -v`
Expected: PASS.

- [ ] **Step 5: Wire `alerts_ongoing` through `build_frame` and move the append before the sort**

In `build_frame`, add the parameter after `alerts_history`:

```python
    alerts_ongoing: dict[tuple[str, Any, str], str] | None = None,
```

Document it in the docstring's Args block, next to `alerts_history`:

```
        alerts_ongoing: output of `GlancesAlerts.get_ongoing()` — the
            authority on which alerts are still active (design §5.6).
```

Then replace the tail of the function (`:976-997`). The append moves **above** the four `sort` calls, which resolves §10.3: `"alert"` is already last in `RIGHT_SLOT`, so the rendered order is unchanged and `RIGHT_SLOT` becomes the single placement mechanism.

```python
    # Synthesize the alerts block in the RIGHT slot (mirrors v4's `alert`
    # plugin in `_right_sidebar`). Appended BEFORE the sort so `RIGHT_SLOT`
    # is the single source of placement (design §10.3) — `"alert"` is last
    # in the tuple, so it still renders at the bottom of the column.
    frame.right.append(
        PluginBlock(
            name="alert",
            rows=render_alert_block(
                alerts_history,
                limit=row_budget(view, "alert", alerts_limit),
                is_initializing=alerts_initializing,
                ongoing=alerts_ongoing,
                width=(view or {}).get("right_width"),
                unicode_ok=bool((view or {}).get("unicode", True)),
            ),
            data_count=len(alerts_history),
        )
    )

    # v4 fidelity: enforce the slot-declared order, not the discovery
    # order (which is alphabetical and would give cpu/load/mem instead
    # of cpu/mem/load in the top row).
    frame.header.sort(key=lambda b: HEADER_SLOT.index(b.name) if b.name in HEADER_SLOT else len(HEADER_SLOT))
    frame.top.sort(key=lambda b: TOP_SLOT.index(b.name) if b.name in TOP_SLOT else len(TOP_SLOT))
    frame.left.sort(key=lambda b: LEFT_SLOT.index(b.name) if b.name in LEFT_SLOT else len(LEFT_SLOT))
    frame.right.sort(key=lambda b: RIGHT_SLOT.index(b.name) if b.name in RIGHT_SLOT else len(RIGHT_SLOT))
    return frame
```

In `glances/outputs/glances_curses_v5.py`, extend the `build_frame(...)` call at `:529`:

```python
        ongoing = self.alerts.get_ongoing() if self.alerts is not None else {}
        frame = build_frame(
            store_snapshot=snapshot,
            fields_by_plugin=self.fields_by_plugin,
            registry=self.registry,
            alerts_history=history,
            alerts_ongoing=ongoing,
            alerts_initializing=initializing,
            view=view,
        )
```

- [ ] **Step 6: Add the integration tests**

In `tests/test_curses_v5.py`:

```python
def test_alert_block_still_renders_last_in_the_right_column(tui_v5):
    """§11 — moving the append before the sort must not move the block."""
    frame = tui_v5._build_fitted_frame(max_x=120, max_y=45)
    assert frame.right[-1].name == "alert"


def test_alert_block_is_appended_exactly_once(tui_v5):
    frame = tui_v5._build_fitted_frame(max_x=120, max_y=45)
    assert [b.name for b in frame.right].count("alert") == 1


def test_alert_block_never_overflows_the_right_column(tui_v5):
    """No emitted row exceeds the painted block width, at any terminal size."""
    for max_x in (80, 96, 120, 200):
        frame = tui_v5._build_fitted_frame(max_x=max_x, max_y=45)
        block = next(b for b in frame.right if b.name == "alert")
        assert block.width <= max_x
```

- [ ] **Step 7: Run the whole suite**

Run: `python -m pytest tests/ -q`
Expected: PASS, no test skipped that was not skipped before.

- [ ] **Step 8: Verify the REST payload really is untouched**

Run: `python -m pytest tests/test_routes_v5.py tests/test_api.py tests/test_mcp_adapter_v5.py -q`
Expected: PASS. Nothing in this task touches `_build_event`.

- [ ] **Step 9: Stage**

```bash
git add glances/outputs/curses_renderer_v5.py glances/outputs/glances_curses_v5.py \
        tests/test_curses_renderer_v5.py tests/test_curses_v5.py
```

---

### Task 7: Document the `[alerts]` section in `conf/glances.conf`

Spec §8.1. The three keys `GlancesAlerts.__init__` reads have never existed in the shipped configuration file, so no user can discover them. Every key is written **commented out at its current default**, so no existing deployment changes behaviour.

`docs/config.rst` is deliberately **not** touched: it documents the file's location and syntax, not per-section keys — `conf/glances.conf` is itself the reference template it points at.

**Files:**
- Modify: `conf/glances.conf` — insert a new section between `[global]` (ends at `:19`) and the `# User interface` banner (`:21`)
- Test: `tests/test_config_v5.py`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing consumed by code — documentation only.

- [ ] **Step 1: Write the failing test**

In `tests/test_config_v5.py`, following the file's existing pattern for loading `conf/glances.conf`:

```python
def test_shipped_conf_documents_the_alerts_section():
    """The three [alerts] keys must be present and COMMENTED, so the shipped
    file documents them without changing any default (design §8.1)."""
    from pathlib import Path

    text = Path("conf/glances.conf").read_text(encoding="utf-8")
    assert "[alerts]" in text
    for key in ("min_duration_seconds", "history_size", "warmup_cycles"):
        assert f"#{key}=" in text, f"{key} must be documented, commented out"
        assert f"\n{key}=" not in text, f"{key} must NOT be active by default"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_config_v5.py -k alerts_section -v`
Expected: FAIL — `assert '[alerts]' in text`.

- [ ] **Step 3: Add the section**

Insert into `conf/glances.conf` immediately after the `[global]` section's last line (`#plugin_dir=...`) and before the `# User interface` banner:

```ini

##############################################################################
# Alerts engine (Glances v5)
##############################################################################

[alerts]
# All keys below are shown at their built-in defaults. Uncomment to change.
#
# Hold time, in seconds, before a level change is committed and logged.
# Suppresses flapping: a stat that crosses a threshold and comes straight
# back never produces an alert.
# Note for users coming from v4: this is NOT v4's [alert] min_duration.
# v4 DISCARDED a finished event shorter than the threshold; v5 DEBOUNCES the
# transition before it is recorded at all.
#min_duration_seconds=5.0
# Maximum number of alert events kept in memory and served by /api/5/alert.
#history_size=200
# Number of refresh cycles skipped, per plugin, at startup. Rates are not
# computed on the first cycles, so thresholds could fire spuriously.
#warmup_cycles=3
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_config_v5.py -q`
Expected: PASS.

- [ ] **Step 5: Verify the defaults in the comments match the code**

Run: `grep -n "_DEFAULT_MIN_DURATION_SECONDS\|_DEFAULT_HISTORY_SIZE\|_DEFAULT_WARMUP_CYCLES" glances/alerts_v5.py`
Expected: `5.0`, `200`, `3` — exactly the values written in the comments above. If any differs, the config comment is wrong, not the code.

- [ ] **Step 6: Confirm the shipped file still parses and changes nothing**

Run: `python -m pytest tests/ -q`
Expected: PASS. Every key is commented, so `config.get("alerts", ...)` still falls through to the code defaults.

- [ ] **Step 7: Run the full pre-commit gate and restage**

```bash
make pre-commit
git add conf/glances.conf tests/test_config_v5.py
git add -u
```

`make pre-commit` runs ≈23 hooks and may reformat files; gitleaks scans the **index**, so restage after it runs. Re-run `make pre-commit` until it is clean.

- [ ] **Step 8: Report to the maintainer**

Do **not** commit. Print `git status --short` and `git diff --cached --stat`, and state plainly which spec sections are covered and that the TUI smoke test at several terminal widths is still owed by the maintainer.

---

## Manual smoke test (maintainer)

Not an automated step; the golden tests cannot prove the block *looks* right.

```bash
python -m glances.main_v5
```

Check, resizing the terminal through ~120, ~96, ~80 and ~60 columns:

1. The block sits at the bottom of the right column, under the process list.
2. Columns stay aligned as rows come and go.
3. `LEVEL` disappears before `DURATION` as the terminal narrows, and no row ever wraps.
4. An ongoing alert stays at the top even when newer alerts resolve below it.
5. `python -m glances.main_v5 --disable-unicode` shows `*` / `-` and an ASCII rule.
6. On a machine with no alert at all, the block is still the single line `ALERT (no alert detected)`.

---

## Self-Review

**Spec coverage:**

| Spec section | Task |
|---|---|
| §5.1 journal not gauge | 6 (no value column emitted) |
| §5.2 column record | 6 |
| §5.3 ongoing pinned | 2 (sort) + 6 (test) |
| §5.4 one row per incident | 2 + 6 |
| §5.6 incident derivation, `get_ongoing()` | 1 + 2 |
| §6.1 width source | 4 |
| §6.2 the [A] grid, `TIME` divergence | 3 + 6 |
| §6.2c title row, empty case | 6 |
| §6.3 degradation ladder | 6 |
| §6.4 duration format | 3 |
| §6.5 glyphs, unicode, no dimming, `prominent` | 5 + 6 |
| §8.1 `[alerts]` documented | 7 |
| §9 no new key binding | — nothing to do, asserted by omission |
| §10.3 `RIGHT_SLOT` single mechanism | 6 |
| §11 non-regression checklist | tests spread over 1, 4, 6, 7 |
| §5.5, §6.2b, §7, §10.1 | **out of scope** — Phase 2.X, per §4.1 option C |

**Open item carried into execution:** spec §6.2c flags that the block now emits *two* non-data rows (title + column header) while `row_budget`'s contract excludes one. Task 6's `test_alert_block_never_overflows_the_right_column` and the existing vertical-fit tests will show whether the accounting drifts by one row at small heights. If it does, the spec's prescribed fix is to fold the column labels into the title row — **not** to change the budget contract.
