# Alert Top Processes (v5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Attach the 3 most persistent processes to every v5 CPU / memory / swap / load alert, and surface them in both the curses alert grid and `GET /api/5/alert`.

**Architecture:** Each alertable field opts in by declaring a `top_processes_sort` key in its `fields_description`. `GlancesAlerts` keeps a per-incident `Counter` of the 6 highest processes seen on every ingest cycle and rewrites the incident's opening event dict in place — the same in-place model v4 uses for `GlancesEvent`. The curses block gains a data-conditional `TOP` column inserted between `TARGET` and `LEVEL`.

**Tech Stack:** Python 3.9+, `collections.Counter`, `glances.processes.sort_stats`, pytest, curses renderer (`glances/outputs/curses_renderer_v5.py`).

**Spec:** `docs/superpowers/specs/2026-08-30-v5-alert-top-processes-design.md`

## Global Constraints

- **Never commit, never push, never open a PR.** Every task ends with `git add` and stops there. The maintainer commits personally. Never add a `Co-Authored-By` trailer.
- **Never touch `NEWS.rst`.** It is updated at release time only.
- Branch: `develop-v5`.
- Run tests with `uv run pytest <path> -q`. The v5 subset is `make test-v5`.
- At the very end of the plan (Task 7): `make pre-commit`. gitleaks scans the **index**, so re-stage before re-running it.
- Payload key names are `top` and `top_sort` — v4's `GlancesEvent.top` / `.sort`. The `fields_description` key is `top_processes_sort`.
- Sampling depth is 6 in / 3 out, hard-coded (v4 parity). **No new config key.**
- The two accumulation rules, from spec §3: accumulate from `warning` upwards, and **never reset** — not on escalation, not on de-escalation. Only the transition back to `ok` releases the accumulator.
- Absence is structural: outside the allowlist the `top` / `top_sort` keys are **absent**, never `None` and never `[]`.
- **Every new alert-engine test that expects an event to be recorded must
  build its config with `_config_with(tmp_path, monkeypatch,
  "[alerts]\nmin_duration_seconds=0\n")`.** The plain `config` fixture leaves
  `min_duration_seconds` at its 5.0 s default against a real
  `time.monotonic`, so `_reconcile` never commits within a test and
  `get_history()` stays empty.
- Existing renderer output must stay byte-identical for any history that carries no `top` key. This is the regression contract for Tasks 5 and 6.

---

### Task 1: Declare `top_processes_sort` on the five alertable fields

Pure data. No behaviour changes — nothing reads the key yet.

**Files:**
- Modify: `glances/plugins/cpu/model_v5.py:67-75` (`total`), `:100-107` (`iowait`)
- Modify: `glances/plugins/mem/model_v5.py:48-55` (`percent`)
- Modify: `glances/plugins/memswap/model_v5.py:63-70` (`percent`)
- Modify: `glances/plugins/load/model_v5.py:76-86` (`min15`)
- Test: `tests/test_alerts_v5.py`

**Interfaces:**
- Consumes: nothing.
- Produces: the schema key `top_processes_sort: str`, read in Task 2 as
  `type(plugin).fields_description.get(field_name, {}).get("top_processes_sort")`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_alerts_v5.py`:

```python
# ---------------------------------------------------------- top processes: allowlist


def test_top_processes_sort_allowlist_is_exactly_five_fields():
    """Spec §4 — only the aggregate signals a user reacts to are annotated.

    Annotating cpu.system/user/steal alongside cpu.total would produce three
    near-identical rows for one episode of CPU pressure; load.min5 alongside
    load.min15 would double every load incident.
    """
    from glances.plugins.cpu.model_v5 import PluginModel as CpuModel
    from glances.plugins.load.model_v5 import PluginModel as LoadModel
    from glances.plugins.mem.model_v5 import PluginModel as MemModel
    from glances.plugins.memswap.model_v5 import PluginModel as SwapModel

    declared = {
        (model.plugin_name, field): schema["top_processes_sort"]
        for model in (CpuModel, LoadModel, MemModel, SwapModel)
        for field, schema in model.fields_description.items()
        if "top_processes_sort" in schema
    }
    assert declared == {
        ("cpu", "total"): "cpu_percent",
        ("cpu", "iowait"): "io_counters",
        ("mem", "percent"): "memory_percent",
        ("memswap", "percent"): "memory_percent",
        ("load", "min15"): "cpu_percent",
    }
```

(`PluginModel` is the class each of the four `model_v5.py` files exports —
verified, not assumed.)

- [ ] **Step 2: Run the test and verify it fails**

Run: `uv run pytest tests/test_alerts_v5.py::test_top_processes_sort_allowlist_is_exactly_five_fields -q`
Expected: FAIL — `declared` is `{}`.

- [ ] **Step 3: Add the key to the five fields**

`glances/plugins/cpu/model_v5.py`, inside the `"total"` schema (after `"default_thresholds"`):

```python
            "top_processes_sort": "cpu_percent",
```

Same file, inside the `"iowait"` schema:

```python
            "top_processes_sort": "io_counters",
```

`glances/plugins/mem/model_v5.py`, inside `"percent"`:

```python
            "top_processes_sort": "memory_percent",
```

`glances/plugins/memswap/model_v5.py`, inside `"percent"`:

```python
            "top_processes_sort": "memory_percent",
```

`glances/plugins/load/model_v5.py`, inside `"min15"`:

```python
            "top_processes_sort": "cpu_percent",
