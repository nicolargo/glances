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
from textual.containers import Container, Grid, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Placeholder

from glances.globals import auto_number

# from glances.logger import logger
from glances.outputs.tui.components import GlancesTuiOneLineComponent, GlancesTuiTableComponent, QuicklookTuiPlugin


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
        self.plugins_description = self.stats.getAllFieldsDescriptionAsDict()
        # TODO: to be replaced by a loops (when it is possible)
        self.plugins = {}
        self.plugins["system"] = GlancesTuiOneLineComponent(
            plugin="system",
            template="{hostname} {hr_name}",
            stats=stats,
            config=config,
            args=args,
        )
        self.plugins["ip"] = GlancesTuiOneLineComponent(
            plugin="ip",
            template="IP {address}/{mask_cidr} {public_info_human} {public_address}",
            stats=stats,
            config=config,
            args=args,
        )
        self.plugins["uptime"] = GlancesTuiOneLineComponent(
            plugin="uptime",
            template="Uptime: {human}",
            stats=stats,
            config=config,
            args=args,
        )
        self.plugins["quicklook"] = QuicklookTuiPlugin(plugin="quicklook", stats=stats, config=config, args=args)
        self.plugins["cpu"] = GlancesTuiTableComponent(plugin="cpu", stats=stats, config=config, args=args)
        self.plugins["mem"] = GlancesTuiTableComponent(plugin="mem", stats=stats, config=config, args=args)
        self.plugins["memswap"] = GlancesTuiTableComponent(plugin="memswap", stats=stats, config=config, args=args)
        self.plugins["load"] = GlancesTuiTableComponent(plugin="load", stats=stats, config=config, args=args)
        self.plugins["now"] = GlancesTuiOneLineComponent(
            plugin="now",
            template="{custom}",
            stats=stats,
            config=config,
            args=args,
        )

    def _header(self) -> Grid:
        return Grid(
            self.plugins["system"],
            self.plugins["ip"],
            self.plugins["uptime"],
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
            Placeholder(id="network"),
            Placeholder(id="diskio"),
            Placeholder(id="fs"),
            Placeholder(id="sensors"),
            id="sidebar",
        )

    def _process(self) -> VerticalScroll:
        return VerticalScroll(
            Placeholder(id="vms"),
            Placeholder(id="containers"),
            Placeholder(id="processcount"),
            Placeholder(id="processlist"),
            id="process",
        )

    def _bottom(self) -> Grid:
        return Grid(
            self.plugins["now"],
            Placeholder(id="alert"),
            id="bottom",
        )

    def compose(self) -> ComposeResult:
        # yield Header(id="header", show_clock=True)
        yield Container(
            self._header(),
            self._top(),
            Grid(
                self._sidebar(),
                self._process(),
                id="middle",
            ),
            self._bottom(),
            id="data",
        )
        # yield Footer(id="footer")

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.set_interval(1, self.update_time)

    def update_time(self) -> None:
        """Method to update the time to the current time."""
        self.time = monotonic() - self.start_time

    def watch_time(self, time: float) -> None:
        """Called when the time attribute changes."""
        # Start by updating Glances stats
        self.stats.update()
        # logger.info(self.stats.getAllAsDict()['cpu'])

        # Get stats views
        views = self.stats.getAllViewsAsDict()
        # logger.info(views['cpu'])

        # Update the stats using Textual query
        for plugin in self.plugins.keys():
            # Get the stats
            stats = self.stats.getAllAsDict()[plugin]

            # Iter through the fields value to update as a Label
            for textual_field in self.query_one(f"#{plugin}").query('.value').exclude(".progressbar"):
                # Remove the plugin name from the field id
                field = '_'.join(textual_field.id.split('_', maxsplit=1)[1:])
                # Ignore field not available in the stats
                if field not in stats:
                    continue
                # Update value
                if (
                    field in self.plugins_description[plugin]
                    and 'rate' in self.plugins_description[plugin][field]
                    and self.plugins_description[plugin][field]['rate']
                ):
                    field_stat = field + "_rate_per_sec"
                else:
                    field_stat = field
                textual_field.update(auto_number(stats.get(field_stat, None)))
                # Update style
                style = views[plugin][field].get('decoration', 'DEFAULT')
                textual_field.classes = f"value {style.lower()}"

            # Iter through the fields value to update as a ProgressBar
            for textual_field in self.query_one(f"#{plugin}").query('.value').filter(".progressbar"):
                # Remove the plugin name from the field id
                field = '_'.join(textual_field.id.split('_', maxsplit=1)[1:])
                # Ignore field not available in the stats
                if field not in stats:
                    continue
                # Update value
                textual_field.update(progress=stats.get(field, None))
                # TODO: Update style
                # Do not work for preogress bar...
                # style = views[plugin][field].get('decoration', 'DEFAULT')
                # textual_field.classes = f"value progressbar {style.lower()}"
