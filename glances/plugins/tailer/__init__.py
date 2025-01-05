# -*- coding: utf-8 -*-
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
            result["last_lines"] = ["", "File Not Found"]
            return result

        try:
            # Last modification time
            mod_time = os.path.getmtime(filename)
            result["last_modified"] = datetime.datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')

            # File size
            result["file_size"] = os.path.getsize(filename)

            # Count lines, read last N lines (efficiently for large files)
            line_count, last_lines = self._tail_file(filename, num_lines)
            result["line_count"] = line_count
            result["last_lines"] = last_lines

        except Exception as e:
            logger.debug(f"Error reading file {filename}: {e}")

        return result

    def _tail_file(self, filename, num_lines):
        """
        Return (total_line_count, list_of_last_N_lines) for a potentially huge file.
        
        1) Count total lines by reading the file in chunks (no huge memory usage).
        2) Retrieve the last N lines by reading from the end in chunks.
        """

        # 1) Count total lines in a streaming fashion
        chunk_size = 8192
        total_line_count = 0

        with open(filename, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                total_line_count += chunk.count(b'\n')

        # If file isn't empty and doesn't end with a newline, that last partial line counts
        file_size = os.path.getsize(filename)
        if file_size > 0:
            with open(filename, 'rb') as f:
                # Seek to last byte
                f.seek(-1, os.SEEK_END)
                if f.read(1) != b'\n':
                    total_line_count += 1

        # 2) Retrieve last N lines from the end
        # We'll read backward in chunks until we find num_lines newlines
        lines_reversed = []
        newlines_found = 0

        with open(filename, 'rb') as f:
            # Start from end of file
            f.seek(0, os.SEEK_END)
            position = f.tell()

            while position > 0 and newlines_found <= num_lines:
                # Read chunk or what's left from start
                read_size = min(chunk_size, position)
                position -= read_size
                f.seek(position)

                chunk = f.read(read_size)
                # Reverse the chunk (we’re scanning backwards)
                reversed_chunk = chunk[::-1]

                # For each byte in reversed_chunk
                for b in reversed_chunk:
                    # b'\n' is ASCII 10
                    if b == 10:
                        newlines_found += 1
                        if newlines_found > num_lines:
                            break
                    lines_reversed.append(b)

                if newlines_found > num_lines:
                    break

        # lines_reversed now includes the bytes for at least N lines in reverse order
        lines_reversed.reverse()
        last_data = bytes(lines_reversed).decode('utf-8', errors='replace')
        all_last_lines = last_data.splitlines()
        last_n_lines = all_last_lines[-num_lines:] if len(all_last_lines) > num_lines else all_last_lines

        return total_line_count, last_n_lines

    def update_views(self):
        """Update stats views (optional)."""
        super().update_views()

    def msg_curse(self, args=None, max_width: Optional[int] = None) -> list[str]:
        """Return the list of lines to display in the TUI."""
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

            # (1) File info
            msg_meta = (
                f"File: {filename}, "
                f"Size: {self.auto_unit(file_size)}, "
                f"Last Modified: {last_modified}, "
                f"Total Lines: {line_count}"
            )
            ret.append(self.curse_new_line())
            ret.append(self.curse_add_line(msg_meta))

            # (2) Last N lines
            first_nonblank = True
            for line in last_lines:
                # If it's the first non-blank line, add a leading blank line
                if first_nonblank:
                    ret.append(self.curse_new_line())
                    first_nonblank = False
                ret.append(self.curse_add_line(f"  {line}"))
                ret.append(self.curse_new_line())

        return ret
