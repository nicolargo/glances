#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""`[outputs] theme`: dark, light/white, or the path of a user CSS theme."""

import logging
import re
from pathlib import Path

import pytest

from glances.theme import MAX_CSS_BYTES, builtin_theme, tui_theme, webui_theme

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_THEME = ROOT / "conf" / "sample_theme.css"
TOKENS_CSS = ROOT / "glances" / "outputs" / "static" / "css" / "glances.css"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("dark", "dark"),
        ("light", "light"),
        ("white", "light"),
        ("  WHITE ", "light"),
        ("Dark", "dark"),
        ("solarized", None),
        ("./conf/sample_theme.css", None),
        ("", None),
    ],
)
def test_builtin_theme(value, expected):
    assert builtin_theme(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [("light", "light"), ("white", "light"), ("dark", "dark"), ("./x.css", "dark"), ("typo", "dark")],
)
def test_tui_theme(value, expected):
    """The TUI has two palettes: anything that is not light/white is dark."""
    assert tui_theme(value) == expected


def test_webui_builtin_themes_carry_no_css():
    assert webui_theme("dark") == {"name": "dark", "css": None}
    assert webui_theme("white") == {"name": "light", "css": None}


def test_webui_user_theme_is_read(tmp_path):
    css_file = tmp_path / "t.css"
    # Bytes, not text: `write_text` would turn `\n` into `\r\n` on Windows.
    css_file.write_bytes(b":root { --gl-bg: #000; }\n")
    assert webui_theme(f"  {css_file} ") == {"name": "custom", "css": ":root { --gl-bg: #000; }\n"}


def test_webui_user_theme_path_is_case_sensitive(tmp_path):
    """Only the keywords are case-folded: a path keeps its case on a case-sensitive filesystem."""
    css_file = tmp_path / "MyTheme.css"
    css_file.write_text(":root {}", encoding="utf-8")
    assert webui_theme(str(css_file))["name"] == "custom"


def test_webui_user_theme_expands_the_home_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # what `expanduser()` reads on Windows
    (tmp_path / "t.css").write_text(":root {}", encoding="utf-8")
    assert webui_theme("~/t.css")["name"] == "custom"


@pytest.mark.parametrize("value", ["", "   ", "not-a-theme"])
def test_webui_falls_back_to_dark_on_a_value_that_is_no_theme(value):
    assert webui_theme(value) == {"name": "dark", "css": None}


def test_webui_falls_back_to_dark_on_a_missing_file(tmp_path, caplog):
    """The warning must not leak the configured path (nor the OSError, which carries it)."""
    with caplog.at_level(logging.WARNING, logger="glances.theme"):
        assert webui_theme(str(tmp_path / "nope.css")) == {"name": "dark", "css": None}
    assert "cannot be read" in caplog.text
    assert "nope.css" not in caplog.text


def test_webui_only_serves_css_files(tmp_path, caplog):
    """A wrong path (a config, a key) must not be served to every WebUI client."""
    secret = tmp_path / "secret.conf"
    secret.write_text("password=hunter2", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="glances.theme"):
        assert webui_theme(str(secret)) == {"name": "dark", "css": None}
    assert "hunter2" not in caplog.text


def test_webui_falls_back_to_dark_on_an_oversized_file(tmp_path):
    css_file = tmp_path / "big.css"
    css_file.write_text("/*" + "x" * MAX_CSS_BYTES + "*/", encoding="utf-8")
    assert webui_theme(str(css_file)) == {"name": "dark", "css": None}


def test_webui_falls_back_to_dark_on_a_file_that_is_not_utf8(tmp_path):
    css_file = tmp_path / "bin.css"
    css_file.write_bytes(b"\xff\xfe\x00")
    assert webui_theme(str(css_file)) == {"name": "dark", "css": None}


def test_webui_falls_back_to_dark_on_a_directory(tmp_path):
    folder = tmp_path / "dir.css"
    folder.mkdir()
    assert webui_theme(str(folder)) == {"name": "dark", "css": None}


# ----------------------------------------------------------- conf/sample_theme.css


def _tokens(css: str) -> set[str]:
    return set(re.findall(r"(--gl-[a-z0-9-]+)\s*:", css))


def test_sample_theme_loads_as_a_user_theme():
    theme = webui_theme(str(SAMPLE_THEME))
    assert theme["name"] == "custom"
    assert 'data-theme="custom"' in theme["css"]


def test_sample_theme_only_sets_tokens_the_webui_defines():
    """A renamed or removed token would leave the sample theme silently half-applied."""
    shipped = _tokens(TOKENS_CSS.read_text(encoding="utf-8"))
    assert _tokens(SAMPLE_THEME.read_text(encoding="utf-8")) <= shipped


def _luminance(hex_colour: str) -> float:
    channels = [int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = (c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a: str, b: str) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_sample_theme_tiers_are_readable_as_text_and_as_badges():
    """WCAG AA (4.5:1) for every tier on the page and the raised surface; the badge text is --gl-bg."""
    css = SAMPLE_THEME.read_text(encoding="utf-8")
    colours = dict(re.findall(r"(--gl-[a-z-]+):\s*(#[0-9a-fA-F]{6})\s*;", css))
    for tier in ("ok", "careful", "warning", "critical"):
        assert _contrast(colours[f"--gl-level-{tier}"], colours["--gl-bg"]) >= 4.5, tier
        assert _contrast(colours[f"--gl-level-{tier}"], colours["--gl-surface"]) >= 4.5, tier
    assert _contrast(colours["--gl-fg"], colours["--gl-bg"]) >= 4.5
    assert _contrast(colours["--gl-muted"], colours["--gl-surface"]) >= 4.5
