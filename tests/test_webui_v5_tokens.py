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
# word match cannot land in prose. The named-colour branch uses a
# hyphen-aware guard, not `\b`: in regex `-` IS a word boundary, so a colour
# NAME can appear inside a hyphenated PROPERTY name (`white-space`,
# `-webkit-text-fill-color`) without being a colour VALUE -- `\bwhite\b`
# matches inside `white-space`, `(?<![\w-])white(?![\w-])` does not.
_COLOUR = re.compile(
    r"#[0-9a-fA-F]{3,8}\b"
    r"|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\s*\("
    rf"|(?<![\w-])(?:{_NAMED_ALTERNATION})(?![\w-])",
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


def test_a_prominent_value_is_a_badge_in_its_tier_colour():
    """TUI parity: a prominent cell is a filled badge -- the tier colour as
    BACKGROUND, a contrasting text on top (glances_curses_v5.py reverse pairs).
    Not a neutral grey background under a tier-coloured text.

    The text token is the theme background, which gives >= 5.0:1 (WCAG AA) on
    every tier of both shipped themes; a fixed black drops to 3.2:1 on the
    light theme's critical. CSS is not observable through the render probe,
    so this reads the token file with comments stripped.
    """
    css = _strip_comments(_TOKENS.read_text())
    assert "--gl-prominent-fg:" in css, "--gl-prominent-fg must be defined"
    for tier in ("ok", "careful", "warning", "critical"):
        body = _rule_body(css, f".gl-prominent.gl-level-{tier}")
        assert re.search(rf"\bbackground:\s*var\(--gl-level-{tier}\)", body), (
            f"a prominent {tier} value must be painted on --gl-level-{tier}: {body!r}"
        )
        assert re.search(r"\bcolor:\s*var\(--gl-prominent-fg\)", body), (
            f"a prominent {tier} value sets its text colour in the same rule: {body!r}"
        )
    # The text colour lives IN each compound rule, never in a lone `.gl-prominent`
    # rule: that one ties with `.gl-level-*` on specificity, so moving it above
    # them would silently paint tier-coloured text on a tier-coloured badge.
    assert not re.search(r"\.gl-prominent\s*\{", css), "no standalone .gl-prominent rule: it depends on rule order"
    assert "--gl-prominent-bg" not in css, "--gl-prominent-bg is no longer read by any rule: remove it"


def _rule_body(text: str, selector: str) -> str:
    match = re.search(rf"{re.escape(selector)}\s*\{{([^}}]*)\}}", text)
    assert match, f"no `{selector}` rule found"
    return match.group(1)


def test_a_plugin_title_has_the_text_size_and_no_margin():
    """Maintainer smoke test: `gpu` sat lower than its neighbours. A scalar
    plugin's title is a <dt> once loaded, while `gpu`/`network` keep an <h2>
    whose browser defaults (margin, 1.5em) pushed it down. CSS is not
    observable through the render probe, so this reads the token file.
    """
    body = _rule_body(_strip_comments(_TOKENS.read_text()), ".gl-plugin-title h2")
    assert re.search(r"\bmargin:\s*0\s*;", body), f"the title <h2> has no margin: {body!r}"
    assert re.search(r"\bfont-size:\s*inherit\s*;", body), f"the title <h2> has the text size: {body!r}"


def test_a_value_column_has_a_width_floor_on_the_grid_not_the_cell():
    """Maintainer smoke test: plugin widths followed their values, so the top
    row reflowed on every refresh. The floor sits on the grid COLUMN: on the
    <dd> it would widen the prominent badge past its text again.
    """
    css = _strip_comments(_TOKENS.read_text())
    assert re.search(r"grid-template-columns:\s*auto\s+minmax\(7ch,\s*auto\)", _rule_body(css, ".gl-stat-grid dl")), (
        "a scalar value column is at least 7ch (100.0%, 1023.9G, 1023.9K)"
    )
    assert re.search(
        r"grid-template-columns:\s*auto\s+minmax\(9ch,\s*auto\)", _rule_body(css, ".gl-stat-grid dl.gl-col-rate")
    ), "a column of rates is at least 9ch (1023.9G/s)"
    assert "min-width" not in _rule_body(css, ".gl-stat-grid dd"), "no floor on the <dd>: it would widen the badge"


def test_the_footer_sticks_to_the_bottom_of_the_viewport():
    """Maintainer smoke test: the alert footer must sit at the bottom of the
    screen and stay visible while the page scrolls. `.gl-app` fills at least
    the viewport, and the footer is pushed down and made sticky, on an opaque
    background so scrolled content does not show through it.
    """
    shell = _strip_comments((_V5_JS / "AppShell.vue").read_text())
    app = _rule_body(shell, ".gl-app")
    assert re.search(r"\bmin-height:\s*100vh\s*;", app), f".gl-app fills the viewport: {app!r}"
    footer = _rule_body(shell, ".gl-alerts")
    for declaration in (r"position:\s*sticky", r"bottom:\s*0", r"margin-top:\s*auto", r"background:\s*var\(--gl-bg\)"):
        assert re.search(rf"\b{declaration}\s*;", footer), f"footer lacks `{declaration}`: {footer!r}"


def test_the_footer_controls_stay_out_of_the_way():
    """The footer is chrome: the server's identity at one end, the cadence and
    its two steppers at the other. Neither end may compete with a plugin for
    attention -- the brief asked for buttons that do not draw the eye. So: no
    button border or background, no browser-blue link, and the whole line one
    notch below the body text. CSS is not observable through the render probe,
    so this reads the component.

    The value box is pinned too: without a width floor, stepping 2s -> 10s
    widens the text and slides the "+" out from under the pointer.
    """
    shell = _strip_comments((_V5_JS / "AppShell.vue").read_text())
    assert re.search(r"justify-content:\s*space-between\s*;", _rule_body(shell, ".gl-alerts")), (
        "the footer's two ends sit at the two edges of the line"
    )
    ends = _rule_body(shell, ".gl-about,\n.gl-refresh")
    assert re.search(r"font-size:\s*var\(--gl-size-sm\)\s*;", ends), f"the footer is one notch down: {ends!r}"
    step = _rule_body(shell, ".gl-step")
    for declaration in (r"background:\s*none", r"border:\s*none", r"color:\s*inherit", r"font:\s*inherit"):
        assert re.search(rf"\b{declaration}\s*;", step), f"a stepper still looks like a button: {step!r}"
    link = _rule_body(shell, ".gl-about a")
    assert re.search(r"color:\s*inherit\s*;", link), f"a footer link keeps the muted colour: {link!r}"
    assert re.search(r"text-decoration:\s*none\s*;", link), f"a footer link drops the solid underline: {link!r}"
    value = _rule_body(shell, ".gl-refresh-value")
    assert re.search(r"min-width:", value), f"the cadence box has no width floor: {value!r}"
    # The "+" sits at the viewport's right edge, where a classic scrollbar
    # crowds it and an overlay one is drawn straight over it. Matched on the
    # standalone `.gl-refresh` rule: the shared `.gl-about, .gl-refresh` one
    # above must NOT carry this, or the left end moves too.
    assert re.search(r"(?<!,)\n\.gl-refresh\s*\{[^}]*padding-right:", shell), (
        "the cadence needs clearance from the scrollbar"
    )


def test_a_name_cell_is_capped_and_can_keep_its_tail():
    """G9-6 D3: a left-sidebar name is capped at the TUI's name width, which
    each component sets as --gl-name-width, on a BLOCK span (max-width on a
    table cell is not reliably honoured). `.gl-truncate-start` puts the
    ellipsis at the start, keeping the tail like the TUI's "_" + name[-17:].
    CSS is not observable through the render probe, so this reads the file.
    """
    css = _strip_comments(_TOKENS.read_text())
    name = _rule_body(css, ".gl-name")
    assert re.search(r"\bdisplay:\s*block\s*;", name), f".gl-name is a block: {name!r}"
    assert re.search(r"\bmax-width:\s*var\(--gl-name-width\)\s*;", name), f".gl-name is capped: {name!r}"
    start = _rule_body(css, ".gl-truncate-start")
    assert re.search(r"\bdirection:\s*rtl\s*;", start), f"the ellipsis moves to the start: {start!r}"
    assert re.search(r"\btext-align:\s*left\s*;", start), f"a short name stays left-aligned: {start!r}"


def test_a_measuring_exclusion_has_its_cap_in_the_token_file():
    """`.gl-measuring` excludes `.gl-name` so its cap survives the
    measurement, and that cap has to live in the token file too: a cap
    defined in a component cannot serve a class the token file exempts
    globally -- a SECOND component using the class would inherit the
    exclusion with no cap and its cascade would under-fire, silently,
    because an uncapped span simply measures narrower than it should.

    `.gl-command` and `.gl-ports` were exempted here for the same reason
    until `containers` became a fixed-layout table: its <colgroup> now sizes
    those columns, so both classes are gone and the exclusion list is back to
    the single class that still needs one.
    """
    css = _strip_comments(_TOKENS.read_text())
    body = _rule_body(css, ".gl-name")
    assert re.search(r"\bdisplay:\s*block\s*;", body), f".gl-name needs a block box for its cap: {body!r}"
    assert re.search(r"\bmax-width:", body), f".gl-name has no cap in the token file: {body!r}"
    for gone in (".gl-command", ".gl-ports"):
        assert not re.search(rf"^{re.escape(gone)}\s*\{{", css, re.M), (
            f"{gone} is back in the token file with no consumer and no measuring exclusion"
        )


def test_every_collection_table_fills_the_left_column():
    """Maintainer's call after the smoke test (spec section 13): every block of
    the left column must have the same width.

    A <table> is shrink-to-fit, so a block whose names are all short renders
    narrower than its neighbours -- measured in headless Chrome before this
    rule: wifi 156px (one 9-character ssid) and diskio 228px against network's
    278px, even after both name caps were raised to the three-column budget.
    `width: 100%` makes each table fill the column the body grid already sized
    to the widest block, whatever the content. CSS is not observable through
    the render probe, so this reads the token file.
    """
    body = _rule_body(_strip_comments(_TOKENS.read_text()), ".gl-table")
    assert re.search(r"\bwidth:\s*100%\s*;", body), f".gl-table fills its column: {body!r}"


def test_a_collection_table_left_aligns_only_its_non_numeric_cells():
    """The browser centres a <th>; the TUI left-aligns names and titles and
    right-aligns values. `:not(.gl-num)` is load-bearing: `.gl-table th`
    outranks the global `.gl-num`, so a plain rule would stop numeric columns
    right-aligning.
    """
    css = _strip_comments(_TOKENS.read_text())
    assert re.search(r"\.gl-table\s+th:not\(\.gl-num\)\s*,", css), "the <th> rule excludes numeric columns"
    body = _rule_body(css, ".gl-table td:not(.gl-num)")
    assert re.search(r"\btext-align:\s*left\s*;", body), f"non-numeric cells left-align: {body!r}"


def test_a_block_keeps_its_natural_width():
    """Spec section 8: a block must not be squeezed by its neighbours, or the
    zone would never report an overflow and the cascade would never run. CSS is
    not observable through the render probe, so this reads the token file.
    """
    body = _rule_body(_strip_comments(_TOKENS.read_text()), ".gl-plugin")
    assert re.search(r"\bflex:\s*0\s+0\s+auto\s*;", body), f".gl-plugin keeps its natural width: {body!r}"


def test_the_header_and_top_zones_never_wrap():
    """Spec goal 1: a plugin never moves to another line. The zones stop
    wrapping and scroll horizontally once the cascade is exhausted (D4).

    `.gl-slot-header-left`/`-right` also need `min-width: 0`: without it a
    flex item's automatic minimum size stops it shrinking below its content,
    `scrollWidth` never exceeds `clientWidth`, and the header cascade in
    AppShell.vue's measureZone() never observes an overflow at all -- it goes
    silently dead with no test failing.
    """
    shell = _strip_comments((_V5_JS / "AppShell.vue").read_text())
    for selector in (".gl-zone-header", ".gl-slot-top"):
        body = _rule_body(shell, selector)
        assert re.search(r"\bflex-wrap:\s*nowrap\s*;", body), f"{selector} does not wrap: {body!r}"
        assert re.search(r"\boverflow-x:\s*auto\s*;", body), f"{selector} scrolls instead: {body!r}"
    for selector in (".gl-slot-header-left", ".gl-slot-header-right"):
        body = _rule_body(shell, selector)
        assert re.search(r"\bflex-wrap:\s*nowrap\s*;", body), f"{selector} does not wrap: {body!r}"
        assert re.search(r"\bmin-width:\s*0\s*;", body), (
            f"{selector} must stay shrinkable or the cascade dies: {body!r}"
        )


def test_a_quicklook_bar_track_keeps_a_width_without_the_cpu_header():
    """Each bar sits in a `1fr` column of a block sized to its content, so the
    CPU name/frequency line was the only thing giving the track a width. With
    no current frequency (many VMs, FreeBSD) the bars rendered 0 px wide.
    Mirrors the TUI: `_MIN_BAR_TOTAL` floor (8 inner columns) always, and
    `_DEFAULT_BAR_WIDTH` (38) when there is no header to justify against.
    CSS is not observable through the render probe, so this reads the file.
    """
    css = _strip_comments(_TOKENS.read_text())
    assert re.search(r"\bmin-width:\s*8ch\s*;", _rule_body(css, ".gl-bar-track")), "the track has the TUI's floor"
    assert re.search(r"\bmin-width:\s*38ch\s*;", _rule_body(css, ".gl-quicklook-no-header .gl-bar-track")), (
        "without a header the track takes the TUI's default bar width"
    )
    template = (_V5_JS / "PluginQuicklook.vue").read_text()
    assert "'gl-quicklook-no-header': !header" in template, "the block flags the missing header"


def test_the_footer_hotkeys_control_is_a_button_dressed_as_a_link():
    """It acts on this page rather than navigating, so an `<a>` would lie to
    assistive tech and offer a middle-click that goes nowhere. It must still
    look like the links beside it, which means resetting the UA's button
    chrome — a reset that is easy to half-do."""
    template = (_V5_JS / "AppShell.vue").read_text()
    assert '<button\n					type="button"\n					class="gl-about-action"' in template, (
        "the footer control must be a <button>, not an <a>"
    )
    assert '@click="toggleHelp"' in template, "it must go through the same switch as the `h` key"

    body = _rule_body(_strip_comments(template), ".gl-about-action")
    assert body, "the button needs its own rule or it renders as UA button chrome"
    for prop in ("appearance", "background", "border", "padding", "font"):
        assert re.search(rf"\b{prop}:", body), f"{prop} must be reset so it matches the links beside it"
    assert re.search(r"\bborder-bottom:\s*1px dotted currentcolor\s*;", body), (
        "it carries the same dotted underline as `.gl-about a`"
    )


def test_full_quicklook_lets_the_block_grow_into_the_row():
    """`4` leaves quicklook alone on the top row; it must then TAKE that row.

    `.gl-slot-top` is `justify-content: space-between`, which does nothing for
    a single child, so the block kept its content width and the freed space
    was blank. Measured in a real browser: 373 px of a 1584 px row.

    Two properties, both of which were wrong in the first attempt:

    1. `flex-grow` only. `.gl-plugin` sets `flex: 0 0 auto`, and that
       `flex-shrink: 0` is what makes a zone overflow rather than squeeze --
       the signal the degradation cascade runs on. The shorthand would have
       reset it.
    2. Qualified with `.gl-plugin`. Both classes are on the same element, so
       at equal specificity source order decides, and `.gl-plugin` comes LATER
       in the file. A bare `.gl-quicklook-full` rule is silently dead.
    """
    css = _strip_comments(_TOKENS.read_text())
    body = _rule_body(css, ".gl-plugin.gl-quicklook-full")
    assert body, "the rule must be qualified with .gl-plugin or it loses to it on source order"
    assert re.search(r"\bflex-grow:\s*1\s*;", body), "the block must grow into the free width"
    assert not re.search(r"\bflex\s*:", body), (
        "use flex-grow alone: the `flex` shorthand resets flex-shrink, which .gl-plugin needs at 0"
    )
    # The rule is dead without the class, and the class without the rule.
    template = (_V5_JS / "PluginQuicklook.vue").read_text()
    assert "'gl-quicklook-full': fullQuicklook" in template, "the block flags full-quicklook mode"
    assert "this.serverArgs.full_quicklook" in template, "the flag comes from the effective view args"


def test_the_cascade_measures_header_text_at_its_natural_width():
    """Maintainer spec D4 order is hide, then crop, then scroll. `.gl-truncate`
    and `.gl-inline` shrink into their ellipsis, so the zone never overflowed
    and the header cascade stayed idle while the OS name and IP location were
    ellipsized (confirmed 1000-1300 px). During the synchronous measurement
    (`gl-measuring`, AppShell.measureZone) they keep their natural width;
    `.gl-name` keeps its deliberate cap (G9-6 D3).
    """
    css = _strip_comments(_TOKENS.read_text())
    body = _rule_body(css, ".gl-measuring .gl-inline,\n.gl-measuring .gl-truncate:not(.gl-name)")
    assert re.search(r"\bmin-width:\s*max-content\s*;", body), body
    assert re.search(r"\bmax-width:\s*none\s*;", body), body
    shell = (_V5_JS / "AppShell.vue").read_text()
    add = shell.index('zone.classList.add("gl-measuring")')
    read = shell.index("zone.scrollWidth", add)
    remove = shell.index('zone.classList.remove("gl-measuring")', read)
    assert add < read < remove


def test_the_left_aligned_rate_column_outranks_the_gl_num_default():
    """`IOW/s` and `Tx/s` are left-aligned so each rate pair hugs in the
    middle, as the TUI paints it (containers/render_curses_v5.py:158-162).

    The selector must qualify the cell element, not just the class: a bare
    `.gl-num-left` (0,1,0) only TIES with the global `.gl-num` (0,1,0), and a
    tie is settled by source order between a scoped component style and the
    token file -- which nothing here guarantees. `.gl-table th.gl-num-left`
    is (0,2,1) and wins outright. Same trap the `.gl-table th:not(.gl-num)`
    comment in css/v5.css already documents.
    """
    source = _strip_comments((_V5_JS / "PluginContainers.vue").read_text())
    body = _rule_body(source, ".gl-table th.gl-num-left,\n.gl-table td.gl-num-left")
    assert re.search(r"\btext-align:\s*left\s*;", body), f"the pair's second column is left-aligned: {body!r}"


def test_the_amps_count_column_drops_the_rate_width_floor():
    """`.gl-num` floors a column at 9ch, a width sized for a rate cell's
    worst case. The AMP count is one to four digits, so it must override that
    floor with the TUI's own column width (amps/render_curses_v5.py
    `_COUNT_COL_WIDTH` = 4). CSS is invisible to the render probe, so the
    class reaching the DOM is asserted there and the width here.
    """
    source = _strip_comments((_V5_JS / "PluginAmps.vue").read_text())
    body = _rule_body(source, ".gl-amp-count")
    assert re.search(r"\bmin-width:\s*calc\(4 \* var\(--gl-col\)\)\s*;", body), (
        f"the count column uses the TUI's 4 characters, in the column unit: {body!r}"
    )


# A width that means "N characters of the TUI" must NOT use `ch`. Measured in
# Chrome on 2026-09-19 with the shipped stack: the rendered advance is 8.473px
# while `1ch` resolves to 7.04px -- exactly 0.5em, the CSS spec's fallback for
# "the measure of the 0 glyph cannot be determined". Every `Nch` therefore
# shows 0.83*N characters. The trigger is the font stack, not a bad value:
# two or more unavailable families before the generic break the resolution
# (`Menlo, Consolas, monospace` measured 0.83; `X, monospace` measured 1.0).
#
# The deliberate exceptions, keyed by the exact declaration rather than by
# file: `smart` carries BOTH a TUI-derived cap (its attribute name column,
# converted) and a layout-budget one (its device line, kept). Each of these
# is a width chosen in the browser, not a TUI character count.
_LAYOUT_BUDGET_NAME_WIDTHS = {
    # The left column's shared width budget (maintainer's call, 2026-09-12),
    # which explicitly REPLACED these two blocks' TUI widths.
    ("PluginSensors.vue", "calc(27ch + var(--gl-gap))"),
    ("PluginWifi.vue", "calc(27ch + var(--gl-gap))"),
    # The smart device line spans both columns: its cap is the block's own
    # width, so it is set inline rather than from the component's variable.
    ("PluginSmart.vue", "34ch"),
}


def _name_width_declarations() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for path in sorted(_V5_JS.glob("*.vue")):
        values = re.findall(r"--gl-name-width:\s*([^;\"]+)", _strip_comments(path.read_text()))
        if values:
            out[path.name] = [v.strip() for v in values]
    return out


def test_a_tui_character_width_uses_the_column_unit_not_ch():
    """`ch` lies under the shipped font stack, so a cap meant to mirror a TUI
    column must be written `calc(N * var(--gl-col))`.

    This is a drift guard, not a style rule: the next plugin ported will copy
    an existing block, and copying a bare `18ch` would silently truncate its
    names 17% early again.
    """
    offenders = {
        (name, value)
        for name, values in _name_width_declarations().items()
        for value in values
        if (name, value) not in _LAYOUT_BUDGET_NAME_WIDTHS
        and re.search(r"\d+(\.\d+)?ch", value)
        and "--gl-col" not in value
    }
    assert not offenders, f"TUI widths still written in `ch`: {offenders}"


def test_the_column_unit_is_defined_once_on_the_root():
    """`--gl-col` is one monospace character's worth of width, with SLACK.

    The measured advance is ~0.6em (DejaVu Sans Mono 0.6017em, Menlo and SF
    Mono 0.6em), and `--gl-col: 0.6em` used to be exactly that -- zero slack.
    A cell whose value exactly FILLED its N-character column then overflowed
    its content box by N * 0.0017em and `text-overflow: ellipsis` ate the
    last character: PID at `4194304`, TIME+ at `99h59:59`, VIRT/RES/R/s/W/s
    at `1023G`, NI at `-20`, USER at ten characters, alert's TIME at
    `--:--:--`. The unit has to sit ABOVE the widest face this stack can land
    on, never at it.

    Defining it anywhere but `:root` would let one block drift from the rest.
    """
    css = _strip_comments(_TOKENS.read_text())
    assert len(re.findall(r"--gl-col:", css)) == 1, "--gl-col is defined exactly once"
    match = re.search(r":root\s*\{[^}]*--gl-col:\s*(\d*\.?\d+)em", css, re.S)
    assert match, "--gl-col lives on :root and is declared in em"
    # 0.6017em is the widest advance measured under the shipped stack; the
    # token must clear it, or a full-width value crops again.
    assert float(match.group(1)) > 0.6017, f"--gl-col leaves no slack for a full-width cell: {match.group(1)}em"


def test_the_row_unit_is_defined_once_and_drives_the_right_column_gap():
    """`plan_right_column.cost()` charges exactly one blank line between blocks
    (curses_renderer_v5.py:1051). For that integer arithmetic to hold in the
    browser, the right column's inter-block gap must be exactly one row -- so
    the line-height has to be a known number, not the font-dependent `normal`
    it was before this batch (design 4.5).
    """
    css = _strip_comments(_TOKENS.read_text())
    assert len(re.findall(r"--gl-row:", css)) == 1, "--gl-row is defined exactly once"
    assert re.search(r":root\s*\{[^}]*--gl-row:\s*1\.25\b", css, re.S), "--gl-row lives on :root"
    assert re.search(r"line-height:\s*var\(--gl-row\)", css), "the token is actually applied"


def test_the_right_column_gives_its_slack_to_the_last_cell():
    """Measured in Chrome at a 2560px viewport: the right slot is 2258px and
    `.gl-table { width: 100% }` -- a rule introduced to equalise the LEFT
    column -- spread that width across the columns, so `amps` (three short
    columns) rendered its name cell 431px wide around a 136px cap: 295px of
    empty space. The TUI gives its slack to the last, unbounded column
    instead. `last-child` rather than a per-block class so a row whose tail
    columns were dropped by the cascade still has one.
    """
    body = _rule_body(
        _strip_comments(_TOKENS.read_text()),
        '[data-slot="right"] .gl-table td:last-child,\n[data-slot="right"] .gl-table th:last-child',
    )
    assert re.search(r"\bwidth:\s*100%\s*;", body), f"the tail cell absorbs the slack: {body!r}"
    # A fixed-layout table excludes itself from the rule above -- under
    # `table-layout: fixed`, `width: 100%` on the last cell would claim the
    # WHOLE table width for the tail column, leaving nothing for the fixed
    # ones. The column left OUT of the <colgroup> already does the job this
    # rule exists for, so the higher-specificity `.gl-process-table` selector
    # overrides it back to `auto`. This narrows the rule the test above pins;
    # it does not replace it -- `amps`/`vms` (automatic layout) must still get
    # their slack from the general rule.
    excluded = _rule_body(
        _strip_comments(_TOKENS.read_text()),
        '[data-slot="right"] .gl-table.gl-process-table td:last-child,\n'
        '[data-slot="right"] .gl-table.gl-process-table th:last-child',
    )
    assert re.search(r"\bwidth:\s*auto\s*;", excluded), f"the fixed-layout table keeps its <col>'s width: {excluded!r}"


def test_the_column_box_separator_multiplier_matches_colstyles_offset():
    """`colStyle()` (PluginProcesslist.vue) adds `+ 1` to every fixed column's
    content width, to reserve room for the separator that
    `.gl-table.gl-process-table th/td:not(:last-child)`'s `padding-right`
    carves out of that same <col> box: under `table-layout: fixed` the <col>
    is the column's WHOLE box, so the separator's padding comes out of the
    content space rather than adding to it.

    Until now that offset and the CSS rule that makes it necessary were two
    independent hardcoded literals that merely happened to agree -- nothing
    parsed the CSS to require it. Widening the separator for visual breathing
    room without touching `colStyle()` would silently reintroduce the exact
    bug the maintainer found by eye, one character at a time, and no other
    test would catch it. This one reads the separator's own multiplier out of
    the stylesheet and requires it to equal `COL_SEPARATOR`
    (js/v5/process_widths.js), the single constant every `colStyle()` and
    every `--gl-fixed-cols` sum now offsets by.
    """
    css = _strip_comments(_TOKENS.read_text())
    body = _rule_body(
        css,
        ".gl-table.gl-process-table th:not(:last-child),\n.gl-table.gl-process-table td:not(:last-child)",
    )
    match = re.search(r"padding-right:\s*(?:calc\((\d+)\s*\*\s*var\(--gl-col\)\)|var\(--gl-col\))\s*;", body)
    assert match, f"no padding-right declaration found: {body!r}"
    # A bare `var(--gl-col)` -- the form actually in the file today -- is an
    # implicit multiplier of 1; `calc(1 * var(--gl-col))` would be the same
    # length, so no test should demand the more verbose form.
    separator_chars = int(match.group(1)) if match.group(1) is not None else 1

    widths = (_V5_JS / "process_widths.js").read_text()
    offset_match = re.search(r"export const COL_SEPARATOR\s*=\s*(\d+)\s*;", widths)
    assert offset_match, f"COL_SEPARATOR is not exported from {_V5_JS / 'process_widths.js'}"
    colstyle_offset = int(offset_match.group(1))

    assert separator_chars == colstyle_offset, (
        f"the separator reserves {separator_chars} character(s) but COL_SEPARATOR is "
        f"{colstyle_offset} -- every fixed column would crop {separator_chars - colstyle_offset} "
        "character(s) early"
    )

    # ...and every <colgroup> actually offsets by that constant rather than by
    # a literal of its own, which is what makes reading one number enough.
    # process_block.js is the mixin PluginProcesslist.vue and
    # PluginProgramlist.vue share, so it carries their colStyle(); PluginAlert
    # and PluginContainers have no width map in common with them and keep
    # their own.
    for name in ("process_block.js", "PluginAlert.vue", "PluginContainers.vue"):
        script = (_V5_JS / name).read_text()
        assert re.search(r"\+\s*COL_SEPARATOR\}\s*\*\s*var\(--gl-col\)", script), (
            f"{name}'s colStyle() does not offset by COL_SEPARATOR"
        )


def test_the_container_cells_are_bounded_by_their_colgroup():
    """Measured in Chrome on 2026-09-19: the `ports` cell rendered 1540px wide
    for "61208/tcp,61209/tcp", and the `command` cell had the same defect --
    both spans are inline, so neither `.gl-truncate`'s ellipsis nor any cap
    applied, and a content-sized table made the width cascade over-fire on a
    host publishing many ports. Both were then capped at 24 characters, which
    pinned the tail column to 24 characters on a 2560px window too: the
    opposite complaint, and the one the maintainer raised next.

    The caps are gone and the table is `table-layout: fixed` with a <colgroup>
    instead, so a cell can no longer grow -- or refuse to grow -- with its
    content: every column but the tail is pinned to the terminal's own
    character width, and the tail takes whatever the window leaves. This pins
    the two halves that make that true, since the caps they replace are no
    longer there to be checked.
    """
    template = (_V5_JS / "PluginContainers.vue").read_text()
    assert 'table-class="gl-process-table"' in template, "the containers table is a fixed-layout one"
    assert ':style="fixedColsStyle"' in template, "the table's min-width comes from the visible columns"
    assert "<col v-for=" in template, "the fixed columns come from a <colgroup>"
    body = _rule_body(_strip_comments(_TOKENS.read_text()), ".gl-table.gl-process-table")
    assert re.search(r"\btable-layout:\s*fixed\s*;", body), f"the class carries the fixed layout: {body!r}"


def test_the_container_colgroup_leaves_exactly_one_column_elastic():
    """Under `table-layout: fixed` a column past the <colgroup>'s count takes
    the whole remainder (CSS 2.1 17.5.2.1), so the tail is elastic only as
    long as the colgroup stops ONE cell short. `fixedCells` is that slice; a
    future edit rendering a <col> per visible cell would pin the tail back to
    its floor, and no CSS assertion would notice.
    """
    script = (_V5_JS / "PluginContainers.vue").read_text()
    assert re.search(r"fixedCells\(\)\s*\{\s*return this\.cells\.slice\(0, -1\);", script), (
        "fixedCells no longer drops the tail cell"
    )
    assert '<col v-for="(cell, index) in fixedCells"' in script, "the <colgroup> no longer renders fixedCells"


def test_the_stacking_breakpoint_matches_the_stylesheet():
    """AppShell reads the breakpoint to disable the vertical budget in the
    stacked layout (design 4.9). Two copies of `48rem` that can drift silently
    would leave the budget active while the columns are stacked.
    """
    shell = (_V5_JS / "AppShell.vue").read_text()
    assert 'STACK_BREAKPOINT = "48rem"' in shell
    assert re.search(r"@media\s*\(max-width:\s*48rem\)", shell)
