#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for GlancesConfigV5.

Test stack: pytest + pytest-asyncio (auto mode). See architecture decisions §9.

Tests cover the **single-file** loading model (v4-aligned):
- DEFAULTS layer always applied (codebase baseline).
- ``-C`` selects exactly one file (no search). Missing path → DEFAULTS only.
- Without ``-C``, v4 search order: user (XDG) → system. First existing wins.
- No cross-file merging — keys present in /etc but absent from XDG are
  **not** inherited when XDG is the chosen file.
- ``GLANCES_<SECTION>__<KEY>`` env vars overlay (orthogonal — kept).
- Typed accessor: int, float, bool variants, list, str, missing keys.
- Bool parsing rejects unknown values.
- ``as_dict_secure()`` redacts secret-like keys, preserves the rest.
- ``reload()`` picks up file changes.
- ``loaded_sources`` reports the (at most one) file actually read.
- ``has_section`` / ``sections`` introspection.
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest

from glances.config_v5 import GlancesConfigV5


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated config environment.

    - All real env vars are cleared.
    - SYSTEM_CONFIG_PATH is redirected to <tmp>/etc/glances.conf.
    - XDG_CONFIG_HOME is set to <tmp>/xdg.
    - HOME is set to <tmp>/home (fallback when XDG is unset).
    """
    for key in list(os.environ.keys()):
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    return tmp_path


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"))


def etc_path(env: Path) -> Path:
    return env / "etc" / "glances.conf"


def xdg_path(env: Path) -> Path:
    return env / "xdg" / "glances" / "glances.conf"


def home_path(env: Path) -> Path:
    return env / "home" / ".config" / "glances" / "glances.conf"


# ============================================================================
# Defaults
# ============================================================================


def test_defaults_only(env: Path) -> None:
    config = GlancesConfigV5()
    assert config.get("global", "refresh_time", 999) == 2
    assert config.get("outputs", "api_doc", False) is True


def test_defaults_section_present(env: Path) -> None:
    assert GlancesConfigV5().has_section("global")


# ============================================================================
# Layered file overlay
# ============================================================================


def test_etc_loaded_when_no_xdg(env: Path) -> None:
    """/etc is read when XDG file is absent."""
    write(etc_path(env), "[global]\nrefresh_time = 5\n")
    assert GlancesConfigV5().get("global", "refresh_time", 999) == 5


def test_xdg_wins_over_etc_when_both_present(env: Path) -> None:
    """User XDG conf is preferred over /etc. v4-style first-found-wins."""
    write(etc_path(env), "[global]\nrefresh_time = 5\n")
    write(xdg_path(env), "[global]\nrefresh_time = 7\n")
    assert GlancesConfigV5().get("global", "refresh_time", 999) == 7


def test_xdg_does_not_inherit_etc_keys(env: Path) -> None:
    """Regression guard: a key present only in /etc must NOT bleed into
    the loaded config when XDG is the chosen file. The pre-rewrite loader
    merged across files, which caused legacy v4-era ``careful=50`` keys
    in /etc to silently apply to v5 plugins reading from XDG."""
    write(etc_path(env), "[memswap]\ncareful = 50\nwarning = 70\ncritical = 90\n")
    write(xdg_path(env), "[memswap]\npercent_careful = 60\n")
    config = GlancesConfigV5()
    # XDG selected → only its keys appear in [memswap].
    assert config.get("memswap", "percent_careful", -1) == 60
    # /etc keys must NOT have been carried over.
    assert config.get("memswap", "careful", "absent") == "absent"
    assert config.get("memswap", "warning", "absent") == "absent"


def test_xdg_fallback_to_home_when_xdg_unset(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME")
    write(home_path(env), "[global]\nrefresh_time = 9\n")
    assert GlancesConfigV5().get("global", "refresh_time", 999) == 9


def test_glances_config_file_env_is_ignored(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``$GLANCES_CONFIG_FILE`` was a v5-only convenience that introduced
    cross-file merging surprises. v5 now aligns with v4: only ``-C`` can
    explicitly select a config file. The env var is silently ignored."""
    custom = env / "custom.conf"
    write(xdg_path(env), "[global]\nrefresh_time = 7\n")
    write(custom, "[global]\nrefresh_time = 10\n")
    monkeypatch.setenv("GLANCES_CONFIG_FILE", str(custom))
    # XDG still wins; the env var was ignored.
    assert GlancesConfigV5().get("global", "refresh_time", 999) == 7


def test_cli_path_bypasses_search(env: Path) -> None:
    """``-C`` selects exactly one file. XDG / /etc are ignored entirely."""
    cli_file = env / "cli.conf"
    write(etc_path(env), "[global]\nrefresh_time = 5\n")
    write(xdg_path(env), "[global]\nrefresh_time = 7\n")
    write(cli_file, "[global]\nrefresh_time = 12\n")
    assert GlancesConfigV5(cli_config_path=str(cli_file)).get("global", "refresh_time", 999) == 12


