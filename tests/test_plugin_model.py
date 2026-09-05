#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the GlancesPluginModel._check_decorator method."""

from glances.plugins.plugin.model import GlancesPluginModel

# _check_decorator is a plain function on the class body (not a bound method
# when accessed through the class), so it can be applied directly to a fake
# update function to test it in isolation.
_check_decorator = GlancesPluginModel._check_decorator


class FakeTimer:
    """Minimal stand-in for glances.timer.Timer."""

    def __init__(self, finished):
        self._finished = finished

    def finished(self):
        return self._finished

    def set(self, duration):
        pass

    def reset(self, duration=None):
        pass


class FakePlugin:
    """Minimal stand-in for a GlancesPluginModel instance."""

    init_value = {}

    def __init__(self, stats, timer_finished):
        self.stats = stats
        self.refresh_timer = FakeTimer(timer_finished)
        self.called = False

    def is_enabled(self, plugin_name=None):
        return True

    def get_init_value(self):
        return self.init_value

    def get_refresh(self):
        return 2

    @_check_decorator
    def update(self):
        self.called = True
        self.stats = {'foo': 'bar'}
        return self.stats


class TestCheckDecorator:
    """Test the update() gating logic in GlancesPluginModel._check_decorator."""

    def test_update_called_when_stats_equal_init_value_and_timer_not_finished(self):
        """Stats still at init value and timer not finished: update MUST run.

        This is the retry-immediately path used after a fetch error (see
        reset() in cpu/mem plugins), so a stale/empty init value should not
        wait out the whole refresh interval.
        """
        plugin = FakePlugin(stats=FakePlugin.init_value, timer_finished=False)

        plugin.update()

        assert plugin.called is True

    def test_update_not_called_when_stats_differ_and_timer_not_finished(self):
        """Stats already populated and timer not finished: update must NOT run."""
        plugin = FakePlugin(stats={'foo': 'previous'}, timer_finished=False)

        plugin.update()

        assert plugin.called is False
