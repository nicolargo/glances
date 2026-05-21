import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from glances.stats import GlancesStats


@pytest.fixture
def plugin_manager():
    """Create plugin manager instance."""
    return GlancesStats()


class Testload_additional_plugins:
    """Tests for helper methods and main method of load_additional_plugins."""

    def test_contains_plugin_model_returns_true(self, plugin_manager):
        """Should return True when PluginModel class exists."""

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_file = Path(tmpdir) / "model.py"

            plugin_file.write_text(
                "class PluginModel:\n    pass\n",
                encoding="utf-8",
            )

            result = plugin_manager._contains_plugin_model(plugin_file)

            assert result is True

    def test_contains_plugin_model_returns_false(self, plugin_manager):
        """Should return False when PluginModel class does not exist."""

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_file = Path(tmpdir) / "model.py"

            plugin_file.write_text(
                "class OtherClass:\n    pass\n",
                encoding="utf-8",
            )

            result = plugin_manager._contains_plugin_model(plugin_file)

            assert result is False

    def test_contains_plugin_model_handles_syntax_error(self, plugin_manager):
        """Should return False for invalid Python syntax."""

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_file = Path(tmpdir) / "model.py"

            plugin_file.write_text(
                "class PluginModel(\n",
                encoding="utf-8",
            )

            result = plugin_manager._contains_plugin_model(plugin_file)

            assert result is False

    def test_get_addl_plugins_returns_valid_plugins(self, plugin_manager):
        """Should return only valid plugin directories."""

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir)

            valid_plugin = plugin_dir / "valid_plugin"
            valid_plugin.mkdir()

            (valid_plugin / "model.py").write_text(
                "class PluginModel:\n    pass\n",
                encoding="utf-8",
            )

            invalid_plugin = plugin_dir / "invalid_plugin"
            invalid_plugin.mkdir()

            (invalid_plugin / "model.py").write_text(
                "class OtherClass:\n    pass\n",
                encoding="utf-8",
            )

            result = plugin_manager._get_addl_plugins(plugin_dir)

            assert result == ["valid_plugin"]

    @patch("glances.stats.import_module")
    @patch("glances.stats.Counter")
    def test_load_additional_plugins_loads_plugin(
        self,
        mock_counter,
        mock_import_module,
        plugin_manager,
    ):
        """Should load and register additional plugins."""

        mock_args = MagicMock()
        mock_args.plugin_dir = "/fake/plugins"
        mock_args.__contains__.return_value = True
        mock_plugin_model = MagicMock()

        mock_module = MagicMock()
        mock_module.PluginModel.return_value = mock_plugin_model

        mock_import_module.return_value = mock_module

        with patch.object(
            plugin_manager,
            "_get_addl_plugins",
            return_value=["test_plugin"],
        ):
            plugin_manager.load_additional_plugins(args=mock_args)

        assert "test_plugin" in plugin_manager._plugins