def test_cli_path_does_not_merge_with_other_files(env: Path) -> None:
    """A key present only in /etc must NOT show up when -C selects another file."""
    cli_file = env / "cli.conf"
    write(etc_path(env), "[memswap]\ncareful = 50\n")
    write(cli_file, "[global]\nrefresh_time = 12\n")
    config = GlancesConfigV5(cli_config_path=str(cli_file))
    assert config.get("global", "refresh_time", 999) == 12
    assert config.get("memswap", "careful", "absent") == "absent"


def test_missing_cli_path_falls_back_to_defaults_only(env: Path, caplog: pytest.LogCaptureFixture) -> None:
    """A non-existent ``-C`` path logs a WARNING and uses DEFAULTS only —
    does NOT silently fall back to the search path."""
    write(xdg_path(env), "[global]\nrefresh_time = 7\n")  # exists but must be ignored
    with caplog.at_level("WARNING"):
        config = GlancesConfigV5(cli_config_path=str(env / "nonexistent.conf"))
    # Default value, not the XDG one.
    assert config.get("global", "refresh_time", 999) == 2
    assert any("does not exist" in r.message for r in caplog.records)


def test_missing_files_silently_skipped(env: Path) -> None:
    """No XDG, no /etc → DEFAULTS only. No crash, no warning."""
    assert GlancesConfigV5().get("global", "refresh_time", 0) == 2


# ============================================================================
# Environment variable overlay (highest priority)
# ============================================================================


