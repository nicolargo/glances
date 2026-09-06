#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the WebUI design-token contract is enforced, not documented.

Spec section 5.1, R1: a component carrying a colour literal cannot be themed.
A user theme sets custom properties; it cannot reach `color: #d33` inside a
component. Unenforced, that promise degrades one plugin at a time across 32
ports and nobody notices until a user's theme half-works.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_STATIC = Path(__file__).resolve().parent.parent / "glances" / "outputs" / "static"
_V5_JS = _STATIC / "js" / "v5"
_TOKENS = _STATIC / "css" / "v5.css"

# The full set of CSS named colours (147 X11/CSS3 keywords + rebeccapurple).
# A curated subset degrades exactly one plugin at a time -- the failure mode
# this whole rule exists to prevent -- so this is data, not a shortlist.
_CSS_NAMED_COLOURS = frozenset(
    {
        "aliceblue",
        "antiquewhite",
        "aqua",
        "aquamarine",
        "azure",
        "beige",
        "bisque",
        "black",
        "blanchedalmond",
        "blue",
        "blueviolet",
        "brown",
        "burlywood",
        "cadetblue",
        "chartreuse",
        "chocolate",
        "coral",
        "cornflowerblue",
        "cornsilk",
        "crimson",
        "cyan",
        "darkblue",
        "darkcyan",
        "darkgoldenrod",
        "darkgray",
        "darkgreen",
        "darkgrey",
        "darkkhaki",
        "darkmagenta",
        "darkolivegreen",
        "darkorange",
        "darkorchid",
        "darkred",
        "darksalmon",
        "darkseagreen",
        "darkslateblue",
        "darkslategray",
        "darkslategrey",
        "darkturquoise",
        "darkviolet",
        "deeppink",
        "deepskyblue",
        "dimgray",
        "dimgrey",
        "dodgerblue",
        "firebrick",
        "floralwhite",
        "forestgreen",
        "fuchsia",
        "gainsboro",
        "ghostwhite",
        "gold",
        "goldenrod",
        "gray",
        "grey",
        "green",
        "greenyellow",
        "honeydew",
        "hotpink",
        "indianred",
        "indigo",
        "ivory",
        "khaki",
        "lavender",
        "lavenderblush",
        "lawngreen",
        "lemonchiffon",
        "lightblue",
        "lightcoral",
        "lightcyan",
        "lightgoldenrodyellow",
        "lightgray",
        "lightgreen",
        "lightgrey",
        "lightpink",
        "lightsalmon",
        "lightseagreen",
        "lightskyblue",
        "lightslategray",
        "lightslategrey",
        "lightsteelblue",
        "lightyellow",
        "lime",
        "limegreen",
        "linen",
        "magenta",
        "maroon",
        "mediumaquamarine",
        "mediumblue",
        "mediumorchid",
        "mediumpurple",
        "mediumseagreen",
        "mediumslateblue",
        "mediumspringgreen",
        "mediumturquoise",
        "mediumvioletred",
        "midnightblue",
        "mintcream",
        "mistyrose",
        "moccasin",
        "navajowhite",
        "navy",
        "oldlace",
        "olive",
        "olivedrab",
        "orange",
        "orangered",
        "orchid",
        "palegoldenrod",
        "palegreen",
        "paleturquoise",
        "palevioletred",
        "papayawhip",
        "peachpuff",
        "peru",
        "pink",
        "plum",
        "powderblue",
        "purple",
        "rebeccapurple",
        "red",
        "rosybrown",
        "royalblue",
        "saddlebrown",
        "salmon",
        "sandybrown",
        "seagreen",
        "seashell",
        "sienna",
        "silver",
        "skyblue",
        "slateblue",
        "slategray",
        "slategrey",
        "snow",
        "springgreen",
        "steelblue",
        "tan",
        "teal",
        "thistle",
        "tomato",
        "turquoise",
        "violet",
        "wheat",
        "white",
        "whitesmoke",
        "yellow",
        "yellowgreen",
    }
)

# Longest-first so e.g. "darkred" is tried before "red" in the alternation.
_NAMED_ALTERNATION = "|".join(re.escape(name) for name in sorted(_CSS_NAMED_COLOURS, key=len, reverse=True))