```

Do **not** add the key to `cpu.system`, `cpu.user`, `cpu.dpc`, `cpu.steal`,
`cpu.ctx_switches` or `load.min5`.

- [ ] **Step 4: Run the test and verify it passes**

Run: `uv run pytest tests/test_alerts_v5.py::test_top_processes_sort_allowlist_is_exactly_five_fields -q`
Expected: PASS

- [ ] **Step 5: Verify no plugin test regressed**

Run: `uv run pytest tests/test_plugin_cpu_v5.py tests/test_plugin_mem_v5.py tests/test_plugin_memswap_v5.py tests/test_plugin_load_v5.py -q`
Expected: all PASS. A schema key nothing reads must be inert.

- [ ] **Step 6: Stage**

```bash
git add glances/plugins/cpu/model_v5.py glances/plugins/mem/model_v5.py \
        glances/plugins/memswap/model_v5.py glances/plugins/load/model_v5.py \
        tests/test_alerts_v5.py
```

---

### Task 2: Accumulate the top processes in `GlancesAlerts`

**Files:**
- Modify: `glances/alerts_v5.py` — imports (~line 42), `_AlertState` (77-96), `ingest_plugin` (238-322), new private helpers after `_update_auto_sort` (line 365)
- Test: `tests/test_alerts_v5.py`

**Interfaces:**
- Consumes: `top_processes_sort` from Task 1.
- Produces: `top: list[str]` and `top_sort: str` written in place onto the incident's opening event dict, i.e. onto entries returned by `GlancesAlerts.get_history()`. Also `_AlertState.top_counter` / `.top_sort` / `.top_event`, read by Task 3.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_alerts_v5.py` (after the Task 1 test):

```python
class _FakeTopProcessEngine:
    """Duck-typed stand-in for `glances.processes.glances_processes`."""

    auto_sort = False

    def __init__(self, procs=None):
        self.procs = list(procs or [])

    def get_list(self):
        return list(self.procs)

    def set_sort_key(self, key, auto=False):  # pragma: no cover - auto_sort is False
        pass


class _FakeTopPlugin(_FakeScalarPlugin):
    """Scalar plugin whose `percent` field opts into top-process capture."""

    plugin_name = "faketop"
    fields_description = {
        "percent": {"description": "p", "unit": "percent", "top_processes_sort": "cpu_percent"},
        "total": {"description": "t", "unit": "bytes"},
    }


def _proc(name, cpu):
    return {"name": name, "cpu_percent": cpu, "memory_percent": 0.0}


def _procs(*names):
    """Processes in descending cpu_percent order, highest first."""
    return [_proc(name, 100.0 - index) for index, name in enumerate(names)]


@pytest.mark.asyncio
async def test_top_processes_favour_persistence_over_the_current_cycle(tmp_path, monkeypatch, store):
    """Spec §5.3 — the top 3 are the most FREQUENT names across the incident,
    not the current cycle's highest consumers."""
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeTopProcessEngine(_procs("p1", "p2", "p3", "p4", "p5", "p6", "p7"))
    alerts = GlancesAlerts(cfg, process_engine=engine)
    plugin = _FakeTopPlugin(store, cfg)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    # p7 becomes the cycle's #1, but p1/p2 have now been seen twice.
    engine.procs = _procs("p7", "p1", "p2", "p8", "p9", "p10")
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})

    opening = alerts.get_history()[0]
    assert opening["top"] == ["p1", "p2", "p3"]
    assert opening["top_sort"] == "cpu_percent"


@pytest.mark.asyncio
async def test_top_processes_survive_de_escalation(tmp_path, monkeypatch, store):
    """Spec §3 decision 2 — critical -> warning must NOT wipe the accumulator."""
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeTopProcessEngine(_procs("a", "b", "c", "d", "e", "f"))
    alerts = GlancesAlerts(cfg, process_engine=engine)
    plugin = _FakeTopPlugin(store, cfg)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    await _run_with_levels(plugin, alerts, {"percent": {"level": "critical", "prominent": True}})
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})

    state = alerts._state[("faketop", None, "percent")]
    assert sum(state.top_counter.values()) == 18  # 3 cycles x 6 sampled
    # The accumulator still points at the OPENING event, not the escalation.
    assert alerts.get_history()[0]["top"] == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_only_the_opening_event_carries_the_top(tmp_path, monkeypatch, store):
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeTopProcessEngine(_procs("a", "b", "c"))
    alerts = GlancesAlerts(cfg, process_engine=engine)
    plugin = _FakeTopPlugin(store, cfg)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    await _run_with_levels(plugin, alerts, {"percent": {"level": "critical", "prominent": True}})

    history = alerts.get_history()
    assert "top" in history[0]
    assert "top" not in history[1]


@pytest.mark.asyncio
async def test_closing_an_incident_freezes_the_top(tmp_path, monkeypatch, store):
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeTopProcessEngine(_procs("a", "b", "c"))
    alerts = GlancesAlerts(cfg, process_engine=engine)
    plugin = _FakeTopPlugin(store, cfg)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    frozen = list(alerts.get_history()[0]["top"])
    await _run_with_levels(plugin, alerts, {"percent": {"level": "ok", "prominent": True}})
    engine.procs = _procs("z1", "z2", "z3")
    await _run_with_levels(plugin, alerts, {"percent": {"level": "ok", "prominent": True}})

    state = alerts._state[("faketop", None, "percent")]
    assert state.top_counter is None
    assert state.top_event is None
    assert alerts.get_history()[0]["top"] == frozen


@pytest.mark.asyncio
async def test_field_without_sort_key_never_gets_a_top(tmp_path, monkeypatch, store):
    """Spec §4 — an fs/sensors-style alert must not carry a meaningless top."""
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeTopProcessEngine(_procs("a", "b", "c"))
    alerts = GlancesAlerts(cfg, process_engine=engine)
    plugin = _FakeScalarPlugin(store, cfg)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})

    opening = alerts.get_history()[0]
    assert "top" not in opening
    assert "top_sort" not in opening


@pytest.mark.asyncio
async def test_empty_process_list_writes_no_top_key(tmp_path, monkeypatch, store):
    """Process plugins disabled -> the key is ABSENT, not an empty list."""
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    alerts = GlancesAlerts(cfg, process_engine=_FakeTopProcessEngine([]))
    plugin = _FakeTopPlugin(store, cfg)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})

    assert "top" not in alerts.get_history()[0]


@pytest.mark.asyncio
async def test_no_process_engine_is_a_no_op(tmp_path, monkeypatch, store):
    """Default construction (tests, headless rigs) must not raise."""
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    alerts = GlancesAlerts(cfg)
    plugin = _FakeTopPlugin(store, cfg)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})

    assert "top" not in alerts.get_history()[0]
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `uv run pytest tests/test_alerts_v5.py -q -k "top_process or opening_event or freezes or sort_key or empty_process or process_engine_is_a_no_op"`
Expected: FAIL — `KeyError: 'top'` / `AttributeError: 'ct' object has no attribute 'top_counter'`.

- [ ] **Step 3: Add the imports and the state fields**

In `glances/alerts_v5.py`, extend the existing `collections` import:

```python
from collections import Counter, deque
```

and add, next to the other `glances` imports:

```python
from glances.processes import sort_stats
```

(`glances/event.py` imports `sort_stats` the same way in v4 — this is parity, not new coupling. `glances.processes` is already imported by `main_v5.py`.)

Add the sampling constants next to `_ALERTABLE_LEVELS`:

```python
# Top-process capture depth: sample the N highest processes each cycle, keep
# the M most frequently sampled names. v4 values, deliberately hard-coded —
# see spec §5.3, no config key.
_TOP_PROCESSES_SAMPLE = 6
_TOP_PROCESSES_KEEP = 3
```

Extend `_AlertState` (after `has_committed`):

```python
    # Top-process accumulation, live only while the incident is open.
    # `top_event` is a REFERENCE to the dict this incident's opening event
    # put in `_history`; rewriting it in place is how v4's GlancesEvent
    # behaves, and it is what keeps `GET /api/5/alert` current on an
    # incident that is still running. All three are None while `ok`.
    top_counter: Counter[str] | None = None
    top_sort: str | None = None
    top_event: dict[str, Any] | None = None
