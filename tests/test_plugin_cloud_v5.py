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

from glances.outputs.curses_renderer_v5 import HEADER_SLOT_RIGHT, slot_for
from glances.plugins.cloud.model_v5 import PROVIDERS, PluginModel
from glances.plugins.cloud.render_curses_v5 import render

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

_FIELDS = PluginModel.fields_description


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


def test_openstack_exception_does_not_prevent_ec2_fallback(store_with, config_with, monkeypatch):
    """Regression: exception in one provider must not prevent fallback.

    If OpenStack probe raises (e.g. connection timeout), EC2 should still
    be attempted. The exception is caught inside _probe_provider, treating
    it as a failed probe (return {}) that allows the loop to continue.
    """

    class _OpenStackBoom(_FakeRequests):
        def get(self, url, timeout=None):
            self.record.append(url)
            if "openstack" in url:
                raise ConnectionError("OpenStack timeout")
            # EC2 works fine
            for path, body in self._responses.items():
                if url.endswith("/" + path):
                    return _FakeResponse(True, body)
            return _FakeResponse(False, "")

    record: list[str] = []
    stub = _OpenStackBoom(EC2_OK, record)
    monkeypatch.setattr("glances.plugins.cloud.model_v5.requests", stub)
    plugin = PluginModel(store_with(), config_with({}))
    stats = asyncio.run(plugin._grab_stats())
    # Should have gotten EC2 result despite OpenStack raising
    assert stats["platform"] == "Amazon EC2"
    assert stats["name"] == "i-abc"
    # Verify we actually tried OpenStack first
    assert any("openstack" in url for url in record)


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
