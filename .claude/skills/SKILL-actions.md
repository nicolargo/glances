# Skill: Glances v5 — Authoring an alert action (`GlancesActionBase`)

Use the v5 action base class (`glances.actions_v5.GlancesActionBase`) to add
a new alert action type to `develop-v5`. Actions are auto-discovered from
the `glances.actions_v5` package — adding one means dropping a single file,
no changes to any core module.

The v4 module `glances/actions.py` is kept untouched during the transition.

## When does an action run?

Actions are triggered by `GlancesAlerts` (architecture §3.4, module
`glances/alerts_v5.py`) when a plugin's `_levels` indicates a level
transition. The scheduler calls `alerts.ingest_plugin(plugin)` after
every plugin update; the alert engine debounces transitions with a
configurable hysteresis (``[alerts] min_duration_seconds=N``, default
``5.0 s``), then dispatches every configured action **fire-and-forget**
via `asyncio.create_task`. The monitoring loop never blocks on an
action.

Concrete actions shipped:

| Package | `action_name` | Status |
|---|---|---|
| `glances/actions_v5/shell/` | `action` (matches v4 `_action` keys) | Phase 1.4 ✅ |
| `glances/actions_v5/apprise/` | `apprise` | Phase 1.5 (deferred) |
| `glances/actions_v5/llm/` | `llm` | Phase 2 (deferred) |

## Action contract

```python
from glances.actions_v5 import GlancesActionBase


class WebhookAction(GlancesActionBase):
    """POST the alert context to a webhook URL.

    Config: [mem] critical_webhook=https://hooks.example.com/alert
    """

    action_name = "webhook"   # → key suffix in glances.conf
    requires = []             # → optional Python module names

    async def execute(
        self,
        plugin_name: str,
        level: str,           # "careful" | "warning" | "critical"
        context: dict,        # plugin.get_export() + built-in vars
        action_value: str,    # raw value from glances.conf
        repeat: bool = False, # True if the alert is repeating
    ) -> None:
        import httpx          # lazy import — already a v5 core dep
        async with httpx.AsyncClient() as client:
            await client.post(action_value, json=context, timeout=5.0)
```

That's it. The class is auto-discovered and immediately available as
`<level>_webhook=<url>` in any plugin section of `glances.conf` —
`GlancesAlerts` resolves the key with 3-level precedence and dispatches
the action when a transition fires (see "Config key precedence" below).

## Optional dependencies (`requires`)

If your action needs a module that is **not** a core v5 dependency (for
example `apprise`), declare it in `requires`:

```python
class AppriseAction(GlancesActionBase):
    action_name = "apprise"
    requires = ["apprise"]

    async def execute(self, plugin_name, level, context, action_value, repeat=False):
        import apprise
        ...
```

At discovery time `is_available()` checks each module via
`importlib.util.find_spec`. Missing modules → action is skipped with a
WARNING log. **Glances always starts**, even if every optional action is
unavailable.

## Auto-discovery

```python
from glances.actions_v5 import discover_actions

registry = discover_actions()
# → {"shell": ShellAction(), "apprise": AppriseAction(), ...}
```

Discovery walks the `glances.actions_v5` package via `pkgutil.iter_modules`
and instantiates every concrete subclass of `GlancesActionBase`. Failure
modes are deliberately defensive:

| Situation | Behaviour |
|---|---|
| Module import raises | WARNING log, skip — Glances starts |
| `is_available()` returns False | WARNING log, skip — action unavailable |
| `action_name` is empty | `ValueError` at instantiation (loud) |
| Two actions share the same `action_name` | `ValueError` at discovery (loud) |
| Re-exported class from another module | Ignored (only register classes defined in their own module) |

## Mustache rendering

`action_value` is the **raw** template string from `glances.conf`.
`GlancesAlerts` does not pre-render it — each action renders the
template itself using the `chevron` library (already a core
dependency). This lets different action types pick the right escape
strategy:

| Action type | Escape strategy |
|---|---|
| `shell` (`ShellAction`) | `shlex.quote()` every context value before `chevron.render` — defeats CVE-2026-32608 shell injection. |
| `apprise` (future) | No escape — body sent as opaque text. |
| `webhook` (future) | JSON-encode context — pass to body, not URL. |

`context` is `plugin.get_export()` output (for the matching item, for
collections) plus four built-in variables:

| Variable | Value |
|---|---|
| `{{_glances_hostname}}` | Hostname of the Glances instance |
| `{{_glances_plugin}}` | Plugin name (e.g. `mem`, `network`) |
| `{{_glances_level}}` | Alert level (`careful` / `warning` / `critical`) |
| `{{_glances_timestamp}}` | ISO 8601 UTC timestamp of the firing |

## Config key precedence — 3 levels

`GlancesAlerts` resolves each action key against three patterns,
walking from most-specific to least-specific and firing the **first
non-empty** value:

1. ``<pk_value>_<field>_<level>_<action_name>[_repeat]``  (collection items only)
2. ``<field>_<level>_<action_name>[_repeat]``
3. ``<level>_<action_name>[_repeat]``

Example for the `network` plugin (pk = `interface_name`):

```ini
[network]
critical_action=logger "ANY field on ANY iface"
bytes_recv_warning_action=logger "bytes_recv only, any iface"
wlan0_bytes_recv_warning_action=ifconfig wlan0 down
```

The same precedence applies to thresholds (see SKILL-plugin.md).

## Firing semantics

- **Non-repeat** (``<level>_<action>``): fires once, on transition
  entry into a non-ok level.
- **`_repeat`** (``<level>_<action>_repeat``): fires every refresh
  cycle while the committed level stays non-ok (matches v4). Entry
  cycle fires both keys if both are configured.
- **Resolution** (any → `ok`): event recorded in history, no action
  fired. Use `_repeat` for "still failing" reminders.

## Fire-and-forget dispatch

`GlancesAlerts` schedules `action.execute()` via `asyncio.create_task`
— the scheduler never waits. Action failures are caught by
`GlancesAlerts` and logged at WARNING with `plugin_name`, `level`,
`repeat`. Well-behaved actions log their own failures with full
context and return normally; do not raise to signal failure.

## Testing an action

Test stack: `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`) +
`unittest.mock` (architecture decision §9). Style: pytest-native top-level
functions with fixtures and `assert` statements.

Pattern: instantiate the action directly, call `await
action.execute(...)`, assert on side effects (HTTP mock, subprocess mock,
written file…).

For discovery tests: build a fake action package on disk via `tmp_path`,
add it to `sys.path` with `monkeypatch.syspath_prepend`, then call
`discover_actions("fake_pkg_name")`. See `tests/test_action_base_v5.py`
for the reference fixture.

## What's deferred (out of scope for new actions today)

- **Apprise action** (multi-service notifications) — Phase 1.5
- **LLM action** (LiteLLM health reports) — Phase 2
- **Per-action timeout / retry** — Phase 2
- **Apprise URL globalisation** (`[outputs] apprise_url=...`) — Phase 1.5
- **Resolution-event actions** (fire on transition to `ok`) — not planned

## Module path

```
glances/actions_v5/__init__.py        # re-exports GlancesActionBase + discover_actions
glances/actions_v5/action_base.py     # base class + discovery
glances/actions_v5/shell/__init__.py  # concrete shell action (Phase 1.4)
glances/alerts_v5.py                  # GlancesAlerts — schedules action.execute()
tests/test_action_base_v5.py          # base class + discovery tests
tests/test_action_shell_v5.py         # shell action tests
tests/test_alerts_v5.py               # state machine + dispatch tests
```

Concrete actions ship as sub-packages: `glances/actions_v5/<name>/__init__.py`.

The v4 module `glances/actions.py` is **not modified**, **not imported**,
**not subclassed** by v5. The two systems coexist through Phase 0 → Phase
N. At the end of the transition the `_v5` suffix is dropped (the package
becomes `glances/actions/`).
