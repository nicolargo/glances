#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 <benjimons>
#
# SPDX-License-Identifier: LGPL-3.0-only
#
"""
Tailer plugin for Glances.

This plugin tails a file (given by the user), displaying:
- last modification time
- total line count
- last N lines
"""

import datetime
import os
from typing import Optional

from glances.logger import logger
from glances.plugins.plugin.model import GlancesPluginModel

# -----------------------------------------------------------------------------
# Globals
# -----------------------------------------------------------------------------

fields_description = {
    "filename": {
        "description": "Name of the file",
    },
    "file_size": {
        "description": "File size in bytes",
        "unit": "byte",
    },
    "last_modified": {
        "description": "Last modification time of the file",
    },
    "line_count": {
        "description": "Line count for the entire file",
        "unit": "lines",
    },
    "last_lines": {
        "description": "The last N lines of the file",
        # No specific unit, it's textual
    },
}

# If you need to store some metrics in the history, you can define them here:
items_history_list = [
    # Example: you could keep track of file size over time
    # {"name": "file_size", "description": "Size of the tailed file", "y_unit": "byte"},
]

# -----------------------------------------------------------------------------
# Plugin class
# -----------------------------------------------------------------------------


class PluginModel(GlancesPluginModel):
    """Tailer plugin main class.

    Attributes:
        self.stats (list): A list of dictionaries, each representing a file’s stats.
    """

    def __init__(self, args=None, config=None):
        """Initialize the plugin."""
        super().__init__(
            args=args,
            config=config,
            items_history_list=items_history_list,
            stats_init_value=[],
            fields_description=fields_description,
        )

        # We want to display the stat in the TUI
        self.display_curse = True

        # Optionally read from the config file [tailer] section
        # e.g.:
        # [tailer]
        # filename=/var/log/syslog
        # lines=10
        self.default_filename = config.get_value(self.plugin_name, 'filename', default='/var/log/syslog')
        self.default_lines = config.get_int_value(self.plugin_name, 'lines', default=10)

        # Force a first update
        self.update()
        self.refresh_timer.set(0)

    def get_key(self):
        """Return the key used in each stats dictionary."""
        # We'll use 'filename' as the key
        return 'filename'

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update the plugin stats.

        Called automatically at each refresh. Must set self.stats.
        """
        if self.input_method == 'local':
            stats = self.update_local()
        else:
            stats = self.get_init_value()

        self.stats = stats
        return self.stats

    def update_local(self):
        """Collect and return stats for our plugin (tailing a file)."""
        stats = self.get_init_value()

        # In a real scenario, you might have the user pass these in
        # or read from the config. For demonstration, we’ll use the defaults.
        filename = self.default_filename
        num_lines = self.default_lines

        # Build a dictionary representing the file stats
        file_stat = self._build_file_stat(filename, num_lines)
        stats.append(file_stat)

        return stats

    def _build_file_stat(self, filename, num_lines):
        """Return a dictionary of stats for the given filename."""
        result = {
            "key": self.get_key(),
            "filename": filename,
            "file_size": 0,
            "last_modified": "",
            "line_count": 0,
            "last_lines": [],
        }

        if not os.path.isfile(filename):
            logger.debug(f"File not found: {filename}")
            return result

        try:
            # Last modification time
            mod_time = os.path.getmtime(filename)
            result["last_modified"] = datetime.datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')

            # File size
            result["file_size"] = os.path.getsize(filename)

            # Count lines, read last N lines
            line_count, last_lines = self._tail_file(filename, num_lines)
            result["line_count"] = line_count
            # Store the last lines as a single string or as a list.
            # For display convenience, we might store them as a list of strings.
            result["last_lines"] = last_lines

        except Exception as e:
            logger.debug(f"Error reading file {filename}: {e}")

        return result

    def _tail_file(self, filename, num_lines):
        """Return (total_line_count, list_of_last_N_lines)."""
        with open(filename, 'rb') as f:
            # If the file is huge, you might want a more efficient way to read
            # the last N lines rather than reading the entire file.
            # For simplicity, read all lines:
            content = f.read().splitlines()
            total_lines = len(content)
            # Extract the last num_lines lines
            last_lines = content[-num_lines:] if total_lines >= num_lines else content
            # Decode to str (assuming UTF-8) for each line
            last_lines_decoded = [line.decode('utf-8', errors='replace') for line in last_lines]

        return total_lines, last_lines_decoded

    def update_views(self):
        """Update stats views (optional).

        If you need to set decorations (alerts or color formatting),
        you can do it here.
        """
        super().update_views()

        # Example: if file_size is above a threshold, we could color it in TUI
        for stat_dict in self.get_raw():
            fsize = stat_dict.get("file_size", 0)
            # Example: decorate if file > 1GB
            if fsize > 1024**3:
                self.views[stat_dict[self.get_key()]]["file_size"]["decoration"] = self.get_alert(
                    fsize, header='bigfile'
                )

    def msg_curse(self, args=None, max_width: Optional[int] = None) -> list[str]:
        """Return the dict (list of lines) to display in the TUI."""
        ret = []

        # If no stats or disabled, return empty
        if not self.stats or self.is_disabled():
            return ret

        # Header
        ret.append(self.curse_add_line("FILE TAILER PLUGIN", "TITLE"))

        # Display the stats
        for stat in self.stats:
            filename = stat.get("filename", "N/A")
            file_size = stat.get("file_size", 0)
            line_count = stat.get("line_count", 0)
            last_modified = stat.get("last_modified", "")
            last_lines = stat.get("last_lines", [])

            # New line for each file
            ret.append(self.curse_new_line())

            # 1) Filename
            msg_filename = f"File: {filename}"
            ret.append(self.curse_add_line(msg_filename))

            # 2) File size + last modified time
            msg_meta = (
                f"Size: {self.auto_unit(file_size)}, " f"Last Modified: {last_modified}, " f"Total Lines: {line_count}"
            )
            ret.append(self.curse_new_line())
            ret.append(self.curse_add_line(msg_meta))

            # 3) Last N lines
            ret.append(self.curse_new_line())
            ret.append(self.curse_add_line("Last lines:"))
            for line in last_lines:
                ret.append(self.curse_new_line())
                ret.append(self.curse_add_line(f"  {line}"))

            ret.append(self.curse_new_line())

        return ret
