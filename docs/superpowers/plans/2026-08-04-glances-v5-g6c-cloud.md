# Glances v5 — G6C `cloud` port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the v4 `cloud` plugin (OpenStack / EC2 instance metadata) to v5, replacing its two pointless daemon threads with a single cached async probe.

**Architecture:** `model_v5.py` is a scalar plugin (`DISABLED_BY_DEFAULT = True`). `_grab_stats()` probes the link-local metadata service **once** on the first cycle and caches the result for the process lifetime — cloud metadata is static, and this is what v4 actually does despite its threads' misleading "Infinite loop" docstring. The probe uses `requests` behind `asyncio.to_thread`, the pattern already used by `ports`, `npu`, `mpp` and `irq`; `httpx` was considered and rejected (spec §4.1b). Vanilla OpenStack is tried first, EC2 only if vanilla yields nothing. A `render_curses_v5.py` puts the one-line banner in the header slot next to `uptime`, matching v4.

**Tech Stack:** Python, `requests` + `asyncio.to_thread`, `glances/plugins/plugin/base_v5.py`, pytest

**Spec:** `docs/superpowers/specs/2026-08-04-glances-v5-g6c-design.md` §4

## Global Constraints

- **Never commit, push, or open a PR.** Every task ends with `git add` only. Never add a `Co-Authored-By` trailer.
- **Do not touch `NEWS.rst`.**
- Run `make pre-commit` before staging each task — not just `make lint && make format`. Treat a failure as blocking. gitleaks scans the **git index**, so `git add` before re-running it.
- Full v5 suite must stay green: `make test-v5`.
- SPDX header on every new file (see `glances/plugins/npu/model_v5.py:1-7`); `from __future__ import annotations` in every new module and test.
- `DISABLED_BY_DEFAULT = True` — v4 ships `[cloud] disable=True`. Do not change the default.
- **No test may touch the network.** Every HTTP interaction is mocked. A test that would reach `169.254.169.254` is a defect.
- **The metadata URLs are hard-coded and MUST NOT become configurable** (spec §4.3). No config key may influence host, scheme, port or path. Making the endpoint configurable would reintroduce an SSRF.

---

### Task 1: `model_v5.py` — cached one-shot async probe

**Files:**
- Create: `glances/plugins/cloud/model_v5.py`
- Test: `tests/test_plugin_cloud_v5.py`

**Interfaces:**
- Produces: `glances.plugins.cloud.model_v5.PluginModel`, a `GlancesPluginBase[dict]` with `plugin_name = "cloud"`. Published payload: `{"platform": str, "id": str, "name": str, "type": str, "region": str}` — or `{}` when no metadata service answered.
- Module constant `PROVIDERS: tuple[_Provider, ...]` describing the two probes, in priority order.

**`pyproject.toml` is NOT touched.** The `cloud` extra already reads
`cloud = ["requests"]` and stays that way. Do not add `httpx`: it is only a
transitive dependency of FastAPI's `TestClient`, no v5 code imports it, and
adding it here would make `cloud` the only v5 plugin using a second HTTP
client (spec §4.1b).

**Semantics to preserve verbatim from v4:**

