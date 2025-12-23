"""Profiler plugin."""

import sys
from collections import Counter

from glances.logger import logger
from glances.plugins.plugin.model import GlancesPluginModel

# Constants for sys.monitoring
TOOL_ID = 2  # ID 0 is reserved, 1 was used in test, 2 should be safe
# We will use PY_START to count function entries
EVENT_ID = getattr(sys.monitoring.events, 'PY_START', None) if hasattr(sys, 'monitoring') else None


class PluginModel(GlancesPluginModel):
    """Glances' Profiler Plugin.

    stats is a list of dict (function name, count)
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(args=args, config=config)

        # We want to display the stats in the UI
        self.args = args

        # Init the internal counter
        self._counts = Counter()
        self._monitoring_active = False

        # Check availability
        if not hasattr(sys, 'monitoring'):
            logger.warning("sys.monitoring not available. Profiler plugin disabled.")
            self.actions.disable()
            return

        try:
            sys.monitoring.use_tool_id(TOOL_ID, "glances_profiler")
            logger.info(f"sys.monitoring tool ID {TOOL_ID} registered.")
            self._monitoring_active = True

            # Register callback
            sys.monitoring.register_callback(TOOL_ID, EVENT_ID, self._callback)

            # Enable events
            sys.monitoring.set_events(TOOL_ID, EVENT_ID)

        except ValueError as e:
            logger.error(f"Failed to register sys.monitoring tool: {e}")
            self.actions.disable()
            self._monitoring_active = False

    def exit(self):
        """Stop monitoring."""
        if self._monitoring_active and hasattr(sys, 'monitoring'):
            sys.monitoring.set_events(TOOL_ID, 0)
            sys.monitoring.free_tool_id(TOOL_ID)
        super().exit()

    def _callback(self, code, instruction_offset):
        """Callback for sys.monitoring."""
        # This is called VERY frqeuently. Keep it minimal.
        # We just increment the counter for the code object name.
        self._counts[code.co_name] += 1
        return sys.monitoring.DISABLE

    def get_key(self):
        """Return the key of the list."""
        return 'function'

    def update_views(self):
        """Update the views."""
        # Standard table view
        self.views = {}
        if not self.stats:
            return self.views

        for i in self.stats:
            self.views[i[self.get_key()]] = {'hidden': False}

        return self.views

    def update(self):
        """Update stats."""
        # Reset stats
        self.reset()

        if not self._monitoring_active:
            return self.stats

        # Get the top 10 most frequent functions
        # We take the counter snapshot and reset it maybe?
        # Or just show cumulative? Let's show rate (per second/update) if possible.
        # For now, let's just show top N in the current interval.

        # NOTE: To show rate, we would need to diff with previous.
        # But for simplicity V1, let's just show the accumulated counts since start (or allow reset).
        # Actually, showing "Hot functions right now" implying per-update interval is better.

        # Snapshot and reset internal counter for the next interval?
        # WARNING: _callback runs in another thread/context potentially?
        # In simple Python (GIL), it is safe-ish, but let's be careful.
        # sys.monitoring callback runs synchronously.

        # Let's copy the current state
        current_counts = self._counts.copy()
        # self._counts.clear() # If we want per-interval stats, we should clear.

        # Sort by count desc
        top_n = current_counts.most_common(10)

        for func_name, count in top_n:
            stat = {'function': func_name, 'count': count}
            self.stats.append(stat)

        return self.stats
