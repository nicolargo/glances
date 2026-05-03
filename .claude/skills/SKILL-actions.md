# Skill: Glances v5 — Authoring an alert action (`GlancesActionBase`)

Use the v5 action base class (`glances.actions_v5.GlancesActionBase`) to add
a new alert action type to `develop-v5`. Actions are auto-discovered from
the `glances.actions_v5` package — adding one means dropping a single file,
no changes to any core module.

The v4 module `glances/actions.py` is kept untouched during the transition.

## When does an action run?

Actions are triggered by `GlancesAlerts` (architecture §3.4) when a plugin's
`_levels` indicates a threshold crossing. `GlancesAlerts` lands in Phase 1.
Phase 0 ships only the base class and the discovery mechanism — there are
**zero concrete actions** in the v5 codebase yet (no dead code).

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

That's it. The class is auto-discovered. As soon as `GlancesAlerts` ships
in Phase 1, the action becomes available as
`<level>_webhook=<url>` in any plugin section of `glances.conf`.

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

## Mustache rendering (deferred — Phase 1)

The architecture (§3.4.1) specifies that `action_value` is a Mustache
template rendered against `context` using the `chevron` library, with
built-in variables `_glances_hostname`, `_glances_plugin`,
`_glances_level`, `_glances_timestamp`. **Phase 0 does not implement
rendering** — `GlancesAlerts` (Phase 1) will inject the rendered string
into `execute()` or pass `chevron.render` into the context. The contract
above shows `action_value: str` deliberately as the raw value for now.

## Shell escaping (CVE-2026-32608)

The `shell` action (Phase 1) is required to shell-escape every Mustache
substitution before exec. This is the responsibility of the concrete
`ShellAction` implementation, **not** of the base class.

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

- **Concrete actions** (`shell`, `apprise`, `llm`) — Phase 1 alongside `GlancesAlerts`
- **Mustache rendering** of `action_value` — Phase 1 (in `GlancesAlerts` or in each action)
- **Shell escaping** — Phase 1 (in `shell` action)
- **Per-action timeout / retry** — Phase 1
- **Apprise URL globalisation** (`[outputs] apprise_url=...`) — Phase 1
- **Action triggering by `GlancesAlerts`** — Phase 1 (no caller exists yet)

## Module path

```
glances/actions_v5/__init__.py        # re-exports GlancesActionBase + discover_actions
glances/actions_v5/action_base.py     # base class + discovery
tests/test_action_base_v5.py          # contract + discovery tests
```

Concrete actions ship as sub-packages: `glances/actions_v5/<name>/__init__.py`.

The v4 module `glances/actions.py` is **not modified**, **not imported**,
**not subclassed** by v5. The two systems coexist through Phase 0 → Phase
N. At the end of the transition the `_v5` suffix is dropped (the package
becomes `glances/actions/`).