```

- [ ] **Step 4: Add the accumulator helpers**

In `glances/alerts_v5.py`, after `_update_auto_sort` (around line 365):

```python
    # ---------------------------------------------------- top processes

    @staticmethod
    def _top_sort_key(plugin: GlancesPluginBase, field_name: str) -> str | None:
        """The field's declared process sort key, or None if it has none.

        Read from `fields_description` rather than from a table here, so a
        plugin opts in without `alerts_v5` knowing it exists (spec §4).
        """
        schema = type(plugin).fields_description.get(field_name, {})
        key = schema.get("top_processes_sort")
        return key if isinstance(key, str) and key else None

    def _open_top(self, state: _AlertState, sort_key: str | None, event: dict[str, Any]) -> None:
        """Start accumulating for an incident that just opened."""
        if sort_key is None:
            return
        state.top_counter = Counter()
        state.top_sort = sort_key
        state.top_event = event

    @staticmethod
    def _release_top(state: _AlertState) -> None:
        """Stop accumulating; the last value stays frozen in the opening event."""
        state.top_counter = None
        state.top_sort = None
        state.top_event = None

    def _sample_processes(self, sort_key: str) -> list[dict[str, Any]]:
        """The `_TOP_PROCESSES_SAMPLE` highest processes for `sort_key`.

        Empty when no engine is wired or the process plugins are disabled —
        the caller then writes nothing at all, so the payload key stays
        absent rather than becoming an empty list.
        """
        engine = self._process_engine
        if engine is None:
            return []
        try:
            procs = engine.get_list()
        except Exception as e:  # pragma: no cover - defensive
            logger.debug("top-process sampling failed: %s", e)
            return []
        if not procs:
            return []
        return sort_stats(procs, sort_key)[:_TOP_PROCESSES_SAMPLE]

    def _accumulate_top(self, state: _AlertState, cache: dict[str, list[dict[str, Any]]]) -> None:
        """One cycle of accumulation, then rewrite the opening event in place.

        `cache` is per-`ingest_plugin`-call, so the process list is sorted at
        most once per distinct sort key per cycle — and not at all while no
        annotated field is in alert.
        """
        if state.top_event is None or state.top_sort is None or state.top_counter is None:
            return
        sampled = cache.get(state.top_sort)
        if sampled is None:
            sampled = self._sample_processes(state.top_sort)
            cache[state.top_sort] = sampled
        if not sampled:
            return
        for proc in sampled:
            name = proc.get("name")
            if name:
                state.top_counter[str(name)] += 1
        # `most_common` is v4's `sorted(..., reverse=True)[0:3]`: Counter
        # keeps insertion order and the sort is stable, so ties break
        # identically — in O(n) instead of O(n log n).
        state.top_event["top"] = [name for name, _ in state.top_counter.most_common(_TOP_PROCESSES_KEEP)]
        state.top_event["top_sort"] = state.top_sort
```

- [ ] **Step 5: Hook the accumulator into `ingest_plugin`**

In `glances/alerts_v5.py`, declare the per-cycle cache just above the
observation loop (before `for key, field_name, observed_level, ... in self._observations(...)`):

```python
        # Sorted process lists for this cycle, keyed by sort key. Built
        # lazily: no active alert on an annotated field means no sort at all.
        top_cache: dict[str, list[dict[str, Any]]] = {}
