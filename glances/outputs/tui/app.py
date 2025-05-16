#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Textual app for Glances."""

from time import monotonic

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Grid, Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Placeholder

from glances.globals import auto_number, dictlist_first_key_value

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

        self.plugins["now"] = GlancesTuiOneLineComponent(
            plugin="now",
            template="{custom}",
            stats=self.stats,
            config=self.config,
            args=self.args,
        )
        self.plugins["alert"] = GlancesTuiListComponent(
            plugin="alert", stats=self.stats, config=self.config, args=self.args, columns_width=[16, 15, 1]
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
            self.plugins["network"],
            self.plugins["diskio"],
            self.plugins["fs"],
            self.plugins["sensors"],
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

    def _middle(self) -> Horizontal:
        return Horizontal(
            self._sidebar(),
            self._process(),
            id="middle",
        )

    def _bottom(self) -> Horizontal:
        return Horizontal(
            self.plugins["now"],
            self.plugins["alert"],
            id="bottom",
        )

    def compose(self) -> ComposeResult:
        # yield Header(id="header", show_clock=True)
        yield Container(
            self._header(),
            self._top(),
            self._middle(),
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

        # Get stats views
        views = self.stats.getAllViewsAsDict()

        # TO BE REMOVED
        # from glances.logger import logger

        # logger.info(views['cpu'])
        # logger.info(self.stats.getAllAsDict()['sensors'])
        # logger.info(f"{dir(self.query_one('#sidebar').styles)}")
        # /TO BE REMOVED

        # Update the stats using Textual query
        for plugin in self.plugins.keys():
            # Get the stats
            stats = self.stats.getAllAsDict()[plugin]

            # TODO: Perhaps it will be cleaner to update per plugin...

            # Update network plugin
            if plugin in ["network", "diskio", "fs", "sensors", "alert"]:
                # TODO: manage add and remove of rows
                key = stats[0].get('key')
                for row_key, row_value in self.plugins[plugin].rows.items():
                    new_values = dictlist_first_key_value(stats, key, row_key)
                    first_column = True
                    for column_key, column_value in self.plugins[plugin].columns.items():
                        # Update value
                        field = column_key
                        if (
                            field in self.plugins_description[plugin]
                            and 'rate' in self.plugins_description[plugin][field]
                            and self.plugins_description[plugin][field]['rate']
                        ):
                            field_stat = field + "_rate_per_sec"
                        else:
                            field_stat = field
                        # With style
                        # WARNING: https://rich.readthedocs.io/en/stable/text.html?highlight=Text#rich-text
                        styled_value = Text(
                            auto_number(new_values.get(field_stat, None)),
                            justify="left" if first_column else "right",
                        )
                        self.query_one(f"#{plugin}").update_cell(
                            row_value, column_value, styled_value, update_width=True
                        )
                        first_column = False

                # Set the height of the list (+ one for the header)
                self.query_one(f"#{plugin}").styles.height = len(stats) + 1

                continue

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
