#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Stdout JSON interface class."""

import time
from typing import Any, List, Optional

from glances.globals import printandflush
from glances.logger import logger
from glances.outputs.glances_json_serializer import GlancesJSONSerializer


class GlancesStdoutJson:
    """This class manages the Stdout JSON display."""

    DEFAULT_DURATION: int = 3
    FALLBACK_ERROR_JSON: str = '{"error": "Failed to serialize stats"}'

    def __init__(self, config: Optional[Any] = None, args: Optional[Any] = None):
        self.config = config
        self.args = args
        self._serializer: Optional[GlancesJSONSerializer] = None
        self._plugins_list: List[str] = []

        self._init_plugins_list()
        self._init_serializer()

    def _init_plugins_list(self) -> None:
        """Initialize the plugins list from args with validation."""
        try:
            self._plugins_list = self.build_list()
        except Exception as e:
            logger.error(f"Failed to build plugins list: {e}")
            self._plugins_list = []

    def _init_serializer(self) -> None:
        """Initialize the JSON serializer with error handling."""
        try:
            self._serializer = GlancesJSONSerializer(
                include_errors=True,
                include_metadata=False
            )
        except Exception as e:
            logger.error(f"Failed to initialize JSON serializer: {e}")
            self._serializer = None

    @property
    def plugins_list(self) -> List[str]:
        """Return the list of plugins to display."""
        return self._plugins_list

    @property
    def serializer(self) -> Optional[GlancesJSONSerializer]:
        """Return the JSON serializer instance."""
        return self._serializer

    def build_list(self) -> List[str]:
        """Return a list of plugin names from self.args.stdout_json.

        Returns:
            List of plugin names parsed from the comma-separated argument.
        """
        if self.args is None:
            logger.debug("args is None, returning empty plugin list")
            return []

        stdout_json_arg = getattr(self.args, 'stdout_json', None)
        if stdout_json_arg is None:
            logger.debug("stdout_json argument is None, returning empty plugin list")
            return []

        if not isinstance(stdout_json_arg, str):
            logger.warning(f"stdout_json is not a string (got {type(stdout_json_arg).__name__}), "
                          "attempting string conversion")
            try:
                stdout_json_arg = str(stdout_json_arg)
            except Exception as e:
                logger.error(f"Failed to convert stdout_json to string: {e}")
                return []

        raw_plugins = stdout_json_arg.split(',')
        plugins = [p.strip() for p in raw_plugins if p.strip()]

        if not plugins:
            logger.debug("No plugins found after parsing stdout_json")

        return plugins

    def end(self) -> None:
        """Clean up resources (currently no-op)."""
        pass

    def update(
        self,
        stats: Any,
        duration: int = 3,
        cs_status: Optional[Any] = None,
        return_to_browser: bool = False
    ) -> bool:
        """Display stats in JSON format to stdout.

        Args:
            stats: The GlancesStats object containing plugin data.
            duration: Time to sleep after output (seconds). 0 or negative to skip.
            cs_status: Client/server status (unused in stdout mode).
            return_to_browser: Whether to return to browser (unused in stdout mode).

        Returns:
            True if output was successful, False otherwise.
        """
        json_output = self._serialize_stats(stats)
        output_success = self._output_json(json_output)
        self._wait_duration(duration)
        return output_success

    def _serialize_stats(self, stats: Any) -> str:
        """Serialize stats to JSON string with fallback on error.

        Args:
            stats: The GlancesStats object to serialize.

        Returns:
            JSON string of the serialized stats, or error JSON on failure.
        """
        if self._serializer is None:
            logger.error("Serializer not initialized, attempting re-initialization")
            self._init_serializer()
            if self._serializer is None:
                return self.FALLBACK_ERROR_JSON

        if stats is None:
            logger.warning("stats object is None")
            return '{}'

        try:
            return self._serializer.serialize_to_string(stats, self._plugins_list)
        except Exception as e:
            logger.error(f"Failed to serialize stats: {e}")
            return self.FALLBACK_ERROR_JSON

    def _output_json(self, json_output: str) -> bool:
        """Output JSON string to stdout.

        Args:
            json_output: The JSON string to output.

        Returns:
            True if output was successful, False otherwise.
        """
        if json_output is None:
            json_output = '{}'

        try:
            printandflush(json_output)
            return True
        except (IOError, OSError) as e:
            logger.error(f"Failed to write JSON to stdout: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error writing to stdout: {e}")
            return False

    def _wait_duration(self, duration: int) -> None:
        """Wait for the specified duration.

        Args:
            duration: Time to sleep in seconds. Skipped if <= 0.
        """
        if duration <= 0:
            return

        try:
            time.sleep(duration)
        except KeyboardInterrupt:
            logger.debug("Sleep interrupted by KeyboardInterrupt")
            raise
        except Exception as e:
            logger.debug(f"Sleep interrupted: {e}")
