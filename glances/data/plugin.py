# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2023 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances Data Plugin class."""

from dataclasses import dataclass, field
import ujson

from glances.data.item import GlancesDataItem


@dataclass
class GlancesDataPlugin:
    """Class for a Glances Data plugin."""

    description: str = None
    name: str = None
    items: dict[str, GlancesDataItem] = field(default_factory=dict)

    def __post_init__(self):
        """Init the GlancesItem object."""
        # Init the last update time
        pass

    def add_item(self, item: GlancesDataItem):
        """Add a new item."""
        if item.name in self.items:
            self.items[item.name].update(item.value)
        else:
            self.items[item.name] = item

    def export(self, json=False):
        """Export the plugin data."""
        ret = {key: value.value for key, value in self.items.items()}
        if json:
            return ujson.dumps(ret)
        else:
            return ret
