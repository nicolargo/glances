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
from typing import List
from glances.data.item import GlancesDataItem, GlancesDataItems


@dataclass
class GlancesDataPlugin:
    """Class for a Glances Data plugin."""

    description: str = None
    name: str = None
    fields_description: dict = field(default_factory=dict)
    data: List[GlancesDataItems] = field(default_factory=list)

    def __post_init__(self):
        """Set the data model from the fields_description variable."""
        # for key, value in self.fields_description.items():
        #     self.add_item(GlancesDataItem(**value, name=key))
        pass

    def has_no_data(self):
        """Return True if the plugin has no data."""
        return len(self.data) == 0

    def has_data(self):
        """Return True if the plugin has data."""
        return not self.has_no_data()

    def key(self):
        """If a key is defined in the fields_description, return the value."""
        if 'key' in self.fields_description.keys():
            return self.fields_description['key'].get('value', None)
        else:
            return None

    def items(self):
        """Return the list of items.
        Assumption: items are the same in all dict in case of list of dicts."""
        if self.has_no_data():
            return []
        else:
            return self.data[0].items

    def data_index(self, key_value: str) -> int:
        """Return the index of the item where key=key_value.
        Return -1 if not found"""
        if not self.key():
            return -1
        else:
            for i, it in enumerate(self.data):
                if self.key() in it.items and it.items[self.key()].value == key_value:
                    return i
            return -1

    def update_data(self, data: dict):
        """Update the plugin data with the given dict."""
        # Start with the key
        key_value = None
        if 'key' in data.keys():
            key_value = data[data['key']]
            self._update_data_item(data['key'],
                                   key_value,
                                   key=key_value)
        # Then others fields
        for name, value in data.items():
            if name != 'key':
                self._update_data_item(name, value, key=key_value)

    def _add_data(self, data: GlancesDataItem):
        """Add a new GlancesDataItem to the plugin."""
        items = GlancesDataItems()
        items.add_item(data)
        self.data.append(items)

    # TODO: Refactor this function
    def _update_data_item(self, name, value, key=None):
        """Update the item called name with the given value."""
        if not key:
            # CPU, Mem, Load...
            if self.has_no_data():
                # Create first data
                self._add_data(GlancesDataItem(**self.fields_description[name],
                                               name=name))
            if name not in self.items():
                # Add new item in existing data
                self.data[self.data_index(name)].add_item(GlancesDataItem(**self.fields_description[name],
                                                          name=name))
            # Update item value of existing data
            self.data[self.data_index(name)].update_item(name, value)
        else:
            # Network, Fs, DiskIO...
            if self.has_no_data() or self.data_index(key) == -1:
                # Create first data
                # Note: pop the value key from the fields_description to avoid duplicate key value error
                without_value = self.fields_description[name].copy()
                without_value.pop('value', None)
                self._add_data(GlancesDataItem(**without_value,
                                               name=name))
            if self.data_index(key) not in self.data:
                # Add new item in existing data
                # Note: pop the value key from the fields_description to avoid duplicate key value error
                without_value = self.fields_description[name].copy()
                without_value.pop('value', None)
                self.data[self.data_index(key)].add_item(GlancesDataItem(**without_value,
                                                         name=name))
            # Update item value of existing data
            self.data[self.data_index(key)].update_item(name, value)

    # TODO: add unitest for this untested function
    def get_item(self, name, default=None, key=None):
        """Return the value of the item called."""
        if not self.key():
            return self.data[0].get_item(name, default)
        elif key:
            return self.data[self.data_index(key)].get_item(name, default)

    def export(self, json=False):
        """Export the plugin data."""
        if not self.key():
            return self.data[0].export(json)
        else:
            return [d.export(json) for d in self.data]
