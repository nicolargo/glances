#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Textual Glances table list component."""

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable

from glances.globals import auto_number, dictlist_first_key_value


class GlancesTuiListComponent(Container):
    """Plugin to display Glances stats with lists."""

    def __init__(
        self,
        plugin,
        stats=None,
        config=None,
        args=None,
        display_name=True,
        display_unit=True,
        first_field_title=True,
        columns_width=[],
        max_rows=20,
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
        self.columns_width = columns_width
        self.max_rows = max_rows

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
        yield DataTable(id=f"{self.plugin}", show_cursor=False, cell_padding=1)

    def on_mount(self) -> None:
        if self.plugin not in self.stats.getAllAsDict():
            self.disabled = True
            return

        dt = self.query_one(DataTable)

        # Init columns
        column_number = 0
        for k, v in self.plugin_description.items():
            if not v.get("display", True):
                continue
            styled_value = Text(
                self.plugin.upper() if column_number == 0 and self.first_field_title else v.get("short_name", k),
                justify="left" if column_number == 0 else "right",
            )

            self.columns[k] = dt.add_column(
                styled_value,
                width=self.columns_width[column_number] if column_number < len(self.columns_width) else None,
            )
            column_number += 1

        # Init rows
        for item in self.stats.getAllAsDict()[self.plugin][: self.max_rows]:
            self.rows[item[item['key']]] = dt.add_row(*[None for _ in self.header])

    def update(self):
        """Update the stats."""
        # Get the stats
        if self.plugin not in self.stats.getAllAsDict():
            return False

        stats = self.stats.getAllAsDict()[self.plugin]

        # TODO: manage add and remove of rows
        key = stats[0].get('key')
        for row_key, row_value in self.rows.items():
            new_values = dictlist_first_key_value(stats, key, row_key)
            first_column = True
            for column_key, column_value in self.columns.items():
                # Update value
                field = column_key
                if (
                    field in self.plugin_description
                    and 'rate' in self.plugin_description[field]
                    and self.plugin_description[field]['rate']
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
                self.query_one(f"#{self.plugin}").update_cell(row_value, column_value, styled_value, update_width=True)
                first_column = False

        # Set the height of the list (+ one for the header)
        self.query_one(f"#{self.plugin}").styles.height = min(len(stats), self.max_rows) + 1

        return True