```

Then rewrite the transition block (currently lines 292-318) as:

```python
            if transition is not None:
                event = self._build_event(
                    plugin.plugin_name,
                    key,
                    field_name,
                    previous_level=transition.previous,
                    new_level=transition.new,
                    value=value,
                    prominent=prominent,
                    is_initial=transition.is_initial,
                )
                self._history.append(event)
                # Same timestamp as the event, by construction — the two can
                # never drift.
                if transition.new == "ok":
                    state.committed_since = None
                    # The incident is over: freeze whatever was accumulated.
                    self._release_top(state)
                elif state.committed_since is None:
                    # This transition OPENS the incident (an escalation leaves
                    # `committed_since` set and must not restart the capture).
                    state.committed_since = event["ts"]
                    self._open_top(state, self._top_sort_key(plugin, field_name), event)
                if transition.new != "ok":
                    # Entry into a non-ok level: fire non-repeat actions.
                    self._fire_actions(plugin, key, field_name, transition.new, value, repeat=False)

            # Steady-state repeat dispatch — fires on every ingest cycle
            # while the committed level is non-ok, including the cycle of
            # the entry transition (v4-aligned behaviour).
            if state.committed_level != "ok":
                self._accumulate_top(state, top_cache)
                self._fire_actions(plugin, key, field_name, state.committed_level, value, repeat=True)
```

- [ ] **Step 6: Run the tests and verify they pass**

Run: `uv run pytest tests/test_alerts_v5.py -q`
Expected: all PASS, including every pre-existing test — no existing test uses an annotated field, so no existing event gains a key.

- [ ] **Step 7: Stage**

```bash
git add glances/alerts_v5.py tests/test_alerts_v5.py
```

---

### Task 3: `GlancesAlerts.get_ongoing_top()`

`_history` is a bounded ring buffer: a long-running incident loses its own opening event, and with it the only copy of its `top`. `_state` is unbounded and stays the authority — exactly the reason `get_ongoing_since()` exists.

**Files:**
- Modify: `glances/alerts_v5.py` — after `get_ongoing_since` (line 195)
- Test: `tests/test_alerts_v5.py`

**Interfaces:**
- Consumes: `_AlertState.top_counter` / `.top_sort` from Task 2.
- Produces: `get_ongoing_top() -> dict[tuple[str, str | None, str], dict[str, Any]]`, values shaped `{"top": list[str], "top_sort": str}`. Consumed by Tasks 4 and 6.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_alerts_v5.py`:

```python
@pytest.mark.asyncio
async def test_get_ongoing_top_reports_active_incidents_only(tmp_path, monkeypatch, store):
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeTopProcessEngine(_procs("a", "b", "c"))
    alerts = GlancesAlerts(cfg, process_engine=engine)
    plugin = _FakeTopPlugin(store, cfg)

    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})
    assert alerts.get_ongoing_top() == {
        ("faketop", None, "percent"): {"top": ["a", "b", "c"], "top_sort": "cpu_percent"}
    }

    await _run_with_levels(plugin, alerts, {"percent": {"level": "ok", "prominent": True}})
    assert alerts.get_ongoing_top() == {}


@pytest.mark.asyncio
async def test_get_ongoing_top_is_read_only_and_returns_a_fresh_dict(tmp_path, monkeypatch, store):
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    engine = _FakeTopProcessEngine(_procs("a", "b", "c"))
    alerts = GlancesAlerts(cfg, process_engine=engine)
    plugin = _FakeTopPlugin(store, cfg)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})

    first = alerts.get_ongoing_top()
    first.clear()
    assert alerts.get_ongoing_top()  # mutating the copy left the engine alone


@pytest.mark.asyncio
async def test_get_ongoing_top_skips_incidents_with_nothing_accumulated(tmp_path, monkeypatch, store):
    """An annotated field with an empty process list must not appear."""
    cfg = _config_with(tmp_path, monkeypatch, "[alerts]\nmin_duration_seconds=0\n")
    alerts = GlancesAlerts(cfg, process_engine=_FakeTopProcessEngine([]))
    plugin = _FakeTopPlugin(store, cfg)
    await _run_with_levels(plugin, alerts, {"percent": {"level": "warning", "prominent": True}})

    assert alerts.get_ongoing_top() == {}
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `uv run pytest tests/test_alerts_v5.py -q -k get_ongoing_top`
Expected: FAIL — `AttributeError: 'GlancesAlerts' object has no attribute 'get_ongoing_top'`.

- [ ] **Step 3: Implement**

In `glances/alerts_v5.py`, immediately after `get_ongoing_since`:

```python
    def get_ongoing_top(self) -> dict[tuple[str, str | None, str], dict[str, Any]]:
        """Return the accumulated top processes of each active incident.

        Companion to :meth:`get_ongoing_since`, keyed identically and read
        from the same unbounded ``_state``. Values are
        ``{"top": [names], "top_sort": <sort key>}``.

        Exists for the same reason: ``get_history()`` is a bounded ring
        buffer, so a long-running incident eventually loses the opening event
        that carries its ``top``. Tuples with nothing accumulated (no process
        engine, process plugins disabled, field not annotated) are omitted
        rather than reported with an empty list.

        Read-only, allocates a fresh dict, never called from the ingest path.
        """
        result: dict[tuple[str, str | None, str], dict[str, Any]] = {}
        for state_key, state in self._state.items():
            if state.committed_level == "ok" or state.top_counter is None or state.top_sort is None:
                continue
            names = [name for name, _ in state.top_counter.most_common(_TOP_PROCESSES_KEEP)]
            if not names:
                continue
            result[state_key] = {"top": names, "top_sort": state.top_sort}
        return result
