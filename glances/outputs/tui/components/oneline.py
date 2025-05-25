#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Textual Glances table component."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Label

from glances.globals import auto_number


class GlancesTuiOneLineComponent(Container):
    """Plugin to display Glances stats in one line from a template."""

    def __init__(self, plugin, template, stats=None, config=None, args=None):
        super().__init__()

        # Init config
        self.config = config

        # Init args
        self.args = args

        # Init stats
        self.stats = stats

        # What to display
        self.template = template

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
            yield Label(f'{self.plugin.upper()} stats not available', id=f"{self.plugin}_not_available")
            return

        yield Label(self.template.format(**self.stats.getAllAsDict()[self.plugin]), id=self.plugin)

    def update(self):
        """Update the stats."""
        if self.plugin not in self.stats.getAllAsDict():
            return False

        # Get the stats
        stats = self.stats.getAllAsDict()[self.plugin]

        # Get stats views
        views = self.stats.getAllViewsAsDict()[self.plugin]

        # Iter through the fields value to update as a Label
        for textual_field in self.query('.value'):
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

        return True
