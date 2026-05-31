#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Docker container engine (issue #3559 performance fix)."""

from unittest.mock import MagicMock, patch

import pytest

from glances.plugins.containers.engines import docker as docker_engine


class FakeImage:
    def __init__(self, tags):
        self.tags = tags


class FakeContainer:
    """Minimal container double counting image lookups and inspects (reload)."""

    def __init__(self, cid, status="exited", tags=None):
        self.id = cid
        self.name = f"name-{cid}"
        self.attrs = {
            "State": {"Status": status},
            "Created": "2026-01-01T00:00:00Z",
            "Config": {"Entrypoint": None, "Cmd": ["sh"]},
            "HostConfig": {},
        }
        self._tags = tags if tags is not None else [f"img-{cid}:latest"]
        self.ports = {}
        self.image_access_count = 0
        self.reload_count = 0

    @property
    def image(self):
        # container.image performs an inspect_image API call in docker-py
        self.image_access_count += 1
        return FakeImage(self._tags)

    def reload(self):
        # reload() performs the per-container inspect in docker-py
        self.reload_count += 1


def make_extension(containers):
    """Build a DockerExtension without connecting to a real daemon."""
    ext = docker_engine.DockerExtension.__new__(docker_engine.DockerExtension)
    ext.disable = False
    ext.display_error = True
    ext.ext_name = "containers (Docker)"
    ext.stats_fetchers = {}
    ext.image_cache = {}
    ext.client = MagicMock()
    ext.client.containers.list.return_value = containers
    return ext


def test_list_is_sparse():
    """The list must be fetched sparse (single API call, no per-container inspect)."""
    containers = [FakeContainer("a"), FakeContainer("b")]
    ext = make_extension(containers)
    with patch.object(docker_engine, "DockerStatsFetcher", MagicMock()):
        ext.update(all_tag=True)
    ext.client.containers.list.assert_called_once_with(all=True, sparse=True)


def test_containers_are_inspected_every_cycle():
    """Each container is inspected (reload) once per update cycle (fresh status/uptime)."""
    containers = [FakeContainer("a"), FakeContainer("b"), FakeContainer("c")]
    ext = make_extension(containers)
    with patch.object(docker_engine, "DockerStatsFetcher", MagicMock()):
        ext.update(all_tag=True)
        ext.update(all_tag=True)
    assert all(c.reload_count == 2 for c in containers)


def test_image_is_cached_across_cycles():
    """Issue #3559: image (inspect_image) must be looked up once, then cached."""
    containers = [FakeContainer("a"), FakeContainer("b")]
    ext = make_extension(containers)
    with patch.object(docker_engine, "DockerStatsFetcher", MagicMock()):
        ext.update(all_tag=True)
        ext.update(all_tag=True)
        ext.update(all_tag=True)
    # 3 cycles, but the immutable image is only fetched once per container
    assert all(c.image_access_count == 1 for c in containers)


def test_image_field_format_preserved():
    """The exposed image field keeps its historical shape (tuple of joined tags)."""
    containers = [FakeContainer("a", tags=["redis:7"])]
    ext = make_extension(containers)
    with patch.object(docker_engine, "DockerStatsFetcher", MagicMock()):
        _, stats = ext.update(all_tag=True)
    assert stats[0]["image"] == ("redis:7",)


def test_image_cache_evicts_removed_containers():
    """Image cache must not grow unbounded: entries for gone containers are dropped."""
    first = [FakeContainer("a"), FakeContainer("b")]
    ext = make_extension(first)
    with patch.object(docker_engine, "DockerStatsFetcher", MagicMock()):
        ext.update(all_tag=True)
        assert set(ext.image_cache) == {"a", "b"}
        # Container "b" disappears
        ext.client.containers.list.return_value = [FakeContainer("a")]
        ext.update(all_tag=True)
    assert set(ext.image_cache) == {"a"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
