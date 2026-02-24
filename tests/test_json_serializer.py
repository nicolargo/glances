#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the JSON serializer module.

These tests are designed to be runnable standalone without requiring
the full Glances initialization, for faster CI feedback.
"""

import json
import os
import sys
import types
import unittest
from datetime import datetime
from unittest.mock import Mock


def setup_mock_modules():
    """Set up mock modules to allow importing the serializer without full Glances."""
    # Create mock glances package
    if 'glances' not in sys.modules:
        glances_pkg = types.ModuleType('glances')
        glances_pkg.__path__ = [os.path.join(os.path.dirname(__file__), '..', 'glances')]
        sys.modules['glances'] = glances_pkg

    # Create mock glances.outputs package
    if 'glances.outputs' not in sys.modules:
        glances_outputs = types.ModuleType('glances.outputs')
        sys.modules['glances.outputs'] = glances_outputs

    # Create mock globals
    if 'glances.globals' not in sys.modules:
        glances_globals = types.ModuleType('glances.globals')
        glances_globals.json_dumps = lambda data: json.dumps(data, default=str).encode('utf-8')
        glances_globals.json_loads = lambda data: json.loads(
            data.decode('utf-8') if isinstance(data, bytes) else data
        )
        sys.modules['glances.globals'] = glances_globals

    # Create mock logger
    if 'glances.logger' not in sys.modules:

        class MockLogger:
            def debug(self, msg):
                pass

            def error(self, msg):
                pass

            def info(self, msg):
                pass

        glances_logger = types.ModuleType('glances.logger')
        glances_logger.logger = MockLogger()
        sys.modules['glances.logger'] = glances_logger


# Setup mocks BEFORE any other imports
setup_mock_modules()

# Now we can import our serializer
# Direct exec to avoid import conflicts
serializer_path = os.path.join(
    os.path.dirname(__file__), '..', 'glances', 'outputs', 'glances_json_serializer.py'
)
with open(serializer_path, 'r') as f:
    code = f.read()
    exec(compile(code, serializer_path, 'exec'), sys.modules['glances.outputs'].__dict__)

PluginSerializationError = sys.modules['glances.outputs'].PluginSerializationError
GlancesJSONSerializer = sys.modules['glances.outputs'].GlancesJSONSerializer


class TestPluginSerializationError(unittest.TestCase):
    """Test the PluginSerializationError class."""

    def test_error_to_dict(self):
        error = PluginSerializationError("cpu", "Test error")
        result = error.to_dict()

        self.assertEqual(result["error"], True)
        self.assertEqual(result["plugin"], "cpu")
        self.assertEqual(result["message"], "Test error")


class TestGlancesJSONSerializer(unittest.TestCase):
    """Test the GlancesJSONSerializer class."""

    def setUp(self):
        self.serializer = GlancesJSONSerializer()

    def test_normalize_none(self):
        self.assertIsNone(self.serializer.normalize_value(None))

    def test_normalize_bytes(self):
        result = self.serializer.normalize_value(b'hello')
        self.assertEqual(result, 'hello')

    def test_normalize_datetime(self):
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = self.serializer.normalize_value(dt)
        self.assertEqual(result, '2024-01-15T10:30:00')

    def test_normalize_primitives(self):
        self.assertEqual(self.serializer.normalize_value(42), 42)
        self.assertEqual(self.serializer.normalize_value(3.14), 3.14)
        self.assertEqual(self.serializer.normalize_value('test'), 'test')
        self.assertEqual(self.serializer.normalize_value(True), True)

    def test_normalize_dict(self):
        data = {'a': 1, 'b': b'bytes', 'c': None}
        result = self.serializer.normalize_value(data)

        self.assertEqual(result['a'], 1)
        self.assertEqual(result['b'], 'bytes')
        self.assertIsNone(result['c'])

    def test_normalize_list(self):
        data = [1, b'bytes', 'string', None]
        result = self.serializer.normalize_value(data)

        self.assertEqual(result, [1, 'bytes', 'string', None])

    def test_normalize_nested(self):
        data = {'outer': {'inner': [1, 2, {'deep': b'value'}]}}
        result = self.serializer.normalize_value(data)

        self.assertEqual(result['outer']['inner'][2]['deep'], 'value')

    def test_serialize_plugin_data_none(self):
        result = self.serializer.serialize_plugin_data('test', None)
        self.assertIsNone(result)

    def test_serialize_plugin_data_bytes_json(self):
        data = b'{"cpu": 50, "memory": 75}'
        result = self.serializer.serialize_plugin_data('test', data)

        self.assertEqual(result['cpu'], 50)
        self.assertEqual(result['memory'], 75)

    def test_serialize_plugin_data_bytes_invalid_json(self):
        data = b'not valid json'
        result = self.serializer.serialize_plugin_data('test', data)
        self.assertEqual(result, 'not valid json')

    def test_serialize_plugin_data_dict(self):
        data = {'cpu': 50, 'memory': 75}
        result = self.serializer.serialize_plugin_data('test', data)

        self.assertEqual(result['cpu'], 50)
        self.assertEqual(result['memory'], 75)

    def test_to_json_string_dict(self):
        data = {'key': 'value', 'number': 42}
        result = self.serializer.to_json_string(data)

        parsed = json.loads(result)
        self.assertEqual(parsed['key'], 'value')
        self.assertEqual(parsed['number'], 42)

    def test_to_json_string_list(self):
        data = [1, 2, 3, 'four']
        result = self.serializer.to_json_string(data)

        parsed = json.loads(result)
        self.assertEqual(parsed, [1, 2, 3, 'four'])

    def test_serialize_plugins_empty_list(self):
        mock_stats = Mock()
        mock_stats.getPluginsList.return_value = []

        result = self.serializer.serialize_plugins(mock_stats, [])
        self.assertEqual(result, {})

    def test_serialize_plugins_with_data(self):
        mock_plugin = Mock()
        mock_plugin.is_enabled.return_value = True
        mock_plugin.get_json.return_value = b'{"value": 42}'

        mock_stats = Mock()
        mock_stats.getPluginsList.return_value = ['test_plugin']
        mock_stats.get_plugin.return_value = mock_plugin

        result = self.serializer.serialize_plugins(mock_stats, ['test_plugin'])

        self.assertIn('test_plugin', result)
        self.assertEqual(result['test_plugin']['value'], 42)

    def test_serialize_plugins_plugin_not_enabled(self):
        mock_plugin = Mock()
        mock_plugin.is_enabled.return_value = False

        mock_stats = Mock()
        mock_stats.getPluginsList.return_value = ['disabled_plugin']
        mock_stats.get_plugin.return_value = mock_plugin

        result = self.serializer.serialize_plugins(mock_stats, ['disabled_plugin'])
        self.assertNotIn('disabled_plugin', result)

    def test_serialize_plugins_plugin_not_found(self):
        mock_stats = Mock()
        mock_stats.getPluginsList.return_value = []
        mock_stats.get_plugin.return_value = None

        result = self.serializer.serialize_plugins(mock_stats, ['nonexistent'])
        self.assertNotIn('nonexistent', result)

    def test_serialize_plugins_with_metadata(self):
        serializer = GlancesJSONSerializer(include_metadata=True)

        mock_stats = Mock()
        mock_stats.getPluginsList.return_value = []

        result = serializer.serialize_plugins(mock_stats, [])

        self.assertIn('_metadata', result)
        self.assertIn('timestamp', result['_metadata'])
        self.assertIn('plugin_count', result['_metadata'])

    def test_serialize_to_string_produces_valid_json(self):
        mock_plugin = Mock()
        mock_plugin.is_enabled.return_value = True
        mock_plugin.get_json.return_value = b'{"cpu": 25.5}'

        mock_stats = Mock()
        mock_stats.getPluginsList.return_value = ['cpu']
        mock_stats.get_plugin.return_value = mock_plugin

        result = self.serializer.serialize_to_string(mock_stats, ['cpu'])

        parsed = json.loads(result)
        self.assertIn('cpu', parsed)

    def test_serialize_handles_unicode(self):
        data = {'name': 'café ☕', 'value': 42}
        result = self.serializer.serialize_plugin_data('test', data)

        self.assertEqual(result['name'], 'café ☕')


class TestSerializerEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def test_serializer_with_errors_disabled(self):
        serializer = GlancesJSONSerializer(include_errors=False)

        mock_plugin = Mock()
        mock_plugin.is_enabled.return_value = True
        mock_plugin.get_json.side_effect = Exception("Plugin error")

        mock_stats = Mock()
        mock_stats.getPluginsList.return_value = ['failing_plugin']
        mock_stats.get_plugin.return_value = mock_plugin

        result = serializer.serialize_plugins(mock_stats, ['failing_plugin'])
        self.assertNotIn('_errors', result)
        self.assertNotIn('failing_plugin', result)

    def test_serializer_with_errors_enabled(self):
        serializer = GlancesJSONSerializer(include_errors=True)

        mock_plugin = Mock()
        mock_plugin.is_enabled.return_value = True
        mock_plugin.get_json.side_effect = Exception("Plugin error")

        mock_stats = Mock()
        mock_stats.getPluginsList.return_value = ['failing_plugin']
        mock_stats.get_plugin.return_value = mock_plugin

        result = serializer.serialize_plugins(mock_stats, ['failing_plugin'])
        self.assertIn('_errors', result)

    def test_multiple_plugins_one_fails(self):
        """Verify that one plugin failing doesn't break the entire output."""
        serializer = GlancesJSONSerializer(include_errors=True)

        good_plugin = Mock()
        good_plugin.is_enabled.return_value = True
        good_plugin.get_json.return_value = b'{"status": "ok"}'

        bad_plugin = Mock()
        bad_plugin.is_enabled.return_value = True
        bad_plugin.get_json.side_effect = Exception("Failed")

        mock_stats = Mock()
        mock_stats.getPluginsList.return_value = ['good', 'bad']

        def get_plugin(name):
            return good_plugin if name == 'good' else bad_plugin

        mock_stats.get_plugin.side_effect = get_plugin

        result = serializer.serialize_plugins(mock_stats, ['good', 'bad'])

        self.assertIn('good', result)
        self.assertEqual(result['good']['status'], 'ok')
        self.assertIn('_errors', result)

    def test_empty_bytes_input(self):
        serializer = GlancesJSONSerializer()
        result = serializer.serialize_plugin_data('test', b'')
        self.assertEqual(result, '')

    def test_all_plugins_fail_still_produces_valid_json(self):
        """Verify that even total failure produces parseable JSON."""
        serializer = GlancesJSONSerializer(include_errors=True)

        failing_plugin = Mock()
        failing_plugin.is_enabled.return_value = True
        failing_plugin.get_json.side_effect = Exception("Total failure")

        mock_stats = Mock()
        mock_stats.getPluginsList.return_value = ['fail1', 'fail2']
        mock_stats.get_plugin.return_value = failing_plugin

        result = serializer.serialize_to_string(mock_stats, ['fail1', 'fail2'])
        parsed = json.loads(result)  # Should not raise
        self.assertIn('_errors', parsed)

    def test_empty_plugins_produces_valid_json(self):
        """Verify that empty plugin list produces valid JSON."""
        serializer = GlancesJSONSerializer()

        mock_stats = Mock()
        mock_stats.getPluginsList.return_value = []

        result = serializer.serialize_to_string(mock_stats, [])
        parsed = json.loads(result)
        self.assertEqual(parsed, {})

    def test_output_structure_consistency(self):
        """Verify the output structure is consistent."""
        serializer = GlancesJSONSerializer(include_errors=True, include_metadata=True)

        mock_plugin = Mock()
        mock_plugin.is_enabled.return_value = True
        mock_plugin.get_json.return_value = b'{"value": 100}'

        mock_stats = Mock()
        mock_stats.getPluginsList.return_value = ['cpu']
        mock_stats.get_plugin.return_value = mock_plugin

        result = serializer.serialize_plugins(mock_stats, ['cpu'])

        # Verify structure
        self.assertIsInstance(result, dict)
        self.assertIn('cpu', result)
        self.assertIn('_metadata', result)
        self.assertIsInstance(result['_metadata'], dict)
        self.assertIn('timestamp', result['_metadata'])
        self.assertIn('plugin_count', result['_metadata'])


if __name__ == '__main__':
    unittest.main()