- **All-or-nothing.** v4 uses a `for…else`: a single failed request `break`s out and leaves `platform` unset. Only when *every* key of a provider's map resolved is `platform` set. Partial results are discarded.
- **Probe order.** Vanilla OpenStack first; EC2 only if vanilla produced nothing (v4 `update()`: `stats = self.OPENSTACK.stats; if not stats: stats = self.OPENSTACKEC2.stats`).
- **No retry.** v4's threads run once and die. `_fetched` is set **before** awaiting so a failure is never retried on a later cycle.
- **Timeout 3 s**, as v4.
- **Suppress partial payloads.** v4 hides the display when `platform` or `name` is missing (#2485). v5 enforces this at the data layer: publish `{}`, so a partial dict never reaches `/api/5/cloud` either.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_plugin_cloud_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Unit tests for the v5 ``cloud`` plugin model.

No test may perform real network I/O — every probe is stubbed.

See docs/superpowers/specs/2026-08-04-glances-v5-g6c-design.md §4
"""

from __future__ import annotations

import asyncio

from glances.plugins.cloud.model_v5 import PROVIDERS, PluginModel

OPENSTACK_OK = {
    "project_id": "proj-42",
    "name": "my-vm",
    "meta/role": "gold",
    "availability_zone": "eu-west-1a",
}
EC2_OK = {
    "ami-id": "ami-123",
    "instance-id": "i-abc",
    "instance-type": "t3.micro",
    "placement/availability-zone": "us-east-1b",
}


class _FakeResponse:
    def __init__(self, ok: bool, text: str):
        self.ok = ok
        self.text = text


class _FakeRequests:
    """Minimal `requests` module stand-in driven by a {path: body} map."""

    def __init__(self, responses: dict[str, str], record: list[str] | None = None):
        self._responses = responses
        self.record = record if record is not None else []

    def get(self, url: str, timeout: int | None = None):
        self.record.append(url)
        for path, body in self._responses.items():
            if url.endswith("/" + path):
                return _FakeResponse(True, body)
        return _FakeResponse(False, "")


def _install(monkeypatch, responses, record=None):
    """Swap the module-level `requests` for a stub. No network, ever."""
    monkeypatch.setattr(
        "glances.plugins.cloud.model_v5.requests",
        _FakeRequests(responses, record),
    )


def test_providers_are_ordered_openstack_then_ec2():
    assert [p.platform for p in PROVIDERS] == ["OpenStack", "Amazon EC2"]


def test_urls_are_link_local_and_not_configurable(store_with, config_with):
    """Spec §4.3: no config key may influence the endpoint."""
    for provider in PROVIDERS:
        assert provider.url.startswith("http://169.254.169.254/")
    # A config section for the plugin must not change anything.
    plugin = PluginModel(store_with(), config_with({"cloud": {"url": "http://evil.example"}}))
    assert all(p.url.startswith("http://169.254.169.254/") for p in PROVIDERS)
    assert not hasattr(plugin, "url")


def test_openstack_success(store_with, config_with, monkeypatch):
    _install(monkeypatch, OPENSTACK_OK)
    plugin = PluginModel(store_with(), config_with({}))
    stats = asyncio.run(plugin._grab_stats())
    assert stats == {
        "platform": "OpenStack",
        "id": "proj-42",
        "name": "my-vm",
        "type": "gold",
        "region": "eu-west-1a",
    }


def test_falls_back_to_ec2_when_openstack_is_silent(store_with, config_with, monkeypatch):
    _install(monkeypatch, EC2_OK)
    plugin = PluginModel(store_with(), config_with({}))
    stats = asyncio.run(plugin._grab_stats())
    assert stats["platform"] == "Amazon EC2"
    assert stats["name"] == "i-abc"
    assert stats["region"] == "us-east-1b"


def test_partial_metadata_is_discarded(store_with, config_with, monkeypatch):
    """v4 uses for/else: one missing key means no platform, hence no payload."""
    partial = dict(OPENSTACK_OK)
    del partial["availability_zone"]
    _install(monkeypatch, partial)
    plugin = PluginModel(store_with(), config_with({}))
    assert asyncio.run(plugin._grab_stats()) == {}


def test_no_metadata_service_yields_empty_dict(store_with, config_with, monkeypatch):
    _install(monkeypatch, {})
    plugin = PluginModel(store_with(), config_with({}))
    assert asyncio.run(plugin._grab_stats()) == {}


def test_transport_error_yields_empty_dict(store_with, config_with, monkeypatch):
    class _Boom(_FakeRequests):
        def get(self, url, timeout=None):
            raise OSError("network unreachable")

    monkeypatch.setattr("glances.plugins.cloud.model_v5.requests", _Boom({}))
    plugin = PluginModel(store_with(), config_with({}))
    assert asyncio.run(plugin._grab_stats()) == {}


def test_second_cycle_issues_no_request_at_all(store_with, config_with, monkeypatch):
    """The core claim: metadata is fetched once and cached for the process."""
    record: list[str] = []
    _install(monkeypatch, OPENSTACK_OK, record)
    plugin = PluginModel(store_with(), config_with({}))
    first = asyncio.run(plugin._grab_stats())
    calls_after_first = len(record)
    assert calls_after_first > 0
    second = asyncio.run(plugin._grab_stats())
    assert len(record) == calls_after_first, "a second cycle must not re-probe"
    assert second == first


def test_a_failed_probe_is_not_retried(store_with, config_with, monkeypatch):
    record: list[str] = []
    _install(monkeypatch, {}, record)
    plugin = PluginModel(store_with(), config_with({}))
    asyncio.run(plugin._grab_stats())
    calls_after_first = len(record)
    asyncio.run(plugin._grab_stats())
    assert len(record) == calls_after_first, "failures must not be retried either"


def test_missing_requests_degrades_to_empty(store_with, config_with, monkeypatch):
    monkeypatch.setattr("glances.plugins.cloud.model_v5.requests", None)
    plugin = PluginModel(store_with(), config_with({}))
    assert asyncio.run(plugin._grab_stats()) == {}


def test_published_payload_is_empty_when_nothing_resolved(store_with, config_with, monkeypatch):
    _install(monkeypatch, {})
    store = store_with()
    plugin = PluginModel(store, config_with({}))
    asyncio.run(plugin.update())
    payload = store.get("cloud")
    assert payload is not None
    assert payload.get("platform") is None


def test_class_flags():
    assert PluginModel.plugin_name == "cloud"
    assert PluginModel.IS_COLLECTION is False
    assert PluginModel.EMITS_ALERTS is False
    assert PluginModel.DISABLED_BY_DEFAULT is True
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_plugin_cloud_v5.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glances.plugins.cloud.model_v5'`

- [ ] **Step 3: Write the implementation**

Create `glances/plugins/cloud/model_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — Cloud plugin (scalar).

Identifies the cloud instance the host runs on by querying the link-local
metadata service. Migrated from `glances/plugins/cloud/__init__.py`.

**One shot, then cached.** v4 spawns two daemon threads whose `run()`
docstring claims an infinite loop; the body has none — each walks its
metadata keys once and returns. Cloud metadata is static, so that is the
correct behaviour with a misleading implementation. Here the probe runs on
the first cycle and the result (success *or* failure) is cached for the
process lifetime.

**Blocking client, off the loop.** `requests` is the HTTP client already used
by every other v5 plugin that speaks HTTP (`ports`, `containers`, the `nginx`
AMP), so no new dependency is introduced. It blocks, and off-cloud the probe
burns four 3-second timeouts, so it runs inside `asyncio.to_thread` — the same
pattern as `ports`, `npu`, `mpp` and `irq`. The cost is paid once at startup,
never per cycle. See the design spec §4.1b for why `httpx` was rejected here.

**Security.** The endpoints are hard-coded link-local addresses and must
never become configurable: a config-controlled URL here is an SSRF
primitive. See the design spec §4.3.

**Default-disabled**: v4 ships `[cloud] disable=True`.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar, NamedTuple

from glances.plugins.plugin.base_v5 import GlancesPluginBase

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 3


class _Provider(NamedTuple):
    """One metadata service: its platform label, base URL and key map.

    `metadata` maps the published field name to the path appended to `url`;
    the response body becomes the field value.
    """

    platform: str
    url: str
    metadata: dict[str, str]


# Order matters: vanilla OpenStack is probed first, EC2 only if it is silent
# (v4 `update()`: `stats = OPENSTACK.stats; if not stats: stats = EC2.stats`).
PROVIDERS: tuple[_Provider, ...] = (
    _Provider(
        platform="OpenStack",
        url="http://169.254.169.254/openstack/latest/meta-data",
        metadata={
            "id": "project_id",
            "name": "name",
            "type": "meta/role",
            "region": "availability_zone",
        },
    ),
    _Provider(
        platform="Amazon EC2",
        url="http://169.254.169.254/latest/meta-data",
        metadata={
            "id": "ami-id",
            "name": "instance-id",
            "type": "instance-type",
            "region": "placement/availability-zone",
        },
    ),
)


class PluginModel(GlancesPluginBase[dict]):
    """Cloud instance identification (scalar)."""

    plugin_name: ClassVar[str] = "cloud"
    IS_COLLECTION: ClassVar[bool] = False
    EMITS_ALERTS: ClassVar[bool] = False
    # Mirrors v4 `[cloud] disable=True`.
    DISABLED_BY_DEFAULT: ClassVar[bool] = True

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "platform": {"description": "Cloud platform name (e.g. OpenStack).", "unit": "string"},
        "id": {"description": "Cloud instance identifier.", "unit": "string"},
        "name": {"description": "Cloud instance name.", "unit": "string"},
        "type": {"description": "Cloud instance type / flavour.", "unit": "string"},
        "region": {"description": "Cloud availability zone or region.", "unit": "string"},
    }

    def __init__(self, store: Any, config: Any) -> None:
        super().__init__(store, config)
        self._fetched = False
        self._cached: dict[str, Any] = {}

    def _probe_provider(self, provider: _Provider) -> dict[str, Any]:
        """Resolve every key of one provider, or return {}.

        All-or-nothing, and **stricter than v4 on purpose**: v4 breaks out
        only on a raised exception, so a plain 404 just skips that key and
        its `for…else` still sets `platform` on a partial dict. Discarding
        the whole provider is what keeps a partial payload out of
        `/api/5/cloud`.

        This is also the provider's own failure domain: an exception is
        caught here and treated like a non-ok response, so the caller can
        still try the next provider. Handling it one level up would let a
        single transient OpenStack timeout permanently mask an EC2
        instance, because `_fetched` latches on the first cycle.
        """
        out: dict[str, Any] = {}
        try:
            for field, path in provider.metadata.items():
                response = requests.get(f"{provider.url}/{path}", timeout=_TIMEOUT_SECONDS)
                if not response.ok:
                    return {}
                out[field] = response.text.strip()
        except Exception as exc:  # noqa: BLE001 — no metadata service is the norm
            logger.debug("cloud: %s probe failed: %s", provider.platform, exc)
            return {}
        out["platform"] = provider.platform
        return out

    def _probe_sync(self) -> dict[str, Any]:
        """Blocking probe of every provider in order. Runs in a worker thread."""
        for provider in PROVIDERS:
            found = self._probe_provider(provider)
            if found:
                return found
        return {}

    async def _grab_stats(self) -> dict:
        if self._fetched:
            return self._cached
        # Set before awaiting: a failed probe must not be retried on every
        # cycle, matching v4 where a dead thread never retries.
        self._fetched = True

        if requests is None:
            logger.debug("cloud: requests is not installed, plugin stays empty")
            return self._cached

        # requests blocks; off-cloud this is 4 x 3s of timeouts. Keep it
        # off the event loop.
        self._cached = await asyncio.to_thread(self._probe_sync)
        return self._cached
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_plugin_cloud_v5.py -v`
Expected: PASS (12 tests)

- [ ] **Step 5: Run the full v5 suite**

Run: `make test-v5`
Expected: no new failures.

- [ ] **Step 6: Pre-commit, then stage**

```bash
git add glances/plugins/cloud/model_v5.py tests/test_plugin_cloud_v5.py
make pre-commit
```

`pyproject.toml` must **not** appear in the staged set for this task.

If a hook rewrites a file, `git add` again and re-run. Do **not** commit.

---

### Task 2: `render_curses_v5.py` + header slot registration

**Files:**
- Create: `glances/plugins/cloud/render_curses_v5.py`
- Modify: `glances/outputs/curses_renderer_v5.py:59` — `HEADER_SLOT_RIGHT`
- Test: `tests/test_plugin_cloud_v5.py` (append)

**Interfaces:**
- Consumes: the scalar payload from Task 1.
- Produces: `render(payload, fields_desc) -> list[Row]`. The renderer module is discovered automatically from its path; **only the slot registration is manual.**

v4 reference (`glances/plugins/cloud/__init__.py::msg_curse`): the platform name as a TITLE cell, then `" <type> instance <name> (<region>)"` as a plain cell, with `Unknown` substituted for any missing part. Nothing is rendered when `platform` or `name` is absent — Task 1 already guarantees that by publishing `{}`.

**Slot placement.** v4 paints `uptime` then `cloud` in the header's right-hand region (`glances/outputs/glances_curses.py:720-726`). v5's `HEADER_SLOT_RIGHT` is `("uptime", "now")` and its comment states `now` closes the banner on the far right. Insert `cloud` between them:

```python
HEADER_SLOT_RIGHT: tuple[str, ...] = ("uptime", "cloud", "now")
```

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_plugin_cloud_v5.py`:

```python
from glances.outputs.curses_renderer_v5 import HEADER_SLOT_RIGHT, slot_for
from glances.plugins.cloud.render_curses_v5 import render

_FIELDS = PluginModel.fields_description


def test_cloud_is_registered_in_the_header_right_group():
    assert slot_for("cloud") == "header"
    # v4 paints uptime then cloud; `now` still closes the banner.
    assert HEADER_SLOT_RIGHT.index("uptime") < HEADER_SLOT_RIGHT.index("cloud")
    assert HEADER_SLOT_RIGHT[-1] == "now"


def test_render_empty_payload_returns_no_rows():
    assert render({}, _FIELDS) == []
    assert render(None, _FIELDS) == []


def test_render_builds_the_v4_banner():
    payload = {
        "platform": "OpenStack",
        "id": "proj-42",
        "name": "my-vm",
        "type": "gold",
        "region": "eu-west-1a",
    }
    rows = render(payload, _FIELDS)
    assert len(rows) == 1
    text = "".join(c.text for c in rows[0].cells)
    assert text == "OpenStack gold instance my-vm (eu-west-1a)"


def test_render_substitutes_unknown_for_missing_optional_parts():
    rows = render({"platform": "OpenStack", "name": "my-vm"}, _FIELDS)
    text = "".join(c.text for c in rows[0].cells)
    assert "Unknown instance my-vm (Unknown)" in text
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_plugin_cloud_v5.py -k "render or header" -v`
Expected: FAIL — `ModuleNotFoundError: ...render_curses_v5`, and the slot assertion fails because `cloud` is not yet in `HEADER_SLOT_RIGHT`.

- [ ] **Step 3: Register the slot**

In `glances/outputs/curses_renderer_v5.py`, change line 59 from:

```python
HEADER_SLOT_RIGHT: tuple[str, ...] = ("uptime", "now")
```

to:

```python
HEADER_SLOT_RIGHT: tuple[str, ...] = ("uptime", "cloud", "now")
```

Leave the surrounding comment intact — it still describes the group correctly.

- [ ] **Step 4: Write the renderer**

Create `glances/plugins/cloud/render_curses_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI renderer for the cloud plugin (header block).

Mirrors v4 `cloud.msg_curse()`: the platform name as a title, followed by
the instance summary.

    OpenStack gold instance my-vm (eu-west-1a)

Routed to the header slot next to `uptime`, matching v4's banner
(`curses_renderer_v5.HEADER_SLOT_RIGHT`). The model publishes `{}` when
the metadata is incomplete, so there is no partial banner to guard
against here.
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import Cell, ColorRole, Row

_UNKNOWN = "Unknown"


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]]) -> list[Row]:
    if not isinstance(payload, dict) or not payload.get("platform"):
        return []
    summary = " {} instance {} ({})".format(
        payload.get("type") or _UNKNOWN,
        payload.get("name") or _UNKNOWN,
        payload.get("region") or _UNKNOWN,
    )
    return [
        Row(
            cells=[
                Cell(text=str(payload["platform"]), color=ColorRole.HEADER, bold=True),
                Cell(text=summary),
            ]
        )
    ]
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_plugin_cloud_v5.py -v`
Expected: PASS (16 tests)

- [ ] **Step 6: Run the full v5 suite**

Run: `make test-v5`
Expected: no new failures. Pay attention to any existing header-layout test that asserts the exact contents of `HEADER_SLOT_RIGHT` — if one fails, update it to include `cloud` rather than reverting the registration.

- [ ] **Step 7: Pre-commit, then stage**

```bash
git add glances/plugins/cloud/render_curses_v5.py glances/outputs/curses_renderer_v5.py tests/test_plugin_cloud_v5.py
make pre-commit
```

Do **not** commit. Report that both tasks are staged.

---

## Manual smoke test (maintainer)

Only meaningful on an actual OpenStack / EC2 instance. On bare metal the plugin correctly shows nothing:

```bash
# with [cloud] disable=False
python -m glances.main_v5 -s &
curl -s http://127.0.0.1:61208/api/5/cloud     # {} off-cloud, populated on an instance
```

Off-cloud, confirm with `-d` that the "metadata probe failed" debug line appears **once**, not once per cycle.
