#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Textual Glances quicklook plugin component."""

from textual.app import ComposeResult
from textual.color import Gradient
from textual.containers import Container, Grid, Vertical
from textual.widgets import Label, ProgressBar

from glances.globals import auto_number


class QuicklookTuiPlugin(Container):
    """Quicklook plugin for Textual."""

    # To be done dynamicaly regarding thresholds defined in the config file
    gradient = Gradient.from_colors(
        "lime",
        "lime",
        "lime",
        "lime",
        "lime",
        "cornflowerblue",
        "cornflowerblue",
        "purple",
        "purple",
        "red",
    )

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
        """Compose the quicklook plugin."""
        if self.plugin not in self.stats.getAllAsDict():
            # Will generate a NoMatches exception when stats are updated
            # TODO: catch it in the main update loop
            yield Label(f'{self.plugin.upper()} stats not available', id=f"{self.plugin}_not_available")
            return

        with Vertical(id=f"{self.plugin}"):
            yield Label('', id=f"{self.plugin}_cpu_name", classes="value default")
            with Grid():
                for field in ['cpu', 'mem', 'load']:
                    yield Label(field.upper(), classes="name")
                    yield ProgressBar(
                        total=100,
                        show_eta=False,
                        gradient=self.gradient,
                        id=f"{self.plugin}_{field}",
                        classes="value progressbar default",
                    )

    def update(self):
        """Update the stats."""
        if self.plugin not in self.stats.getAllAsDict():
            return False

        # Get the stats
        stats = self.stats.getAllAsDict()[self.plugin]

        # Get stats views
        views = self.stats.getAllViewsAsDict()[self.plugin]

        # Iter through the fields value to update as a Label
        for textual_field in self.query('.value').exclude(".progressbar"):
            # Remove the plugin name from the field id
            field = '_'.join(textual_field.id.split('_', maxsplit=1)[1:])
            # Ignore field not available in the stats
            if field not in stats:
                continue
            # Update value
            if (
                field in self.plugin_description
                and 'rate' in self.plugin_description[field]
                and self.plugin_description[field]['rate']
            ):
                field_stat = field + "_rate_per_sec"
            else:
                field_stat = field
            textual_field.update(auto_number(stats.get(field_stat, None)))
            # Update style
            style = views[field].get('decoration', 'DEFAULT')
            textual_field.classes = f"value {style.lower()}"

        # Iter through the fields value to update as a ProgressBar
        for textual_field in self.query('.value').filter(".progressbar"):
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

        return True
