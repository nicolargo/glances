#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Regression tests for GHSA-2jqf-3j6f-683p.

The ports plugin used to publish its configuration verbatim as statistics, so
`GET /api/4/ports` (and /api/4/all, the XML-RPC server, the curses UI and every
export module) returned the HTTP Basic credentials of the monitored URL and the
credentials of the forward proxy, in cleartext and without authentication.

`as_dict_secure()` masks those exact values on /api/4/config: its perimeter
never covered plugin statistics. The credentials now stay in a private
structure that only the scanner reads, and the published `url` goes through the
same sanitiser as the configuration view.
"""

import pytest

from glances.config import Config
from glances.web_list import GlancesWebList

SECRET = 'Sup3rS3cret'
PROXY_SECRET = 'Pr0xyP4ss'

CONFIG = f"""
[ports]
refresh=60
timeout=3
port_default_gateway=False
web_1_url=https://svcmonitor:{SECRET}@intranet.corp.example/health
web_1_http_proxy=http://proxyuser:{PROXY_SECRET}@proxy.corp.example:3128
web_1_https_proxy=http://proxyuser:{PROXY_SECRET}@proxy.corp.example:3128
web_2_url=https://public.example:8443/health
web_3_url=https://svcmonitor:{SECRET}@intranet.corp.example/health
web_3_description=Intranet health
"""


@pytest.fixture
def web_list_object(tmp_path):
    conf_file = tmp_path / 'glances.conf'
    conf_file.write_text(CONFIG)
    return GlancesWebList(config=Config(config_dir=str(conf_file)))


@pytest.fixture
def web_list(web_list_object):
    return web_list_object.get_web_list()


def entry(web_list, indice):
    return next(web for web in web_list if web['indice'] == indice)


def test_no_secret_anywhere_in_the_published_list(web_list):
    """The published statistics must not carry a single credential."""
    published = repr(web_list)

    assert SECRET not in published
    assert PROXY_SECRET not in published


def test_published_url_is_redacted(web_list):
    assert entry(web_list, 'web_1')['url'] == 'https://********@intranet.corp.example/health'


def test_proxies_are_not_published(web_list):
    assert 'proxies' not in entry(web_list, 'web_1')


def test_default_description_drops_the_userinfo(web_list):
    """The default description is the netloc, which used to embed the password."""
    assert entry(web_list, 'web_1')['description'] == 'intranet.corp.example'


def test_default_description_keeps_the_port(web_list):
    assert entry(web_list, 'web_2')['description'] == 'public.example:8443'


def test_explicit_description_is_untouched(web_list):
    assert entry(web_list, 'web_3')['description'] == 'Intranet health'


def test_credentialless_url_is_published_verbatim(web_list):
    """Negative control: only the credential bearing part is sanitised."""
    assert entry(web_list, 'web_2')['url'] == 'https://public.example:8443/health'


def test_scanner_still_gets_the_real_url_and_proxies(web_list_object):
    """The scan must keep working: the credentials are moved, not dropped."""
    secrets = web_list_object.get_web_secrets()['web_1']

    assert secrets['url'] == f'https://svcmonitor:{SECRET}@intranet.corp.example/health'
    assert secrets['proxies'] == {
        'http': f'http://proxyuser:{PROXY_SECRET}@proxy.corp.example:3128',
        'https': f'http://proxyuser:{PROXY_SECRET}@proxy.corp.example:3128',
    }


def test_no_proxy_configured_stays_none(web_list_object):
    assert web_list_object.get_web_secrets()['web_2']['proxies'] is None


def test_scan_requests_the_real_url_not_the_redacted_one(web_list_object, monkeypatch):
    """The scanner reads the secrets: redacting the published URL must not break it."""
    from glances.plugins.ports import ThreadScanner

    called = {}

    def fake_head(url, **kwargs):
        called['url'] = url
        called['proxies'] = kwargs['proxies']
        raise RuntimeError('stop here, no request is actually sent')

    monkeypatch.setattr('glances.plugins.ports.requests.head', fake_head)

    web = entry(web_list_object.get_web_list(), 'web_1')
    ThreadScanner(web_list_object.get_web_list(), web_list_object.get_web_secrets())._web_scan(web)

    assert called['url'] == f'https://svcmonitor:{SECRET}@intranet.corp.example/health'
    assert called['proxies']['http'] == f'http://proxyuser:{PROXY_SECRET}@proxy.corp.example:3128'