```

- [ ] **Step 4: Run the tests and verify they pass**

Run: `uv run pytest tests/test_alerts_v5.py -q`
Expected: all PASS.

- [ ] **Step 5: Stage**

```bash
git add glances/alerts_v5.py tests/test_alerts_v5.py
```

---

### Task 4: Carry `top` through `_derive_incidents`

**Files:**
- Modify: `glances/outputs/curses_renderer_v5.py:576-692` (`_derive_incidents`)
- Test: `tests/test_curses_renderer_v5.py`

**Interfaces:**
- Consumes: `top` / `top_sort` on history events (Task 2); `get_ongoing_top()` output shape (Task 3).
- Produces: `_derive_incidents(history, ongoing=None, ongoing_since=None, ongoing_top=None)`; every incident dict now always has `"top": list[str]` and `"top_sort": str | None`. Consumed by Tasks 5 and 6.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_curses_renderer_v5.py` (near the other `_derive_incidents` tests; `_derive_incidents` must be in the module's import list at the top):

```python
def _evt_top(*args, top=None, top_sort=None, **kwargs):
    """`_evt` plus the top-process keys, which only annotated fields carry."""
    event = _evt(*args, **kwargs)
    if top is not None:
        event["top"] = list(top)
        event["top_sort"] = top_sort
    return event


def test_derive_incidents_carries_top_from_the_opening_event():
    history = [
        _evt_top("2026-08-16T14:02:11+00:00", "cpu", "total", "warning",
                 top=["python3", "chrome"], top_sort="cpu_percent"),
        _evt("2026-08-16T14:03:11+00:00", "cpu", "total", "critical", previous="warning"),
    ]
    incidents = _derive_incidents(history)
    assert len(incidents) == 1
    assert incidents[0]["top"] == ["python3", "chrome"]
    assert incidents[0]["top_sort"] == "cpu_percent"


def test_derive_incidents_defaults_top_to_an_empty_list():
    incidents = _derive_incidents([_evt("2026-08-16T14:02:11+00:00", "fs", "percent", "warning", key="/")])
    assert incidents[0]["top"] == []
    assert incidents[0]["top_sort"] is None


def test_derive_incidents_ongoing_top_overrides_the_history():
    """The engine is the authority for an active incident (spec §5.4)."""
    history = [
        _evt_top("2026-08-16T14:02:11+00:00", "cpu", "total", "warning",
                 top=["stale"], top_sort="cpu_percent"),
    ]
    ongoing = {("cpu", None, "total"): "warning"}
    ongoing_top = {("cpu", None, "total"): {"top": ["fresh", "node"], "top_sort": "cpu_percent"}}
    incidents = _derive_incidents(history, ongoing, None, ongoing_top)
    assert incidents[0]["top"] == ["fresh", "node"]


def test_derive_incidents_ongoing_top_does_not_touch_resolved_incidents():
    history = [
        _evt_top("2026-08-16T14:02:11+00:00", "cpu", "total", "warning",
                 top=["frozen"], top_sort="cpu_percent"),
        _evt("2026-08-16T14:04:11+00:00", "cpu", "total", "ok", previous="warning"),
    ]
    ongoing_top = {("cpu", None, "total"): {"top": ["nope"], "top_sort": "cpu_percent"}}
    incidents = _derive_incidents(history, {}, None, ongoing_top)
    assert incidents[0]["ongoing"] is False
    assert incidents[0]["top"] == ["frozen"]


def test_derive_incidents_synthesized_incident_gets_its_top_from_the_engine():
    """An incident whose events all aged out of the ring buffer."""
    ongoing = {("mem", None, "percent"): "critical"}
    ongoing_top = {("mem", None, "percent"): {"top": ["chrome"], "top_sort": "memory_percent"}}
    incidents = _derive_incidents([], ongoing, None, ongoing_top)
    assert incidents[0]["top"] == ["chrome"]
    assert incidents[0]["top_sort"] == "memory_percent"
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `uv run pytest tests/test_curses_renderer_v5.py -q -k derive_incidents`
Expected: FAIL — `KeyError: 'top'` and `TypeError: _derive_incidents() takes at most 3 arguments`.

- [ ] **Step 3: Implement**

In `glances/outputs/curses_renderer_v5.py`, extend the signature:

```python
def _derive_incidents(
    history: list[dict[str, Any]],
    ongoing: dict[tuple[str, Any, str], str] | None = None,
    ongoing_since: dict[tuple[str, Any, str], str] | None = None,
    ongoing_top: dict[tuple[str, Any, str], dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
```

and add to its docstring, after the `ongoing_since` paragraph:

```
    ``ongoing_top`` is ``GlancesAlerts.get_ongoing_top()`` — the accumulated
    top processes of each ACTIVE incident, and the authority for them for the
    same ring-buffer reason as ``ongoing_since``. Resolved incidents keep the
    value frozen in their opening event.
```

In the opening-incident dict literal, after `"prominent"`:

```python
                "top": list(evt.get("top") or []),
                "top_sort": evt.get("top_sort"),
```

In the synthesized-incident dict literal (the `for state_key, committed in ongoing.items()` loop), after `"prominent": False,`:

```python
                    "top": [],
                    "top_sort": None,
```

And after the `if ongoing_since:` block, before the two sort passes:

```python
    # Same authority argument as `ongoing_since`: for an ACTIVE incident the
    # engine's live accumulator wins over whatever copy the history still
    # holds. Resolved incidents are absent from the map and keep the value
    # frozen in their opening event.
    if ongoing_top:
        for incident in incidents:
            if not incident["ongoing"]:
                continue
            entry = ongoing_top.get((incident["plugin"], incident["key"], incident["field"]))
            if entry:
                incident["top"] = list(entry.get("top") or [])
                incident["top_sort"] = entry.get("top_sort")
```

- [ ] **Step 4: Run the tests and verify they pass**

Run: `uv run pytest tests/test_curses_renderer_v5.py -q`
Expected: all PASS.

- [ ] **Step 5: Stage**

```bash
git add glances/outputs/curses_renderer_v5.py tests/test_curses_renderer_v5.py
```

---

### Task 5: The `TOP` column in the alert grid

Column order is `GLYPH · TIME · DURATION · TARGET · TOP · LEVEL`, so `LEVEL` stays the right-aligned anchor and `row.cells[-1]` still means `LEVEL`.

**Files:**
- Modify: `glances/outputs/curses_renderer_v5.py:695-724` (grid constants), `:794-983` (`render_alert_block`)
- Test: `tests/test_curses_renderer_v5.py`

**Interfaces:**
- Consumes: `incident["top"]` from Task 4.
- Produces: `render_alert_block(..., ongoing_top=None)`; `_ALERT_W_TOP = 22`, `_ALERT_W_WITH_TOP = 66`. Consumed by Task 6.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_curses_renderer_v5.py`:

```python
_TOP_HISTORY = [
    _evt_top("2026-08-16T14:02:11+00:00", "cpu", "total", "critical",
             top=["python3", "chrome", "node"], top_sort="cpu_percent"),
]
_TOP_ONGOING = {("cpu", None, "total"): "critical"}


def test_alert_grid_top_column_sits_between_target_and_level():
    rows = render_alert_block(_TOP_HISTORY, limit=10, now=_GRID_NOW, ongoing=_TOP_ONGOING, width=80)
    header = _line(rows[1])
    assert header.index("TARGET") < header.index("TOP") < header.index("LEVEL")
    data = rows[2]
    assert data.cells[-1].text.strip() == "CRITICAL"
    assert data.cells[-2].text.strip() == "python3, chrome, node"


def test_alert_grid_top_column_drops_first_when_narrow():
    """66 is the threshold; 65 keeps today's exact column set."""
    wide = _line(render_alert_block(_TOP_HISTORY, limit=10, now=_GRID_NOW, ongoing=_TOP_ONGOING, width=66)[1])
    narrow = _line(render_alert_block(_TOP_HISTORY, limit=10, now=_GRID_NOW, ongoing=_TOP_ONGOING, width=65)[1])
    assert "TOP" in wide
    assert "TOP" not in narrow
    assert "LEVEL" in narrow and "DURATION" in narrow


def test_alert_grid_without_any_top_is_byte_identical_to_before():
    """The regression contract: a history with no `top` key must render
    exactly as it did before this feature existed."""
    rows = render_alert_block(_GRID_HISTORY, limit=10, now=_GRID_NOW, ongoing=_GRID_ONGOING, width=80)
    assert "TOP" not in _line(rows[1])
    for row in rows[2:]:
        assert row.cells[-1].text.strip() in {"CRITICAL", "WARNING"}


def test_alert_grid_pads_incidents_that_have_no_top():
    history = _TOP_HISTORY + [
        _evt("2026-08-16T14:01:03+00:00", "fs", "percent", "warning", key="/"),
    ]
    ongoing = dict(_TOP_ONGOING)
    ongoing[("fs", "/", "percent")] = "warning"
    rows = render_alert_block(history, limit=10, now=_GRID_NOW, ongoing=ongoing, width=80)
    data = [_line(r) for r in rows[2:]]
    assert len(data) == 2
    assert len({len(line) for line in data}) == 1


def test_alert_grid_truncates_a_long_top_with_the_ascii_ellipsis():
    history = [
        _evt_top("2026-08-16T14:02:11+00:00", "cpu", "total", "critical",
                 top=["systemd-journald", "containerd-shim", "postgres"], top_sort="cpu_percent"),
    ]
    rows = render_alert_block(history, limit=10, now=_GRID_NOW, ongoing=_TOP_ONGOING,
                              width=80, unicode_ok=False)
    top_cell = rows[2].cells[-2]
    assert len(top_cell.text) == 22
    assert top_cell.text.rstrip().endswith(".")
    assert top_cell.text.isascii()


def test_alert_grid_width_none_sizes_top_to_its_content():
    rows = render_alert_block(_TOP_HISTORY, limit=10, now=_GRID_NOW, ongoing=_TOP_ONGOING)
    assert rows[2].cells[-2].text == "python3, chrome, node"


def test_render_alert_block_forwards_ongoing_top():
    rows = render_alert_block(
        _TOP_HISTORY,
        limit=10,
        now=_GRID_NOW,
        ongoing=_TOP_ONGOING,
        width=80,
        ongoing_top={("cpu", None, "total"): {"top": ["fresh"], "top_sort": "cpu_percent"}},
    )
    assert rows[2].cells[-2].text.strip() == "fresh"
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `uv run pytest tests/test_curses_renderer_v5.py -q -k "top_column or without_any_top or no_top or long_top or width_none_sizes or forwards_ongoing_top"`
Expected: FAIL — no `TOP` header, and `render_alert_block()` rejects `ongoing_top`.

- [ ] **Step 3: Add the geometry constants**

In `glances/outputs/curses_renderer_v5.py`, next to `_ALERT_W_WITH_DURATION`:

```python
_ALERT_W_TOP = 22
# TOP is the FIRST column to drop, so every threshold above is unchanged and
# no terminal that renders the block correctly today changes behaviour.
_ALERT_W_WITH_TOP = _ALERT_W_WITH_LEVEL + 1 + _ALERT_W_TOP  # 66
```

- [ ] **Step 4: Implement the column in `render_alert_block`**

Add the parameter to the signature, after `ongoing_since`:

```python
    ongoing_top: dict[tuple[str, Any, str], dict[str, Any]] | None = None,
```

document it in the docstring `Args:` block:

```
        ongoing_top: ``GlancesAlerts.get_ongoing_top()`` — the accumulated
            top processes of each active incident. Ignored when ``incidents``
            is passed (the caller already applied it while deriving).
```

and forward it:

```python
    if incidents is None:
        incidents = _derive_incidents(history, ongoing, ongoing_since, ongoing_top)
```

Then replace the column-fit block (currently "Which columns fit …" through
`target_width = max(0, target_width)`) with:

```python
    visible = incidents[:limit] if limit > 0 else []

    def target_of(incident: dict[str, Any]) -> str:
        return _humanise_target(incident["plugin"], incident["key"], incident["field"])

    def top_of(incident: dict[str, Any]) -> str:
        return ", ".join(str(name) for name in (incident.get("top") or []))

    # Which columns fit. TARGET is the only elastic one and never drops.
    show_level = width is None or width >= _ALERT_W_WITH_LEVEL
    show_duration = width is None or width >= _ALERT_W_WITH_DURATION
    # TOP is BOTH width-gated and data-conditional: a host whose only alerts
    # are fs or sensors ones never pays 23 columns for an empty header, and a
    # history with no `top` key renders exactly as it did before the column
    # existed.
    show_top = any(top_of(incident) for incident in visible) and (width is None or width >= _ALERT_W_WITH_TOP)
    if width is None:
        top_width = max((len(top_of(incident)) for incident in visible), default=0)
    else:
        top_width = _ALERT_W_TOP

    if width is None:
        target_width = max((len(target_of(i)) for i in visible), default=_ALERT_MIN_TARGET)
        target_width = max(target_width, _ALERT_MIN_TARGET)
    elif show_level:
        target_width = width - (_ALERT_W_WITH_LEVEL - _ALERT_MIN_TARGET)
    elif show_duration:
        target_width = width - (_ALERT_W_WITH_DURATION - _ALERT_MIN_TARGET)
    else:
        target_width = width - _ALERT_MIN_TARGET
    if show_top and width is not None:
        # The painter's one-space separator plus the column itself.
        target_width -= top_width + 1
    target_width = max(0, target_width)
```

Note the `visible` / `target_of` definitions move **above** the column-fit
block; delete the originals further down so they are not defined twice.

In the header row, between the `TARGET` and `LEVEL` cells:

```python
    if show_top:
        header_cells.append(Cell(text=_fit_text("TOP", top_width), color=ColorRole.HEADER, bold=True))
```

In the per-incident row, between the `TARGET` and `LEVEL` cells:

```python
        if show_top:
            cells.append(
                Cell(text=_fit_text(top_of(incident), top_width, ellipsis="…" if unicode_ok else "."))
            )
```

- [ ] **Step 5: Update `_alert_block_height`'s docstring**

No code change — one row per incident is preserved — but state it, so a
future reader does not go looking:

```python
    Adding the TOP column (spec §7.3) changed the block's WIDTH only: still
    one row per incident, so this cost function is unchanged.
```

- [ ] **Step 6: Run the tests and verify they pass**

Run: `uv run pytest tests/test_curses_renderer_v5.py -q`
Expected: all PASS, including every pre-existing alert-grid test (they use
`_evt()`, which carries no `top`, so `show_top` is False for all of them).

- [ ] **Step 7: Stage**

```bash
git add glances/outputs/curses_renderer_v5.py tests/test_curses_renderer_v5.py
```

---

### Task 6: Wire `ongoing_top` from the engine to the frame

**Files:**
- Modify: `glances/outputs/curses_renderer_v5.py:1303-1332` (`build_frame` signature + docstring), `:1435` (the `_derive_incidents` call)
- Modify: `glances/outputs/glances_curses_v5.py:537-556`
- Test: `tests/test_curses_renderer_v5.py`

**Interfaces:**
- Consumes: `get_ongoing_top()` (Task 3), `_derive_incidents(..., ongoing_top)` (Task 4).
- Produces: `build_frame(..., alerts_ongoing_top: dict | None = None)`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_curses_renderer_v5.py`. The empty
`build_frame({}, {}, [], alerts_history=...)` shape is already used by a
neighbouring test in this file, so it is known to work:

```python
def test_build_frame_passes_ongoing_top_to_the_alert_block():
    frame = build_frame(
        store_snapshot={},
        fields_by_plugin={},
        registry=[],
        alerts_history=_TOP_HISTORY,
        alerts_ongoing=_TOP_ONGOING,
        alerts_ongoing_top={("cpu", None, "total"): {"top": ["fresh"], "top_sort": "cpu_percent"}},
        view={"right_width": 80, "unicode": True},
    )
    alert_block = next(b for b in frame.right if b.name == "alert")
    assert any("fresh" in _line(row) for row in alert_block.rows)
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `uv run pytest tests/test_curses_renderer_v5.py -q -k build_frame_passes_ongoing_top`
Expected: FAIL — `build_frame() got an unexpected keyword argument 'alerts_ongoing_top'`.

- [ ] **Step 3: Extend `build_frame`**

Add the parameter after `alerts_ongoing_since`:

```python
    alerts_ongoing_top: dict[tuple[str, Any, str], dict[str, Any]] | None = None,
```

document it in the `Args:` block:

```
        alerts_ongoing_top: output of `GlancesAlerts.get_ongoing_top()` — the
            accumulated top processes of each active incident.
```

and pass it at the single derivation point:

```python
    alert_incidents = _derive_incidents(
        alerts_history, alerts_ongoing, alerts_ongoing_since, alerts_ongoing_top
    )
```

`render_alert_block` still receives `incidents=alert_incidents`, so it needs
no new argument here.

- [ ] **Step 4: Read the engine in the TUI loop**

In `glances/outputs/glances_curses_v5.py`, after the `ongoing_since` line:

```python
        # The accumulated top processes of each active alert. Same
        # ring-buffer argument as `ongoing_since`: the engine outlives the
        # history entry that carries them.
        ongoing_top = self.alerts.get_ongoing_top() if self.alerts is not None else {}
```

and add to the `build_frame(...)` call, after `alerts_ongoing_since=ongoing_since,`:

```python
            alerts_ongoing_top=ongoing_top,
```

- [ ] **Step 5: Run the tests and verify they pass**

Run: `uv run pytest tests/test_curses_renderer_v5.py tests/test_curses_v5.py -q`
Expected: all PASS.

- [ ] **Step 6: Stage**

```bash
git add glances/outputs/curses_renderer_v5.py glances/outputs/glances_curses_v5.py \
        tests/test_curses_renderer_v5.py
```

---

### Task 7: Verify the API surface, the regression watch list, and close the phase

No new route or adapter code: `GET /api/5/alert` (`glances/routes_v5.py:142`)
and the synthetic MCP `alert` plugin (`glances/outputs/mcp_adapter_v5.py:204`)
both return `get_history()` and inherit the keys. This task PROVES that and
clears spec §12.

**Files:**
- Test: `tests/test_routes_v5.py`
- Possibly modify: nothing (this task may end with production code untouched)

**Interfaces:**
- Consumes: everything above.
- Produces: nothing new.

- [ ] **Step 1: Write the API test**

Append to `tests/test_routes_v5.py`, following that file's existing app /
client fixture pattern. The point is that no route code had to change:

```python
def test_alert_route_exposes_top_processes(...):
    """`/api/5/alert` returns `get_history()` verbatim, so the top-process
    keys added by the alert engine reach the API with no route change."""
    # Seed the app's alerts engine with one incident whose opening event
    # carries `top` / `top_sort`, then:
    payload = client.get("/api/5/alert").json()
    assert payload[0]["top"] == ["python3", "chrome", "node"]
    assert payload[0]["top_sort"] == "cpu_percent"
```

- [ ] **Step 2: Run it, make it pass**

Run: `uv run pytest tests/test_routes_v5.py -q`
Expected: PASS with **no change to `glances/routes_v5.py`**. If it fails,
the failure is real and belongs in this task — do not patch the route to
paper over it.

- [ ] **Step 3: Clear spec §12 — the schema key must be inert**

Check whether `fields_description` is echoed by a description/limits route or
an MCP tool schema, and whether `top_processes_sort` now leaks into it:

```bash
grep -rn "fields_description\|fields_by_plugin" glances/routes_v5.py glances/outputs/mcp_adapter_v5.py
uv run pytest tests/test_routes_v5.py tests/test_mcp_adapter_v5.py tests/test_plugin_base_v5.py -q
```

If the key does surface, that is acceptable (it is descriptive metadata like
`watch_direction`) — record it in the phase notes. If any test asserts an
exact key set, that assertion needs updating, and that is the only production
decision this step may produce.

- [ ] **Step 4: Confirm the direct-caller path still works**

`_derive_incidents` is called by export and by tests with `ongoing_top=None`.

Run: `uv run pytest tests/test_export_base_v5.py tests/test_export_json_v5.py tests/test_export_csv_v5.py -q`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -q`
Expected: no new failures. `tests/test_restful.py::test_050/051` is flaky by
construction (a hard-coded `time.sleep(5)` against a subprocess server) —
re-run it before investigating, and never bisect on it.

- [ ] **Step 6: Run the pre-commit hooks**

```bash
git add -A
make pre-commit
```

gitleaks scans the **index**, so if a hook reformats anything, `git add` the
result and re-run `make pre-commit` until it is clean.

- [ ] **Step 7: Stage and stop**

```bash
git add -A
git status --short
```

**Do not commit.** Report to the maintainer: what is staged, the full-suite
count, and the manual TUI smoke still owed (below).

- [ ] **Step 8: Hand over the manual smoke checklist**

The maintainer runs these; the agent does not:

1. `python -m glances.main_v5` on a wide terminal, put the box under CPU load
   (`stress-ng --cpu 4` or a build), wait for the `Cpu total` alert, and check
   the `TOP` column names the load generator.
2. Shrink the terminal until the alert block drops below 66 columns — `TOP`
   must vanish and `LEVEL` / `DURATION` must stay.
3. Let the alert resolve; the row's `TOP` must freeze rather than clear.
4. `curl -s localhost:61208/api/5/alert | jq '.[0]'` — `top` and `top_sort`
   present on the opening event, absent on an `fs` alert.

---

## Self-Review

**Spec coverage**

| Spec section | Task |
|---|---|
| §4 declaration mechanism + 5-field allowlist | 1 |
| §5.1 state fields | 2 |
| §5.2 lifecycle (open / escalate / close) | 2 |
| §5.3 accumulation, depth, per-cycle sort cache, empty list | 2 |
| §5.4 `get_ongoing_top()` | 3 |
| §6 payload keys, absence semantics | 2 (written), 7 (proven end-to-end) |
| §7.1 column, content, colour, data-conditional | 5 |
| §7.2 shrink ladder, 66 threshold | 5 |
| §7.3 vertical budget unchanged | 5 (docstring), asserted by existing tests |
| §8 plumbing | 4, 6 |
| §9 cost (lazy per-cycle cache) | 2 |
| §10 tests | 2, 3, 4, 5, 6, 7 |
| §12 regression watch | 7 |

**Type consistency** — names used identically across tasks:
`top_processes_sort` (schema key), `top` / `top_sort` (payload + incident
keys), `get_ongoing_top()` returning `{state_key: {"top": [...], "top_sort":
...}}`, `_AlertState.top_counter` / `.top_sort` / `.top_event`,
`_derive_incidents(history, ongoing, ongoing_since, ongoing_top)`,
`build_frame(..., alerts_ongoing_top=...)`, `render_alert_block(...,
ongoing_top=...)`, `_ALERT_W_TOP` / `_ALERT_W_WITH_TOP`,
`_TOP_PROCESSES_SAMPLE` / `_TOP_PROCESSES_KEEP`.

**Verified while writing this plan** (do not re-check):
- all four `model_v5.py` files export the class `PluginModel`;
- `tests/test_curses_renderer_v5.py` already imports `_derive_incidents`,
  `build_frame` and `render_alert_block`, so Tasks 4-6 add no imports;
- the existing alert-grid tests render at `width=61` (< 66) or with events
  built by `_evt()` (no `top` key), so `show_top` is False for every one of
  them — this is why Task 5 is a strict addition.

**One assumption left to verify at execution time:**
- the app/client fixture shape in `tests/test_routes_v5.py` (Task 7, Step 1).
