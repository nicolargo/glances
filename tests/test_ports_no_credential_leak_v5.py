#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Regression tests for GHSA-2jqf-3j6f-683p, v5 side.

v5 never published `proxies` (`model_v5.fields_description` declares it as
deliberately absent, and `_remove_parameters()` strips every undeclared field),
but it reuses `GlancesWebList` verbatim and declares `url`, so it shared the
URL-userinfo half of the leak.

The v4 fix moved the credentials out of the published list and into a private
structure the scanner reads, which changed `ThreadScanner.__init__`. v5 builds
its own scanner, so these tests exercise the REAL `ThreadScanner` rather than
the fake used elsewhere in the v5 ports tests, which would hide the mismatch.
"""

from __future__ import annotations

import pytest

from glances.plugins.ports import ThreadScanner
from glances.plugins.ports.model_v5 import PluginModel

SECRET = 'Sup3rS3cret'
PROXY_SECRET = 'Pr0xyP4ss'

_SECTION = {
    "refresh": "60",
    "timeout": "3",
    "port_default_gateway": "False",
    "web_1_url": f"https://svcmonitor:{SECRET}@intranet.corp.example/health",
    "web_1_http_proxy": f"http://proxyuser:{PROXY_SECRET}@proxy.corp.example:3128",
    "web_1_https_proxy": f"http://proxyuser:{PROXY_SECRET}@proxy.corp.example:3128",
    "web_2_url": "https://public.example:8443/health",
}


@pytest.fixture
def plugin(store_with, config_with, monkeypatch):
    """A v5 ports plugin whose scans never touch the network."""

    def fake_head(url, **kwargs):
        raise RuntimeError('no request is actually sent')

    monkeypatch.setattr('glances.plugins.ports.requests.head', fake_head)
    return PluginModel(store_with(), config_with({"ports": _SECTION}))


def entry(payload, indice):
    return next(item for item in payload if item['indice'] == indice)


async def test_real_scanner_is_constructed_by_grab_stats(plugin):
    """`_grab_stats()` must build the real ThreadScanner, secrets included.

    The v5 ports tests patch ThreadScanner with a fake taking `(stats)` only,
    so only an unpatched run catches a constructor mismatch.
    """
    await plugin._grab_stats()

    assert isinstance(plugin._thread, ThreadScanner)
    plugin._thread.join(timeout=5)
    plugin.stop()


async def test_payload_carries_no_credential(plugin):
    payload = await plugin._grab_stats()

    assert SECRET not in repr(payload)
    assert PROXY_SECRET not in repr(payload)
    plugin.stop()


async def test_published_url_is_redacted(plugin):
    payload = await plugin._grab_stats()

    assert entry(payload, 'web_1')['url'] == 'https://********@intranet.corp.example/health'
    plugin.stop()


async def test_default_description_drops_the_userinfo(plugin):
    payload = await plugin._grab_stats()

    assert entry(payload, 'web_1')['description'] == 'intranet.corp.example'
    plugin.stop()


async def test_credentialless_url_is_published_verbatim(plugin):
    """Negative control: only the credential bearing part is sanitised."""
    payload = await plugin._grab_stats()

    assert entry(payload, 'web_2')['url'] == 'https://public.example:8443/health'
    plugin.stop()


async def test_proxies_stay_out_of_the_payload(plugin):
    payload = await plugin._grab_stats()

    assert 'proxies' not in entry(payload, 'web_1')
    plugin.stop()


async def test_scan_requests_the_real_url_not_the_redacted_one(plugin, monkeypatch):
    """The scan must keep working: the credentials are moved, not dropped."""
    # The scanner sweeps every entry, so record them all and look up the one
    # under test rather than keeping the last call.
    calls = []

    def recording_head(url, **kwargs):
        calls.append((url, kwargs['proxies']))
        raise RuntimeError('no request is actually sent')

    monkeypatch.setattr('glances.plugins.ports.requests.head', recording_head)

    await plugin._grab_stats()
    plugin._thread.join(timeout=5)

    url, proxies = next(call for call in calls if 'intranet.corp.example' in call[0])

    assert url == f'https://svcmonitor:{SECRET}@intranet.corp.example/health'
    assert proxies['http'] == f'http://proxyuser:{PROXY_SECRET}@proxy.corp.example:3128'
    plugin.stop()
