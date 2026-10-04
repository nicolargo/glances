#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — Graph export module (P3-3, wave E): one SVG chart per plugin.

Ported from the v4 module in this directory: same `[graph]` section (`path`,
`generate_every`, `width`, `height`, `style`), same `--export-graph-path`
option, same files (`<path>/<plugin>.svg`, a pygal `DateTimeLine` per
plugin). The charts are drawn from the history store (history design,
2026-09-26), through `plugin.get_history()`: the fields a plugin declares
`history: True`, over the last `[global] history_size` points.

When: every `generate_every` seconds, or when the TUI's `g` key asks for it
(v4 parity), at the next export cycle. A collection's series are named
`<item>.<field>`, as its exported columns are.

Divergences from v4, all fixes: the `path` given on the command line wins
over the configuration file (v4's comment said so, its code did the
opposite); a series longer than the chart's width is averaged down to
it -- v4 passed a dict where `time_series_subsample` wanted a list, so it
never subsampled anything; and the files are never written through a shared
temporary folder (security audit 2026-10-04, M7): the default folder is the
user's own, and each chart is written to a fresh file then renamed over the
target, so a symlink planted under the target name is replaced, not followed.
"""

from __future__ import annotations

import contextlib
import os
import stat
import sys
import tempfile
import threading
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase
from glances.globals import time_series_subsample
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5
    from glances.plugins.plugin.base_v5 import GlancesPluginBase


def default_path() -> str:
    """`$XDG_DATA_HOME/glances/graphs`, else `~/.local/share/glances/graphs`: the user's own folder.

    Not the shared temporary folder v4 used: as root, a folder another user
    created there first is a place where that user chooses what root writes.
    """
    data_home = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(data_home, "glances", "graphs")


class Export(GlancesExportBase):
    """Write one SVG chart per plugin from the stats history."""

    export_name = "graph"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)
        try:
            import pygal.style  # noqa: F401 -- checked here, used in export()
        except ImportError as e:
            logger.critical("Export graph needs the pygal library (%s)", e)
            sys.exit(2)
        self.path: str | None = None
        self.generate_every: Any = 0
        self.width: Any = 800
        self.height: Any = 600
        self.style: str = "DarkStyle"
        # Optional section: v4 ran on its defaults without one.
        self.load_conf("graph", mandatories=(), options=("path", "generate_every", "width", "height", "style"))
        configured = getattr(args, "export_graph_path", None) or self.path
        self.path = configured or default_path()
        try:
            self.generate_every = int(self.generate_every or 0)
            self.width = int(self.width or 800)
            self.height = int(self.height or 600)
        except ValueError as e:
            logger.critical("Error in the graph configuration (%s)", e)
            sys.exit(2)
        try:
            # The default folder is private; a configured one keeps its owner's choice.
            os.makedirs(self.path, mode=0o755 if configured else 0o700, exist_ok=True)
            tempfile.TemporaryFile(dir=self.path).close()
        except OSError as e:
            logger.critical("Graph output folder %s is not writable (%s)", self.path, e)
            sys.exit(2)
        if os.stat(self.path).st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            logger.warning("Graph output folder %s is writable by other users: they can replace the graphs", self.path)
        # The mode a plain `open()` would give the files, read once: the umask
        # can only be read by setting it.
        umask = os.umask(0)
        os.umask(umask)
        self._file_mode = 0o666 & ~umask
        self._requested = threading.Event()
        self._last_generation = time.monotonic()
        if self.generate_every:
            logger.info(
                "Graphs will be created in %s every %d seconds, or on the TUI's `g` key", self.path, self.generate_every
            )
        else:
            logger.info("Graphs will be created in %s on the TUI's `g` key", self.path)

    def request(self) -> str:
        """The TUI's `g` key: draw at the next export cycle. Returns what to tell the user."""
        self._requested.set()
        return f"Graphs will be written to {self.path}\nat the next export cycle."

    def _due(self) -> bool:
        if self._requested.is_set():
            return True
        return bool(self.generate_every) and time.monotonic() - self._last_generation >= self.generate_every

    def update(self, plugins: list[GlancesPluginBase]) -> None:
        # Not the base class's loop: the charts read the history, not the
        # current payload. Same lock, for the same reason (see the base).
        with self._lifecycle_lock:
            if not self._due():
                return
            self._requested.clear()
            self._last_generation = time.monotonic()
            drawn = [p.plugin_name for p in plugins if getattr(p, "EXPORTABLE", True) and self._draw(p)]
            logger.info("Graphs created in %s: %s", self.path, ", ".join(drawn) or "none (no history yet)")

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:  # pragma: no cover
        raise NotImplementedError("the graph export draws from the history, see update()")

    def series(self, plugin: GlancesPluginBase) -> dict[str, list[tuple[datetime, float]]]:
        """`{name: [(time, value), ...]}` from the plugin's history; a collection's names are `<item>.<field>`."""
        history = plugin.get_history()
        times = [datetime.fromtimestamp(ts) for ts in history["timestamps"]]
        flat: dict[str, list[Any]] = {}
        for field, values in history["series"].items():
            if isinstance(values, dict):
                for item, item_values in values.items():
                    flat[f"{item}.{field}"] = item_values
            else:
                flat[field] = values
        return {
            name: [(t, v) for t, v in zip(times, values) if isinstance(v, (int, float)) and not isinstance(v, bool)]
            for name, values in flat.items()
        }

    def _draw(self, plugin: GlancesPluginBase) -> bool:
        import pygal.style
        from pygal import DateTimeLine

        series = {name: points for name, points in self.series(plugin).items() if points}
        if not series:
            return False
        chart = DateTimeLine(
            title=plugin.plugin_name.capitalize(),
            width=self.width,
            height=self.height,
            # A pygal style class by name (`DarkStyle`, `LightStyle`...), nothing else.
            style=getattr(pygal.style, self.style, pygal.style.DarkStyle)
            if str(self.style).endswith("Style") and str(self.style).isidentifier()
            else pygal.style.DarkStyle,
            show_dots=False,
            legend_at_bottom=True,
            x_label_rotation=20,
            x_value_formatter=lambda dt: dt.strftime("%Y/%m/%d %H:%M:%S"),
        )
        for name, points in series.items():
            chart.add(name, time_series_subsample(points, self.width))
        try:
            self._write(f"{plugin.plugin_name}.svg", chart.render())
        except OSError as e:
            logger.warning("Cannot write the %s graph (%s)", plugin.plugin_name, e)
            return False
        return True

    def _write(self, name: str, content: bytes) -> None:
        """Write `content` to `<path>/<name>` without following a link planted there.

        `mkstemp` creates a new file (O_EXCL), and `os.replace` renames it over
        the target: a symlink at the target is replaced, never followed.
        """
        fd, tmp = tempfile.mkstemp(dir=self.path, prefix=f".{name}.", suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as f:
                if hasattr(os, "fchmod"):
                    os.fchmod(f.fileno(), self._file_mode)
                f.write(content)
            os.replace(tmp, os.path.join(self.path, name))
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp)
            raise
