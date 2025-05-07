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
from textual.widgets import Footer, Label, Placeholder

from glances.plugins.plugin.model import fields_unit_short


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
        self.plugins = {}
        self.plugins["cpu"] = GlancesPlugin("cpu", stats=stats, config=config, args=args)

    def compose(self) -> ComposeResult:
        # yield Header(id="header", show_clock=True)
        yield Container(
            Grid(
                Placeholder(id="system"),
                Placeholder(id="ip"),
                Placeholder(id="uptime"),
                id="header",
            ),
            Grid(
                Placeholder(id="quicklook"),
                self.plugins["cpu"],
                Placeholder(id="gpu", classes="remove"),
                Placeholder(id="mem"),
                Placeholder(id="memswap"),
                Placeholder(id="load"),
                id="top",
            ),
            Grid(
                VerticalScroll(
                    Placeholder(id="network"),
                    Placeholder(id="diskio"),
                    Placeholder(id="fs"),
                    Placeholder(id="sensors"),
                    id="sidebar",
                ),
                VerticalScroll(
                    Placeholder(id="vms"),
                    Placeholder(id="containers"),
                    Placeholder(id="processcount"),
                    Placeholder(id="processlist"),
                    id="process",
                ),
                id="middle",
            ),
            Grid(
                Placeholder(id="now"),
                Placeholder(id="alert"),
                id="bottom",
            ),
            id="data",
        )
        yield Footer(id="footer")

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

        # Solution 1: make the update in the GlancesTuiApp class
        self.query_one("#cpu").query_one("#total").update(str(self.stats.getAllAsDict()["cpu"]["total"]))
        self.query_one("#cpu").query_one("#system").update(str(self.stats.getAllAsDict()["cpu"]["system"]))
        # Solution 2: implement the update method in the CpuTextualPlugin class
        # ... (TODO)


class GlancesPlugin(Container):
    """Plugin to display Glances stats for most of Glances plugins.
    It's a simple table with the field name and the value.
    Display order: from left to right, top to bottom.
    """

    def __init__(self, plugin, stats=None, config=None, args=None):
        super().__init__()

        # Init config
        self.config = config

        # Init args
        self.args = args

        # Init stats
        self.stats = stats

        # Init plugin name (convert by default to lowercase)
        self.plugin = plugin.lower()
        self.plugin_description = (
            self.stats.getAllFieldsDescriptionAsDict()[self.plugin]
            if self.plugin in self.stats.getAllFieldsDescriptionAsDict()
            else {}
        )

    def compose(self) -> ComposeResult:
        if self.plugin not in self.stats.getAllAsDict():
            # Will generate a NoMatches exception when stats are updated
            # TODO: catch it in the main update loop
            yield Label(f'{self.plugin.upper()} stats not available', id=f"{self.plugin}-not-available")

        with Grid(id=f"{self.plugin}"):
            for field in self.stats.getAllAsDict()[f"{self.plugin}"].keys():
                # Get the field short name
                if field in self.plugin_description and 'short_name' in self.plugin_description[field]:
                    field_name = self.plugin_description[field]['short_name']
                else:
                    field_name = field
                yield Label(field_name, classes="name")
                # Display value
                yield Label('', id=field, classes="value ok")
                # Display unit
                if field in self.plugin_description and 'unit' in self.plugin_description[field]:
                    field_unit = fields_unit_short.get(self.plugin_description[field]['unit'], '')
                else:
                    field_unit = ''
                yield Label(field_unit, classes="unit ok")
