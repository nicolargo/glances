#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 configuration loader.

Loading model (v4-aligned, **single config file**):

1. Hardcoded DEFAULTS — codebase baseline.
2. **Exactly one** glances.conf file:
   - If ``-C <path>`` is passed, that file is used (no search, no
     fallback merging). A missing CLI path logs a WARNING and the
     loader proceeds with DEFAULTS only.
   - Otherwise the loader walks the v4 search path and stops at the
     first existing file:
       a. ``$XDG_CONFIG_HOME/glances/glances.conf`` (or
          ``~/.config/glances/glances.conf``)
       b. ``/etc/glances/glances.conf``
3. ``GLANCES_<SECTION>__<KEY>=<value>`` env vars overlay on top — kept
   because env-driven overrides are useful for containers / CI and are
   orthogonal to the config-file question.

Note: prior versions of this loader merged keys across all available
config files (the "layered overlay" design). That introduced surprising
cross-file inheritance — e.g. a legacy v4-era ``~/.config/glances/glances.conf``
silently leaking ``[memswap] careful=50`` onto v5's new opt-in
``memswap.sin``/``sout`` fields. The single-file model mirrors v4
``glances/config.py::config_file_paths`` (first existing wins).

Public API:
- ``get(section, option, default: T) -> T``   (typed accessor, T inferred)
- ``get_value(...)``                          (v4 alias)
- ``has_section(section) / sections()``       (introspection)
- ``as_dict() / as_dict_secure()``            (full / redacted dump)
- ``reload()``                                (re-run the resolution)
- ``loaded_sources``                          (the **at most one** file
                                              actually read)
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

        # 1. Defaults — codebase baseline. Always applied; not a "file
        # merge", just the set of keys the codebase guarantees to read.
        self._overlay_dict(self.DEFAULTS)

        # 2. Exactly one glances.conf — see module docstring for the
        # resolution rules. Missing-file paths are silent no-ops.
        chosen = self._resolve_config_file()
        if chosen is not None:
            self._overlay_file(chosen)

        # 3. Environment variable overlay (orthogonal to the file
        # question — useful for containers / CI / per-run overrides).
        self._overlay_env()

    def _resolve_config_file(self) -> Path | None:
        """Pick the single glances.conf to load, or ``None``.

        Honours ``-C`` first (any path, no search); otherwise walks the
        v4 search path (user → system) and returns the first existing
        entry. A non-existing ``-C`` path logs a WARNING; missing search
        entries are silent (operating without a config file is valid —
        the DEFAULTS layer suffices).
        """
        if self._cli_config_path:
            path = Path(self._cli_config_path)
            if path.is_file():
                return path
            logger.warning(
                "Config file %s (from -C / --config) does not exist — using DEFAULTS only.",
                path,
            )
            return None

        for path in self._search_paths():
            if path.is_file():
                return path
        return None

    def _search_paths(self) -> list[Path]:
        """v4-style search list: user config first, then system."""
        return [self._user_config_path(), self.SYSTEM_CONFIG_PATH]

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
