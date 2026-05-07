from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

from glances.outputs.glances_curses import _GlancesCurses


@pytest.fixture
def glancescreen():
    """Create a lightweight _GlancesCurses instance for helper method testing.

    The full curses interface is intentionally bypassed in order to isolate
    and test layout/helper logic independently from terminal rendering.
    """

    # Bypass full curses initialization and create a lightweight instance
    screen = _GlancesCurses.__new__(_GlancesCurses)

    # Mock runtime arguments required by helper methods
    screen.args = SimpleNamespace(
        disable_cpu=False,
        disable_mem=False,
        disable_load=False,
        disable_quicklook=False,
        full_quicklook=False,
    )

    # Mock terminal dimensions
    screen.term_window = Mock()
    screen.term_window.getmaxyx.return_value = (24, 120)

    # Mock rendering-related methods to isolate layout logic
    screen.display_plugin = Mock()
    screen.new_column = Mock()

    # Initialize required internal state
    screen.space_between_column = 3
    screen._quicklook_max_width = 100
    screen._top = ['cpu', 'mem', 'load']

    return screen


class TestDisplayTopHelpers:
    """Tests for helper methods extracted from __display_top."""

    def test_get_stats_summary(self, glancescreen):
        """Ensure plugin width totals and active plugin counts are computed correctly."""

        stat_display = {
            'cpu': {'msgdict': ['cpu']},
            'mem': {'msgdict': ['mem']},
            'load': {'msgdict': []},
        }

        plugin_widths = {
            'cpu': 10,
            'mem': 20,
            'load': 5,
        }

        stats_width, stats_number = glancescreen._get_stats_summary(
            stat_display,
            plugin_widths,
        )

        assert stats_width == 35
        assert stats_number == 2

    def test_compute_spacing_single_plugin(self, glancescreen):
        """Ensure spacing logic behaves correctly when only one plugin is displayed."""

        stat_display = {
            'cpu': {'msgdict': ['cpu']},
        }

        plugin_widths = {
            'cpu': 10,
        }

        glancescreen._top = ['cpu']

        plugin_display_optional, _ = glancescreen._compute_spacing_and_optional(
            stat_display,
            plugin_widths,
            stats_width=10,
            stats_number=1,
        )

        assert glancescreen.space_between_column == 0
        assert plugin_display_optional['cpu'] is True

    def test_compute_spacing_disables_optional_stats(
        self,
        glancescreen,
    ):
        """Ensure optional CPU and MEM display elements are disabled when spacing is constrained."""

        stat_display = {
            'cpu': {'msgdict': ['cpu']},
            'mem': {'msgdict': ['mem']},
        }

        plugin_widths = {
            'cpu': 80,
            'mem': 80,
        }

        glancescreen._top = ['cpu', 'mem']

        # Simulate a constrained terminal width
        glancescreen.term_window.getmaxyx.return_value = (24, 40)

        # Mock reduced widths after optional content removal
        glancescreen.get_stats_display_width = MagicMock(return_value=20)

        plugin_display_optional, _ = glancescreen._compute_spacing_and_optional(
            stat_display,
            plugin_widths,
            stats_width=160,
            stats_number=2,
        )

        assert plugin_display_optional['cpu'] is False
        assert plugin_display_optional['mem'] is False
        assert glancescreen.space_between_column >= 1

    def test_get_plugin_width(self, glancescreen):
        """Ensure plugin widths are correctly retrieved and mapped."""

        stat_display = {
            'cpu': {'msgdict': ['cpu']},
            'mem': {'msgdict': ['mem']},
        }

        glancescreen._top = ['cpu', 'mem']

        glancescreen.args.disable_cpu = False
        glancescreen.args.disable_mem = False

        glancescreen.get_stats_display_width = MagicMock(side_effect=[10, 20])

        plugin_widths = glancescreen._get_plugin_width(stat_display)

        assert plugin_widths == {
            'cpu': 10,
            'mem': 20,
        }

    def test_handle_quicklook_plugin_unavailable(
        self,
        glancescreen,
    ):
        """Ensure unavailable quicklook plugins are handled gracefully."""

        stats = Mock()

        # Simulate unavailable quicklook plugin
        stats.get_plugin.side_effect = AttributeError

        stat_display = {
            'quicklook': {'msgdict': []},
        }

        plugin_widths = {}

        result_widths, result_stats_width = glancescreen._handle_quicklook_for_display(
            stat_display,
            stats,
            plugin_widths,
            stats_width=0,
            stats_number=1,
        )

        assert result_widths == plugin_widths
        assert result_stats_width == 0
