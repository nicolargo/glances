"""Tests for the TTL-based lru cache helpers in glances.globals."""

from unittest import mock

import pytest

from glances.globals import _get_ttl_hash


@pytest.fixture
def clock():
    with mock.patch('glances.globals.time.monotonic') as m:
        yield m


def test_hash_is_stable_within_the_ttl(clock):
    clock.return_value = 1000.0
    first = _get_ttl_hash(5)
    clock.return_value = 1004.0
    assert _get_ttl_hash(5) == first


def test_hash_changes_once_the_ttl_has_passed(clock):
    clock.return_value = 1000.0
    first = _get_ttl_hash(5)
    clock.return_value = 1006.0
    assert _get_ttl_hash(5) != first


def test_hash_honours_the_requested_ttl(clock):
    """A longer ttl must hold its value where a shorter one has already moved on."""
    clock.return_value = 1000.0
    short, long = _get_ttl_hash(1), _get_ttl_hash(30)
    clock.return_value = 1002.0
    assert _get_ttl_hash(1) != short
    assert _get_ttl_hash(30) == long


def test_hash_does_not_repeat_after_a_minute(clock):
    """The value must not cycle, or an entry could be served long after it expired."""
    clock.return_value = 1000.0
    first = _get_ttl_hash(1)
    clock.return_value = 1060.0
    assert _get_ttl_hash(1) != first


def test_hash_is_disabled_without_a_ttl():
    assert _get_ttl_hash(None) == 0
