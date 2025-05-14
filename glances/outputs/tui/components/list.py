#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Textual Glances table list component."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Label


class GlancesTuiListComponent(Container):
    """Plugin to display Glances stats with lists."""

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
        self.header = [k for k, v in self.plugin_description.items() if v.get("display", True)]
        self.columns = {}
        self.rows = {}

    def compose(self) -> ComposeResult:
        if self.plugin not in self.stats.getAllAsDict():
            # Will generate a NoMatches exception when stats are updated
            # TODO: catch it in the main update loop
            # WARNING: Not GOOD, because if it you are here then the on_mount will fail...
            yield Label(f'{self.plugin.upper()} stats not available', id=f"{self.plugin}_not_available")
            return

        yield DataTable(id=f"{self.plugin}", show_cursor=False)

    def on_mount(self) -> None:
        dt = self.query_one(DataTable)

        self.columns = dict(
            zip(
                self.header,
                dt.add_columns(
                    *[
                        v.get('short_name', None) if 'short_name' in v else k
                        for k, v in self.plugin_description.items()
                        if v.get("display", True)
                    ]
                ),
            )
        )

        for item in self.stats.getAllAsDict()[self.plugin]:
            self.rows[item[item['key']]] = dt.add_row(*[None for _ in self.header])