def test_env_overlay_top_priority(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write(etc_path(env), "[global]\nrefresh_time = 5\n")
    monkeypatch.setenv("GLANCES_GLOBAL__REFRESH_TIME", "11")
    assert GlancesConfigV5().get("global", "refresh_time", 0) == 11


def test_env_overlay_creates_new_section(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GLANCES_NEWSECTION__SOMEKEY", "value")
    assert GlancesConfigV5().get("newsection", "somekey", "") == "value"


def test_env_overlay_key_with_underscores(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Section names have no '_' by convention; keys may have any number.
    monkeypatch.setenv("GLANCES_MEM__CRITICAL_ACTION", "echo critical")
    assert GlancesConfigV5().get("mem", "critical_action", "") == "echo critical"


def test_env_var_without_separator_ignored(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GLANCES_BADVAR", "value")
    assert "badvar" not in GlancesConfigV5().sections()


def test_env_var_wrong_prefix_ignored(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOTGLANCES_GLOBAL__REFRESH_TIME", "99")
    assert GlancesConfigV5().get("global", "refresh_time", 0) == 2


def test_env_var_empty_section_ignored(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GLANCES___KEY", "value")
    assert "" not in GlancesConfigV5().sections()


# ============================================================================
# Typed accessor
# ============================================================================


@pytest.fixture
def typed_config(env: Path) -> GlancesConfigV5:
    write(
        etc_path(env),
        """
        [test]
        int_val = 42
        float_val = 3.14
        list_val = a, b, c
        string_val = hello
    """,
    )
    return GlancesConfigV5()


def test_get_int(typed_config: GlancesConfigV5) -> None:
    assert typed_config.get("test", "int_val", 0) == 42


def test_get_float(typed_config: GlancesConfigV5) -> None:
    assert typed_config.get("test", "float_val", 0.0) == pytest.approx(3.14)


def test_get_str(typed_config: GlancesConfigV5) -> None:
    assert typed_config.get("test", "string_val", "") == "hello"


def test_get_list(typed_config: GlancesConfigV5) -> None:
    assert typed_config.get("test", "list_val", []) == ["a", "b", "c"]


def test_get_list_strips_whitespace_and_empty(env: Path) -> None:
    write(etc_path(env), "[test]\nlist_val = a,, b ,c \n")
    assert GlancesConfigV5().get("test", "list_val", []) == ["a", "b", "c"]


def test_get_missing_section_returns_default(env: Path) -> None:
    assert GlancesConfigV5().get("absent", "absent", "default") == "default"


def test_get_missing_option_returns_default(typed_config: GlancesConfigV5) -> None:
    assert typed_config.get("test", "absent", 99) == 99


def test_get_value_alias(typed_config: GlancesConfigV5) -> None:
    assert typed_config.get_value("test", "int_val", 0) == typed_config.get("test", "int_val", 0)


def test_default_native_type_passes_through(env: Path) -> None:
    # DEFAULTS hold int/bool natively — they must reach get() without coercion.
    result = GlancesConfigV5().get("global", "refresh_time", 0)
    assert isinstance(result, int)
    assert result == 2


# ============================================================================
# Bool coercion
# ============================================================================


@pytest.mark.parametrize("value", ["yes", "true", "1", "on", "YES", "TRUE", "On"])
def test_bool_true_variants(env: Path, value: str) -> None:
    write(etc_path(env), f"[test]\nflag = {value}\n")
    assert GlancesConfigV5().get("test", "flag", False) is True


@pytest.mark.parametrize("value", ["no", "false", "0", "off", "NO", "False"])
def test_bool_false_variants(env: Path, value: str) -> None:
    write(etc_path(env), f"[test]\nflag = {value}\n")
    assert GlancesConfigV5().get("test", "flag", True) is False


def test_bool_invalid_raises(env: Path) -> None:
    write(etc_path(env), "[test]\nflag = maybe\n")
    config = GlancesConfigV5()
    with pytest.raises(ValueError):
        config.get("test", "flag", False)


# ============================================================================
# as_dict_secure() — secret redaction
# ============================================================================


@pytest.fixture
def secret_config(env: Path) -> GlancesConfigV5:
    write(
        etc_path(env),
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
    return GlancesConfigV5()


def test_redacts_passwords(secret_config: GlancesConfigV5) -> None:
    assert secret_config.as_dict_secure()["influxdb"]["password"] == "***"


def test_redacts_passphrases_and_api_keys(secret_config: GlancesConfigV5) -> None:
    d = secret_config.as_dict_secure()
    assert d["smtp"]["passphrase"] == "***"
    assert d["smtp"]["api_key"] == "***"


def test_redacts_uri(secret_config: GlancesConfigV5) -> None:
    assert secret_config.as_dict_secure()["serverlist"]["uri"] == "***"


def test_redacts_snmp_secrets(secret_config: GlancesConfigV5) -> None:
    d = secret_config.as_dict_secure()
    assert d["snmp"]["snmp_community"] == "***"
    assert d["snmp"]["snmp_authkey"] == "***"


def test_preserves_non_secret(secret_config: GlancesConfigV5) -> None:
    d = secret_config.as_dict_secure()
    assert d["influxdb"]["host"] == "localhost"
    assert d["influxdb"]["port"] == "8086"
    assert d["smtp"]["user"] == "bob"


def test_includes_all_sections(secret_config: GlancesConfigV5) -> None:
    d = secret_config.as_dict_secure()
    for section in ["influxdb", "smtp", "serverlist", "snmp"]:
        assert section in d


def test_as_dict_unmodified(secret_config: GlancesConfigV5) -> None:
    # as_dict() returns the raw data without redaction.
    assert secret_config.as_dict()["influxdb"]["password"] == "secret123"


# ============================================================================
# reload()
# ============================================================================


def test_reload_picks_up_changes(env: Path) -> None:
    write(etc_path(env), "[global]\nrefresh_time = 5\n")
    config = GlancesConfigV5()
    assert config.get("global", "refresh_time", 0) == 5

    write(etc_path(env), "[global]\nrefresh_time = 11\n")
    assert config.get("global", "refresh_time", 0) == 5  # cached

    config.reload()
    assert config.get("global", "refresh_time", 0) == 11


def test_reload_preserves_cli_override(env: Path) -> None:
    cli_file = env / "cli.conf"
    write(cli_file, "[global]\nrefresh_time = 13\n")
    config = GlancesConfigV5(cli_config_path=str(cli_file))
    assert config.get("global", "refresh_time", 0) == 13

    write(cli_file, "[global]\nrefresh_time = 17\n")
    config.reload()
    assert config.get("global", "refresh_time", 0) == 17


# ============================================================================
# Introspection
# ============================================================================


def test_has_section_true(env: Path) -> None:
    write(etc_path(env), "[outputs]\napi_doc = no\n")
    assert GlancesConfigV5().has_section("outputs")


def test_has_section_false(env: Path) -> None:
    assert not GlancesConfigV5().has_section("absent")


def test_sections_includes_defaults_and_files(env: Path) -> None:
    write(etc_path(env), "[a]\nx = 1\n[b]\ny = 2\n")
    sections = set(GlancesConfigV5().sections())
    assert "a" in sections
    assert "b" in sections
    assert "global" in sections


# ============================================================================
# loaded_sources
# ============================================================================


def test_loaded_sources_empty_with_no_files(env: Path) -> None:
    assert GlancesConfigV5().loaded_sources == []


def test_loaded_sources_lists_etc_when_only_etc_present(env: Path) -> None:
    write(etc_path(env), "[global]\nrefresh_time = 5\n")
    assert GlancesConfigV5().loaded_sources == [etc_path(env)]


def test_loaded_sources_contains_only_the_chosen_file(env: Path) -> None:
    """When both XDG and /etc exist, only XDG (the chosen file) appears."""
    write(etc_path(env), "[global]\nrefresh_time = 5\n")
    write(xdg_path(env), "[global]\nrefresh_time = 7\n")
    sources = GlancesConfigV5().loaded_sources
    assert sources == [xdg_path(env)]


def test_loaded_sources_returns_a_copy(env: Path) -> None:
    write(etc_path(env), "[global]\nrefresh_time = 5\n")
    config = GlancesConfigV5()
    sources = config.loaded_sources
    sources.clear()
    assert len(config.loaded_sources) == 1
