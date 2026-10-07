# SPDX-FileCopyrightText: 2026 Glances contributors
# SPDX-License-Identifier: LGPL-3.0-only

"""Tests for the Cloud plugin metadata threads."""

from types import SimpleNamespace
from unittest import mock

import pytest

pytest.importorskip("requests")

from glances.plugins import cloud  # noqa: E402


def fake_get(ok_urls):
    """Return a requests.get replacement answering 200 only for ok_urls."""

    def _get(url, timeout=None):
        return mock.Mock(ok=url in ok_urls, content=b'value')

    return _get


def test_openstack_platform_not_set_when_no_metadata_is_found():
    thread = cloud.ThreadOpenStack()
    with mock.patch.object(cloud.requests, 'get', side_effect=fake_get(set())):
        thread.run()

    assert thread.stats == {}


def test_ec2_metadata_is_used_when_openstack_api_is_missing():
    ec2_api = cloud.ThreadOpenStackEC2
    ec2_urls = {f'{ec2_api.OPENSTACK_API_URL}/{v}' for v in ec2_api.OPENSTACK_API_METADATA.values()}
    with mock.patch.object(cloud.ThreadOpenStack, 'start'):
        plugin = cloud.CloudPlugin(args=SimpleNamespace(disable_cloud=False, disable_history=True))
    with mock.patch.object(cloud.requests, 'get', side_effect=fake_get(ec2_urls)):
        plugin.OPENSTACK.run()
        plugin.OPENSTACKEC2.run()

    stats = plugin.update()

    assert stats['platform'] == 'Amazon EC2'
    assert stats['name'] == 'value'
