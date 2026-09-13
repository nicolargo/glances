#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the WebUI bundle rendered against a fake DOM.

These tests run tests/fixtures/webui_render_probe.js under node against the
built bundle; they never start the FastAPI app. Moved out of
test_webserver_v5.py unchanged (G9-6 Task 0).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from glances.outputs.curses_renderer_v5 import HEADER_SLOT_LEFT, HEADER_SLOT_RIGHT, LEFT_SLOT, RIGHT_SLOT, TOP_SLOT

_BUNDLE_PATH = Path(__file__).parent.parent / "glances" / "outputs" / "static" / "public" / "glances5.js"
_RENDER_PROBE_PATH = Path(__file__).parent / "fixtures" / "webui_render_probe.js"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_v5_bundle_actually_renders_an_element():
    """Guards against a silent, all-tests-green blank page.

    `import { createApp } from "vue"` resolves to Vue's runtime-only build
    unless webpack aliases it to the compiler-included build. A component
    that only supplies a string `template:` (as app_v5.js does) then gets
    `render = NOOP` -- in production mode the dev warning for this is
    compiled out, so nothing is logged and nothing throws. The mount target
    ends up holding a single, silently-empty comment node instead of real
    markup.

    Every HTTP-level test in this file (e.g. test_the_v5_bundle_is_served)
    only checks that the bundle is served with a non-empty body -- a bundle
    that renders nothing passes all of them. This test instead runs the
    actual bundle against a minimal DOM stub and asserts that the `#app`
    mount target ends up containing a real ELEMENT node, not just Vue's
    empty-render comment placeholder -- the distinction Finding 1 hinged on.

    G9-2's AppShell also renders a bare `<main>`, so a `tagName == "MAIN"`
    check alone would pass against a stub as blank as G9-1's -- e.g. a
    `createApp({ template: "<main></main>" })`. Assert markup that only the
    real shell (header + plugin area + footer) produces and that a blank
    page cannot satisfy: the `gl-app` class and both a HEADER and a FOOTER
    descendant.

    The fixture's `fetch` stub answers `api/5/alert` with twelve events in the
    real `_build_event()` shape (glances/alerts_v5.py:706-716), oldest first
    -- matching get_history()'s documented most-recent-LAST contract
    (glances/alerts_v5.py:181). Assert the footer actually renders them --
    identified by plugin AND field, not just the bare level, so a fallback to
    a field that does not exist cannot pass unnoticed -- AND that it keeps the
    ten MOST RECENT, newest first: a single-alert stub could not catch
    AppShell using `history.slice(0, 10)` (the ten OLDEST) instead of the
    correct `history.slice(-10).reverse()`, which is exactly the bug that
    shipped in the previous fix round. This is exactly the shape the G9-1
    blank page took: an untested corner of an otherwise-green test suite --
    and the corner turned out deeper than the first probe fix realised.
    """
    if not _BUNDLE_PATH.exists():
        pytest.fail(f"{_BUNDLE_PATH} is missing -- run `npm run build` in glances/outputs/static/")

    result = subprocess.run(
        ["node", str(_RENDER_PROBE_PATH), str(_BUNDLE_PATH)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"render probe crashed:\n{result.stderr}"
    # A thrown exception inside AppShell's async mounted() hook (e.g. a
    # sandbox missing a global it calls) does not necessarily flip the exit
    # code -- it can land as stderr noise on an otherwise-green run. Assert
    # stderr is empty so a broken lifecycle hook cannot hide behind a
    # passing returncode again.
    assert result.stderr == "", f"render probe printed to stderr:\n{result.stderr}"

    payload = json.loads(result.stdout)
    # nodeType 1 == ELEMENT_NODE, 8 == COMMENT_NODE (the runtime-only-Vue
    # failure mode). Assert the concrete element, not just "has children":
    # a broken build also has exactly one child -- an empty comment.
    assert payload["nodeType"] == 1, (
        f"expected an ELEMENT_NODE under #app, got nodeType={payload['nodeType']!r} "
        f"(tagName={payload['tagName']!r}) -- the Vue template rendered nothing"
    )
    assert payload["tagName"] == "MAIN"
    assert payload["hasClass"], "expected the root <main> to carry class 'gl-app'"
    assert payload["hasHeader"], "expected a <header> descendant of the app shell"
    assert payload["hasFooter"], "expected a <footer> descendant of the app shell"
    # The stub's api/5/alert fixture carries plugin="pluginN", field="total"
    # for N in 0..11, oldest (0) first -- get_history()'s documented order.
    # A footer that renders only the level (e.g. a fallback to a
    # non-existent `description` field) would show "critical" with no
    # plugin/field at all -- assert both are present for the regression
    # from fix round 1.
    footer_text = payload["footerText"] or ""
    assert "plugin11" in footer_text and "total" in footer_text, (
        f"expected the footer to identify the alert by plugin and field, got {footer_text!r}"
    )
    # The two OLDEST alerts must have been dropped (only 10 of 12 shown) --
    # `history.slice(0, 10)` would keep these and drop the newest two
    # instead, which is the regression from fix round 2. Match "pluginN "
    # (with the trailing space before " total"), not a bare substring:
    # "plugin1" is also a substring of "plugin10" and "plugin11".
    assert "plugin0 " not in footer_text and "plugin1 " not in footer_text, (
        f"expected the two oldest alerts dropped, got {footer_text!r}"
    )
    # Newest first: plugin11 (most recent) must render before plugin2
    # (oldest of the ten kept) -- a `slice(-10)` without `.reverse()` would
    # still keep the right ten alerts but in oldest-first order.
    assert footer_text.index("plugin11") < footer_text.index("plugin2"), (
        f"expected newest-first order, got {footer_text!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_registry_renders_every_registered_plugin():
    """Proves plugins/index.js is wired up end to end, not just importable.

    G9-3 replaced AppShell's four hardcoded per-plugin surfaces (import,
    components map, spec list, template tag) with a loop over
    `PLUGINS` from `plugins/index.js`. A regression here would not be a
    missing import -- the bundle would still build -- it would be a loop
    that silently renders zero, or only one, of the registered plugins.

    Each plugin component renders an <article class="gl-plugin"> carrying
    its registry name as `data-plugin` (PluginMem.vue -> "mem",
    PluginNetwork.vue -> "network", PluginLoad.vue -> "load",
    PluginMemswap.vue -> "memswap", PluginCpu.vue -> "cpu",
    PluginGpu.vue -> "gpu"). Assert all are
    present, not just "some markup exists": a loop that iterates only
    `PLUGINS[0]` would still produce one gl-plugin article and could pass a
    weaker assertion.

    The order is the DOCUMENT order, i.e. zone by zone: a registry entry
    whose `slot` is missing or misspelled is rendered in no zone at all, and
    this explicit list is what catches it -- the drift guard below only sees
    what rendered.
    """
    if not _BUNDLE_PATH.exists():
        pytest.fail(f"{_BUNDLE_PATH} is missing -- run `npm run build` in glances/outputs/static/")

    result = subprocess.run(
        ["node", str(_RENDER_PROBE_PATH), str(_BUNDLE_PATH)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"render probe crashed:\n{result.stderr}"
    assert result.stderr == "", f"render probe printed to stderr:\n{result.stderr}"

    payload = json.loads(result.stdout)
    # `percpu` is absent on purpose: the `default` scenario carries no
    # `--percpu`, and AppShell now shows exactly one of `cpu`/`percpu`
    # (final review, Critical 1 -- glances_curses_v5.py:565-567 mirrors this
    # in the TUI). `test_percpu_renders_and_cpu_does_not_when_the_server_ran_with_percpu`
    # covers the other half.
    assert payload["pluginNames"] == [
        "system",
        "ip",
        "uptime",
        "cloud",
        "now",
        "quicklook",
        "cpu",
        "npu",
        "mpp",
        "gpu",
        "mem",
        "memswap",
        "load",
        "network",
        "ports",
        "wifi",
        "connections",
        "diskio",
        "fs",
        "irq",
        "folders",
        "raid",
        "smart",
        "sensors",
    ], f"expected all registered plugins to render, got {payload['pluginNames']!r}"


_TUI_SLOTS = {
    "header-left": HEADER_SLOT_LEFT,
    "header-right": HEADER_SLOT_RIGHT,
    "top": TOP_SLOT,
    "left": LEFT_SLOT,
    "right": RIGHT_SLOT,
}


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_every_slot_orders_its_plugins_like_the_tui():
    """The drift guard G9-5's decision D4 depends on.

    The WebUI keeps its own copy of the TUI's slot lists (a `slot` attribute
    per entry in plugins/index.js, order = registry order). Nothing prevents
    the two copies from drifting apart; this test makes drift a failure. It
    compares the RENDERED layout -- not the registry source -- against the
    tuples imported from glances.outputs.curses_renderer_v5, which it must
    never restate.

    For each slot container, the plugins rendered in it must be exactly the
    TUI tuple for that slot, filtered to the plugins that rendered, in the
    tuple's order. A plugin placed in the wrong slot is absent from that
    slot's tuple and fails; two plugins swapped within a slot fail on order.
    """
    payload = _run_render_probe("default")
    rendered = payload["pluginNames"]
    slots = payload["slots"]

    assert rendered, "vacuous: nothing rendered"
    assert set(slots) <= set(_TUI_SLOTS), f"a slot the TUI does not have rendered: {sorted(slots)!r}"
    placed = [name for names in slots.values() for name in names]
    assert sorted(placed) == sorted(rendered), f"every plugin must sit in exactly one slot: {slots!r}"
    for slot, names in slots.items():
        expected = [name for name in _TUI_SLOTS[slot] if name in rendered]
        assert names == expected, f"slot {slot!r}: rendered {names!r}, the TUI orders {expected!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_every_collection_block_keeps_its_root_attributes():
    """G9-7 Task 0 moved the root <article> into CollectionBlock.vue, so
    `data-plugin` and `aria-label` now reach it through TWO component roots.
    Vue drops a fallthrough attribute without error when a template has more
    than one root node -- a root-level comment is enough -- and the symptom is
    a plugin that silently vanishes from the page.
    """
    payload = _run_render_probe("default")
    attrs = payload["pluginAttrs"]
    for name in ("network", "wifi", "diskio", "fs", "sensors"):
        assert name in attrs, f"{name} did not render at all: {sorted(attrs)!r}"
        assert "data-plugin" in attrs[name], f"{name} lost data-plugin: {attrs[name]!r}"
        assert "aria-label" in attrs[name], f"{name} lost aria-label: {attrs[name]!r}"
        assert "server-args" not in attrs[name], f"{name} leaked a prop as an attribute: {attrs[name]!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_plugin_the_server_did_not_instantiate_is_not_rendered():
    """A disabled plugin is never instantiated (glances/main_v5.py:372), so it
    is never in /api/5/all, and before G9-5 the WebUI showed it as "loading…"
    forever. `gpu-disabled` answers /api/5/pluginslist without `gpu`.
    """
    payload = _run_render_probe("gpu-disabled")
    assert "gpu" not in payload["pluginNames"], f"gpu is disabled: {payload['pluginNames']!r}"
    assert "cpu" in payload["pluginNames"], f"vacuous: the other plugins must still render: {payload['pluginNames']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_unreadable_pluginslist_renders_the_whole_registry():
    """/api/5/pluginslist failing must degrade to the pre-G9-5 behaviour --
    every registered plugin rendered -- never to an empty page.

    `percpu` is still absent: the cpu/percpu exclusivity rule (final review,
    Critical 1) is unconditional on `serverArgs.percpu`, applied on top of
    whichever plugin list `slots()` resolved to -- including this fallback.
    """
    payload = _run_render_probe("pluginslist-unreachable")
    assert payload["pluginNames"] == [
        "system",
        "ip",
        "uptime",
        "cloud",
        "now",
        "quicklook",
        "cpu",
        "npu",
        "mpp",
        "gpu",
        "mem",
        "memswap",
        "load",
        "network",
        "ports",
        "wifi",
        "connections",
        "diskio",
        "fs",
        "irq",
        "folders",
        "raid",
        "smart",
        "sensors",
    ], f"expected the whole registry, got {payload['pluginNames']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_refresh_cadence_renders_in_the_footer():
    """G9-5 decision D5: the top bar is gone and the cadence moved to the
    footer. The probe answers /api/5/config with `{}`, so the cadence is
    api.js' DEFAULT_REFRESH_SECONDS (2).
    """
    payload = _run_render_probe("default")
    assert "refresh 2s" in (payload["footerText"] or ""), f"got {payload['footerText']!r}"


# --------------------------------------------------------- mem TUI parity (G9-3 Task 5)


def _run_render_probe(scenario: str) -> dict:
    if not _BUNDLE_PATH.exists():
        pytest.fail(f"{_BUNDLE_PATH} is missing -- run `npm run build` in glances/outputs/static/")

    result = subprocess.run(
        ["node", str(_RENDER_PROBE_PATH), str(_BUNDLE_PATH), scenario],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"render probe crashed:\n{result.stderr}"
    assert result.stderr == "", f"render probe printed to stderr:\n{result.stderr}"
    return json.loads(result.stdout)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_mem_renders_all_eight_statistics_with_avail():
    """`render_curses_v5.py`'s reference block (module docstring, lines
    16-28) is eight (label, value) pairs: percent, total, avail, free,
    active, inactive, buffers, cached. The probe's `api/5/all` stub answers
    with the `mem-with-available` fixture -- a full psutil-shaped payload
    that HAS `available` -- so this asserts every one of the eight
    formatted values actually reaches the DOM, and that the avail/used
    switch shows `avail`: the fixture's `used` field carries a DIFFERENT
    value (9.0G) than `available` (8.0G) specifically so a component that
    rendered `used` instead, or both, could not pass unnoticed.
    """
    payload = _run_render_probe("mem-with-available")
    mem_text = payload["pluginText"].get("mem", "")

    for expected in ("53.2%", "16.0G", "8.0G", "2.0G", "5.0G", "4.0G", "100.0M", "3.0G"):
        assert expected in mem_text, f"expected {expected!r} in the MEM plugin text, got {mem_text!r}"
    assert "avail" in mem_text, f"expected the 'avail' label in the MEM plugin text, got {mem_text!r}"
    assert "9.0G" not in mem_text, f"expected 'used' (9.0G) NOT shown when 'available' is present: {mem_text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_mem_shows_used_when_available_is_absent():
    """Avail/used switch, other side: the `mem-no-available` fixture omits
    `available` entirely (e.g. a BSD without it), so the component must fall
    back to showing `used` -- and the `avail` label must not appear at all.
    """
    payload = _run_render_probe("mem-no-available")
    mem_text = payload["pluginText"].get("mem", "")

    for expected in ("53.2%", "16.0G", "9.0G", "2.0G", "5.0G", "4.0G", "100.0M", "3.0G"):
        assert expected in mem_text, f"expected {expected!r} in the MEM plugin text, got {mem_text!r}"
    assert "avail" not in mem_text, f"expected no 'avail' label when 'available' is absent: {mem_text!r}"


# ------------------------------------------------- network TUI parity (labels)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_network_column_headers_are_the_tui_strings():
    """The WebUI's network column headers must be the TUI's, not field names.

    The TUI header row is the block title then the two rate labels
    (`glances/plugins/network/render_curses_v5.py`: `NETWORK` / `Rx/s` /
    `Tx/s`). Since G9-6 D6 the WebUI's first <th> is that title; the rate
    headers resolve through `labelFor()` from the schema, and degrade to
    `bytes_recv` / `bytes_sent` without a `short_name`.

    The probe's `/info` stub is keyed by plugin name and carries the network
    schema's own short_names, so this observes the RESOLVED headers: with the
    mem schema answering every `/info` (as it did before this fix) the
    assertion below fails on field names.
    """
    payload = _run_render_probe("network")
    headers = payload["pluginColumnHeaders"].get("network")

    assert headers == ["NETWORK", "Rx/s", "Tx/s"], f"expected the TUI's network header row, got {headers!r}"


def test_network_schema_declares_the_tui_short_names():
    """Pin the schema the WebUI's network headers resolve from.

    `test_network_column_headers_are_the_tui_strings` renders through the
    probe, whose `/info` stub is a hand-copied mirror of this schema -- so it
    passes even if `short_name` is dropped from the real plugin. This asserts
    the source instead: drop a `short_name` here and the WebUI silently falls
    back to field names (`labelFor()` degrades to the field name by design),
    with no other test noticing.
    """
    from glances.plugins.network.model_v5 import PluginModel

    fields = PluginModel.fields_description
    # G9-6 D6: the name column's header cell is the block title, so the key
    # field declares no label of its own.
    assert "short_name" not in fields["interface_name"]
    assert fields["bytes_recv"]["short_name"] == "Rx/s"
    assert fields["bytes_sent"]["short_name"] == "Tx/s"


@pytest.mark.parametrize(
    ("plugin", "expected"),
    [
        pytest.param("diskio", {"read_bytes": "R/s", "write_bytes": "W/s"}, id="diskio"),
        pytest.param("fs", {"used": "Used", "free": "Free", "size": "Total"}, id="fs"),
        pytest.param("wifi", {"quality_level": "dBm"}, id="wifi"),
    ],
)
def test_left_sidebar_schemas_declare_the_tui_short_names(plugin, expected):
    """Pin the schema the WebUI's column headers AND the TUI's resolve from
    (G9-6 D5). The probe's /all/info stub is a hand copy, so only this test
    notices a `short_name` dropped from the real plugin.
    """
    import importlib

    fields = importlib.import_module(f"glances.plugins.{plugin}.model_v5").PluginModel.fields_description
    assert {field: fields[field].get("short_name") for field in expected} == expected


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cross_cutting_props_do_not_leak_into_the_dom_as_attributes():
    """Every component must DECLARE `serverArgs` AND `degrade`, even when it
    ignores one or both.

    Vue turns an undeclared prop into a fallthrough attribute, so a component
    missing a declaration renders `server-args="[object Object]"` or
    `degrade="[object Object]"` onto its root <article> -- AppShell.vue binds
    both as `:server-args` and `:degrade`, and Vue keeps that exact
    kebab-case key on an undeclared attribute, it does not concatenate it to
    `serverargs`/`degrade`. Verified by actually deleting a prop declaration
    from PluginMem.vue and observing the probe emit the matching kebab-case
    name in `pluginAttrs.mem` before restoring it. This observes the rendered
    attribute rather than the source, so it fails for a component added later
    that forgets either line -- `degrade` in particular has no other test:
    the eleven declare-only components never read it, so no behaviour test
    would notice a dropped declaration on them.
    """
    payload = _run_render_probe("mem-with-available")
    # Without this the loop below is vacuous: an empty `pluginAttrs` (a probe
    # that stopped collecting the attribute, a render that produced no
    # article) would pass silently. Twenty-four, not the registry's
    # twenty-five: `cpu`/`percpu` are mutually exclusive (final review,
    # Critical 1) -- this scenario's `percpu: true` (ARGS_FIXTURES) selects
    # `percpu` over `cpu` so the loop below still covers percpu's
    # `serverPlugins` inject specifically (G9-8 Task 4 review).
    assert len(payload["pluginAttrs"]) == 24, (
        f"expected all twenty-four rendered plugins' attributes, got {payload['pluginAttrs']!r}"
    )
    for name, attrs in payload["pluginAttrs"].items():
        assert "server-args" not in attrs, f"{name} leaked serverArgs as an attribute: {attrs!r}"
        assert "degrade" not in attrs, f"{name} leaked degrade as an attribute: {attrs!r}"
        # G9-8 Task 4 review: `serverPlugins` is provide/inject (AppShell.vue's
        # `provide()`, PluginPercpu.vue's `inject`), not a prop on this shared
        # binding -- so it must never appear as a DOM attribute on ANY plugin,
        # percpu included.
        assert "server-plugins" not in attrs, f"{name} leaked serverPlugins as an attribute: {attrs!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_every_scalar_grid_renders_its_values_with_the_same_classes():
    """The six `.gl-stat-grid` plugins must dress their <dd>s identically.

    `.gl-num` is not only alignment: `css/v5.css` floors it at 9ch, a width
    sized for `formatRate()`'s worst case ("1023.9G/s") in a collection
    TABLE. On a scalar <dd> that floor is too wide for any non-rate value --
    load's "0.86" in a 9ch cell -- and, being on the <dd>, it would also widen
    the prominent badge past its text. A scalar column's width floor lives on
    the grid COLUMN instead (`.gl-stat-grid dl`, 9ch only for `gl-col-rate`),
    and jitter-free digits come from `font-variant-numeric: tabular-nums` on
    `.gl-stat-grid dd`, which costs no width.

    So the only class a scalar value cell may carry is its tier
    (`gl-level-*`), and every one of the six must agree. Observed through
    the rendered class lists, not the component sources: a comment asking the
    next port to "keep these consistent" is not a test.

    `.gl-num` on the COLLECTION tables is untouched and still asserted by
    test_network_rate_columns_are_marked_numeric.
    """
    payload = _run_render_probe("scalar-grids")

    non_tier = {}
    for name in ("mem", "load", "memswap", "cpu", "gpu", "connections"):
        classes = payload["pluginValueClasses"].get(name)
        assert classes, f"{name} rendered no value cells: {payload['pluginValueClasses']!r}"
        non_tier[name] = sorted({c for cls in classes for c in cls.split() if not c.startswith("gl-level-")})

    assert non_tier == dict.fromkeys(non_tier, []), (
        f"a scalar value cell carries a non-tier class -- the six grids disagree: {non_tier!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_load_renders_the_three_averages_and_the_core_count():
    """TUI reference (load/render_curses_v5.py docstring): a header carrying
    LOAD and the core count, then three rows labelled from the schema.

    `cpucore` is `internal: true` -- it is the header's suffix, never a row
    of its own, so this asserts the label "cpucore" is absent.
    """
    payload = _run_render_probe("load")
    text = payload["pluginText"].get("load", "")

    for expected in ("LOAD", "4core", "1 min", "0.86", "5 min", "0.72", "15 min", "0.80"):
        assert expected in text, f"expected {expected!r} in the LOAD plugin text, got {text!r}"
    assert "cpucore" not in text, f"cpucore is internal and must not be a row: {text!r}"


@pytest.mark.parametrize(
    ("scenario", "name", "expected"),
    [
        pytest.param(
            "mem-with-available",
            "mem",
            [
                [["MEM", "53.2%"], ["total", "16.0G"], ["avail", "8.0G"], ["free", "2.0G"]],
                [["active", "5.0G"], ["inacti", "4.0G"], ["buffer", "100.0M"], ["cached", "3.0G"]],
            ],
            id="mem",
        ),
        pytest.param(
            "load",
            "load",
            [[["LOAD", "4core"], ["1 min", "0.86"], ["5 min", "0.72"], ["15 min", "0.80"]]],
            id="load",
        ),
        pytest.param(
            "memswap",
            "memswap",
            [[["SWAP", "25.0%"], ["total", "16.0G"], ["sin", "100.0K/s"], ["sout", "0B/s"]]],
            id="memswap",
        ),
        pytest.param(
            "cpu",
            "cpu",
            [
                [["CPU", "4.5%"], ["user", "3.8%"], ["system", "0.7%"], ["iowait", "0.0%"]],
                [["idle", "95.5%"], ["irq", "0.0%"], ["nice", "0.0%"], ["steal", "0.0%"]],
                [["ctx_sw", "6.7K"], ["inter", "3.0K"], ["sw_int", "1.8K"], ["guest", "0.0%"]],
            ],
            id="cpu",
        ),
    ],
)
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_scalar_title_is_the_first_pair_of_its_first_column(scenario, name, expected):
    """TUI reference layouts (mem/memswap/load/cpu render_curses_v5.py
    docstrings): line 1 carries the title AND its value as the first
    (label, value) pair of column 1 -- `SWAP 25.0%`, `CPU 4.5% | idle 95.5% |
    ctx_sw 6.7K`. So the title value shares the right-aligned value column,
    and every column has the same four lines.

    A title row rendered ABOVE the grid puts the value next to the title
    instead of in the value column, and shifts `active`/`idle`/`ctx_sw` one
    line below the title in mem and cpu. `pluginGrid` is every <dl> of the
    plugin as (dt, dd) text pairs, so this observes both the pairing and the
    per-column line count.
    """
    payload = _run_render_probe(scenario)
    assert payload["pluginGrid"].get(name) == expected, (
        f"{name}: expected the TUI grid {expected!r}, got {payload['pluginGrid'].get(name)!r}"
    )


@pytest.mark.parametrize(
    ("scenario", "name", "expected"),
    [
        pytest.param("memswap", "memswap", ["gl-col-rate"], id="memswap"),
        pytest.param("mem-with-available", "mem", ["", ""], id="mem"),
        pytest.param("load", "load", [""], id="load"),
        pytest.param("cpu", "cpu", ["", "", ""], id="cpu"),
    ],
)
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_only_a_column_of_rates_takes_the_wider_floor(scenario, name, expected):
    """Every scalar value column has a 7ch floor so a block keeps its width as
    values change (css/v5.css). Only a column holding formatRate() values --
    memswap's sin/sout, up to "1023.9G/s" -- needs 9ch, via `gl-col-rate`. A
    rate column without it would still resize as the rate grows.
    """
    payload = _run_render_probe(scenario)
    assert payload["pluginGridClasses"].get(name) == expected, (
        f"{name}: expected column classes {expected!r}, got {payload['pluginGridClasses'].get(name)!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_loaded_scalar_plugin_still_names_itself_for_assistive_technology():
    """Once loaded, a scalar plugin's title is a <dt> -- a heading is not
    allowed inside <dt> -- so the <article> carries an aria-label, or a screen
    reader navigating by landmark/heading loses mem, swap, load and cpu.
    `scalar-grids` renders all four loaded. `data-plugin` is asserted in the
    same breath: a template comment placed before the root <article> would
    make a second root node and silently drop both fallthrough attributes.
    """
    payload = _run_render_probe("scalar-grids")
    for name in ("mem", "memswap", "load", "cpu"):
        attrs = payload["pluginAttrs"].get(name) or []
        assert "aria-label" in attrs, f"{name}: the loaded article names itself: {attrs!r}"
        assert "data-plugin" in attrs, f"{name}: data-plugin still lands on the root: {attrs!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_scalar_plugin_keeps_its_title_while_loading():
    """The title moves into the grid only once a payload exists; before that
    (cycle 0) the plugin must still say what it is, not show a bare
    "loading…". Checked on the `default` scenario, which publishes nothing.
    """
    payload = _run_render_probe("default")
    for name, title in (
        ("mem", "MEM"),
        ("load", "LOAD"),
        ("memswap", "SWAP"),
        ("cpu", "CPU"),
        ("connections", "TCP CONNECTIONS"),
        ("quicklook", "QUICKLOOK"),
    ):
        text = payload["pluginText"].get(name, "")
        assert text.startswith(title) and "loading" in text, f"{name}: expected {title} then loading, got {text!r}"
        assert name not in payload["pluginGrid"], f"{name}: no grid before the first payload"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_prominent_alert_badges_its_level_word_only():
    """TUI parity (curses_renderer_v5.py alert grid): a prominent incident
    paints the badge on its LEVEL cell only. Now that `gl-prominent` fills
    the tier colour as a background, putting it on the whole footer <li>
    would turn every prominent alert into a full-width coloured band.

    Every alert in the probe fixture is critical AND prominent, so the line
    keeps the tier text colour without the badge, and the level word alone
    carries both classes.
    """
    payload = _run_render_probe("default")
    alerts = payload["footerAlerts"]
    assert len(alerts) == 10, f"vacuous: expected the ten most recent alerts, got {alerts!r}"
    for alert in alerts:
        item_classes = alert["className"].split()
        assert "gl-level-critical" in item_classes and "gl-prominent" not in item_classes, (
            f"the line keeps the tier colour but never the badge: {alert!r}"
        )
        assert alert["level"] == "critical", f"the level word renders on its own: {alert!r}"
        assert set((alert["levelClass"] or "").split()) == {"gl-level-critical", "gl-prominent"}, (
            f"the level word carries the badge: {alert!r}"
        )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_network_rate_columns_are_marked_numeric():
    """The two rate columns must carry `.gl-num`, the title column must not.

    `.gl-num` right-aligns, fixes the digit width and floors the column at
    9ch -- wider than any collection value today (network's bits "1023.9Gb"
    is 8 characters) -- so a rate going from "1.2K/s" to "10.2M/s" between
    two ticks stops resizing the column. This observes the rendered <th>
    class lists, so it fails if the `numeric` flag is dropped from the
    descriptor or the binding stops reaching the header.
    """
    payload = _run_render_probe("network")
    classes = payload["pluginColumnClasses"].get("network")

    assert classes is not None, "no NETWORK column classes rendered"
    assert "gl-num" not in classes[0], f"the title column must not be numeric, got {classes[0]!r}"
    for i in (1, 2):
        assert "gl-num" in classes[i], f"expected the rate column {i} to carry gl-num, got {classes[i]!r}"


def _tier_classes(class_name):
    return {c for c in (class_name or "").split() if c.startswith("gl-level-") or c == "gl-prominent"}


@pytest.mark.parametrize(
    ("scenario", "name", "cell_index", "expected"),
    [
        # Columns: name, Rx/s, Tx/s -> cell 1 is eth0's Rx.
        pytest.param("network-prominent", "network", 1, {"gl-level-warning", "gl-prominent"}, id="network"),
        # Columns: name, proc, mem -> cell 1 is card 0's proc.
        pytest.param("gpu-multi-levels", "gpu", 1, {"gl-level-critical"}, id="gpu"),
        # Columns: name, R/s, W/s -> row 1 (sdb) cell 4 is its read rate.
        pytest.param("diskio", "diskio", 4, {"gl-level-warning"}, id="diskio"),
        # Columns: name, Used, Total -> row 1 (/home) cell 4 is its used space.
        pytest.param("fs", "fs", 4, {"gl-level-careful"}, id="fs"),
        # Columns: name, dBm -> row 0 (wlan0) cell 1 is its signal.
        pytest.param("wifi", "wifi", 1, {"gl-level-warning"}, id="wifi"),
        # Columns: name, value -> row 2 (Core 0) cell 5 is its value.
        pytest.param("sensors", "sensors", 5, {"gl-level-critical", "gl-prominent"}, id="sensors"),
    ],
)
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_table_value_carries_its_tier_on_the_text_not_the_cell(scenario, name, cell_index, expected):
    """A prominent badge paints the tier colour as a BACKGROUND. On a <td>
    that background fills the whole cell -- including `.gl-num`'s 9ch floor
    and the padding -- so a short value like "0%" sat on a wide coloured
    block (maintainer smoke test). The tier classes therefore go on a <span>
    around the formatted value, like the TUI badge that covers the cell text;
    the <td> keeps only its layout class.
    """
    payload = _run_render_probe(scenario)
    cell = payload["pluginTableCells"][name][cell_index]
    assert _tier_classes(cell["value"]) == expected, f"the value span carries the tier: {cell!r}"
    assert _tier_classes(cell["cell"]) == set(), f"the <td> itself carries no tier class: {cell!r}"
    assert "gl-num" in cell["cell"].split(), f"the <td> keeps its numeric layout class: {cell!r}"


# ------------------------------------------- left-sidebar collections (G9-6)


def _table_rows(payload, name, width):
    """The rendered <td> texts of a collection plugin, grouped into rows."""
    cells = [cell["text"] for cell in payload["pluginTableCells"].get(name, [])]
    return [cells[i : i + width] for i in range(0, len(cells), width)]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_network_renders_only_the_rows_the_tui_renders_in_payload_order():
    """network/render_curses_v5.py:129-142 skips a down interface, one
    hide_zero still hides, and one without a rate yet; it keeps payload order
    and shows the alias. Rates are bits, as `_format_rate()` prints them.
    """
    payload = _run_render_probe("network-rows")
    assert _table_rows(payload, "network", 3) == [["Loopback", "800b", "800b"], ["eth0", "8.0Mb", "4.0Mb"]]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_network_shows_bytes_under_the_byte_flag():
    """`--byte` reaches the WebUI through /api/5/args (`serverArgs.byte`)."""
    payload = _run_render_probe("network-byte")
    assert _table_rows(payload, "network", 3) == [["Loopback", "100", "100"], ["eth0", "1.0M", "512.0K"]]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_network_keeps_its_header_row_and_shows_no_line():
    """The TUI paints the header row of an empty block; so does the WebUI now,
    instead of G9-3's "no interface" text.
    """
    payload = _run_render_probe("network-empty")
    assert payload["pluginColumnHeaders"].get("network") == ["NETWORK", "Rx/s", "Tx/s"]
    assert "network" not in payload["pluginTableCells"], "no row may render"
    assert "no interface" not in payload["pluginText"].get("network", "")


@pytest.mark.parametrize(
    ("scenario", "name", "title"),
    [
        pytest.param("network-rows", "network", "NETWORK", id="network"),
        pytest.param("diskio", "diskio", "DISK I/O", id="diskio"),
        pytest.param("fs", "fs", "FILE SYS", id="fs"),
        pytest.param("wifi", "wifi", "WIFI", id="wifi"),
        pytest.param("sensors", "sensors", "SENSORS", id="sensors"),
        pytest.param("irq", "irq", "IRQ", id="irq"),
        pytest.param("folders", "folders", "FOLDERS", id="folders"),
        pytest.param("raid", "raid", "RAID disks", id="raid"),
        pytest.param("smart", "smart", "SMART disks", id="smart"),
        # `ports` is the deliberate exception (G9-7 D4, and
        # ports/render_curses_v5.py's own test_no_title_row_deliberate_do_not_fix):
        # it renders NO header row at all, so `title` is None here and the
        # assertions below flip to proving the ABSENCE of a <th> instead of
        # its presence -- a future change that gives ports a header row
        # turns this test red rather than silently passing.
        pytest.param("ports", "ports", None, id="ports-has-no-header-row"),
        # `mpp` is the same exception, for the same reason (G9-8 Task 3): its
        # TUI line 1 is the title alone, no column labels, so it too carries
        # no #head slot. `npu` is NOT here at all -- it does not use
        # CollectionBlock (its "header" line is the device's own name, not a
        # fixed label) and its <h2> never disappears once loaded, so the
        # `pluginHeaders[index] is None` assertion below does not apply to it,
        # exactly as it already does not apply to `gpu`.
        pytest.param("mpp", "mpp", None, id="mpp-has-no-header-row"),
        # `percpu` DOES keep a header row and a title cell, standalone (the
        # `percpu` scenario's pluginslist has no quicklook) -- G9-8 Task 4.
        pytest.param("percpu", "percpu", "CPU", id="percpu"),
    ],
)
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_loaded_collection_puts_its_title_in_the_header_row(scenario, name, title):
    """G9-6 D6: once loaded, the title is the first <th> and there is no <h2>;
    the <article> keeps naming itself through aria-label. `ports` is the
    deliberate exception covered above.
    """
    payload = _run_render_probe(scenario)
    index = payload["pluginNames"].index(name)
    assert payload["pluginHeaders"][index] is None, f"{name}: no <h2> once loaded"
    if title is None:
        assert name not in payload["pluginColumnHeaders"], (
            f"{name}: must render no header row at all: {payload['pluginColumnHeaders']!r}"
        )
    else:
        assert payload["pluginColumnHeaders"][name][0] == title
    assert "aria-label" in payload["pluginAttrs"][name]


@pytest.mark.parametrize(
    ("name", "title"),
    [
        pytest.param("network", "NETWORK", id="network"),
        pytest.param("diskio", "DISK I/O", id="diskio"),
        pytest.param("fs", "FILE SYS", id="fs"),
        pytest.param("wifi", "WIFI", id="wifi"),
        pytest.param("sensors", "SENSORS", id="sensors"),
        pytest.param("irq", "IRQ", id="irq"),
        pytest.param("folders", "FOLDERS", id="folders"),
        pytest.param("raid", "RAID disks", id="raid"),
        pytest.param("smart", "SMART disks", id="smart"),
        # `ports` still shows its title WHILE loading -- only its LOADED state
        # has no visible header row (G9-7 D4, see
        # test_a_loaded_collection_puts_its_title_in_the_header_row above).
        pytest.param("ports", "PORTS", id="ports"),
        pytest.param("npu", "NPU", id="npu"),
        pytest.param("mpp", "MPP", id="mpp"),
        # `percpu` is NOT here: the `default` scenario carries no `--percpu`,
        # and percpu never renders without it (final review, Critical 1) --
        # see test_percpu_keeps_its_title_while_loading_when_visible below,
        # which uses a scenario where percpu is actually on screen.
    ],
)
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_collection_keeps_its_title_heading_while_loading(name, title):
    """Before its first payload a collection still says what it is."""
    payload = _run_render_probe("default")
    index = payload["pluginNames"].index(name)
    assert payload["pluginHeaders"][index] == title
    assert "loading" in payload["pluginText"][name]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_percpu_keeps_its_title_while_loading_when_visible():
    """The `percpu` case moved out of the shared parametrize above (final
    review, Critical 1): percpu needs `--percpu` to render at all, so it
    cannot share the `default` scenario the other collections use. Same
    assertion, a scenario where percpu is actually visible and has not
    published its first payload.
    """
    payload = _run_render_probe("percpu-loading")
    index = payload["pluginNames"].index("percpu")
    assert payload["pluginHeaders"][index] == "CPU"
    assert "loading" in payload["pluginText"]["percpu"]


@pytest.mark.parametrize(
    ("scenario", "name"),
    [
        pytest.param("network-rows", "network", id="network"),
        pytest.param("diskio", "diskio", id="diskio"),
        pytest.param("fs", "fs", id="fs"),
    ],
)
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_path_like_name_keeps_its_tail_and_its_full_text_on_hover(scenario, name):
    """G9-6 D3: interfaces, disks and mount points lose their START, like the
    TUI's "_" + name[-17:]. That needs `.gl-truncate-start` AND a <bdi>, which
    stops the bidi algorithm from moving a leading "/" to the end.
    """
    cells = _run_render_probe(scenario)["pluginNameCells"].get(name)
    assert cells, f"{name}: vacuous, no name cell rendered"
    for cell in cells:
        classes = cell["className"].split()
        assert {"gl-name", "gl-truncate", "gl-truncate-start"} <= set(classes), cell
        assert cell["hasBdi"], f"{name}: the name must sit in a <bdi>: {cell!r}"
        assert cell["title"] == cell["text"], f"{name}: the full name is on hover: {cell!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_diskio_renders_the_tui_rows_sorted_by_raw_name():
    """diskio/render_curses_v5.py:100-131: sorted by raw disk_name, hide_zero
    and rate-less rows skipped, the alias displayed, byte rates without "/s".
    """
    payload = _run_render_probe("diskio")
    assert payload["pluginColumnHeaders"]["diskio"] == ["DISK I/O", "R/s", "W/s"]
    assert _table_rows(payload, "diskio", 3) == [["nvme0n1", "855B", "1.2K"], ["Backup", "1.5K", "0B"]]


@pytest.mark.parametrize(
    ("scenario", "label", "rows"),
    [
        pytest.param(
            "fs",
            "Used",
            [
                ["root", "125.0G", "500.0G"],
                ["/home", "512.0G", "1.0T"],
                ["/var/snap/firefox/common/host-hunspell", "1.2K", "1.2K"],
            ],
            id="used",
        ),
        pytest.param(
            "fs-free-space",
            "Free",
            [
                ["root", "375.0G", "500.0G"],
                ["/home", "512.0G", "1.0T"],
                ["/var/snap/firefox/common/host-hunspell", "0B", "1.2K"],
            ],
            id="free",
        ),
    ],
)
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_fs_renders_the_tui_rows_and_switches_used_for_free(scenario, label, rows):
    """fs/render_curses_v5.py:73-121: the payload's `free_space` picks both
    the second column and its label; rows sorted by raw mount point.
    """
    payload = _run_render_probe(scenario)
    assert payload["pluginColumnHeaders"]["fs"] == ["FILE SYS", label, "Total"]
    assert _table_rows(payload, "fs", 3) == rows


@pytest.mark.parametrize("scenario", ["fs", "fs-free-space"])
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_fs_colours_the_used_or_free_cell_from_percent_never_the_total(scenario):
    """v4 decorates the used/free cell from `percent` (fs/render_curses_v5.py
    docstring); Total is never coloured. Cells: root 0-2, /home 3-5, snap 6-8.
    """
    cells = _run_render_probe(scenario)["pluginTableCells"]["fs"]
    assert _tier_classes(cells[4]["value"]) == {"gl-level-careful"}, cells[4]
    assert _tier_classes(cells[5]["value"]) == set(), cells[5]
    assert _tier_classes(cells[7]["value"]) == {"gl-level-critical"}, cells[7]
    assert _tier_classes(cells[8]["value"]) == set(), cells[8]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_memswap_renders_total_and_the_paging_rates():
    """TUI reference (memswap/render_curses_v5.py docstring): SWAP + percent,
    then total, sin, sout.

    `used` and `free` are deliberately absent: v5 trades that redundant pair
    (they are derivable from total and percent) for the live paging rates.
    Asserting their VALUES are absent, not just their labels, is what makes
    this a parity test rather than a spelling test.

    Note on "0B/s" rather than the docstring's illustrative "0.0K/s": the
    real formatter (`format_bytespers`/`formatRate`, both base-1024
    "K/M/G" scaling) never promotes a zero value to "K" -- `sout=0` reads
    as "0B/s" on both the TUI and the WebUI. Confirmed against
    `glances.outputs.curses_formatters_v5.format_bytespers(0.0)`, which
    also returns "0B/s"; the docstring's "0.0K/s" is not literal.
    """
    payload = _run_render_probe("memswap")
    text = payload["pluginText"].get("memswap", "")

    for expected in ("SWAP", "25.0%", "total", "16.0G", "sin", "100.0K/s", "sout", "0B/s"):
        assert expected in text, f"expected {expected!r} in the SWAP plugin text, got {text!r}"
    assert "4.0G" not in text, f"`used` must not be rendered: {text!r}"
    assert "12.0G" not in text, f"`free` must not be rendered: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_memswap_shows_a_dash_for_rates_before_the_second_cycle():
    """`sin`/`sout` are rate fields: null until a baseline exists, and PRESENT
    in the payload while null. The component must render "-" for them and
    still render everything else.
    """
    payload = _run_render_probe("memswap-no-rates")
    text = payload["pluginText"].get("memswap", "")

    assert "16.0G" in text, f"total must still render: {text!r}"
    assert "-" in text, f"expected the missing marker for the null rates: {text!r}"
    assert "K/s" not in text, f"no rate should be formatted when both are null: {text!r}"


@pytest.mark.parametrize(("scenario", "name"), [("wifi", "wifi"), ("sensors", "sensors")])
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_label_like_name_keeps_its_head_and_its_full_text_on_hover(scenario, name):
    """G9-6 D3: ssids and sensor labels lose their END, like the TUI's
    label[:N] -- plain `.gl-truncate`, no <bdi> needed.
    """
    cells = _run_render_probe(scenario)["pluginNameCells"].get(name)
    assert cells, f"{name}: vacuous, no name cell rendered"
    for cell in cells:
        classes = set(cell["className"].split())
        assert {"gl-name", "gl-truncate"} <= classes and "gl-truncate-start" not in classes, cell
        assert cell["title"] == cell["text"], f"{name}: the full name is on hover: {cell!r}"
        assert not cell["hasBdi"], f"{name}: a trailing-ellipsis name needs no <bdi>: {cell!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_wifi_renders_the_tui_rows_sorted_by_ssid():
    payload = _run_render_probe("wifi")
    assert payload["pluginColumnHeaders"]["wifi"] == ["WIFI", "dBm"]
    assert _table_rows(payload, "wifi", 2) == [["wlan0", "-71"], ["wlp0s20f3", "-54"]]


@pytest.mark.parametrize(
    ("scenario", "values"),
    [
        pytest.param("sensors", ["42C", "1200R", "44C", "80%↓", "100%✓", "55%↑", "ERR", "36C"], id="celsius"),
        pytest.param(
            "sensors-fahrenheit", ["108F", "1200R", "110F", "80%↓", "100%✓", "55%↑", "ERR", "97F"], id="fahrenheit"
        ),
    ],
)
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_sensors_renders_the_tui_values_in_payload_order(scenario, values):
    """sensors/render_curses_v5.py:77-128: payload order; `--fahrenheit`
    converts temperatures but never a battery or a fan; battery trend arrows;
    a sentinel verbatim; an empty battery and a non-numeric value skipped.
    The TUI's header row is one cell, so the value column's <th> is empty.
    """
    payload = _run_render_probe(scenario)
    assert payload["pluginColumnHeaders"]["sensors"] == ["SENSORS", ""]
    labels = [
        "Composite",
        "fan1",
        "Core 0",
        "BAT BAT0",
        "BAT BAT2",
        "BAT BAT3",
        "sda",
        "Composite temperature of the NVMe controller",
    ]
    assert _table_rows(payload, "sensors", 2) == [list(pair) for pair in zip(labels, values)]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_sensors_renders_both_rows_of_a_repeated_label():
    """A real payload repeats labels (a chip's temperature and fan are both
    "dell_smm 0"); the TUI shows both rows, so must the WebUI.
    """
    payload = _run_render_probe("sensors-duplicate-labels")
    assert _table_rows(payload, "sensors", 2) == [["dell_smm 0", "52C"], ["dell_smm 0", "2418R"]]


def test_sensors_rows_are_not_keyed_by_their_label():
    """The render probe only sees the first paint, where duplicate keys still
    render; the bug is in Vue's keyed diff on a LATER tick (stale rows pile up
    when the list changes -- reproduced on Vue's production runtime in the
    G9-6 final review). Labels are not unique, so the row key must not be the
    label. Source-level, like the CSS checks in test_webui_v5_tokens.py.
    """
    source = (
        Path(__file__).resolve().parent.parent / "glances" / "outputs" / "static" / "js" / "v5" / "PluginSensors.vue"
    ).read_text()
    assert ':key="row.item.label"' not in source
    assert 'v-for="(row, index) in rows" :key="index"' in source


# ------------------------------------------------------- cpu TUI parity (G9-4)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cpu_renders_the_linux_three_column_grid():
    """TUI reference (cpu/render_curses_v5.py docstring, lines 17-21)."""
    payload = _run_render_probe("cpu")
    text = payload["pluginText"].get("cpu", "")

    for expected in (
        "CPU",
        "4.5%",
        "idle",
        "95.5%",
        "ctx_sw",
        "6.7K",
        "user",
        "3.8%",
        "inter",
        "3.0K",
        "system",
        "0.7%",
        "sw_int",
        "1.8K",
        "iowait",
        "steal",
        "guest",
    ):
        assert expected in text, f"expected {expected!r} in the CPU plugin text, got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cpu_title_row_carries_only_the_total_not_idle_or_ctx_sw():
    """Task 6b: `idle` and `ctx_sw` move out of the title row -- `idle` becomes
    the first row of column 2, `ctx_sw` the first row of column 3.

    The substring checks in `test_cpu_renders_the_linux_three_column_grid`
    cannot tell this layout apart from Task 6's (title row carrying `idle`/
    `ctx_sw` beside `CPU 4.5%`): every string it looks for is present either
    way, since `pluginText` concatenates the whole article regardless of
    where each pair sits.

    `textContent` concatenates in DOM order, and the three columns are three
    sequential <dl> elements after the title. So `user` (column 1's first
    row) must appear in the text BEFORE `idle` (column 2's first row) in the
    new layout. In Task 6's layout `idle` sits in the title row, ahead of
    the grid entirely, so it appears BEFORE `user` -- this assertion fails
    against that layout, which is the RED step for this task.
    """
    payload = _run_render_probe("cpu")
    text = payload["pluginText"].get("cpu", "")

    assert "user" in text and "idle" in text, f"expected both `user` and `idle` in the CPU text: {text!r}"
    assert text.index("user") < text.index("idle"), (
        f"expected `user` (column 1) before `idle` (column 2's first row): {text!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cpu_switches_column_one_and_column_three_on_payload_content():
    """The TUI branches on payload CONTENT, never on the OS, so the WebUI can
    reproduce it exactly (cpu/render_curses_v5.py:181-200).

    This fixture has no `user` key (column 1 becomes idle/cpucore/dpc), a
    null-but-present `soft_interrupts` (column 3 falls back to ctx_switches),
    and no `guest` key (column 3's last row falls back to syscalls). It fails
    if the two kinds of check -- key presence vs value -- are collapsed into
    one.
    """
    payload = _run_render_probe("cpu-idle-tag")
    text = payload["pluginText"].get("cpu", "")

    assert "dpc" in text, f"the idle-tag branch must show dpc: {text!r}"
    assert "user" not in text, f"no `user` key, so no user row: {text!r}"
    assert "sw_int" not in text, f"soft_interrupts is null -> ctx_switches instead: {text!r}"
    assert "syscalls" in text, f"no `guest` key -> syscalls instead: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cpu_leaves_column_three_short_when_neither_guest_nor_syscalls():
    """Column 3's last row carries neither `guest` nor `syscalls`.

    `pluginText` cannot distinguish an emitted empty label/value pair from an
    absent one -- the three `<dl>` are independent grids -- so what is asserted
    is the absence of both labels while the rest of column 3 still renders.
    """
    payload = _run_render_probe("cpu-no-third-row")
    text = payload["pluginText"].get("cpu", "")

    assert "guest" not in text, f"no guest key: {text!r}"
    assert "syscalls" not in text, f"syscalls is null: {text!r}"
    assert "sw_int" in text, f"the rest of column 3 must still render: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cpu_drops_ctx_switches_when_it_has_no_rate_yet():
    """`ctx_switches` opens column 3 only when it has a value.

    It is a `rate` field, so it is null-but-present on the first cycle -- the
    real production state, not an edge case. `soft_interrupts` is populated
    here, so the column-3 fallback does not bring `ctx_sw` back either and it
    must not appear anywhere in the block.
    """
    payload = _run_render_probe("cpu-ctx-switches-null")
    text = payload["pluginText"].get("cpu", "")

    assert "ctx_sw" not in text, f"a null ctx_switches must render nowhere: {text!r}"
    assert "inter" in text, f"the rest of column 3 must still render: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cpu_keeps_a_null_guest_ahead_of_a_populated_syscalls():
    """`guest` is chosen on KEY PRESENCE, `syscalls` on VALUE
    (cpu/render_curses_v5.py:196-199).

    A `guest` that is present but null therefore still wins the last row --
    shown as the missing marker -- and `syscalls` must not appear even though
    it carries a value. Every other cpu fixture passes with the two checks
    collapsed into one; this is the one that does not.
    """
    payload = _run_render_probe("cpu-guest-null")
    text = payload["pluginText"].get("cpu", "")

    assert "guest-" in text, f"a null guest must still render, as the missing marker: {text!r}"
    assert "syscalls" not in text, f"`guest` is present as a key, so syscalls must not render: {text!r}"


# ------------------------------------------------------- gpu TUI parity (G9-4)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_one_card_renders_the_summary_block():
    """TUI reference (gpu/render_curses_v5.py docstring, lines 13-16): a single
    card renders the summary block -- its name as the title, then proc, mem and
    temperature, one row each.
    """
    payload = _run_render_probe("gpu-one-card")
    text = payload["pluginText"].get("gpu", "")

    assert "GeForce RTX 3080" in text, f"the title is the card's name: {text!r}"
    for expected in ("proc", "30%", "mem", "40%", "temperature", "55C"):
        assert expected in text, f"expected {expected!r} in the GPU plugin text, got {text!r}"
    assert ":" not in text, f"labels carry no trailing colon: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_several_cards_render_one_row_each_without_temperature():
    """v4 quirk reproduced on purpose: multi mode shows name + proc + mem, and
    NO temperature -- unlike summary mode, which shows all three.
    """
    payload = _run_render_probe("gpu-three-cards")
    text = payload["pluginText"].get("gpu", "")

    assert "3 GeForce RTX 3080" in text, f"title counts the cards: {text!r}"
    for expected in ("30%", "45%", "12%"):
        assert expected in text, f"expected every card's proc: {text!r}"
    assert "55C" not in text, f"multi mode shows no temperature: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_meangpu_forces_the_summary_and_the_mean_labels():
    """`--meangpu` reaches the WebUI through /api/5/args (design spec §5).

    Same three cards as `gpu-three-cards`, which renders the per-card table:
    the ONLY difference is the args fixture, so the switch to the summary
    block and to the "mean" labels can only come from the flag.
    """
    payload = _run_render_probe("gpu-three-cards-mean")
    text = payload["pluginText"].get("gpu", "")

    assert "proc mean" in text, f"meangpu switches the labels: {text!r}"
    assert ":" not in text, f"labels carry no trailing colon: {text!r}"
    assert "29%" in text, f"the mean of 30/45/12 rounds to 29: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_drops_the_memory_column_only_when_no_card_reports_it():
    """#3631: an unavailable sensor on ONE card shows N/A rather than being
    hidden, because hiding it per card misaligns heterogeneous rows. The
    column disappears only when no card reports memory at all.
    """
    payload = _run_render_probe("gpu-no-memory")
    text = payload["pluginText"].get("gpu", "")

    # `N/A` is what an undropped memory cell renders for a null value
    # (`gpuValue`), so its absence observes the dropped CELLS directly rather
    # than the absence of a label -- which would also hold for a component
    # that never labels the column at all.
    assert "N/A" not in text, f"no card reports memory -> no mem cells at all: {text!r}"
    assert "30%" in text and "45%" in text, f"proc must still render: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_keeps_the_memory_cell_of_a_card_that_reports_nothing():
    """The other half of #3631, and the half the spec section 8.4 actually
    argues for: a card reporting no memory still shows `N/A`, because hiding
    the cell per card drops a cell and misaligns heterogeneous rows.

    `gpu-no-memory` (every card null) cannot observe this -- a component that
    hid the cell per card passes it. This fixture has card 0 at 40% and card 1
    at null, so only the column-level rule renders an "N/A".
    """
    payload = _run_render_probe("gpu-mixed-memory")
    text = payload["pluginText"].get("gpu", "")

    assert "40%" in text, f"the reporting card's memory must render: {text!r}"
    assert "N/A" in text, f"the non-reporting card keeps its cell as N/A: {text!r}"
    assert "30%" in text and "45%" in text, f"both cards' proc must still render: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_with_no_card_renders_nothing_beyond_its_title():
    """Design spec section 11: a machine with no GPU (or with every backend
    failing) publishes an empty `data` list, and the plugin then renders its
    title and nothing else -- no empty table, no "loading…" (the payload
    arrived, it is just empty).
    """
    payload = _run_render_probe("gpu-zero-cards")

    assert payload["pluginText"].get("gpu") == "GPU", (
        f"expected the bare fallback title, got {payload['pluginText'].get('gpu')!r}"
    )
    assert "gpu" not in payload["pluginValueClasses"], (
        f"no card -> no value cell: {payload['pluginValueClasses'].get('gpu')!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_multi_card_name_cell_is_capped_and_keeps_the_full_name_in_title():
    """The multi-card table's name column must get the same `.gl-name
    .gl-truncate` treatment the left sidebar (and npu's own header) use,
    capped with `--gl-name-width: 9ch` -- the TUI's own `[0:9]` cut
    (render_curses_v5.py:114). Like every other `.gl-truncate` cell the cap
    is CSS-only: the DOM text stays the full name, and `title` repeats it
    for hover (G9-8 smoke fix 3).
    """
    payload = _run_render_probe("gpu-three-cards")
    names = payload["pluginNameCells"]["gpu"]
    assert len(names) == 3, f"got {names!r}"
    for cell in names:
        assert "gl-name" in cell["className"] and "gl-truncate" in cell["className"], f"got {cell!r}"
        assert cell["text"] == "GeForce RTX 3080", f"got {cell!r}"
        assert cell["title"] == "GeForce RTX 3080", f"got {cell!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_multi_card_value_cells_still_carry_gl_num():
    """Fix 3 (and G9-8 smoke fix 4, which replaced the global `.gl-num` 9ch
    floor with a table-scoped 8ch one -- see `test_gpu_value_column_floor_is_
    scoped_and_fits_its_widest_cell`) both rely on the value cells keeping
    the class that drives right-alignment and tabular digits. The name cell
    must NOT carry it (it is not a value).
    """
    payload = _run_render_probe("gpu-three-cards")
    cells = payload["pluginTableCells"]["gpu"]
    name_cells = [c for c in cells if "gl-name" in (c["value"] or "")]
    num_cells = [c for c in cells if "gl-num" in c["cell"]]
    assert len(name_cells) == 3, f"got {cells!r}"
    assert len(num_cells) == 6, f"one proc + one mem cell per of 3 rows: {cells!r}"
    assert all("gl-num" not in c["cell"] for c in name_cells), f"got {name_cells!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_value_column_floor_is_scoped_and_fits_its_widest_cell():
    """G9-8 smoke fix 4: the previous round's `min-width: 0` let the value
    column resize with the text on every tick ("9%" -> "100%"), which is the
    jitter the maintainer's smoke test caught. The render probe reports cell
    classes and text, not geometry, so this pins what it actually can:
    the scoped rule text in the stylesheet the component ships, and that the
    numeric cells it targets still carry `gl-num` (asserted for real payload
    data by `test_gpu_multi_card_value_cells_still_carry_gl_num`).

    8ch, not the TUI's 4-character `{:>3.0f}%`/`{:>4}` value width: the
    `mem` column's `valueColumns()` format function prepends the literal
    "mem " *inside* the `.gl-num` cell ("mem 100%" is 8 characters), and this
    one selector floors both the `proc` and `mem` columns.
    """
    source = (
        Path(__file__).resolve().parent.parent / "glances" / "outputs" / "static" / "js" / "v5" / "PluginGpu.vue"
    ).read_text()
    assert ".gl-plugin table td.gl-num" in source, "the scoped rule must still exist"
    assert "min-width: 8ch;" in source, f"expected an 8ch floor, source did not contain it verbatim: {source!r}"
    assert "min-width: 0;" not in source, "the previous round's zero floor (the jitter bug) must be gone"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_honours_fahrenheit():
    """`--fahrenheit` also arrives through /api/5/args. Same single card as
    `gpu-one-card`, which renders 55C: only the args fixture differs.
    """
    payload = _run_render_probe("gpu-one-card-fahrenheit")
    text = payload["pluginText"].get("gpu", "")

    assert "131F" in text, f"55C is 131F: {text!r}"
    assert "55C" not in text, f"Celsius must not also render: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_summary_colours_from_the_first_card_not_from_the_mean():
    """v4 quirk reproduced on purpose (gpu/render_curses_v5.py:69, 80): summary
    mode averages ACROSS the cards but passes `first_id` to `_level_role()`,
    i.e. it colours from the FIRST card's `_levels`.

    The fixture carries the same three cards as `gpu-three-cards` with card 0
    critical on `proc` and cards 1 and 2 ok, and `--meangpu` to force the
    summary. Two thirds of the tiers are ok, so a colour derived from the mean
    -- or from any card but the first -- cannot come out critical: the
    assertion distinguishes the quirk from the "fix".

    The tier reaches the DOM only as a `gl-level-*` class, never as text,
    which is why this reads `pluginValueClasses` rather than `pluginText`.
    """
    payload = _run_render_probe("gpu-first-card-colour")
    classes = payload["pluginValueClasses"].get("gpu")

    assert classes, "no GPU value cells rendered"
    # Summary order is proc, mem, temperature -- proc is the first <dd>.
    assert "gl-level-critical" in classes[0], f"the proc cell must take card 0's critical tier, got {classes[0]!r}"


# ------------------------------------------------------- header plugins (G9-5)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_header_blocks_are_hidden_while_their_plugin_has_not_published():
    """The `default` scenario publishes nothing. The TUI renders `[]` for an
    empty payload, so the header blocks are hidden -- not "loading…", which
    would fill the banner with placeholders.

    `mem` is asserted NOT hidden in the same run: without that, a probe that
    reported every element as hidden would pass this test.
    """
    payload = _run_render_probe("default")
    hidden = payload["pluginHidden"]
    for name in ("system", "ip", "uptime", "cloud", "now"):
        assert hidden.get(name) is True, f"{name} must be hidden before it publishes: {hidden!r}"
    assert hidden.get("mem") is False, f"vacuous: a panel plugin is never hidden: {hidden!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_system_renders_the_hostname_and_the_os_name():
    """system/render_curses_v5.py: `hostname` then `hr_name`."""
    payload = _run_render_probe("header")
    text = payload["pluginText"].get("system", "")
    assert payload["pluginHidden"].get("system") is False
    assert "test-host" in text, f"got {text!r}"
    assert "Ubuntu 26.04 64bit / Linux 7.0.0-31-generic" in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_system_without_a_hostname_is_hidden():
    payload = _run_render_probe("system-no-hostname")
    assert payload["pluginHidden"].get("system") is True, f"got {payload['pluginHidden']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_uptime_renders_in_the_tui_format():
    """uptime/render_curses_v5.py: `Uptime:` then format_seconds(seconds)."""
    payload = _run_render_probe("header")
    text = payload["pluginText"].get("uptime", "")
    assert "Uptime:" in text and "3d04h" in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_now_renders_the_custom_date():
    """now/render_curses_v5.py: the `custom` string only; `iso` is REST-only."""
    payload = _run_render_probe("header")
    text = payload["pluginText"].get("now", "")
    assert text == "2026-09-11 10:20:30 CEST", f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_header_plugins_sit_in_the_header_zone():
    payload = _run_render_probe("header")
    assert payload["slots"].get("header-left") == ["system", "ip"], f"got {payload['slots']!r}"
    assert payload["slots"].get("header-right") == ["uptime", "cloud", "now"], f"got {payload['slots']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_ip_renders_the_private_and_public_addresses():
    """ip/render_curses_v5.py: `IP addr/cidr`, then `Pub addr` and the
    geolocation string."""
    payload = _run_render_probe("header")
    text = payload["pluginText"].get("ip", "")
    for expected in ("IP", "192.168.1.10/24", "Pub", "203.0.113.42", "Paris, France (AS64496 Example Net)"):
        assert expected in text, f"expected {expected!r} in the ip text, got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_ip_without_a_cidr_shows_the_bare_address():
    """`mask_cidr is not None` gates the suffix (ip/render_curses_v5.py:53)."""
    payload = _run_render_probe("ip-no-cidr")
    text = payload["pluginText"].get("ip", "")
    assert "192.168.1.10" in text, f"got {text!r}"
    assert "192.168.1.10/" not in text, f"no cidr -> no slash: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_ip_masks_the_public_address_with_hide_public_info():
    """`--hide-public-info` reaches the WebUI through /api/5/args. Same payload
    as `header`; only the args fixture differs.

    Display-only, like the TUI: the API still serves the address in clear
    (G9-5 spec §11). This test proves the rendered text, nothing more.
    """
    payload = _run_render_probe("header-hide-public")
    text = payload["pluginText"].get("ip", "")
    assert "203.0.*.*" in text, f"got {text!r}"
    assert "113.42" not in text, f"the masked octets must not render: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_ip_with_no_address_is_hidden():
    payload = _run_render_probe("ip-no-address")
    assert payload["pluginHidden"].get("ip") is True, f"got {payload['pluginHidden']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cloud_renders_the_platform_and_the_instance_summary():
    """cloud/render_curses_v5.py docstring: `OpenStack gold instance my-vm (eu-west-1a)`."""
    payload = _run_render_probe("header")
    text = payload["pluginText"].get("cloud", "")
    assert "OpenStack" in text, f"got {text!r}"
    assert "gold instance my-vm (eu-west-1a)" in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cloud_without_a_name_is_hidden():
    """#2485: platform and name are both mandatory, or nothing renders."""
    payload = _run_render_probe("cloud-no-name")
    assert payload["pluginHidden"].get("cloud") is True, f"got {payload['pluginHidden']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cloud_fills_a_missing_part_with_unknown():
    payload = _run_render_probe("cloud-no-region")
    text = payload["pluginText"].get("cloud", "")
    assert "gold instance my-vm (Unknown)" in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cloud_disabled_on_the_server_is_not_rendered():
    """The shipped default. Before G9-5 this block would have sat in the header
    as a permanent loading state for most users."""
    payload = _run_render_probe("cloud-disabled")
    assert "cloud" not in payload["pluginNames"], f"got {payload['pluginNames']!r}"
    assert "system" in payload["pluginNames"], f"vacuous: the header still renders: {payload['pluginNames']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_header_blocks_show_their_error_when_all_fails():
    """Spec §9: "`/api/5/all` fails -> every visible block shows its error,
    header included." `fetchAll()` (api.js) turns the failed fetch into
    `api/5/all: HTTP 500` for every requested plugin, and each header
    component's root is `v-show="error || <guard>"` -- the `error ||` term is
    what keeps the block visible although its guard field never arrived."""
    payload = _run_render_probe("all-unreachable")
    for name in ("system", "ip", "uptime", "cloud", "now"):
        assert payload["pluginHidden"].get(name) is False, (
            f"{name} must show its error, not hide: {payload['pluginHidden']!r}"
        )
        text = payload["pluginText"].get(name, "")
        assert "HTTP 500" in text, f"{name}: expected the HTTP 500 error text, got {text!r}"


# ------------------------------------------- horizontal degradation (2026-09-12)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_wide_window_degrades_nothing():
    """The cascade only runs when a zone overflows."""
    payload = _run_render_probe("degrade-wide")
    assert payload["degrade"] == {"header": {}, "top": {}}
    for name in ("cpu", "mem", "memswap", "gpu"):
        assert name in payload["pluginNames"], f"{name} must still render: {payload['pluginNames']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_narrow_top_row_degrades_in_the_tui_order():
    """glances_curses_v5.py:62 -- MEM's 2nd column goes first, whole blocks last."""
    payload = _run_render_probe("degrade-medium")
    assert payload["degrade"]["top"] == {"mem_cols": 1}
    assert "memswap" in payload["pluginNames"], "a block is hidden only after the column notches"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_exhausted_cascade_hides_the_last_resort_blocks():
    """Both cascades run to the end: swap and gpu go from the top row, and the
    header keeps only the hostname (spec section 4.1).
    """
    payload = _run_render_probe("degrade-narrow")
    assert payload["degrade"]["top"]["hide_memswap"] is True
    assert payload["degrade"]["top"]["hide_gpu"] is True
    assert payload["degrade"]["header"]["hide_uptime"] is True
    for name in ("memswap", "gpu", "cloud", "now", "ip", "uptime"):
        assert name not in payload["pluginNames"], f"{name} must be hidden: {payload['pluginNames']!r}"
    assert "system" in payload["pluginNames"], "the hostname block always survives"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_narrow_top_row_collapses_the_quicklook_header_to_the_frequency():
    """Cascade step (d), `quicklook_freq_only`: the CPU name is replaced by the
    literal "Frequency" — the TUI shrinks the block that way rather than
    dropping the line."""
    payload = _run_render_probe("top-narrow-quicklook")
    text = payload["pluginText"]["quicklook"]
    assert "Frequency" in text and "Intel Core" not in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_exhausted_cascade_hides_quicklook_last():
    """Cascade step (e), `hide_quicklook`: the last notch before the top row
    crops. `hide_quicklook` goes through `HIDDEN_BY`, the same shell-level
    removal `hide_memswap`/`hide_gpu` use (test_an_exhausted_cascade_hides_the_
    last_resort_blocks): the plugin is filtered out of `slots` and never
    reaches the DOM at all, so it is absent from `pluginNames` -- there is no
    `<article data-plugin="quicklook">` for `pluginHidden` to observe a
    `v-show` on, unlike `quicklook-empty`'s own internal hide rule.
    """
    payload = _run_render_probe("top-narrowest-quicklook")
    assert "quicklook" not in payload["pluginNames"], f"got {payload['pluginNames']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_dom_without_layout_degrades_nothing():
    """Spec section 9: an unusable measurement (0) must never hide a stat. Every
    pre-existing scenario runs with no widths at all, which is this case.
    """
    payload = _run_render_probe("default")
    assert payload["degrade"] == {"header": {}, "top": {}}


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_mem_drops_its_second_column_first():
    """mem/render_curses_v5.py:92 -- at mem_cols=1 the 2nd column goes, which in
    the WebUI is where `active` lives (G9-5 A1).
    """
    payload = _run_render_probe("degrade-medium")
    columns = payload["pluginGrid"]["mem"]
    assert len(columns) == 1, f"only column 1 survives: {columns!r}"
    assert [pair[0] for pair in columns[0]] == ["MEM", "total", "avail", "free"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cpu_drops_its_third_then_its_second_column():
    """cpu/render_curses_v5.py:127 -- cpu_cols 3 -> 2 -> 1."""
    narrow = _run_render_probe("degrade-narrow")
    assert len(narrow["pluginGrid"]["cpu"]) == 1, narrow["pluginGrid"]["cpu"]
    assert [pair[0] for pair in narrow["pluginGrid"]["cpu"][0]] == ["CPU", "user", "system", "iowait"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_header_drops_the_geolocation_before_the_addresses():
    """glances_curses_v5.py:87 -- step (1) drops ip's geolocation string; the
    addresses themselves survive until step (4).
    """
    payload = _run_render_probe("degrade-header-location")
    text = payload["pluginText"]["ip"]
    assert "192.168.1.10" in text, f"the private address stays: {text!r}"
    assert "Paris" not in text, f"the geolocation goes: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_header_drops_the_os_string_but_keeps_the_hostname():
    """glances_curses_v5.py:87 -- step (2)."""
    payload = _run_render_probe("degrade-header-os")
    text = payload["pluginText"]["system"]
    assert "test-host" in text, f"the hostname stays: {text!r}"
    assert "Ubuntu" not in text, f"the OS string goes: {text!r}"


# ------------------------------------------------------ ports (G9-7 Task 4)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_ports_renders_every_status_branch():
    """ports/render_curses_v5.py:57-78 -- the eight status strings, in payload
    order (the TUI does not sort), each next to its description.
    """
    payload = _run_render_probe("ports")
    texts = [cell["text"] for cell in payload["pluginTableCells"]["ports"]]
    assert texts == [
        "Home Box",
        "12ms",
        "Internet ICMP",
        "Timeout",
        "Mail relay",
        "Timeout",
        "SSH",
        "Open",
        "Still scanning",
        "Scanning",
        "No gateway",
        "None",
        "My Blog",
        "Code 200",
        "Broken site",
        "Error",
        "Web scanning",
        "Scanning",
    ], f"got {texts!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_ports_skips_an_item_it_cannot_scan():
    """An item with neither `url` nor `host` is skipped, not rendered with a
    blank status (ports/render_curses_v5.py:107-114)."""
    payload = _run_render_probe("ports")
    assert "Neither url nor host" not in payload["pluginText"]["ports"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_ports_has_no_header_row():
    """G9-7 D4, and ports/render_curses_v5.py's own
    `test_no_title_row_deliberate_do_not_fix`: `ports` reads as one block with
    `network` above it, so it paints no title and no column header. The block
    is still named for assistive technology.
    """
    payload = _run_render_probe("ports")
    assert "ports" not in payload["pluginColumnHeaders"], (
        f"ports must render no <th>: {payload['pluginColumnHeaders']!r}"
    )
    assert "PORTS" not in payload["pluginText"]["ports"], "the title must not be visible"
    assert "aria-label" in payload["pluginAttrs"]["ports"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_ports_colours_the_status_from_its_levels_entry():
    """The tier reaches the DOM as a class on the value <span> and nowhere
    else; a healthy port is green ("ok"), v4's OK decoration."""
    payload = _run_render_probe("ports")
    status_classes = [cell["value"] for cell in payload["pluginTableCells"]["ports"]][1::2]
    assert status_classes[0] == "gl-level-ok", f"Home Box is healthy: {status_classes!r}"
    assert status_classes[1] == "gl-level-critical", f"a timeout is critical: {status_classes!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_ports_collection_is_hidden():
    """The TUI returns [] for an empty list, so the block is not painted."""
    payload = _run_render_probe("ports-empty")
    assert payload["pluginHidden"].get("ports") is True, f"got {payload['pluginHidden']!r}"


# ---------------------------------------------------- folders (G9-7 Task 4)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_folders_renders_its_title_and_an_empty_size_header():
    """G9-7 D4: the TUI's FOLDERS line has no size label, and the empty <th>
    keeps the header aligned column by column with the body (the sensors
    precedent)."""
    payload = _run_render_probe("folders")
    assert payload["pluginColumnHeaders"]["folders"] == ["FOLDERS", ""], f"got {payload['pluginColumnHeaders']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_folders_renders_its_sizes():
    payload = _run_render_probe("folders")
    texts = [cell["text"] for cell in payload["pluginTableCells"]["folders"]]
    assert texts[1] == "125.0M", f"got {texts!r}"
    assert texts[3] == "17.0G", f"got {texts!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_folders_marks_an_unreadable_folder_bold_and_untiered():
    """errno != 0 -> a "?" prefix and curses.A_BOLD with NO colour pair. The
    model emits no _levels entry for it, so a tier class here would mean the
    component invented one."""
    payload = _run_render_probe("folders")
    cells = payload["pluginTableCells"]["folders"]
    assert cells[5]["text"].startswith("?"), f"got {cells[5]!r}"
    assert cells[5]["value"] == "gl-strong", f"bold, no tier: {cells[5]!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_folders_renders_a_row_with_no_usable_path():
    """folders/render_curses_v5.py:93-94,103 keeps every dict item and
    coalesces a missing/falsy path to "" -- it never drops the row. A
    component filtering rows on `item.path` would silently swallow this one,
    so this asserts the row COUNT and the empty name cell, not text that
    would also pass if the row were merely renamed.
    """
    payload = _run_render_probe("folders")
    cells = payload["pluginTableCells"]["folders"]
    assert len(cells) == 8, f"expected 4 rows x 2 cells, got {cells!r}"
    assert cells[6]["text"] == "", f"the no-path row's name cell must be empty, not 'undefined': {cells[6]!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_folders_truncates_a_long_path_from_the_start():
    """The TUI keeps the tail ("_" + path[-23:]), so the ellipsis falls at the
    start; the <bdi> is load-bearing (without it the bidi algorithm moves the
    leading "/" to the end)."""
    payload = _run_render_probe("folders")
    cells = payload["pluginNameCells"]["folders"]
    assert all(cell["hasBdi"] for cell in cells), f"got {cells!r}"
    assert all("gl-truncate-start" in cell["className"] for cell in cells), f"got {cells!r}"
    assert cells[1]["title"] == "/home/nicolargo/media/library/Videos"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_folders_collection_is_hidden():
    payload = _run_render_probe("folders-empty")
    assert payload["pluginHidden"].get("folders") is True, f"got {payload['pluginHidden']!r}"


# ------------------------------------------------ connections (G9-7 Task 5)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_connections_renders_the_tui_rows_in_order():
    """connections/render_curses_v5.py:80-100 -- the title, then the four state
    counters in the TUI's fixed order, then Tracked as `count/max`. The labels
    come from the schema (G9-7 D5), so this also proves the component reads
    /api/5/all/info rather than hardcoding them.
    """
    payload = _run_render_probe("connections")
    grid = payload["pluginGrid"]["connections"]
    assert grid == [
        [
            ["TCP CONNECTIONS", ""],
            ["Listen", "3"],
            ["Initiated", "0"],
            ["Established", "12"],
            ["Terminated", "204"],
            ["Tracked", "512/1024"],
        ]
    ], f"got {grid!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_connections_colours_only_the_tracked_row():
    """The Tracked row is the only coloured one, from nf_conntrack_percent."""
    payload = _run_render_probe("connections")
    classes = payload["pluginValueClasses"]["connections"]
    assert classes[-1] == "gl-level-careful", f"got {classes!r}"
    assert set(classes[:-1]) == {""}, f"no other row may be coloured: {classes!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_connections_without_conntrack_drops_the_tracked_row():
    payload = _run_render_probe("connections-no-conntrack")
    labels = [pair[0] for pair in payload["pluginGrid"]["connections"][0]]
    assert labels == ["TCP CONNECTIONS", "Listen", "Initiated", "Established", "Terminated"], f"got {labels!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_connections_without_net_connections_keeps_only_tracked():
    payload = _run_render_probe("connections-no-net")
    labels = [pair[0] for pair in payload["pluginGrid"]["connections"][0]]
    assert labels == ["TCP CONNECTIONS", "Tracked"], f"got {labels!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_connections_with_both_probes_off_is_hidden():
    """The TUI returns [] when neither probe is enabled."""
    payload = _run_render_probe("connections-off")
    assert payload["pluginHidden"].get("connections") is True, f"got {payload['pluginHidden']!r}"


# -------------------------------------------------------- irq (G9-7 Task 5)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_irq_keeps_the_five_busiest_lines_ranked():
    """Ranking lives in the renderer, not the model: model_v5 publishes every
    line (a v4 divergence made for exporters), and the TUI sorts by rate
    descending and keeps five (irq/render_curses_v5.py:48-58). A null rate
    sorts last instead of throwing.
    """
    payload = _run_render_probe("irq")
    texts = [cell["text"] for cell in payload["pluginTableCells"]["irq"]]
    assert texts == [
        "RES",
        "501",
        "LOC",
        "340",
        "1_i8042",
        "95",
        "0",
        "12",
        "CAL",
        "7",
    ], f"got {texts!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_irq_labels_its_rate_column_from_the_schema():
    payload = _run_render_probe("irq")
    assert payload["pluginColumnHeaders"]["irq"] == ["IRQ", "Rate/s"], f"got {payload['pluginColumnHeaders']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_irq_collection_is_hidden():
    payload = _run_render_probe("irq-empty")
    assert payload["pluginHidden"].get("irq") is True, f"got {payload['pluginHidden']!r}"


# ------------------------------------------------------- raid (G9-7 Task 6)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_raid_groups_each_array_with_its_sub_lines():
    """G9-7 D3: one <tbody> per array, sub-lines inside it, the TUI's glyphs
    kept. Arrays are sorted by name as strings (raid/render_curses_v5.py:96),
    which puts md12 before md4.

    md12 is inactive AND degraded: both sub-line groups are emitted, in that
    order -- they are not exclusive, and a component that treated them as an
    if/else would drop the second.
    """
    payload = _run_render_probe("raid")
    groups = payload["pluginRowGroups"]["raid"]
    assert groups == [
        [["RAID1 md0", "2", "2"]],
        [
            ["RAID1 md12", "", ""],
            ["└─ Status inactive"],
            ["   ├─ disk 0: sde1"],
            ["   └─ disk 1: sdf1"],
            ["└─ Degraded mode"],
            ["   └─ UA"],
        ],
        [["RAID5 md4", "2", "3"], ["└─ Degraded mode"], ["   └─ UUA"]],
        [["RAID0 md9", "2", "-"]],
        [["UNKNOWN md99", "2", "2"]],
    ], f"got {groups!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_raid_renders_unknown_for_a_null_type():
    """v4/raid/render_curses_v5.py:50: a null `type` renders the literal
    "UNKNOWN" rather than an empty or missing type string. `md99` (type:
    null) exercises exactly this branch and nothing else -- active, no
    sub-lines -- so this test names the behaviour on its own instead of
    leaving it buried in the long list above.
    """
    payload = _run_render_probe("raid")
    groups = payload["pluginRowGroups"]["raid"]
    titles = [group[0][0] for group in groups]
    assert "UNKNOWN md99" in titles, f"got {titles!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_raid_labels_its_columns_from_the_schema():
    payload = _run_render_probe("raid")
    assert payload["pluginColumnHeaders"]["raid"] == ["RAID disks", "Used", "Avail"], (
        f"got {payload['pluginColumnHeaders']!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_raid_colours_the_values_and_the_status_lines_from_levels():
    """The tier reaches the DOM as a class on the value <span>, never on the
    <td> -- a prominent badge's background would otherwise fill the whole cell.
    `pluginTableCells[i]["value"]` is that span's class list;
    `pluginValueClasses` would give the cell's ("gl-num") and prove nothing.
    """
    payload = _run_render_probe("raid")
    spans = [cell["value"] for cell in payload["pluginTableCells"]["raid"]]
    assert any("gl-level-critical" in (span or "") for span in spans), f"md12 must be critical: {spans!r}"
    assert any("gl-level-warning" in (span or "") for span in spans), f"md4 must be warning: {spans!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_raid_collection_is_hidden():
    """v4 parity, and Task 3's TUI fix: no array, no block -- not a bare
    "RAID disks  Used  Avail" header."""
    payload = _run_render_probe("raid-empty")
    assert payload["pluginHidden"].get("raid") is True, f"got {payload['pluginHidden']!r}"


# ------------------------------------------------------ smart (G9-7 Task 6)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_smart_groups_each_device_with_its_attributes():
    """G9-7 D3 and smart/render_curses_v5.py: a device row, then one row per
    attribute -- the name indented by the TUI's leading space, underscores
    rendered as spaces, the raw value right-aligned. A LARGE_VALUE_KEYS raw
    goes through auto_unit() (5307033647 -> "4.94G"); everything else is
    printed as-is; a null raw renders an empty cell. The fixture carries a
    second device with its own attributes, so this also proves the grouping
    is per-device rather than one flat table.
    """
    payload = _run_render_probe("smart")
    groups = payload["pluginRowGroups"]["smart"]
    assert groups == [
        [
            ["/dev/sda Samsung SSD 850"],
            [" Power On Hours", "12345"],
            [" Reallocated Sector Ct", "0"],
            [" Data Units Written", "4.94G"],
            [" Unknown Attribute", ""],
        ],
        [
            ["/dev/sdb Crucial MX500"],
            [" Bytes Read", "2.05G"],
            [" Power Cycle Count", "87"],
        ],
    ], f"got {groups!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_smart_never_colours_a_cell():
    """v4 `smart` is display-only: EMITS_ALERTS is False and no field is
    watched, so no cell may carry a tier class."""
    payload = _run_render_probe("smart")
    spans = [cell["value"] for cell in payload["pluginTableCells"]["smart"]]
    assert not any("gl-level-" in (span or "") for span in spans), f"smart must not colour anything: {spans!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_smart_collection_is_hidden():
    payload = _run_render_probe("smart-empty")
    assert payload["pluginHidden"].get("smart") is True, f"got {payload['pluginHidden']!r}"


# -------------------------------------------------------- mpp (G9-8 Task 3)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_mpp_renders_one_row_per_engine():
    """mpp/render_curses_v5.py:38-57 — name + type, the load as a percentage
    or N/A, and the session cell ONLY when the count is non-zero (v4 omits it
    entirely at zero, it does not render "0 sess").
    """
    payload = _run_render_probe("mpp")
    texts = [cell["text"] for cell in payload["pluginTableCells"]["mpp"]]
    assert texts == [
        "RKVENC enc",
        "24.8%",
        "2 sess",
        "JPEGD jpeg",
        "0.0%",
        "RKVDEC dec",
        "N/A",
    ], f"got {texts!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_mpp_colours_only_the_load():
    payload = _run_render_probe("mpp")
    spans = [cell["value"] for cell in payload["pluginTableCells"]["mpp"]]
    assert "gl-level-careful" in (spans[1] or ""), f"got {spans!r}"
    assert not any("gl-level-" in (s or "") for s in (spans[0], spans[2])), f"only the load: {spans!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_mpp_collection_is_hidden():
    payload = _run_render_probe("mpp-empty")
    assert payload["pluginHidden"].get("mpp") is True, f"got {payload['pluginHidden']!r}"


# -------------------------------------------------------- npu (G9-8 Task 3)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_npu_renders_the_first_device_only():
    """v4 parity (npu/render_curses_v5.py:40-43): the block shows ONE NPU, the
    first, whatever the payload carries. The fixture holds two."""
    text = _run_render_probe("npu")["pluginText"]["npu"]
    assert "Second NPU" not in text, f"only the first NPU may render: {text!r}"
    assert "45" in text and "1.0G/2.0GHz" in text, f"got {text!r}"
    assert "mem" in text and "N/A" in text, f"a null mem renders N/A: {text!r}"
    assert "temperature" in text and "55C" in text, f"got {text!r}"
    assert ":" not in text, f"labels carry no trailing colon: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_npu_truncates_the_name_to_the_tui_width():
    """`name[:17]` in the TUI (_HEADER_MAX); the browser caps the cell and
    keeps the full text in `title`."""
    cells = _run_render_probe("npu")["pluginNameCells"]["npu"]
    assert cells and cells[0]["title"].startswith("Intel NPU 3720"), f"got {cells!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_npu_without_a_load_shows_the_frequency_percentage():
    """npu/render_curses_v5.py:47-54 — no load, so the cell shows the FREQ
    percentage, coloured from the `freq` level rather than the `load` one.
    """
    payload = _run_render_probe("npu-no-load")
    assert "80" in payload["pluginText"]["npu"], f"got {payload['pluginText']['npu']!r}"
    assert any("gl-level-warning" in (c or "") for c in payload["pluginValueClasses"]["npu"]), (
        f"the freq tier must colour the cell: {payload['pluginValueClasses']['npu']!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_npu_honours_fahrenheit():
    """Same payload as `npu`, `--fahrenheit` on the server: 55C -> 131F."""
    text = _run_render_probe("npu-fahrenheit")["pluginText"]["npu"]
    assert "131F" in text, f"got {text!r}"
    assert "55C" not in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_npu_collection_is_hidden():
    payload = _run_render_probe("npu-empty")
    assert payload["pluginHidden"].get("npu") is True, f"got {payload['pluginHidden']!r}"


# ----------------------------------------------------- percpu (G9-8 Task 4)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_percpu_renders_the_transposed_grid_standalone():
    """percpu/render_curses_v5.py -- columns are stats, rows are cores, sorted
    by `total` descending. Standalone (no quicklook instantiated) the block
    keeps its CPU title, its `total` column and its row labels.

    Asserts the FULL header list, not just its first two cells (final
    review, Important 3): the fixture's `stat_fields` is a SUBSET of the raw
    core's numeric keys, in the TUI's order (`_os_headers()`), not the
    payload's own key order -- the narrower assertion this replaces could not
    have told the two apart, which is how the component reading the wrong
    source went unnoticed.
    """
    payload = _run_render_probe("percpu")
    assert payload["pluginColumnHeaders"]["percpu"] == [
        "CPU",
        "total",
        "user",
        "system",
        "iowait",
        "idle",
        "irq",
        "nice",
        "steal",
        "guest",
    ], f"got {payload['pluginColumnHeaders']['percpu']!r}"
    names = [cell["text"] for cell in payload["pluginNameCells"]["percpu"]]
    assert names == ["CPU0", "CPU1", "CPU2", "CPU3", "CPU*"], f"got {names!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_percpu_stays_hidden_by_default_even_when_quicklook_is_instantiated():
    """Interaction between the two Critical fixes of the final review:
    quicklook being instantiated does NOT, by itself, bring percpu onto the
    WebUI screen -- `AppShell.vue`'s cpu/percpu exclusivity gate (Critical 1)
    hides `percpu` whenever `serverArgs.percpu` is falsy, REGARDLESS of
    quicklook. `percpu-with-quicklook` has quicklook instantiated and no
    `--percpu`; this is also why PluginPercpu.vue's own Critical 2 predicate
    (`standalone` unless quicklook is instantiated AND `serverArgs.percpu` is
    set) is not independently observable through the full AppShell-driven
    stack: percpu can only ever be VISIBLE here when `serverArgs.percpu` is
    already true, at which point Critical 2's AND-clause is trivially
    satisfied. The genuine regression guard for Critical 2 lives at the TUI
    level (test_curses_renderer_v5.py::
    test_percpu_keeps_its_labels_when_quicklook_is_instantiated_but_not_drawing_percore),
    where no such shell-level gate exists. See
    test_percpu_drops_title_total_and_labels_when_quicklook_draws_percore for
    the one combination that IS reachable here.
    """
    payload = _run_render_probe("percpu-with-quicklook")
    assert "percpu" not in payload["pluginNames"], f"got {payload['pluginNames']!r}"
    assert "cpu" in payload["pluginNames"], f"vacuous: {payload['pluginNames']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_percpu_drops_title_total_and_labels_when_quicklook_draws_percore():
    """v4 parity, mirrored from the TUI: quicklook, instantiated AND actually
    drawing its per-core bars (--percpu), already shows the per-core totals,
    so percpu stops repeating them. The WebUI learns "instantiated" from
    /api/5/pluginslist (the same notion build_frame derives from the
    instantiated plugins) and "drawing per-core bars" from
    `serverArgs.percpu` (/api/5/args) -- both halves of the corrected
    predicate (final review, Critical 2).
    """
    payload = _run_render_probe("percpu-with-quicklook-percpu")
    headers = payload["pluginColumnHeaders"]["percpu"]
    assert "CPU" not in headers and "total" not in headers, f"got {headers!r}"
    assert "percpu" not in payload["pluginNameCells"], f"no row labels: {payload['pluginNameCells'].get('percpu')!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_percpu_honours_the_configured_core_cap():
    """The test that makes `[percpu] max_cpu_display` non-inert in the browser:
    with a cap of 2, four cores collapse into the mean row."""
    payload = _run_render_probe("percpu-cap-2")
    names = [cell["text"] for cell in payload["pluginNameCells"]["percpu"]]
    assert names == ["CPU0", "CPU1", "CPU*"], f"got {names!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_percpu_never_colours_a_cell():
    """v5 percpu publishes no field-level alert (its model docstring says so);
    the system-wide `cpu` plugin is the source of CPU alerts."""
    payload = _run_render_probe("percpu")
    spans = [cell["value"] for cell in payload["pluginTableCells"]["percpu"]]
    assert not any("gl-level-" in (s or "") for s in spans), f"got {spans!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_percpu_collection_is_hidden():
    payload = _run_render_probe("percpu-empty")
    assert payload["pluginHidden"].get("percpu") is True, f"got {payload['pluginHidden']!r}"


# ------------------------------------- cpu/percpu mutual exclusion (final review, Critical 1)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_percpu_renders_and_cpu_does_not_when_the_server_ran_with_percpu():
    """The v5 TUI shows exactly one of `cpu`/`percpu` in the TOP row
    (glances_curses_v5.py:565-567: `hidden_top = "cpu" if
    self._view.show_percpu else "percpu"`, applied on every frame). The
    WebUI had no equivalent -- both rendered side by side, a duplicated CPU
    surface. `AppShell.vue`'s `slots()` now hides `cpu` when the server ran
    with `--percpu` (the best available server-side signal, since
    `show_percpu` is a TUI-only runtime toggle with no wire representation).
    Both plugins are instantiated and carry data in this scenario -- only
    /api/5/args differs from the "off" scenario below.
    """
    payload = _run_render_probe("cpu-percpu-on")
    top = payload["slots"].get("top", [])
    assert "percpu" in top, f"got {top!r}"
    assert "cpu" not in top, f"got {top!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cpu_renders_and_percpu_does_not_without_percpu():
    """The other half: no `--percpu`, so the aggregate `cpu` block renders
    and `percpu` does not -- the default screen, and also the fix for the
    "quicklook disappears at 1600px" observation from the group's
    verification report (at that width the terminal has no `percpu` block
    competing for the row at all, because the WebUI, unlike the TUI, was
    rendering both).
    """
    payload = _run_render_probe("cpu-percpu-off")
    top = payload["slots"].get("top", [])
    assert "cpu" in top, f"got {top!r}"
    assert "percpu" not in top, f"got {top!r}"


# -------------------------------------------------- quicklook (G9-8 Task 5)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_quicklook_renders_one_bar_per_stats_list_entry_in_order():
    """`[quicklook] list` drives the selection AND the order
    (quicklook/render_curses_v5.py:161-175). The fixture asks for cpu, mem,
    load — `swap` is in the payload and must NOT render.
    """
    payload = _run_render_probe("quicklook")
    labels = payload["barLabels"]["quicklook"]
    assert labels == ["CPU", "MEM", "LOAD"], f"got {labels!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_bars_width_is_its_percentage_and_its_colour_is_its_tier():
    """D1: the fill's width IS the value, and the tier reaches it as a class
    (the CSS turns that into `background: currentColor`). A bar drawn at a
    fixed width, or coloured from the aggregate instead of its own field,
    would pass a text-only assertion.
    """
    payload = _run_render_probe("quicklook")
    bars = payload["bars"]["quicklook"]
    assert bars[0]["width"] == "45%", f"got {bars[0]!r}"
    assert "gl-level-careful" in bars[0]["fillClass"], f"got {bars[0]!r}"
    assert "gl-level-warning" in bars[1]["fillClass"], f"mem is warning: {bars[1]!r}"
    assert bars[0]["role"] == "progressbar" and bars[0]["valuenow"] == "45", (
        f"a bar is a progress indicator for assistive tech: {bars[0]!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_no_quicklook_bar_is_prominent_with_the_real_fixture():
    """The real schema (quicklook/model_v5.py) ships `prominent: false` on
    every bar-selectable field (G9-8 smoke fix 2: the filled badge was
    rejected after a smoke test), and `QUICKLOOK_FIXTURE._levels` mirrors
    that -- no bar value should carry the badge class.
    """
    payload = _run_render_probe("quicklook")
    for bar in payload["bars"]["quicklook"]:
        assert "gl-prominent" not in bar["valueClass"], f"got {bar!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_prominent_bar_value_still_renders_its_badge():
    """`levelClass()` must still honour a `prominent: true` `_levels` entry
    when given one -- the schema is the single source of truth, not a
    hard-coded False in the component (G9-8 smoke fix 2). `cpu` is prominent
    in the `quicklook-prominent` fixture only."""
    payload = _run_render_probe("quicklook-prominent")
    assert "gl-prominent" in payload["bars"]["quicklook"][0]["valueClass"], f"got {payload['bars']['quicklook'][0]!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_quicklook_renders_its_cpu_name_and_frequency_header():
    text = _run_render_probe("quicklook")["pluginText"]["quicklook"]
    assert "Intel Core i7-9750H" in text, f"got {text!r}"
    assert "2.60/4.50GHz" in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_quicklook_header_is_not_a_paragraph():
    """The CPU name/frequency header is quicklook's only NORMAL-state content
    rendered outside a scalar `.gl-stat-grid` -- every other component's `<p>`
    is a transient loading/error state, so `css/v5.css` never zeroes a `<p>`
    margin. A `<p class="gl-inline">` here keeps the browser's default
    `margin: 1em 0` and pushes the whole block one line down (G9-8 smoke fix
    1); the header must be a plain `<div>` (or another margin-less tag)
    instead.
    """
    tags = _run_render_probe("quicklook")["pluginInlineTags"]["quicklook"]
    assert "P" not in tags, f"got {tags!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_quicklook_without_a_current_frequency_has_no_header():
    """`cur is None -> return None` (render_curses_v5.py:115-117): no header
    row at all, not an empty one."""
    text = _run_render_probe("quicklook-no-freq")["pluginText"]["quicklook"]
    assert "GHz" not in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_quicklook_per_core_replaces_the_cpu_bar_and_caps_with_a_mean_row():
    """With the server's --percpu, the `cpu` bar is REPLACED by one bar per
    core (render_curses_v5.py:168-170), capped by max_cpu_display (2 here),
    sorted by total descending, plus the CPU* row whose value comes from
    `percpu_other` — not from the displayed cores.
    """
    payload = _run_render_probe("quicklook-percpu")
    labels = payload["barLabels"]["quicklook"]
    assert labels == ["CPU0", "CPU1", "CPU*", "MEM", "LOAD"], f"got {labels!r}"
    bars = {b["label"]: b for b in payload["bars"]["quicklook"]}
    assert bars["CPU0"]["width"] == "90%", f"got {bars['CPU0']!r}"
    assert "gl-level-critical" in bars["CPU0"]["fillClass"], (
        f"each core takes ITS OWN level, not the aggregate: {bars['CPU0']!r}"
    )
    assert bars["CPU*"]["width"] == "15%", f"the mean of the HIDDEN cores: {bars['CPU*']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_quicklook_renames_the_two_gpu_bar_labels():
    """`gpu_mem` -> GMEM and `gpu_proc` -> GPU (_BAR_LABEL): the raw upper-cased
    keys are 7 chars and break the TUI's grid, so both surfaces use the short
    form."""
    labels = _run_render_probe("quicklook-gpu")["barLabels"]["quicklook"]
    assert labels == ["CPU", "MEM", "GMEM", "GPU"], f"got {labels!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_quicklook_payload_is_hidden():
    payload = _run_render_probe("quicklook-empty")
    assert payload["pluginHidden"].get("quicklook") is True, f"got {payload['pluginHidden']!r}"


# ------------------------------------------- full_quicklook (G9-8 Task 6)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_full_quicklook_hides_the_tui_s_six_blocks_and_spares_load():
    """--full-quicklook hides cpu/npu/mpp/gpu/mem/memswap and deliberately NOT
    load or percpu (curses_renderer_v5.py:89, exact v4 parity). The WebUI reads
    the flag from /api/5/args, the way mem reads --byte.

    All six hidden plugins and both spared ones are covered here (final
    review, Minor 2 -- the original test only checked four of the six hidden
    plugins and neither spared one). The `cpu-percpu-on` scenario's fixtures
    set `--percpu` too, so `percpu` is not ALSO hidden by the unrelated
    cpu/percpu exclusivity rule (Critical 1) -- this test observes only what
    full_quicklook itself hides.
    """
    payload = _run_render_probe("quicklook-full")
    rendered = set(payload["pluginNames"])
    for name in ("cpu", "npu", "mpp", "gpu", "mem", "memswap"):
        assert name not in rendered, f"{name} must be hidden: {sorted(rendered)!r}"
    assert "load" in rendered, f"load is spared: {sorted(rendered)!r}"
    assert "percpu" in rendered, f"percpu is spared: {sorted(rendered)!r}"
    assert "quicklook" in rendered, f"vacuous: {sorted(rendered)!r}"
