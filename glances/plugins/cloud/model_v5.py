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
AMP), so no new dependency is introduced. It blocks, and each provider requires
up to four 3-second timeouts (one per metadata key), but the cost is bounded
per provider: OpenStack alone (worst case) is 12 seconds; EC2 is only probed
if OpenStack is silent. The probe runs inside `asyncio.to_thread` — the same
pattern as `ports`, `npu`, `mpp` and `irq`. Cost is paid once at startup,
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
    # Cloud metadata API calls are slow. The probe is one-shot and cached
    # anyway, so this only bounds the retry after a failed first attempt.
    DEFAULT_REFRESH_TIME: ClassVar[float | None] = 120.0

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

        All-or-nothing: any non-ok response (404, timeout, etc.) on any key
        discards the entire provider and returns {}. v5 is stricter than v4,
        which only broke on exception; this ensures no partial dict reaches
        the API. Exceptions are caught here, not propagated, so they don't
        prevent other providers from being tried.
        """
        try:
            out: dict[str, Any] = {}
            for field, path in provider.metadata.items():
                response = requests.get(f"{provider.url}/{path}", timeout=_TIMEOUT_SECONDS)
                if not response.ok:
                    return {}
                out[field] = response.text.strip()
            out["platform"] = provider.platform
            return out
        except Exception as exc:  # noqa: BLE001 — treat like non-ok response
            logger.debug("cloud: %s probe failed: %s", provider.platform, exc)
            return {}

    def _probe_sync(self) -> dict[str, Any]:
        """Blocking probe of every provider in order. Runs in a worker thread.

        Tries each provider in turn; the first one that returns a complete
        dict is returned. If all providers return {}, returns {}.
        """
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

        # requests blocks (cost bounded per provider, see module docstring);
        # keep it off the event loop.
        self._cached = await asyncio.to_thread(self._probe_sync)
        return self._cached
