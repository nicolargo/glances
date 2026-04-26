#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for GlancesConfigV5.

Test stack: unittest + unittest.mock (architecture decision §9, no pytest).

Tests cover:
- Layered priority: defaults < /etc < XDG < $GLANCES_CONFIG_FILE < -C < env
- XDG_CONFIG_HOME respected with fallback to ~/.config
- Typed accessor: int, float, bool variants, list, str, missing keys
- Bool parsing rejects unknown values
- as_dict_secure() redacts secret-like keys, preserves the rest
- reload() picks up file changes
- loaded_sources reports the file load order
- has_section / sections introspection
"""

from __future__ import annotations

import os
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from glances.config_v5 import GlancesConfigV5


class _ConfigCase(unittest.TestCase):
    """Base class providing an isolated config environment.

    - All real env vars are cleared.
    - SYSTEM_CONFIG_PATH is redirected to <tmp>/etc/glances.conf.
    - XDG_CONFIG_HOME is set to <tmp>/xdg.
    - HOME is set to <tmp>/home (fallback when XDG is unset).
    """

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tmp_path = Path(self.tmp.name)

        env_patcher = patch.dict(os.environ, {}, clear=True)
        env_patcher.start()
        self.addCleanup(env_patcher.stop)

        # Default isolation: XDG and HOME inside the tmp dir
        os.environ["XDG_CONFIG_HOME"] = str(self.tmp_path / "xdg")
        os.environ["HOME"] = str(self.tmp_path / "home")

        etc_patcher = patch.object(
            GlancesConfigV5,
            "SYSTEM_CONFIG_PATH",
            self.tmp_path / "etc" / "glances.conf",
        )
        etc_patcher.start()
        self.addCleanup(etc_patcher.stop)

    # --- Helpers -----------------------------------------------------------

    def write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).lstrip("\n"))

    @property
    def etc_path(self) -> Path:
        return self.tmp_path / "etc" / "glances.conf"

    @property
    def xdg_path(self) -> Path:
        return self.tmp_path / "xdg" / "glances" / "glances.conf"

    @property
    def home_path(self) -> Path:
        return self.tmp_path / "home" / ".config" / "glances" / "glances.conf"


# ============================================================================
# Defaults
# ============================================================================


class DefaultsTest(_ConfigCase):
    def test_defaults_only(self):
        config = GlancesConfigV5()
        self.assertEqual(config.get("global", "refresh_time", 999), 2)
        self.assertEqual(config.get("outputs", "api_doc", False), True)

    def test_defaults_section_present(self):
        config = GlancesConfigV5()
        self.assertTrue(config.has_section("global"))


# ============================================================================
# Layered file overlay
# ============================================================================


class FileLayeringTest(_ConfigCase):
    def test_etc_overrides_defaults(self):
        self.write(
            self.etc_path,
            """
            [global]
            refresh_time = 5
        """,
        )
        self.assertEqual(GlancesConfigV5().get("global", "refresh_time", 999), 5)

    def test_xdg_overrides_etc(self):
        self.write(self.etc_path, "[global]\nrefresh_time = 5\n")
        self.write(self.xdg_path, "[global]\nrefresh_time = 7\n")
        self.assertEqual(GlancesConfigV5().get("global", "refresh_time", 999), 7)

    def test_xdg_fallback_to_home_when_xdg_unset(self):
        del os.environ["XDG_CONFIG_HOME"]
        self.write(self.home_path, "[global]\nrefresh_time = 9\n")
        self.assertEqual(GlancesConfigV5().get("global", "refresh_time", 999), 9)

    def test_glances_config_file_env_overrides_xdg(self):
        custom = self.tmp_path / "custom.conf"
        self.write(self.xdg_path, "[global]\nrefresh_time = 7\n")
        self.write(custom, "[global]\nrefresh_time = 10\n")
        os.environ["GLANCES_CONFIG_FILE"] = str(custom)
        self.assertEqual(GlancesConfigV5().get("global", "refresh_time", 999), 10)

    def test_cli_path_overrides_glances_config_file(self):
        env_file = self.tmp_path / "env.conf"
        cli_file = self.tmp_path / "cli.conf"
        self.write(env_file, "[global]\nrefresh_time = 10\n")
        self.write(cli_file, "[global]\nrefresh_time = 12\n")
        os.environ["GLANCES_CONFIG_FILE"] = str(env_file)
        config = GlancesConfigV5(cli_config_path=str(cli_file))
        self.assertEqual(config.get("global", "refresh_time", 999), 12)

    def test_missing_files_silently_skipped(self):
        # No fixture files written. Should not crash.
        config = GlancesConfigV5()
        self.assertEqual(config.get("global", "refresh_time", 0), 2)


# ============================================================================
# Environment variable overlay (highest priority)
# ============================================================================


class EnvOverlayTest(_ConfigCase):
    def test_env_overlay_top_priority(self):
        self.write(self.etc_path, "[global]\nrefresh_time = 5\n")
        os.environ["GLANCES_GLOBAL__REFRESH_TIME"] = "11"
        self.assertEqual(GlancesConfigV5().get("global", "refresh_time", 0), 11)

    def test_env_overlay_creates_new_section(self):
        os.environ["GLANCES_NEWSECTION__SOMEKEY"] = "value"
        config = GlancesConfigV5()
        self.assertEqual(config.get("newsection", "somekey", ""), "value")

    def test_env_overlay_key_with_underscores(self):
        # Section names have no '_' by convention; keys may have any number.
        os.environ["GLANCES_MEM__CRITICAL_ACTION"] = "echo critical"
        config = GlancesConfigV5()
        self.assertEqual(config.get("mem", "critical_action", ""), "echo critical")

    def test_env_var_without_separator_ignored(self):
        os.environ["GLANCES_BADVAR"] = "value"
        config = GlancesConfigV5()
        self.assertNotIn("badvar", config.sections())

    def test_env_var_wrong_prefix_ignored(self):
        os.environ["NOTGLANCES_GLOBAL__REFRESH_TIME"] = "99"
        config = GlancesConfigV5()
        self.assertEqual(config.get("global", "refresh_time", 0), 2)

    def test_env_var_empty_section_ignored(self):
        os.environ["GLANCES___KEY"] = "value"
        config = GlancesConfigV5()
        self.assertNotIn("", config.sections())


# ============================================================================
# Typed accessor
# ============================================================================


class TypedAccessorTest(_ConfigCase):
    def setUp(self):
        super().setUp()
        self.write(
            self.etc_path,
            """
            [test]
            int_val = 42
            float_val = 3.14
            list_val = a, b, c
            string_val = hello
        """,
        )

    def test_get_int(self):
        self.assertEqual(GlancesConfigV5().get("test", "int_val", 0), 42)

    def test_get_float(self):
        self.assertAlmostEqual(GlancesConfigV5().get("test", "float_val", 0.0), 3.14)

    def test_get_str(self):
        self.assertEqual(GlancesConfigV5().get("test", "string_val", ""), "hello")

    def test_get_list(self):
        self.assertEqual(GlancesConfigV5().get("test", "list_val", []), ["a", "b", "c"])

    def test_get_list_strips_whitespace_and_empty(self):
        self.write(self.etc_path, "[test]\nlist_val = a,, b ,c \n")
        self.assertEqual(GlancesConfigV5().get("test", "list_val", []), ["a", "b", "c"])

    def test_get_missing_section_returns_default(self):
        config = GlancesConfigV5()
        self.assertEqual(config.get("absent", "absent", "default"), "default")

    def test_get_missing_option_returns_default(self):
        self.assertEqual(GlancesConfigV5().get("test", "absent", 99), 99)

    def test_get_value_alias(self):
        config = GlancesConfigV5()
        self.assertEqual(
            config.get_value("test", "int_val", 0),
            config.get("test", "int_val", 0),
        )

    def test_default_native_type_passes_through(self):
        # DEFAULTS hold int/bool natively — they must reach get() without coercion.
        config = GlancesConfigV5()
        result = config.get("global", "refresh_time", 0)
        self.assertIsInstance(result, int)
        self.assertEqual(result, 2)


class BoolCoercionTest(_ConfigCase):
    def _config_with_flag(self, value: str) -> GlancesConfigV5:
        self.write(self.etc_path, f"[test]\nflag = {value}\n")
        return GlancesConfigV5()

    def test_bool_true_variants(self):
        for v in ["yes", "true", "1", "on", "YES", "TRUE", "On"]:
            with self.subTest(value=v):
                self.assertTrue(self._config_with_flag(v).get("test", "flag", False))

    def test_bool_false_variants(self):
        for v in ["no", "false", "0", "off", "NO", "False"]:
            with self.subTest(value=v):
                self.assertFalse(self._config_with_flag(v).get("test", "flag", True))

    def test_bool_invalid_raises(self):
        config = self._config_with_flag("maybe")
        with self.assertRaises(ValueError):
            config.get("test", "flag", False)


# ============================================================================
# as_dict_secure() — secret redaction
# ============================================================================


class SecureViewTest(_ConfigCase):
    def setUp(self):
        super().setUp()
        self.write(
            self.etc_path,
            """
            [influxdb]
            host = localhost
            port = 8086
            password = secret123

            [smtp]
            user = bob
            passphrase = topsecret
            api_key = ak_xxx

            [serverlist]
            uri = http://user:pass@example.com

            [snmp]
            snmp_community = public
            snmp_authkey = mykey
        """,
        )

    def test_redacts_passwords(self):
        d = GlancesConfigV5().as_dict_secure()
        self.assertEqual(d["influxdb"]["password"], "***")

    def test_redacts_passphrases_and_api_keys(self):
        d = GlancesConfigV5().as_dict_secure()
        self.assertEqual(d["smtp"]["passphrase"], "***")
        self.assertEqual(d["smtp"]["api_key"], "***")

    def test_redacts_uri(self):
        d = GlancesConfigV5().as_dict_secure()
        self.assertEqual(d["serverlist"]["uri"], "***")

    def test_redacts_snmp_secrets(self):
        d = GlancesConfigV5().as_dict_secure()
        self.assertEqual(d["snmp"]["snmp_community"], "***")
        self.assertEqual(d["snmp"]["snmp_authkey"], "***")

    def test_preserves_non_secret(self):
        d = GlancesConfigV5().as_dict_secure()
        self.assertEqual(d["influxdb"]["host"], "localhost")
        self.assertEqual(d["influxdb"]["port"], "8086")
        self.assertEqual(d["smtp"]["user"], "bob")

    def test_includes_all_sections(self):
        d = GlancesConfigV5().as_dict_secure()
        for section in ["influxdb", "smtp", "serverlist", "snmp"]:
            self.assertIn(section, d)

    def test_as_dict_unmodified(self):
        # as_dict() returns the raw data without redaction.
        d = GlancesConfigV5().as_dict()
        self.assertEqual(d["influxdb"]["password"], "secret123")


# ============================================================================
# reload()
# ============================================================================


class ReloadTest(_ConfigCase):
    def test_reload_picks_up_changes(self):
        self.write(self.etc_path, "[global]\nrefresh_time = 5\n")
        config = GlancesConfigV5()
        self.assertEqual(config.get("global", "refresh_time", 0), 5)

        self.write(self.etc_path, "[global]\nrefresh_time = 11\n")
        self.assertEqual(config.get("global", "refresh_time", 0), 5)  # cached

        config.reload()
        self.assertEqual(config.get("global", "refresh_time", 0), 11)

    def test_reload_preserves_cli_override(self):
        cli_file = self.tmp_path / "cli.conf"
        self.write(cli_file, "[global]\nrefresh_time = 13\n")
        config = GlancesConfigV5(cli_config_path=str(cli_file))
        self.assertEqual(config.get("global", "refresh_time", 0), 13)

        self.write(cli_file, "[global]\nrefresh_time = 17\n")
        config.reload()
        self.assertEqual(config.get("global", "refresh_time", 0), 17)


# ============================================================================
# Introspection
# ============================================================================


class IntrospectionTest(_ConfigCase):
    def test_has_section_true(self):
        self.write(self.etc_path, "[outputs]\napi_doc = no\n")
        self.assertTrue(GlancesConfigV5().has_section("outputs"))

    def test_has_section_false(self):
        self.assertFalse(GlancesConfigV5().has_section("absent"))

    def test_sections_includes_defaults_and_files(self):
        self.write(self.etc_path, "[a]\nx = 1\n[b]\ny = 2\n")
        sections = set(GlancesConfigV5().sections())
        self.assertIn("a", sections)
        self.assertIn("b", sections)
        self.assertIn("global", sections)


class LoadedSourcesTest(_ConfigCase):
    def test_empty_with_no_files(self):
        self.assertEqual(GlancesConfigV5().loaded_sources, [])

    def test_lists_etc_when_present(self):
        self.write(self.etc_path, "[global]\nrefresh_time = 5\n")
        self.assertIn(self.etc_path, GlancesConfigV5().loaded_sources)

    def test_preserves_load_order(self):
        self.write(self.etc_path, "[global]\nrefresh_time = 5\n")
        self.write(self.xdg_path, "[global]\nrefresh_time = 7\n")
        sources = GlancesConfigV5().loaded_sources
        self.assertLess(sources.index(self.etc_path), sources.index(self.xdg_path))

    def test_returns_a_copy(self):
        self.write(self.etc_path, "[global]\nrefresh_time = 5\n")
        config = GlancesConfigV5()
        sources = config.loaded_sources
        sources.clear()
        self.assertEqual(len(config.loaded_sources), 1)


if __name__ == "__main__":
    unittest.main()
