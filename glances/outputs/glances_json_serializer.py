#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""JSON serialization utilities for Glances output layer."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from glances.globals import json_dumps, json_loads
from glances.logger import logger


class PluginSerializationError:
    """Represents a serialization error for a plugin."""

    def __init__(self, plugin_name: str, error_message: str):
        self.plugin_name = plugin_name
        self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": True,
            "plugin": self.plugin_name,
            "message": self.error_message,
        }


class GlancesJSONSerializer:
    """Serializer that produces consistent, valid JSON output from plugin data."""

    def __init__(self, include_errors: bool = True, include_metadata: bool = False):
        """
        Initialize the JSON serializer.

        Args:
            include_errors: If True, include error information for failed plugins.
            include_metadata: If True, include metadata like timestamp.
        """
        self.include_errors = include_errors
        self.include_metadata = include_metadata

    def normalize_value(self, value: Any) -> Any:
        """Normalize a value to be JSON-serializable."""
        if value is None:
            return None

        if isinstance(value, bytes):
            return value.decode('utf-8', errors='replace')

        if isinstance(value, datetime):
            return value.isoformat()

        if isinstance(value, (int, float, str, bool)):
            return value

        if isinstance(value, dict):
            return {str(k): self.normalize_value(v) for k, v in value.items()}

        if isinstance(value, (list, tuple)):
            return [self.normalize_value(item) for item in value]

        if hasattr(value, '_asdict'):
            return self.normalize_value(value._asdict())

        return str(value)

    def serialize_plugin_data(
        self, plugin_name: str, raw_data: Any
    ) -> Optional[Union[Dict[str, Any], List[Any], str]]:
        """
        Serialize plugin data to a JSON-compatible format.

        Args:
            plugin_name: Name of the plugin.
            raw_data: Raw data from the plugin (can be bytes, dict, list, etc.).

        Returns:
            JSON-compatible data structure, or error dict if serialization fails.
        """
        try:
            if raw_data is None:
                return None

            if isinstance(raw_data, bytes):
                decoded = raw_data.decode('utf-8', errors='replace')
                try:
                    return json_loads(decoded)
                except Exception:
                    return self.normalize_value(decoded)

            return self.normalize_value(raw_data)

        except Exception as e:
            logger.debug(f"Error serializing plugin {plugin_name}: {e}")
            if self.include_errors:
                return PluginSerializationError(plugin_name, str(e)).to_dict()
            return None

    def serialize_plugins(
        self, stats: Any, plugin_list: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Serialize data from multiple plugins into a single JSON object.

        Args:
            stats: The GlancesStats object.
            plugin_list: List of plugin names to include. If None, includes all enabled.

        Returns:
            Dictionary containing all plugin data.
        """
        result: Dict[str, Any] = {}
        errors: List[Dict[str, Any]] = []

        if plugin_list is None:
            plugin_list = stats.getPluginsList()

        for plugin_name in plugin_list:
            plugin_data = self._get_plugin_data(stats, plugin_name)
            if plugin_data is not None:
                if isinstance(plugin_data, dict) and plugin_data.get("error"):
                    errors.append(plugin_data)
                else:
                    result[plugin_name] = plugin_data

        if self.include_metadata:
            result["_metadata"] = {
                "timestamp": datetime.now().isoformat(),
                "plugin_count": len(result),
            }

        if self.include_errors and errors:
            result["_errors"] = errors

        return result

    def _get_plugin_data(self, stats: Any, plugin_name: str) -> Any:
        """Get and serialize data from a single plugin."""
        try:
            if plugin_name not in stats.getPluginsList():
                return None

            plugin = stats.get_plugin(plugin_name)
            if plugin is None or not plugin.is_enabled():
                return None

            json_data = plugin.get_json()
            return self.serialize_plugin_data(plugin_name, json_data)

        except Exception as e:
            logger.debug(f"Error getting data from plugin {plugin_name}: {e}")
            if self.include_errors:
                return PluginSerializationError(plugin_name, str(e)).to_dict()
            return None

    def to_json_string(self, data: Any) -> str:
        """Convert data to a JSON string."""
        try:
            result = json_dumps(data)
            if isinstance(result, bytes):
                return result.decode('utf-8')
            return result
        except Exception as e:
            logger.error(f"Error converting to JSON string: {e}")
            return '{"error": "Failed to serialize data"}'

    def serialize_to_string(
        self, stats: Any, plugin_list: Optional[List[str]] = None
    ) -> str:
        """
        Serialize plugins to a JSON string.

        Args:
            stats: The GlancesStats object.
            plugin_list: List of plugin names to include.

        Returns:
            JSON string containing all plugin data.
        """
        data = self.serialize_plugins(stats, plugin_list)
        return self.to_json_string(data)