# Hex colours, the colour-producing CSS functions, and the full CSS named
# colour set. No anchor is needed here -- comments are stripped from the
# text before this pattern ever sees it (see `_strip_comments`), so a bare
# word match cannot land in prose.
_COLOUR = re.compile(
    r"#[0-9a-fA-F]{3,8}\b"
    r"|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\s*\("
    rf"|\b(?:{_NAMED_ALTERNATION})\b",
)

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_LINE_COMMENT = re.compile(r"//[^\n]*")


def _blank_out(match: re.Match) -> str:
    """Replace a matched comment with the same number of newlines it spanned.

    This keeps line numbers in failure messages accurate -- getting the
    line number wrong in a failure message makes the test annoying to act
    on, which is how rules get disabled.
    """
    return "\n" * match.group(0).count("\n")


def _strip_comments(text: str) -> str:
    """Strip /* */, <!-- --> and // comments so colour matching only ever
    sees real code, never prose.

    The anchor in the old regex was only ever a proxy for "this text is not
    prose"; stripping comments addresses that directly. `//` is stripped to
    end-of-line unconditionally (not string-literal-aware): a URL truncated
    inside a string cannot itself contain a colour literal, so this costs
    nothing here and avoids a fiddly quote-parity tracker.
    """
    text = _BLOCK_COMMENT.sub(_blank_out, text)
    text = _HTML_COMMENT.sub(_blank_out, text)
    return _LINE_COMMENT.sub("", text)


def _colour_hits(text: str) -> list[str]:
    """Return `"{line_no}: {line}"` for every line carrying a colour literal."""
    stripped = _strip_comments(text)
    return [f"{i}: {line.strip()}" for i, line in enumerate(stripped.splitlines(), 1) if _COLOUR.search(line)]


def _v5_sources() -> list[Path]:
    return sorted(p for p in _V5_JS.rglob("*") if p.suffix in {".vue", ".js"})


def test_v5_sources_exist():
    """Guard: an empty glob would make every assertion below vacuous."""
    assert _v5_sources(), f"no v5 sources found under {_V5_JS}"


@pytest.mark.parametrize("path", _v5_sources(), ids=lambda p: p.name)
def test_no_colour_literal_outside_the_token_file(path: Path):
    hits = [f"{path.name}:{hit}" for hit in _colour_hits(path.read_text())]
    assert not hits, (
        "Colour literals must live in css/v5.css so a user theme can override them (spec 5.1 R1):\n" + "\n".join(hits)
    )


@pytest.mark.parametrize(
    ("source", "expect_hit"),
    [
        pytest.param("border: 1px solid red;", True, id="named-in-shorthand"),
        pytest.param("box-shadow: 0 0 4px gray;", True, id="named-in-shadow"),
        pytest.param("color: #d33;", True, id="hex"),
        pytest.param("background: rgb(1,2,3);", True, id="rgb-function"),
        pytest.param("background: gold;", True, id="named-not-in-old-shortlist"),
        pytest.param("border-color:blue", True, id="named-no-space-before-colon"),
        pytest.param("outline: 2px dashed hotpink;", True, id="named-compound-word"),
        pytest.param("// the green light is on", False, id="line-comment-named"),
        pytest.param("// magenta comes from ANSI", False, id="line-comment-named-2"),
        pytest.param("// fixed in commit #abc123", False, id="line-comment-hex-like-sha"),
        pytest.param("/* red herring */", False, id="block-comment-named"),
        pytest.param("<!-- blue sky -->", False, id="html-comment-named"),
        pytest.param("color: var(--gl-level-critical);", False, id="token-reference-not-a-literal"),
    ],
)
def test_colour_literal_detection(source: str, expect_hit: bool):
    hits = _colour_hits(source)
    assert bool(hits) is expect_hit, f"source={source!r} hits={hits!r}"


def test_token_file_defines_both_shipped_themes():
    css = _TOKENS.read_text()
    assert ':root[data-theme="light"]' in css
    # `dark` is the default block on bare :root, matching [outputs] theme=dark.
    assert re.search(r"^:root\s*\{", css, re.M)


def test_every_tier_has_a_token_in_both_themes():
    css = _TOKENS.read_text()
    for tier in ("ok", "careful", "warning", "critical"):
        assert css.count(f"--gl-level-{tier}:") >= 2, (
            f"--gl-level-{tier} must be defined in both the default and the light block"
        )
