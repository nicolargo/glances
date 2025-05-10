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

from glances.globals import auto_number
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
        self.plugins_description = self.stats.getAllFieldsDescriptionAsDict()
        # TODO: to be replaced by a loop
        self.plugins = {}
        self.plugins["cpu"] = GlancesPlugin("cpu", stats=stats, config=config, args=args)
        self.plugins["mem"] = GlancesPlugin("mem", stats=stats, config=config, args=args)
        self.plugins["memswap"] = GlancesPlugin("memswap", stats=stats, config=config, args=args)
        self.plugins["load"] = GlancesPlugin("load", stats=stats, config=config, args=args)

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
                self.plugins["mem"],
                self.plugins["memswap"],
                self.plugins["load"],
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
        # logger.info(self.stats.getAllAsDict()['cpu'])

        # Get stats views
        views = self.stats.getAllViewsAsDict()
        # logger.info(views['cpu'])

        # Update the stats using Textual query
        for plugin in self.plugins.keys():
            stats = self.stats.getAllAsDict()[plugin]
            for field in self.query_one(f"#{plugin}").query('.value'):
                # Ignore field not available in the stats
                if field.id not in self.stats.getAllAsDict()[plugin]:
                    continue
                # Update value
                if (
                    field.id in self.plugins_description[plugin]
                    and 'rate' in self.plugins_description[plugin][field.id]
                    and self.plugins_description[plugin][field.id]['rate']
                ):
                    field_stat = field.id + "_rate_per_sec"
                else:
                    field_stat = field.id
                field.update(auto_number(stats.get(field_stat, None)))
                # Update style
                style = views[plugin][field.id].get('decoration', 'DEFAULT')
                field.classes = f"value {style.lower()}"


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
            return

        with Grid(id=f"{self.plugin}"):
            for field in self.plugin_description.keys():
                # Ignore field if the display=False option is defined in the description
                if not self.plugin_description[field].get('display', True):
                    continue
                # Get the field short name
                if 'short_name' in self.plugin_description[field]:
                    field_name = self.plugin_description[field]['short_name']
                else:
                    field_name = field
                yield Label(field_name, classes="name")
                # Display value (with decoration classes)
                yield Label('', id=field, classes="value default")
                # Display unit
                if field in self.plugin_description and 'unit' in self.plugin_description[field]:
                    field_unit = fields_unit_short.get(self.plugin_description[field]['unit'], '')
                else:
                    field_unit = ''
                yield Label(field_unit, classes="unit")
