#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Glances contributors
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the REST API MessagePack response."""

from datetime import datetime
from types import SimpleNamespace

import msgpack

from glances.outputs.glances_restful_api import GlancesMsgpackResponse, GlancesRestfulApi


class _Stats:
    def __init__(self, payload):
        self.payload = payload

    def getAllAsDict(self):
        return self.payload


def _api_with_stats(payload):
    api = object.__new__(GlancesRestfulApi)
    api.stats = _Stats(payload)
    api._GlancesRestfulApi__update_stats = lambda: None
    return api


def test_all_msgpack_returns_the_complete_stats_mapping():
    payload = {
        'cpu': {'total': 17.5, 'history': [12.0, 17.5]},
        'system': {'hostname': 'glances-test', 'booted_at': datetime(2026, 9, 6, 9, 30)},
    }

    response = _api_with_stats(payload)._api_all_msgpack()

    assert isinstance(response, GlancesMsgpackResponse)
    assert response.media_type == 'application/msgpack'
    decoded = msgpack.unpackb(response.body, raw=False)
    assert decoded == {
        'cpu': {'total': 17.5, 'history': [12.0, 17.5]},
        'system': {'hostname': 'glances-test', 'booted_at': '2026-09-06T09:30:00'},
    }


def test_all_msgpack_route_is_registered_before_plugin_routes():
    api = object.__new__(GlancesRestfulApi)
    api.args = SimpleNamespace(password=None, bind_address='127.0.0.1', disable_webui=True)
    api.config = SimpleNamespace(get_list_value=lambda *args, **kwargs: ['http://localhost'])
    api.bind_url = 'http://127.0.0.1:61208/'
    api.url_prefix = ''
    api.webui_allowed_hosts = ['localhost']

    routes = api._router().routes
    paths = [route.path for route in routes]

    assert '/api/4/all/msgpack' in paths
    assert paths.index('/api/4/all/msgpack') < paths.index('/api/4/{plugin}/{item}')
    route = routes[paths.index('/api/4/all/msgpack')]
    assert route.response_class is GlancesMsgpackResponse
