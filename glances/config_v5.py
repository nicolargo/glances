#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 configuration loader.

Layered overlay of (ascending priority):
1. Hardcoded DEFAULTS
2. /etc/glances/glances.conf
3. $XDG_CONFIG_HOME/glances/glances.conf (fallback ~/.config/glances/glances.conf)
4. $GLANCES_CONFIG_FILE
5. -C <path> CLI flag
6. GLANCES_<SECTION>__<KEY>=<value> environment variables (highest)

Each layer overlays specific keys onto the previous; layers are not
replaced in bulk. This is a semantic change vs. v4 (which used
"first-found-wins"), accepted as part of the v5 clean break.

Public API:
- get(section, option, default: T) -> T   (typed accessor, T inferred)
- get_value(...)                          (v4 alias)
- has_section(section) / sections()       (introspection)
- as_dict() / as_dict_secure()            (full / redacted dump)
- reload()                                (re-run the overlay chain)
- loaded_sources                          (files actually read, in order)
"""

from __future__ import annotations

import configparser
import logging
import os
from pathlib import Path
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _coerce_bool(raw: str) -> bool:
    """Helper to coerce config values to bool, accepting common string representations."""
    s = raw.strip().lower()
    if s in {"1", "true", "yes", "on"}:
        return True
    if s in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Cannot interpret {raw!r} as boolean")


def _coerce_list(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


class GlancesConfigV5:
    """Layered configuration loader for Glances v5."""

    # Hardcoded baseline. Phase 0 keeps this minimal; later phases will add
    # the keys they reference. The DEFAULTS contract is: every key read by
    # the codebase must have a default here OR be passed explicitly via the
    # `default=` argument of get().
    DEFAULTS: dict[str, dict[str, Any]] = {
        "global": {
            "refresh_time": 2,
        },
        "outputs": {
            "api_doc": True,
        },
    }

    # Substring match (case-insensitive) on the option name. Any option whose
    # name contains one of these tokens is redacted by as_dict_secure() —
    # CVE-2026-32609. Substring match is intentionally permissive (over-redact
    # rather than under-redact).
    SECRET_KEYS: set[str] = {
        "password",
        "passphrase",
        "token",
        "api_key",
        "secret",
        "ssl_key",
        "ssl_cert",
        "snmp_community",
        "snmp_user",
        "snmp_authkey",
        "snmp_privkey",
        "uri",  # may embed credentials inline (CVE-2026-32633)
    }

    SECRET_REDACTED: str = "***"

    # Class-level paths, indirected for testability (patch.object friendly).
    SYSTEM_CONFIG_PATH: Path = Path("/etc/glances/glances.conf")
    USER_CONFIG_RELATIVE: Path = Path("glances/glances.conf")

    ENV_PREFIX: str = "GLANCES_"
    ENV_SEPARATOR: str = "__"  # split on first occurrence

    def __init__(self, cli_config_path: str | None = None) -> None:
        self._cli_config_path: str | None = cli_config_path
        self._loaded_sources: list[Path] = []
        self._merged: dict[str, dict[str, Any]] = {}
        self._load()

    # ------------------------------------------------------------------ load

    def _load(self) -> None:
        self._loaded_sources = []
        self._merged = {}

        # 1. Defaults
        self._overlay_dict(self.DEFAULTS)

        # 2. /etc
        self._overlay_file(self.SYSTEM_CONFIG_PATH)

        # 3. XDG user config
        self._overlay_file(self._user_config_path())

        # 4. $GLANCES_CONFIG_FILE
        env_path = os.environ.get("GLANCES_CONFIG_FILE")
        if env_path:
            self._overlay_file(Path(env_path))

        # 5. -C CLI flag
        if self._cli_config_path:
            self._overlay_file(Path(self._cli_config_path))

        # 6. Environment variable overlay (highest priority)
        self._overlay_env()

    def _user_config_path(self) -> Path:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        if xdg:
            return Path(xdg) / self.USER_CONFIG_RELATIVE
        return Path.home() / ".config" / self.USER_CONFIG_RELATIVE

    def _overlay_dict(self, data: dict[str, dict[str, Any]]) -> None:
        for section, options in data.items():
            self._merged.setdefault(section, {})
            for key, value in options.items():
                self._merged[section][key] = value

    def _overlay_file(self, path: Path) -> None:
        if not path.is_file():
            return
        parser = configparser.ConfigParser()
        try:
            parser.read(path)
        except configparser.Error as e:
            logger.warning("Failed to parse config file %s: %s", path, e)
            return
        for section in parser.sections():
            target = self._merged.setdefault(section, {})
            for key, value in parser.items(section):
                target[key] = value
        self._loaded_sources.append(path)

    def _overlay_env(self) -> None:
        for env_key, env_value in os.environ.items():
            if not env_key.startswith(self.ENV_PREFIX):
                continue
            stripped = env_key[len(self.ENV_PREFIX) :]
            if self.ENV_SEPARATOR not in stripped:
                continue
            section, _, key = stripped.partition(self.ENV_SEPARATOR)
            section = section.lower()
            key = key.lower()
            if not section or not key:
                continue
            self._merged.setdefault(section, {})[key] = env_value

    # ------------------------------------------------------------------ read

    def get(self, section: str, option: str, default: T) -> T:
        """Return option from section coerced to type(default), else default."""
        raw = self._merged.get(section, {}).get(option)
        if raw is None:
            return default
        return self._coerce(raw, type(default))

    def get_value(self, section: str, option: str, default: T) -> T:
        """v4 compatibility alias for get()."""
        return self.get(section, option, default)

    @staticmethod
    def _coerce(raw: Any, target_type: type) -> Any:
        # Native types in DEFAULTS flow through unchanged.
        if not isinstance(raw, str):
            return raw
        if target_type is str:
            return raw
        if target_type is bool:
            return _coerce_bool(raw)
        if target_type is int:
            return int(raw)
        if target_type is float:
            return float(raw)
        if target_type is list:
            return _coerce_list(raw)
        raise TypeError(f"Unsupported config target type {target_type!r} for value {raw!r}")

    # ------------------------------------------------------------ introspect

    def has_section(self, section: str) -> bool:
        return section in self._merged

    def sections(self) -> list[str]:
        return list(self._merged.keys())

    def as_dict(self) -> dict[str, dict[str, Any]]:
        return {s: dict(opts) for s, opts in self._merged.items()}

    def as_dict_secure(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for section, options in self._merged.items():
            result[section] = {
                key: (self.SECRET_REDACTED if self._is_secret_key(key) else value) for key, value in options.items()
            }
        return result

    @classmethod
    def _is_secret_key(cls, key: str) -> bool:
        key_lower = key.lower()
        return any(token in key_lower for token in cls.SECRET_KEYS)

    # ---------------------------------------------------------------- reload

    def reload(self) -> None:
        """Re-run the full layered overlay chain.

        Public hook for hot-reload. The polling loop that calls this every 5s
        for safe-to-reload keys is deferred to Phase 4 (mtime polling task).
        """
        self._load()

    @property
    def loaded_sources(self) -> list[Path]:
        """Files actually read, in load order."""
        return list(self._loaded_sources)
