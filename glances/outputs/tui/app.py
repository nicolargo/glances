#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Textual app for Glances."""

from time import monotonic

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Grid, Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Placeholder

# from glances.logger import logger
from glances.outputs.tui.components import (
    GlancesTuiListComponent,
    GlancesTuiOneLineComponent,
    GlancesTuiTableComponent,
    QuicklookTuiPlugin,
)


class GlancesTuiApp(App):
    CSS_PATH = "main.tcss"
    # BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]
    BINDINGS = [Binding(key="q", action="quit", description="Quit the app")]

    start_time = reactive(monotonic)
    time = reactive(0.0)

    def __init__(self, stats=None, config=None, args=None):
        super().__init__()

        # Init config
        self.config = config

        # Init args
        self.args = args

        # Init stats
        self.stats = stats

        # Init plugins
        self.init_plugins()

    def init_plugins(self) -> None:
        """Init the plugins."""
        self.plugins_description = self.stats.getAllFieldsDescriptionAsDict()

        # TODO: to be replaced by a loops (when it is possible)
        self.plugins = {}
        self.plugins["system"] = GlancesTuiOneLineComponent(
            plugin="system",
            template="{hostname} {hr_name}",
            stats=self.stats,
            config=self.config,
            args=self.args,
        )
        self.plugins["ip"] = GlancesTuiOneLineComponent(
            plugin="ip",
            template="IP {address}/{mask_cidr} {public_info_human} {public_address}",
            stats=self.stats,
            config=self.config,
            args=self.args,
        )
        self.plugins["uptime"] = GlancesTuiOneLineComponent(
            plugin="uptime",
            template="Uptime: {human}",
            stats=self.stats,
            config=self.config,
            args=self.args,
        )
        self.plugins["now"] = GlancesTuiOneLineComponent(
            plugin="now",
            template="{custom}",
            stats=self.stats,
            config=self.config,
            args=self.args,
        )

        self.plugins["quicklook"] = QuicklookTuiPlugin(
            plugin="quicklook", stats=self.stats, config=self.config, args=self.args
        )
        self.plugins["cpu"] = GlancesTuiTableComponent(
            plugin="cpu", stats=self.stats, config=self.config, args=self.args
        )
        self.plugins["mem"] = GlancesTuiTableComponent(
            plugin="mem", stats=self.stats, config=self.config, args=self.args
        )
        self.plugins["memswap"] = GlancesTuiTableComponent(
            plugin="memswap", stats=self.stats, config=self.config, args=self.args
        )
        self.plugins["load"] = GlancesTuiTableComponent(
            plugin="load", stats=self.stats, config=self.config, args=self.args
        )

        self.plugins["network"] = GlancesTuiListComponent(
            plugin="network", stats=self.stats, config=self.config, args=self.args, columns_width=[16, 8, 8]
        )
        self.plugins["diskio"] = GlancesTuiListComponent(
            plugin="diskio", stats=self.stats, config=self.config, args=self.args, columns_width=[16, 8, 8]
        )
        self.plugins["fs"] = GlancesTuiListComponent(
            plugin="fs", stats=self.stats, config=self.config, args=self.args, columns_width=[16, 8, 8]
        )
        self.plugins["sensors"] = GlancesTuiListComponent(
            plugin="sensors", stats=self.stats, config=self.config, args=self.args, columns_width=[16, 15, 1]
        )

        self.plugins["vms"] = GlancesTuiListComponent(
            plugin="vms", stats=self.stats, config=self.config, args=self.args, columns_width=[16, 15, 1]
        )
        self.plugins["containers"] = GlancesTuiListComponent(
            plugin="containers", stats=self.stats, config=self.config, args=self.args, columns_width=[16, 15, 1]
        )
        self.plugins["processcount"] = GlancesTuiOneLineComponent(
            plugin="processcount",
            template="TASKS {total} ({thread} thr), {running} run, {sleeping} slp, {other} oth",
            stats=self.stats,
            config=self.config,
            args=self.args,
        )
        self.plugins["processlist"] = GlancesTuiListComponent(
            plugin="processlist", stats=self.stats, config=self.config, args=self.args, columns_width=[16, 15, 1]
        )
        self.plugins["alert"] = GlancesTuiListComponent(
            plugin="alert", stats=self.stats, config=self.config, args=self.args, columns_width=[16, 15, 1]
        )

    def _header(self) -> Grid:
        return Grid(
            self.plugins["system"],
            self.plugins["ip"],
            self.plugins["uptime"],
            self.plugins["now"],
            id="header",
        )

    def _top(self) -> Grid:
        return Grid(
            self.plugins["quicklook"],
            self.plugins["cpu"],
            Placeholder(id="gpu", classes="remove"),
            self.plugins["mem"],
            self.plugins["memswap"],
            self.plugins["load"],
            id="top",
        )

    def _sidebar(self) -> VerticalScroll:
        return VerticalScroll(
            self.plugins["network"],
            self.plugins["diskio"],
            self.plugins["fs"],
            self.plugins["sensors"],
            id="sidebar",
        )

    def _process(self) -> VerticalScroll:
        return VerticalScroll(
            self.plugins["vms"],
            self.plugins["containers"],
            self.plugins["processcount"],
            self.plugins["processlist"],
            self.plugins["alert"],
            id="process",
        )

    def _middle(self) -> Horizontal:
        return Horizontal(
            self._sidebar(),
            self._process(),
            id="middle",
        )

    def compose(self) -> ComposeResult:
        # yield Header(id="header", show_clock=True)
        yield Container(
            self._header(),
            self._top(),
            self._middle(),
            id="data",
        )
        # yield Footer(id="footer")

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        # TODO: set interval to the Glances refresh rate
        self.set_interval(3, self.update_time)

    def update_time(self) -> None:
        """Method to update the time to the current time."""
        self.time = monotonic() - self.start_time

    def watch_time(self, time: float) -> None:
        """Called when the time attribute changes."""
        # Start by updating Glances stats
        self.stats.update()

        # Update the stat in the TUI
        for plugin in self.plugins.keys():
            self.plugins[plugin].update()
