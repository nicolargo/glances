#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Textual Glances table component."""

from textual.app import ComposeResult
from textual.containers import Container, Grid
from textual.widgets import Label

from glances.plugins.plugin.model import fields_unit_short


class GlancesTuiTableComponent(Container):
    """Plugin to display Glances stats for most of Glances plugins.
    It's a simple table with the field name and the value.
    Display order: from left to right, top to bottom.
    """

    def __init__(
        self, plugin, stats=None, config=None, args=None, display_name=True, display_unit=True, first_field_title=True
    ):
        super().__init__()

        # Init config
        self.config = config

        # Init args
        self.args = args

        # Init stats
        self.stats = stats

        # What to display
        self.display_name = display_name
        self.display_unit = display_unit
        self.first_field_title = first_field_title

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

        with Grid(id=f"{self.plugin}"):
            first_field = True
            for field in self.plugin_description.keys():
                # Ignore field if the display=False option is defined in the description
                if not self.plugin_description[field].get('display', True):
                    continue
                if self.display_name:
                    # Get the field short name
                    if 'short_name' in self.plugin_description[field]:
                        field_name = self.plugin_description[field]['short_name']
                    else:
                        field_name = field
                    yield Label(field_name, classes="name title" if self.first_field_title and first_field else "name")
                    first_field = False
                # Display value (with decoration classes)
                yield Label('', id=f"{self.plugin}_{field}", classes="value default")
                # Display unit
                if self.display_unit:
                    if field in self.plugin_description and 'unit' in self.plugin_description[field]:
                        field_unit = fields_unit_short.get(self.plugin_description[field]['unit'], '')
                    else:
                        field_unit = ''
                    yield Label(field_unit, classes="unit")
