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
import re
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

    G9-9B moved the alert list out of the footer into PluginAlert.vue (fed by
    /api/5/alert/incidents); see test_the_alert_grid_renders_the_tui_columns
    and its siblings for that coverage now.
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
    # G9-9B: the raw alert list moved out of the footer entirely, into
    # PluginAlert.vue (fed by /api/5/alert/incidents, itself the collapsed
    # incident grid -- not the raw transition log this test used to pin).
    # The footer now carries only the refresh cadence
    # (test_the_refresh_cadence_renders_in_the_footer); assert the old
    # per-event markers are gone rather than restating that coverage here.
    footer_text = payload["footerText"] or ""
    assert "plugin11" not in footer_text, f"expected the alert list gone from the footer, got {footer_text!r}"


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
        "vms",
        "containers",
        "processcount",
        "amps",
        "processlist",
        "alert",
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
        "vms",
        "containers",
        "processcount",
        "amps",
        "processlist",
        "alert",
    ], f"expected the whole registry, got {payload['pluginNames']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_refresh_cadence_renders_in_the_footer():
    """G9-5 decision D5: the top bar is gone and the cadence moved to the
    footer. The probe answers /api/5/config with `{}`, so the cadence is
    api.js' DEFAULT_REFRESH_SECONDS (2), and it is now flanked by the two
    stepper buttons that change it.
    """
    payload = _run_render_probe("default")
    assert "2s" in (payload["footerText"] or ""), f"got {payload['footerText']!r}"
    assert "Refresh:" in (payload["footerText"] or ""), f"got {payload['footerText']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_cadence_is_flanked_by_two_stepper_buttons():
    """The whole point of the footer's cadence control: a viewer can change
    the poll rate without editing glances.conf. Two real <button>s, not
    decorative spans -- a span carries no click target and no keyboard focus.
    """
    buttons = _run_render_probe("default")["footerButtons"]
    assert [b["text"] for b in buttons] == ["\u2212", "+"], f"got {buttons!r}"
    # The default cadence (2 s) sits inside the ladder, so neither end is
    # reached and both buttons are live.
    assert [b["disabled"] for b in buttons] == [False, False], f"got {buttons!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_footer_names_the_release_and_links_github_and_the_api_docs():
    """The left end of the footer is the server's identity: the release the
    probe's /status answers with, then the project and the Swagger UI.
    """
    payload = _run_render_probe("default")
    assert "Glances v5.0.0" in (payload["footerText"] or ""), f"got {payload['footerText']!r}"
    assert payload["footerLinks"] == [
        {"text": "GitHub", "href": "https://github.com/nicolargo/glances"},
        {"text": "API", "href": "/docs"},
    ], f"got {payload['footerLinks']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_api_docs_link_is_dropped_when_the_server_mounts_no_docs():
    """`[outputs] api_doc=false` makes webserver_v5.build_app() pass
    `docs_url=None`, so /docs 404s. The footer reads the same key and offers
    no link rather than a dead one. The `api-doc-off` scenario answers
    /api/5/config with the string form a glances.conf value arrives as.
    """
    payload = _run_render_probe("api-doc-off")
    assert [link["text"] for link in payload["footerLinks"]] == ["GitHub"], f"got {payload['footerLinks']!r}"


# --------------------------------------------------------- mem TUI parity (G9-3 Task 5)


def _run_render_probe(scenario: str, keys: str = "") -> dict:
    if not _BUNDLE_PATH.exists():
        pytest.fail(f"{_BUNDLE_PATH} is missing -- run `npm run build` in glances/outputs/static/")

    result = subprocess.run(
        ["node", str(_RENDER_PROBE_PATH), str(_BUNDLE_PATH), scenario, keys],
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

    `rowBudget` (Task 4, the vertical row budget) is checked here too, but
    for a DIFFERENT reason than the two props above: it travels by
    `provide`/`inject` (AppShell's `provide()`, fix round 1), not by a prop
    on this shared binding, and no plugin declares it -- so today there is no
    code path that could produce a `row-budget` attribute at all, and this
    assertion is currently vacuous against the CURRENT source. It is kept as
    a regression guard against a FUTURE change: if `rowBudget` is ever bound
    back onto the shared `<component>` (the leak fix round 1 corrected), this
    is what would catch it reappearing on the 26+ plugins that do not consume
    it, without anyone having to remember why it must not be a prop.
    """
    payload = _run_render_probe("mem-with-available")
    # Without this the loop below is vacuous: an empty `pluginAttrs` (a probe
    # that stopped collecting the attribute, a render that produced no
    # article) would pass silently. Thirty, not the registry's
    # thirty-one: `cpu`/`percpu` are mutually exclusive (final review,
    # Critical 1) -- this scenario's `percpu: true` (ARGS_FIXTURES) selects
    # `percpu` over `cpu` so the loop below still covers percpu's
    # `serverPlugins` inject specifically (G9-8 Task 4 review).
    assert len(payload["pluginAttrs"]) == 30, (
        f"expected all thirty rendered plugins' attributes, got {payload['pluginAttrs']!r}"
    )
    for name, attrs in payload["pluginAttrs"].items():
        assert "server-args" not in attrs, f"{name} leaked serverArgs as an attribute: {attrs!r}"
        assert "degrade" not in attrs, f"{name} leaked degrade as an attribute: {attrs!r}"
        # Regression guard, not a check on current behaviour (see docstring):
        # `rowBudget` is provide/inject, not a prop, so nothing today could
        # leak it -- this only protects against someone reintroducing the
        # `:row-budget` binding on the shared <component> later.
        assert "row-budget" not in attrs, f"{name} leaked rowBudget as an attribute: {attrs!r}"
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


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_probe_models_vertical_geometry():
    """The vertical budget reads viewport height, the right slot's top edge and
    one row's height. The probe has no layout engine, so it models all three --
    the same harness-hook pattern `_notches` already uses for scrollWidth.
    """
    payload = _run_render_probe("budget-tall")
    geometry = payload["geometry"]
    assert geometry["viewport"] > 0
    assert geometry["rowPx"] > 0
    assert geometry["slotTop"] >= 0


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
def test_full_quicklook_hides_every_top_block_but_quicklook():
    """--full-quicklook hides EVERY TOP sibling, `load` and `percpu` included
    (curses_renderer_v5.py:91). The WebUI reads the flag from /api/5/args, the
    way mem reads --byte, and mirrors the constant in full_quicklook.js --
    tests/test_webui_v5_full_quicklook_drift.py fails on drift between the two.

    Was "…and spares load": until 2026-09-22 this matched v4's six-plugin set
    exactly, leaving `load` and `percpu` on the row. The maintainer widened the
    mode (`…decisions.md` §10, "Reversed decision -- full quicklook"), so the
    two spared blocks are now hidden like the rest.
    """
    payload = _run_render_probe("quicklook-full")
    rendered = set(payload["pluginNames"])
    for name in ("cpu", "percpu", "npu", "mpp", "gpu", "mem", "memswap", "load"):
        assert name not in rendered, f"{name} must be hidden: {sorted(rendered)!r}"
    assert "quicklook" in rendered, f"vacuous: {sorted(rendered)!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
@pytest.mark.parametrize(
    ("scenario", "name", "labels"),
    [
        ("memswap-unavailable", "memswap", ("SWAP", "total", "sin", "sout")),
        ("load-unavailable", "load", ("LOAD", "1 min", "5 min", "15 min")),
    ],
)
def test_a_scalar_published_without_stats_renders_dashes_not_a_shape_error(scenario, name, labels):
    """memswap/load publish only their metadata when the grab fails (no swap
    on OpenBSD/Illumos, getloadavg() OSError). The TUI shows dashes; the WebUI
    showed a permanent red "unexpected shape: missing total/min1"."""
    payload = _run_render_probe(scenario)
    text = payload["pluginText"].get(name, "")
    assert "unexpected shape" not in text, text
    for label in labels:
        assert label in text, f"expected {label!r} in {text!r}"
    assert "-" in text, text


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_percpu_keeps_title_total_and_labels_when_the_cascade_hides_quicklook():
    """Twin of the TUI fix in curses_renderer_v5.build_frame: a quicklook the
    width cascade removed (`hide_quicklook`) is not on screen, so percpu must
    not drop the per-core totals it would otherwise repeat."""
    payload = _run_render_probe("percpu-quicklook-cascaded-out")
    assert payload["degrade"]["top"].get("hide_quicklook") is True, f"guard: {payload['degrade']!r}"
    assert "quicklook" not in payload["pluginNames"], f"got {payload['pluginNames']!r}"
    headers = payload["pluginColumnHeaders"]["percpu"]
    assert "CPU" in headers and "total" in headers, f"got {headers!r}"
    assert payload["pluginNameCells"].get("percpu"), "row labels must survive"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cpu_shows_dpc_in_place_of_iowait_on_a_windows_payload():
    """Twin of test_render_windows_payload_shows_dpc_in_place_of_iowait (TUI)."""
    text = _run_render_probe("cpu-windows")["pluginText"].get("cpu", "")
    assert "user" in text, text
    assert "dpc" in text, f"dpc takes the iowait row: {text!r}"
    assert "iowait" not in text, text


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_footer_no_longer_renders_a_raw_alert_list():
    """G9-9B: the footer's raw event list (this test used to pin a resolution
    event reading as "fs /home percent — ok" rather than an alert) moved into
    PluginAlert.vue, fed by the already-collapsed /api/5/alert/incidents --
    the footer keeps only the refresh cadence. The resolved-vs-ongoing
    distinction this test guarded is now
    test_only_an_ongoing_incident_colours_its_level's job."""
    payload = _run_render_probe("alert-resolved")
    assert payload["footerAlerts"] == [], f"expected no <li> in the footer, got {payload['footerAlerts']!r}"


# ------------------------------------------------- processcount TUI parity (G9-9A Task 1)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_processcount_renders_the_tui_tasks_line():
    """processcount/render_curses_v5.py:73-113 paints ONE line:
    `TASKS 215 (1452 thr), 3 run, 195 slp, 17 oth`. `oth` is computed
    (total - running - sleeping), so 17 proves the arithmetic and not a
    field read.
    """
    payload = _run_render_probe("processcount")
    text = " ".join((payload["pluginText"].get("processcount") or "").split())
    assert text == "TASKS 215 (1452 thr), 3 run, 195 slp, 17 oth", f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_processcount_drops_the_thread_group_when_psutil_has_no_count():
    """`thread` is None on some systems (issue #1463): the TUI emits
    `TASKS 215, 3 run, …` -- the comma moves onto the total."""
    payload = _run_render_probe("processcount-no-thread")
    text = " ".join((payload["pluginText"].get("processcount") or "").split())
    assert text == "TASKS 215, 3 run, 195 slp, 17 oth", f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_processcount_shows_only_its_title_before_the_first_aggregate():
    """No `total` yet (scheduler cycle 0) -> the title alone. A component
    that defaulted the aggregates to 0 would render `TASKS 0, 0 run…`,
    which the TUI explicitly avoids."""
    payload = _run_render_probe("processcount-empty")
    text = " ".join((payload["pluginText"].get("processcount") or "").split())
    assert text == "TASKS", f"got {text!r}"


# ------------------------- processcount TASKS counter + sort indicator (G9-9B Task 8)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_processcount_shows_the_truncation_counter_when_the_cap_cuts_the_list():
    """`_count_text` (processcount/render_curses_v5.py:37-55), browser
    equivalent: `[outputs] max_processes_display=30` (CONFIG_FIXTURES) is
    below PROCESSCOUNT_FIXTURE's total (215), so the cap actually cuts the
    list and the TASKS line must show `30/215`, not the bare total."""
    payload = _run_render_probe("processcount-cut")
    text = " ".join((payload["pluginText"].get("processcount") or "").split())
    assert text == "TASKS 30/215 (1452 thr), 3 run, 195 slp, 17 oth", f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_processcount_shows_the_bare_total_when_the_cap_does_not_cut_the_list():
    """No CONFIG_FIXTURES entry for "processcount" -> no cap -> "215" alone,
    exactly test_processcount_renders_the_tui_tasks_line's existing
    assertion -- this test names the "not cut" half explicitly."""
    payload = _run_render_probe("processcount")
    text = " ".join((payload["pluginText"].get("processcount") or "").split())
    assert "30/215" not in text, f"got {text!r}"
    assert "215" in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_processcount_omits_the_counter_in_the_programs_view_even_when_cut():
    """`_count_text`'s own guard: never applied in the programs view, because
    `total` counts PROCESSES while the list below shows PROGRAMS -- the
    ratio would compare two different things. Same cap (30) as the cut
    scenario above, only `serverArgs.programs` differs."""
    payload = _run_render_probe("processcount-cut-programs")
    text = " ".join((payload["pluginText"].get("processcount") or "").split())
    assert "30/215" not in text, f"got {text!r}"
    assert "215" in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_processcount_sort_indicator_reads_threads_in_the_default_view():
    """`_sort_indicator_cell` (processcount/render_curses_v5.py:58-70):
    `serverArgs.sort_processes_key` is the only half of its input the
    browser can honestly read (see PluginProcesscount.vue's
    `sortIndicatorText` comment for why `auto_sort` is not reproduced) --
    when a key WAS passed on the CLI, main_v5.py:423-424 always applies it
    with `auto=False`, so "sorted by X", never "automatically", is always
    correct in that case."""
    payload = _run_render_probe("processcount-sorted-threads")
    text = " ".join((payload["pluginText"].get("processcount") or "").split())
    assert "Threads sorted by CPU consumption" in text, f"got {text!r}"
    assert "automatically" not in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_processcount_sort_indicator_reads_programs_in_the_programs_view():
    """Same indicator, `serverArgs.programs` true: the prefix switches from
    `Threads` to `Programs` (processcount/render_curses_v5.py:64), and the
    sort key's human label follows `sort_for_human` (glances/processes.py)
    -- `memory_percent` -> "memory consumption"."""
    payload = _run_render_probe("processcount-sorted-programs")
    text = " ".join((payload["pluginText"].get("processcount") or "").split())
    assert "Programs sorted by memory consumption" in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_processcount_shows_no_sort_indicator_without_a_sort_key():
    """No `sort_processes_key` in ARGS_FIXTURES for "processcount" -- absent
    means `{}` -- so the engine's sort key is unknown to the browser (it may
    be auto-sorting) and the indicator must be entirely absent, matching the
    TUI's own "no view supplied" branch (render_curses_v5.py:61-62)."""
    payload = _run_render_probe("processcount")
    text = " ".join((payload["pluginText"].get("processcount") or "").split())
    assert "sorted" not in text, f"got {text!r}"


# ------------------------------------------------------- amps TUI parity (G9-9A Task 2)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_amps_renders_name_count_and_result_without_a_header_row():
    """amps/render_curses_v5.py has NO title row and NO column header
    (module docstring, v4 parity), like `ports` in G9-7 -- so the block
    renders no <thead> at all.
    """
    payload = _run_render_probe("amps")
    rows = _table_rows(payload, "amps", 3)
    assert rows == [
        ["Python", "2", "CPU: 1.0% | MEM: 2.0%"],
        ["Systemd", "1", "Services\nactive: 3"],
        ["Kernel", "", "up"],
    ], f"got {rows!r}"
    assert not payload["pluginHeaderCells"].get("amps"), (
        f"amps must render no header row, got {payload['pluginHeaderCells'].get('amps')!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_amps_skips_an_amp_that_has_produced_nothing():
    """`result is None` -> v4 renders no row at all
    (amps/render_curses_v5.py:70-73). `Dropped` must be absent, and its
    count (4) must not appear anywhere in the block.
    """
    payload = _run_render_probe("amps")
    text = payload["pluginText"].get("amps") or ""
    assert "Dropped" not in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_amps_badges_the_count_tier_on_the_name():
    """The TUI colours the NAME cell from `_levels[name].count`
    (amps/render_curses_v5.py:78-79), not the count cell. Same convention as
    test_a_table_value_carries_its_tier_on_the_text_not_the_cell (the tier
    goes on the value span, never the <td>), but not folded into that
    parametrization: unlike every case there, amps' badged column (NAME) is
    text, not numeric, so its <td> carries no `gl-num` layout class to
    assert on.
    """
    payload = _run_render_probe("amps")
    cell = payload["pluginTableCells"]["amps"][0]  # Python's name cell
    assert _tier_classes(cell["value"]) == {"gl-level-warning", "gl-prominent"}, f"got {cell!r}"
    assert _tier_classes(cell["cell"]) == set(), f"the <td> itself carries no tier class: {cell!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_amps_collection_is_hidden():
    """The TUI returns [] for an empty collection, so the block is not
    painted -- the G9-7 rule for ports/folders/irq/raid/smart."""
    payload = _run_render_probe("amps-empty")
    assert payload["pluginHidden"].get("amps") is True, f"got {payload['pluginHidden']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_amps_height_the_solver_sees_excludes_the_phantom_header_and_null_results():
    """AppShell.vue's `ampsHeight()` used to read `1 + rows.reduce(...)` over
    the RAW payload -- a phantom header row amps/render_curses_v5.py never
    paints (module docstring: "NO TITLE ROW and no column header"), plus one
    phantom row per AMP whose `result` is still `None`, which
    amps/render_curses_v5.py:67-71 skips entirely rather than rendering
    empty. AMPS_FIXTURE (scenario "amps") has one such null-result item
    (`Dropped`) and one two-line item (`Systemd`): its correct height is 4
    (Python 1 + Systemd 2 + Kernel 1), not the old buggy 6 (1 header +
    Python 1 + Systemd 2 + Dropped 1 + Kernel 1) -- a difference this test
    cannot observe directly (the solver's `ampsHeight` never reaches the
    DOM), so it reads it off `rowBudget.processlist` instead: at this
    scenario's bodyHeight (24 rows) the solver's growth branch gives
    processlist 14 rows with the correct height and 12 with the buggy one,
    confirmed by calling row_budget.js's `planRightColumn()` directly rather
    than predicted (see task-11-report.md).
    """
    payload = _run_render_probe("budget-amps-height-defect")
    assert "amps" not in payload["rowBudget"], f"the growth branch never sets an amps quota: {payload['rowBudget']!r}"
    assert payload["rowBudget"]["processlist"] == 14, f"got {payload['rowBudget']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_truncated_amps_block_keeps_a_marker_line():
    """Ladder step j truncates amps to what is left and keeps at least the
    `+N lines` marker (amps/render_curses_v5.py:98-105: "The marker consumes
    the last budgeted line, so `budget` rows are emitted in total."). The
    browser renders a multi-line result in ONE `pre-line` cell (G9-9A spec
    D6), so PluginAmps.vue clamps LINES within a cell rather than dropping
    whole rows -- "budget-amps-truncated" gives the solver a natural amps
    height of 10 (five two-line AMPS) and a bodyHeight of 8, which
    `planRightColumn()` truncates to `rowBudget.amps == 4` (confirmed by
    calling it directly, not predicted): 3 content lines plus the marker.
    """
    payload = _run_render_probe("budget-amps-truncated")
    assert payload["rowBudget"]["amps"] == 4, f"got {payload['rowBudget']!r}"
    rows = payload["pluginRowGroups"]["amps"][0]
    text = rows[-1][-1]
    assert text.rstrip().endswith("lines"), f"got {text!r}"
    assert text.strip() == "… +7 lines", f"got {text!r}"


# -------------------------------------------------------- vms TUI parity (G9-9A Task 3)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_vms_renders_the_tui_columns_and_rows():
    """vms/render_curses_v5.py:83-155. Engine shown (two engines), LOAD
    shown (load_1min present), MEM and MAX in ONE cell, a missing value as
    `-` (spec divergence 5, `format.js` MISSING) -- never `_`.
    """
    payload = _run_render_probe("vms")
    assert payload["pluginHeaderCells"].get("vms") == [
        "Engine",
        "Name",
        "Status",
        "Core",
        "CPU%",
        "MEM/MAX",
        "LOAD 1/5/15min",
        "Release",
    ], f"got {payload['pluginHeaderCells'].get('vms')!r}"
    rows = _table_rows(payload, "vms", 8)
    assert rows == [
        ["virsh", "builder", "running", "4", "12.5%", "2.00G/4.00G", "0.5/0.7/1.2", "24.04"],
        ["multipass", "sandbox", "stopped", "2", "-", "-/-", "0.0/0.0/0.0", "-"],
    ], f"got {rows!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_vms_hides_engine_and_load_when_the_data_makes_them_irrelevant():
    """One distinct engine -> no Engine column
    (vms/render_curses_v5.py:157). No `load_1min` -> no LOAD column
    (:162). Both are data-driven, never width-driven.
    """
    payload = _run_render_probe("vms-one-engine")
    assert payload["pluginHeaderCells"].get("vms") == [
        "Name",
        "Status",
        "Core",
        "CPU%",
        "MEM/MAX",
        "Release",
    ], f"got {payload['pluginHeaderCells'].get('vms')!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_vms_colours_cpu_and_memory_from_levels_and_never_the_status():
    """CPU% takes `cpu_time`'s tier, MEM/MAX takes `memory_percent`'s, and
    `status` keeps its own mapping -- the TUI never reads `_levels` for it
    (vms/render_curses_v5.py `_status_role`). Tiers are observable only on
    the value <span> inside each <td> (`pluginValueClasses` holds each
    <td>'s OWN class -- see `_tier_classes` and
    `test_a_table_value_carries_its_tier_on_the_text_not_the_cell`), so this
    reads `pluginTableCells` like the fs/amps tier tests do. Row 0
    (builder): engine=0, name=1, status=2, core=3, cpu%=4, mem/max=5,
    load=6, release=7. `builder`'s `_levels` entry carries no `status`
    field, so a `status` class here can only have come from the component's
    OWN `_STATUS_ROLE` mirror (G9-9A fix wave item 1), never from `_levels`.
    """
    payload = _run_render_probe("vms")
    cells = payload["pluginTableCells"]["vms"]
    assert _tier_classes(cells[4]["value"]) == {"gl-level-careful"}, cells[4]
    assert _tier_classes(cells[4]["cell"]) == set(), f"the <td> itself carries no tier class: {cells[4]!r}"
    assert _tier_classes(cells[5]["value"]) == {"gl-level-warning"}, cells[5]
    assert _tier_classes(cells[5]["cell"]) == set(), f"the <td> itself carries no tier class: {cells[5]!r}"
    # "running" -> "ok" in vms's OWN status map, not from `_levels`.
    assert _tier_classes(cells[2]["value"]) == {"gl-level-ok"}, cells[2]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_vms_gives_an_unmapped_status_no_colour():
    """`stopped` is not in vms's `_STATUS_ROLE` mirror (only running/
    starting/restarting/delayed shutdown are), so row 1 (sandbox, cells[10])
    must render with no tier class -- the TUI's `ColorRole.DEFAULT` paints
    nothing for an unclassified status, and the WebUI must match."""
    payload = _run_render_probe("vms")
    cells = payload["pluginTableCells"]["vms"]
    assert _tier_classes(cells[10]["value"]) == set(), cells[10]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_vms_collection_is_hidden():
    """`CollectionBlock` hides an empty collection with `v-show`, not
    `v-if`, so the <article> stays in the DOM and stays listed in
    `slots["right"]` -- `payload["slots"]` cannot observe this (the G9-7
    convention, see `test_an_empty_folders_collection_is_hidden`)."""
    payload = _run_render_probe("vms-empty")
    assert payload["pluginHidden"].get("vms") is True, f"got {payload['pluginHidden']!r}"


# ------------------------------------------------- containers TUI parity (G9-9A Task 4)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_containers_renders_the_tui_columns_and_rows():
    """containers/render_curses_v5.py:124-215. `CONTAINER` IS the title (no
    separate title row, G9-6 D6). Engine and Pod are shown because the data
    makes them relevant (:264-265); /MAX is unconditional (:298 reads only
    `hidden`, never `memory_limit` -- see
    `test_containers_shows_max_even_when_no_container_has_a_limit`). Rates
    follow `network`'s bit default: 100 B/s -> "800b".
    """
    payload = _run_render_probe("containers")
    assert payload["pluginHeaderCells"].get("containers") == [
        "Engine",
        "Pod",
        "CONTAINER",
        "Status",
        "Uptime",
        "CPU%",
        "MEM",
        "/MAX",
        "IOR/s",
        "IOW/s",
        "Rx/s",
        "Tx/s",
        "Ports",
        "Command",
    ], f"got {payload['pluginHeaderCells'].get('containers')!r}"
    rows = _table_rows(payload, "containers", 14)
    assert rows[0] == [
        "docker",
        "pod-7f3a",
        "web",
        "running",
        "2 days",
        "12.5%",
        "512M",
        "/2.00G",
        "1024B",
        "2KB",
        "800b",
        "1.6Kb",
        "0.0.0.0:80->80/tcp",
        "nginx -g daemon off;",
    ], f"got {rows[0]!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_containers_colours_status_from_its_own_map():
    """G9-9A fix wave item 1: `status` was rendered as plain text with no
    class, silently dropping a signal both the TUI (`_STATUS_ROLE`) and the
    old v4 WebUI (`getStatusClass`) carry. Row 0 (web) is "running" -> "ok",
    row 1 (db) is "paused" -> "careful"; header order gives `status` index 3
    of 14 (Engine=0, Pod=1, CONTAINER=2, Status=3), so row 1 is cells[17].
    Neither status has a `_levels` entry for `status`, so a class here can
    only come from the component's own map, never `_levels`.
    """
    payload = _run_render_probe("containers")
    cells = payload["pluginTableCells"]["containers"]
    assert _tier_classes(cells[3]["value"]) == {"gl-level-ok"}, cells[3]
    assert _tier_classes(cells[3]["cell"]) == set(), f"the <td> itself carries no tier class: {cells[3]!r}"
    assert _tier_classes(cells[17]["value"]) == {"gl-level-careful"}, cells[17]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_containers_gives_an_unmapped_status_no_colour():
    """`removing` is not in containers's `_STATUS_ROLE` mirror -- the TUI's
    `ColorRole.DEFAULT` paints nothing for an unclassified status, and the
    WebUI must match."""
    payload = _run_render_probe("containers-unmapped-status")
    cells = payload["pluginTableCells"]["containers"]
    assert _tier_classes(cells[3]["value"]) == set(), cells[3]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_containers_shows_the_placeholder_for_every_missing_value():
    """Spec divergence 5: the WebUI's single placeholder is `-`
    (`format.js` MISSING), not the `_` this TUI renderer prints. The `db`
    row has no rate, no uptime and no command yet.
    """
    payload = _run_render_probe("containers")
    row = _table_rows(payload, "containers", 14)[1]
    assert "_" not in " ".join(row), f"got {row!r}"
    assert row[4] == "-", f"uptime must be the placeholder, got {row!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_containers_honours_disable_stats_from_the_config():
    """`[containers] disable_stats` reaches the browser as payload metadata
    (containers/model_v5.py:220-221) and removes columns regardless of
    width (spec §5.1)."""
    payload = _run_render_probe("containers-disable-stats")
    headers = payload["pluginHeaderCells"].get("containers") or []
    assert "Ports" not in headers, f"got {headers!r}"
    assert "Command" not in headers, f"got {headers!r}"
    assert "CPU%" in headers, f"vacuous: the rest must survive: {headers!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_containers_disabling_mem_also_hides_the_max_column():
    """containers/render_curses_v5.py:286-288: `disable_stats=mem` cascades
    into `memory_max` too -- `/MAX` is meaningless without `MEM` next to it.
    Config-driven, not the width cascade (out of scope for this task)."""
    payload = _run_render_probe("containers-disable-mem")
    headers = payload["pluginHeaderCells"].get("containers") or []
    assert "MEM" not in headers, f"got {headers!r}"
    assert "/MAX" not in headers, f"got {headers!r}"
    assert "CPU%" in headers, f"vacuous: the rest must survive: {headers!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_containers_shows_max_even_when_no_container_has_a_limit():
    """render_curses_v5.py `show_mem_max` (:298) reads only `hidden` -- the
    config's `disable_stats`, the `mem` cascade (:287-288) and the width
    cascade (:295, out of scope here). Nothing reads `memory_limit` to gate
    the COLUMN; the data only decides what the cell PRINTS (`_cpu_mem_cells`:
    "/" + the limit, or the placeholder when absent). So a host where no
    container declares a limit still shows `/MAX`, with `-` in every row.
    """
    payload = _run_render_probe("containers-no-limits")
    headers = payload["pluginHeaderCells"].get("containers") or []
    assert "/MAX" in headers, f"got {headers!r}"
    rows = _table_rows(payload, "containers", len(headers))
    max_index = headers.index("/MAX")
    # The cell is "/" + formatAutoUnit(limit); a missing limit renders
    # formatAutoUnit's own placeholder ("-"), so the cell reads "/-", not
    # a bare "-" -- the "/" prefix is unconditional (PluginContainers.vue).
    for row in rows:
        assert row[max_index] == "/-", f"got {row!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_containers_collection_is_hidden():
    """`CollectionBlock` hides an empty collection with `v-show`, not
    `v-if`, so the <article> stays in the DOM and stays listed in
    `slots["right"]` -- `payload["slots"]` cannot observe this (the G9-7
    convention, see `test_an_empty_folders_collection_is_hidden`)."""
    payload = _run_render_probe("containers-empty")
    assert payload["pluginHidden"].get("containers") is True, f"got {payload['pluginHidden']!r}"


# ------------------------------------- containers column cascade (G9-9A Task 6)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_wide_containers_block_keeps_every_column():
    """The cascade starts from NO flag on every pass (degrade.js
    `resolveDegrade`), so a block that fits drops nothing -- this is also
    what gives the columns back when the window widens."""
    payload = _run_render_probe("containers-wide")
    headers = payload["pluginHeaderCells"].get("containers") or []
    assert "Command" in headers, f"got {headers!r}"
    assert "Status" in headers, f"got {headers!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_one_notch_drops_the_command_column_first():
    """`_DROP_ORDER`'s first entry (containers/render_curses_v5.py:60):
    `command` goes before anything else -- the deliberate divergence from
    processlist, where Command is the protected tail."""
    payload = _run_render_probe("containers-one-notch")
    headers = payload["pluginHeaderCells"].get("containers") or []
    assert "Command" not in headers, f"got {headers!r}"
    assert "Ports" in headers, f"only ONE notch was budgeted: {headers!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_narrow_containers_block_keeps_only_the_undroppable_columns():
    """The cascade run to its last step: `name`, `cpu` and `mem` are absent
    from `_DROP_ORDER`, so CONTAINER / CPU% / MEM always survive."""
    payload = _run_render_probe("containers-narrow")
    assert payload["pluginHeaderCells"].get("containers") == [
        "CONTAINER",
        "CPU%",
        "MEM",
    ], f"got {payload['pluginHeaderCells'].get('containers')!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_unmeasurable_containers_block_keeps_every_column():
    """The `containers` scenario sets no block width, so clientWidth is 0 --
    `fits()` reads that as "cannot measure" and must never degrade on it
    (degrade.js). A hidden tab must not lose the user's columns."""
    payload = _run_render_probe("containers")
    headers = payload["pluginHeaderCells"].get("containers") or []
    assert "Command" in headers, f"got {headers!r}"


# -------------------------------- containers elastic tail column (maintainer)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_container_table_declares_the_terminal_column_widths():
    """The block used to paint an automatic-layout table whose `command` and
    `ports` spans were capped at 24 characters, so the tail column stayed 24
    characters wide however much room the window had -- the maintainer asked
    for the processlist treatment instead: a <colgroup> in the terminal's own
    character widths (`_COL_GEOMETRY`) and an elastic last column.

    The expectation is re-extracted from process_widths.js by regex, never by
    importing or calling the component's own colStyle(), for the same reason
    test_the_column_box_reserves_one_character_for_the_separator_inside_it
    gives: a copy of the code under test proves nothing. `+ COL_SEPARATOR` per
    <col> because under `table-layout: fixed` the <col> is the column's WHOLE
    box and the separator's `padding-right` comes out of it.
    """
    widths_path = _BUNDLE_PATH.parent.parent / "js" / "v5" / "process_widths.js"
    source = widths_path.read_text()
    widths_match = re.search(r"export const WEBUI_CONTAINER_COL_WIDTHS\s*=\s*\{(.*?)\};", source, re.S)
    assert widths_match, f"WEBUI_CONTAINER_COL_WIDTHS is not exported from {widths_path}"
    widths = {k: int(v) for k, v in re.findall(r'"([^"]+)"\s*:\s*(\d+)', widths_match.group(1))}
    separator_match = re.search(r"export const COL_SEPARATOR\s*=\s*(\d+)\s*;", source)
    assert separator_match, f"COL_SEPARATOR is not exported from {widths_path}"
    separator = int(separator_match.group(1))

    # The `containers` fixture's longest name is "web", so the name column
    # falls back to the header label's own 9 characters (`CONTAINER`).
    expected = [
        widths["engine"],
        widths["pod"],
        len("CONTAINER"),
        widths["status"],
        widths["uptime"],
        widths["cpu"],
        widths["mem"],
        widths["memory_max"],
        # One key, two painted cells: the pair splits its width evenly.
        widths["diskio"] // 2,
        widths["diskio"] // 2,
        widths["networkio"] // 2,
        widths["networkio"] // 2,
        widths["ports"],
        # `command`, the elastic tail, gets no <col> at all.
    ]
    payload = _run_render_probe("containers")
    assert payload["pluginColWidths"]["containers"] == [f"calc({n + separator} * var(--gl-col))" for n in expected], (
        payload["pluginColWidths"]["containers"]
    )
    assert "gl-process-table" in payload["pluginTableClasses"]["containers"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_container_tail_column_is_the_one_left_out_of_the_colgroup():
    """Under `table-layout: fixed` a column past the <colgroup>'s count takes
    the whole remaining width (CSS 2.1 17.5.2.1), so the tail is elastic only
    because the colgroup stops one cell short -- exactly how processlist's
    Command column works. `Command` is that tail here; `Ports` becomes it once
    the cascade's first step drops `Command` (`_DROP_ORDER`), which is why the
    <col> list is one short in BOTH cases rather than pinned to a column name.
    """
    for scenario in ("containers", "containers-one-notch"):
        payload = _run_render_probe(scenario)
        headers = payload["pluginHeaderCells"]["containers"]
        cols = payload["pluginColWidths"]["containers"]
        assert len(cols) == len(headers) - 1, f"{scenario}: {len(cols)} <col> for {len(headers)} columns"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_container_name_column_is_sized_from_the_data():
    """The terminal's `name_w` (containers/render_curses_v5.py:262) is the
    LONGEST name, capped by `[containers] max_name_size` and floored at the
    header label. The WebUI used to spend a flat 20 characters here whatever
    the names were, which is 11 characters the tail column never got back.

    `containers-long-names` publishes a 25-character name against the
    fixture's own `max_name_size: 20`, so this pins both ends: the column
    grows past the label, and stops at the configured cap.
    """
    separator = int(
        re.search(
            r"export const COL_SEPARATOR\s*=\s*(\d+)\s*;",
            (_BUNDLE_PATH.parent.parent / "js" / "v5" / "process_widths.js").read_text(),
        ).group(1)
    )
    short = _run_render_probe("containers")["pluginColWidths"]["containers"][2]
    assert short == f"calc({len('CONTAINER') + separator} * var(--gl-col))", short
    long_names = _run_render_probe("containers-long-names")["pluginColWidths"]["containers"][2]
    assert long_names == f"calc({20 + separator} * var(--gl-col))", long_names


# ------------------------------- right-column alignment retouches (maintainer)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_containers_glues_each_rate_pair_the_way_the_tui_does():
    """containers/render_curses_v5.py:158-162 and :205-209 right-align
    `IOR/s`/`Rx/s` and LEFT-align `IOW/s`/`Tx/s`, header and data cell alike,
    so each pair reads as one group hugging in the middle instead of two
    columns drifting apart. The WebUI marked all four `.gl-num`
    (right-aligned), which split every pair.

    Columns are located by label, not by index: the header set depends on the
    payload (Engine, Pod and /MAX are data- or config-driven), so a hardcoded
    index would break the day a fixture changes.
    """
    payload = _run_render_probe("containers")
    headers = payload["pluginHeaderCells"]["containers"]
    classes = payload["pluginColumnClasses"]["containers"]

    for label in ("IOR/s", "Rx/s"):
        cls = classes[headers.index(label)]
        assert "gl-num" in cls, f"{label} stays numeric: {cls!r}"
        assert "gl-num-left" not in cls, f"{label} keeps the TUI's right alignment: {cls!r}"
    for label in ("IOW/s", "Tx/s"):
        cls = classes[headers.index(label)]
        assert "gl-num" in cls, f"{label} stays numeric: {cls!r}"
        assert "gl-num-left" in cls, f"{label} is left-aligned like the TUI: {cls!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_containers_rate_data_cells_match_their_header_alignment():
    """A header flipped without its data cell would misalign the column it
    labels, so the same rule is asserted on the first row's <td>s. The value
    class list is every <td> in document order, so the first row's cells are
    the first `len(headers)` entries.
    """
    payload = _run_render_probe("containers")
    headers = payload["pluginHeaderCells"]["containers"]
    first_row = payload["pluginValueClasses"]["containers"][: len(headers)]

    assert "gl-num-left" not in first_row[headers.index("IOR/s")], f"got {first_row!r}"
    assert "gl-num-left" in first_row[headers.index("IOW/s")], f"got {first_row!r}"
    assert "gl-num-left" not in first_row[headers.index("Rx/s")], f"got {first_row!r}"
    assert "gl-num-left" in first_row[headers.index("Tx/s")], f"got {first_row!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_amps_count_cell_is_marked_as_its_own_narrow_column():
    """`.gl-num` floors a column at 9ch -- a width sized for a rate cell's
    worst case ("1023.9G/s"). The AMP count is one to four digits
    (amps/render_curses_v5.py `_COUNT_COL_WIDTH` = 4), so it inherited a
    floor it can never use and the column rendered far wider than the TUI's.

    This observes the marker class reaching the DOM; the width itself is CSS,
    which the probe's fake DOM cannot evaluate -- that half is pinned in
    tests/test_webui_v5_tokens.py, the same split the `.gl-command` cap uses.
    """
    payload = _run_render_probe("amps")
    classes = payload["pluginValueClasses"]["amps"]
    # Three columns, three rendered rows: name, count, result.
    count_cells = [classes[i] for i in range(1, len(classes), 3)]

    assert count_cells, f"no amps cells rendered: {classes!r}"
    for cls in count_cells:
        assert "gl-num" in cls, f"the count stays numeric: {cls!r}"
        assert "gl-amp-count" in cls, f"the count carries its own width class: {cls!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_containers_ports_cell_keeps_its_full_value_on_hover():
    """The ports cell is now capped and ellipsized (see
    tests/test_webui_v5_tokens.py), so the full published list must stay
    reachable as a `title`, exactly as the command cell does. A cap without
    a title would DELETE information from the page rather than fold it.
    """
    payload = _run_render_probe("containers")
    titled = payload["pluginTitles"].get("containers") or []
    titles = [c.get("title") for c in titled]
    assert "0.0.0.0:80->80/tcp" in titles, f"the ports cell carries its full value: {titles!r}"


# ------------------------------------------------- alert TUI parity (G9-9B Task 6)


def _alert_title(payload):
    """The alert block's own title line -- its <h2>, NOT the grid's first <th>.

    The title used to be the glyph column's header cell, which pinned the
    whole `ALERTS N ongoing · M resolved` sentence inside a 1-character <col>
    under `table-layout: fixed`; it is a full-width line above the grid now,
    like the terminal's own title row (curses_renderer_v5.py:806-816).
    """
    text = payload["pluginTitleLine"].get("alert")
    assert text is not None, "the alert block renders no title line at all"
    return text


def _alert_rows(payload):
    """The rendered alert grid's <td> cells, grouped by row (6 columns:
    glyph, TIME, DURATION, TARGET, TOP PROCESSES, LEVEL)."""
    cells = payload["pluginTableCells"].get("alert", [])
    return [cells[i : i + 6] for i in range(0, len(cells), 6)]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_alert_grid_renders_the_tui_columns():
    """curses_renderer_v5.py:1004-1062 -- glyph, TIME, DURATION, TARGET, TOP
    PROCESSES, LEVEL, in that order. This scenario carries no block-width
    fixture, so the block is "unmeasurable" (degrade.js's `fits()` reads a
    zero clientWidth as "cannot measure" and never degrades on it) and every
    column survives -- see test_the_alert_grid_drops_top_processes_first and
    its siblings below for the width cascade itself."""
    payload = _run_render_probe("alert")
    header = payload["pluginHeaderCells"]["alert"]
    assert header[1:] == ["TIME", "DURATION", "TARGET", "TOP PROCESSES", "LEVEL"]
    # The glyph column's header is BLANK, like the terminal's
    # (curses_renderer_v5.py:818): the title is a full-width line of its own
    # above the grid, not the first <th>. ALERT_INCIDENTS_FIXTURE has 3
    # ongoing (rows 0, 1, 4) and 2 resolved (rows 2, 3).
    assert header[0] == "", f"got {header[0]!r}"
    assert _alert_title(payload) == "ALERTS  3 ongoing · 2 resolved", f"got {_alert_title(payload)!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_only_an_ongoing_incident_colours_its_level():
    """curses_renderer_v5.py:1056 -- a resolved incident's LEVEL goes neutral
    so colour there means "still happening"; the glyph keeps the level
    colour regardless, so the severity reached stays readable either way.
    Fixture row 0 is ongoing+prominent+critical, row 2 is resolved+warning,
    row 3 is resolved+prominent, row 4 carries an unknown duration.
    """
    payload = _run_render_probe("alert")
    rows = _alert_rows(payload)
    assert len(rows) == 5, f"expected the five fixture incidents, got {rows!r}"

    ongoing_level = rows[0][5]
    assert "gl-level-critical" in (ongoing_level["value"] or ""), f"got {ongoing_level!r}"
    assert "gl-prominent" in (ongoing_level["value"] or ""), (
        f"the prominent badge belongs on LEVEL in the browser: {ongoing_level!r}"
    )
    # Fix round 1, restored: the badge (and the tier colour) sit on the LEVEL
    # <span>, never on the <td> itself -- a prominent cell's fill must not
    # spread to the whole cell. `test_a_table_value_carries_its_tier_on_the_text_not_the_cell`
    # guards this for the six CollectionBlock-routed plugins; PluginAlert is a
    # hand-rolled <table> on its own code path, so it needs its own check.
    assert _tier_classes(ongoing_level["cell"]) == set(), f"got {ongoing_level!r}"

    resolved_level = rows[2][5]
    assert "gl-level" not in (resolved_level["value"] or ""), (
        f"a resolved incident's LEVEL must go neutral: {resolved_level!r}"
    )

    ongoing_glyph = rows[0][0]
    assert "gl-level-critical" in (ongoing_glyph["value"] or ""), f"the glyph keeps the level colour: {ongoing_glyph!r}"
    resolved_glyph = rows[2][0]
    assert "gl-level-warning" in (resolved_glyph["value"] or ""), (
        f"the glyph keeps the level colour even once resolved: {resolved_glyph!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_resolved_incident_keeps_its_prominent_badge_without_colour():
    """Fix round 1, IMPORTANT 2: curses_renderer_v5.py:851-861 passes
    `color=role if is_ongoing else DEFAULT, prominent=prominent` -- the
    COLOUR drops once resolved, the BADGE does not. The shared `levelClass()`
    token helper cannot express "badge, no tier hue" (a lone `.gl-prominent`
    has no CSS rule at all, css/v5.css:77-91, precisely so a badge can never
    appear without some tier colour behind it) -- PluginAlert.vue therefore
    carries a small, alert-local `.gl-alert-resolved-prominent` class for
    this one case, matching the TUI rather than silently dropping the badge.
    Fixture row 3 is resolved + prominent + critical.
    """
    payload = _run_render_probe("alert")
    rows = _alert_rows(payload)
    resolved_prominent = rows[3][5]
    classes = (resolved_prominent["value"] or "").split()
    assert "gl-alert-resolved-prominent" in classes, f"got {resolved_prominent!r}"
    assert "gl-level-critical" not in classes, f"resolved drops the tier hue: {resolved_prominent!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_unknown_duration_renders_the_placeholder():
    """Fix round 1, MINOR 5: `incident_duration()` is typed `str | None` --
    render the WebUI's "-" placeholder, never blank or a computed value.
    Fixture row 4 carries `duration: null`."""
    payload = _run_render_probe("alert")
    rows = _alert_rows(payload)
    assert rows[4][2]["text"] == "-", f"got {rows[4][2]!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_all_outage_does_not_blank_the_alert_block():
    """Fix round 1, IMPORTANT 1: `alert` is `ownEndpoint` -- it must never be
    part of fetchAll()'s spec list, or fetchAll()'s catch branch
    (`errors[s.name] = e.message` for EVERY requested spec, api.js:134-138)
    hands the alert block an error that belongs to a dead /api/5/all, an
    endpoint it never reads from. `all-unreachable` fails only /api/5/all;
    /api/5/alert/incidents keeps answering normally -- today this scenario
    (test_header_blocks_show_their_error_when_all_fails) only asserted the
    header plugins, so nothing pinned alert's side of this."""
    payload = _run_render_probe("all-unreachable")
    rows = _alert_rows(payload)
    assert rows, (
        "expected the alert grid to render its incidents despite the /all outage: "
        f"{payload['pluginText'].get('alert')!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_partial_incident_marks_its_duration_as_a_lower_bound():
    """`partial` means the opening event aged out of the history, so the
    duration `/api/5/alert/incidents` sends is already a lower bound,
    prefixed ">" server-side (incident_duration()) -- a bare number here
    would be a lie. The component must render the string as it arrives,
    never recompute it."""
    payload = _run_render_probe("alert")
    rows = _alert_rows(payload)
    durations = [row[2]["text"] for row in rows]
    assert any(d.startswith(">") for d in durations), f"got {durations!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_footer_keeps_the_cadence_and_drops_the_alert_list():
    """AppShell.tick()'s alert fetch is repointed at /api/5/alert/incidents
    and its result now feeds PluginAlert.vue, not the footer -- the footer
    keeps only the refresh cadence."""
    payload = _run_render_probe("alert")
    assert "Refresh:" in (payload["footerText"] or ""), f"got {payload['footerText']!r}"
    assert "No alert" not in (payload["footerText"] or ""), f"got {payload['footerText']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_failing_alert_endpoint_does_not_disturb_the_plugins_above_it():
    """The alert fetch stays in its own try/catch (AppShell.vue tick()),
    separate from the one guarding /api/5/all: a 500 from
    /api/5/alert/incidents must not blank the plugins fetchAll() already
    resolved. `alert-incidents-unreachable` fails only that endpoint --
    /api/5/all and /api/5/pluginslist answer normally."""
    payload = _run_render_probe("alert-incidents-unreachable")
    assert "mem" in payload["pluginNames"], f"other plugins must still render: {payload['pluginNames']!r}"
    assert "alert" in payload["pluginNames"], f"the alert block itself must still render: {payload['pluginNames']!r}"
    assert "Refresh:" in (payload["footerText"] or ""), f"the footer must still render: {payload['footerText']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_alert_block_never_claims_all_clear_during_warm_up():
    """Fix round 2, IMPORTANT 2: `/api/5/alert/incidents` now answers an
    envelope (`{is_initializing, incidents}`), and the browser may not claim
    health it cannot know -- the same rule `render_alert_block` already
    follows (curses_renderer_v5.py:738-745). `alert-initializing` answers
    `is_initializing: true` with no incidents."""
    payload = _run_render_probe("alert-initializing")
    text = payload["pluginText"].get("alert", "")
    assert "initializing" in text, f"got {text!r}"
    assert "no alert detected" not in text, f"must not claim an all-clear during warm-up: {text!r}"
    # One GLUED line, `ALERT (initializing)`, exactly as `render_alert_block`
    # paints it (curses_renderer_v5.py:734-754 -- the same string
    # test_curses_renderer_v5.py asserts on the TUI side). Not cosmetic: the
    # block-title-plus-paragraph form this replaced cost three rows where
    # `alertBlockHeight(0, ...)` (row_budget.js) budgets one, so the right
    # column overran the planned body height and the state line was painted
    # under the sticky, opaque `.gl-alerts` footer -- leaving only `ALERT`
    # visible in the browser.
    assert text == "ALERT (initializing)", f"the collapse is one line: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_alert_block_shows_no_alert_detected_once_warmed_up():
    """Control for the test above: once warmed up (`is_initializing: false`)
    with genuinely nothing having ever fired, the block may say so -- in its
    OK colour, matching the TUI (curses_renderer_v5.py:745), not muted."""
    payload = _run_render_probe("alert-empty")
    text = payload["pluginText"].get("alert", "")
    assert "no alert detected" in text, f"got {text!r}"
    cells = payload["pluginTableCells"].get("alert", [])
    assert not cells, f"the empty state renders no incident grid: {cells!r}"
    # Same single-line collapse as the warm-up test above, and for the same
    # row-budget reason -- see its comment.
    assert text == "ALERT (no alert detected)", f"the collapse is one line: {text!r}"


# ------------------------------------------------- alert width cascade + row budget


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_alert_target_column_takes_its_natural_width():
    """TARGET is sized to the LONGEST target on screen, floored at
    `_ALERT_MIN_TARGET` -- what the terminal does whenever it is not
    width-constrained (curses_renderer_v5.py:781-784).

    The <col> used to be pinned to that floor instead, which cropped every
    target past twelve characters although the block had room beside it:
    ALERT_INCIDENTS_FIXTURE's own `Diskio sda read bytes` is 21, and rendered
    as `Diskio sda r…`. The scenario carries no block-width fixture, so no
    cascade fires and the natural width is what reaches the DOM.
    """
    payload = _run_render_probe("alert")
    rows = _alert_rows(payload)
    natural = max(len(row[3]["text"]) for row in rows)
    assert natural > 12, f"the fixture no longer exercises a target past the floor: {natural}"
    # GLYPH, TIME, DURATION, TARGET, TOP (width-less), LEVEL -- TARGET is the
    # fourth <col>, and every <col> box carries COL_SEPARATOR on top of its
    # content width.
    widths = payload["pluginColWidths"]["alert"]
    assert widths[3] == f"calc({natural + 2} * var(--gl-col))", f"got {widths!r} for a {natural}-character target"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_alert_grid_drops_top_processes_first():
    """The TUI sacrifices TOP to keep TARGET readable
    (curses_renderer_v5.py:538-540). The browser must not do the opposite."""
    payload = _run_render_probe("alert-narrow-one-notch")
    headers = payload["pluginHeaderCells"].get("alert") or []
    assert "TOP PROCESSES" not in headers, f"got {headers!r}"
    assert "TARGET" in headers, f"got {headers!r}"
    assert "LEVEL" in headers, f"got {headers!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_alert_grid_drops_level_then_duration():
    headers = _run_render_probe("alert-narrow-two-notches")["pluginHeaderCells"].get("alert") or []
    assert "LEVEL" not in headers and "DURATION" in headers, f"got {headers!r}"
    headers = _run_render_probe("alert-narrowest")["pluginHeaderCells"].get("alert") or []
    assert "DURATION" not in headers and "TARGET" in headers, f"got {headers!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_alert_block_honours_its_row_budget():
    """AppShell.refitVertical()'s row_budget.js solver (Task 4) hands this
    block a quota through `rowBudget` (provide()/inject) -- `budget-short`'s
    cramped viewport shrinks the alert ladder below ALERT_INCIDENTS_FIXTURE's
    5 incidents, exactly as it does for processlist's own 30 rows
    (test_the_row_budget_caps_the_process_block).

    Also pins the title's ongoing/resolved counts to the UNBUDGETED incident
    set: `rows` is capped to the quota, but `titleText()` must keep counting
    every incident regardless -- a regression that points it at the capped
    `rows` instead renders "3 ongoing (dot) 0 resolved" here (ALERT_INCIDENTS_
    FIXTURE's 2 resolved incidents both sort after the 3 ongoing ones and
    fall outside the 3-row cap), silently under-reporting resolved incidents
    that still exist. Reverting the `allRows`/`rows` split in PluginAlert.vue
    (pointing `titleText()` back at `rows`) was confirmed to make exactly
    this assertion fail while every other assertion in this file still
    passed -- see task-10-report.md for the recorded revert/restore output.
    """
    payload = _run_render_probe("budget-short-with-alerts")
    rows = payload["pluginRowGroups"]["alert"][0]
    assert len(rows) == payload["rowBudget"]["alert"], (
        f"rendered {len(rows)} rows, budget was {payload['rowBudget']['alert']}"
    )
    assert _alert_title(payload) == "ALERTS  3 ongoing · 2 resolved", (
        f"the title must count ALL incidents, not just the budgeted rows: got {_alert_title(payload)!r}"
    )


# ------------------------------------------------- processlist TUI parity (G9-9B Task 7)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_processlist_renders_the_tui_columns_and_rows():
    """processlist/render_curses_v5.py `_FIXED_COL_KEYS` (:91) plus `Command`.
    No title cell (unlike `containers`): the renderer never puts one in its
    header row, so every one of the 13 headers below is a field label.
    """
    payload = _run_render_probe("processlist")
    assert payload["pluginHeaderCells"].get("processlist") == [
        "CPU%",
        "MEM%",
        "VIRT",
        "RES",
        "PID",
        "USER",
        "THR",
        "NI",
        "S",
        "TIME+",
        "R/s",
        "W/s",
        "Command",
    ], f"got {payload['pluginHeaderCells'].get('processlist')!r}"
    rows = _table_rows(payload, "processlist", 13)
    # VIRT is "120M", not "120.0M": VIRT/RES/R/s/W/s render through
    # `formatProcessBytes` (processlist/render_curses_v5.py's OWN
    # `_format_bytes`, not the shared `formatBytes` every other byte column
    # uses), which drops the decimal at >= 100 -- 125829120 bytes is exactly
    # 120.0M, so this row is the one fixture value that tells the two
    # formatters apart. RES (32.0M, < 100) keeps its decimal under either
    # formatter, so it is not a distinguishing case.
    assert rows[0] == [
        "78.4%",
        "3.1%",
        "120M",
        "32.0M",
        "12345",
        "alice",
        "4",
        "0",
        "S",
        "0:12",
        "512B",
        "512B",
        "python3 myscript.py --verbose",
    ], f"got {rows[0]!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_processlist_shows_the_placeholder_for_every_missing_value_and_the_kernel_thread_fallback():
    """Row 1 of the `processlist` fixture carries every optional field as
    null. VIRT/RES/R/s/W/s (`formatProcessBytes`) and USER (`formatUsername`,
    format.js) mirror the TUI's OWN per-column marker `?` for a missing
    value -- `_memory_info_field`/`_io_rate`/`_format_username`
    (processlist/render_curses_v5.py) all render `?`, not `-`, and
    `formatProcessBytes`'s own docstring says why a null there is a live,
    reachable case rather than a defensive guard. Every other column
    (CPU%, MEM%, THR, NI, S, TIME+) keeps the WebUI's single
    placeholder `-` (format.js `MISSING`). Its Command cell is the OTHER TUI
    fallback: no `cmdline` at all renders the kernel-thread bracket form from
    the process `name`.
    """
    payload = _run_render_probe("processlist")
    rows = _table_rows(payload, "processlist", 13)
    row = rows[1]
    # VIRT, RES, USER, R/s, W/s -- the five columns that render through a
    # formatter that answers "?" for a missing value.
    question_mark_columns = {2, 3, 5, 10, 11}
    # PID (index 4) is the only non-null field among the first 12 columns.
    for i, cell in enumerate(row[:12]):
        if i == 4:
            assert cell == "999", f"PID must render, got {row!r}"
        elif i in question_mark_columns:
            assert cell == "?", f"column {i} must mirror the TUI's own marker, got {row!r}"
        else:
            assert cell == "-", f"column {i} must be the WebUI placeholder, got {row!r}"
    assert row[12] == "[kthread0]", f"got {row!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_processlist_colours_cpu_and_mem_from_levels():
    """`_levels` is keyed by `pid` (processlist/render_curses_v5.py
    `levels_index.get(pid)`); row 0's pid (12345) carries a warning CPU%
    and an ok MEM% in the fixture."""
    payload = _run_render_probe("processlist")
    cells = payload["pluginTableCells"]["processlist"]
    assert _tier_classes(cells[0]["value"]) == {"gl-level-warning"}, cells[0]
    assert _tier_classes(cells[0]["cell"]) == set(), f"the <td> itself carries no tier class: {cells[0]!r}"
    assert _tier_classes(cells[1]["value"]) == {"gl-level-ok"}, cells[1]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_processlist_caps_at_max_processes_display_in_payload_order():
    """`[outputs] max_processes_display=2` (CONFIG_FIXTURES) slices the
    FIRST two of the `processlist-cap` fixture's three payload-order rows,
    never the top two by `cpu_percent` (pid 10, in the middle, is the
    highest at 50 and must NOT be pulled to the front, nor kept over pid 20
    just because it is bigger) -- the engine sorts, this component must not.
    """
    payload = _run_render_probe("processlist-cap")
    headers = payload["pluginHeaderCells"]["processlist"]
    rows = _table_rows(payload, "processlist", len(headers))
    assert len(rows) == 2, f"expected exactly 2 rows (the cap), got {len(rows)}: {rows!r}"
    pid_index = headers.index("PID")
    command_index = headers.index("Command")
    assert [r[pid_index] for r in rows] == ["30", "10"], f"got {rows!r}"
    assert [r[command_index] for r in rows] == ["third", "first"], f"got {rows!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_processlist_block_with_no_config_cap_shows_every_row():
    """A scenario absent from CONFIG_FIXTURES gets `{}` -- no `outputs` key
    at all -- which must read as "no cap", not as a cap of zero/undefined
    that hides everything. "processlist" (2 rows) has no CONFIG_FIXTURES
    entry, unlike "processlist-cap"."""
    payload = _run_render_probe("processlist")
    headers = payload["pluginHeaderCells"]["processlist"]
    rows = _table_rows(payload, "processlist", len(headers))
    assert len(rows) == 2, f"expected both fixture rows with no configured cap, got {len(rows)}: {rows!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_processlist_underlines_the_active_sort_column_and_no_other():
    """`serverArgs.sort_processes_key` (task 5) names the column the engine
    really sorts by; `_HEADER_SORT_KEY` (:97) says CPU% <-> `cpu_percent`.
    Exactly that header gets the underline class, no other."""
    payload = _run_render_probe("processlist-sorted")
    headers = payload["pluginColumnHeaders"]["processlist"]
    classes = payload["pluginColumnClasses"]["processlist"]
    sorted_indices = [i for i, cls in enumerate(classes) if "gl-sorted" in cls.split()]
    assert sorted_indices == [headers.index("CPU%")], f"got headers={headers!r} classes={classes!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_processlist_underlines_nothing_without_a_sort_key():
    """The `processlist` scenario carries no `sort_processes_key` in
    ARGS_FIXTURES -- absent means `{}`, i.e. no flag -- so no header may be
    underlined."""
    payload = _run_render_probe("processlist")
    classes = payload["pluginColumnClasses"]["processlist"]
    assert not any("gl-sorted" in cls.split() for cls in classes), f"got {classes!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_wide_processlist_block_keeps_every_column():
    """The cascade starts from NO flag on every pass (degrade.js
    resolveDegrade), so a block that fits drops nothing."""
    payload = _run_render_probe("processlist-wide")
    headers = payload["pluginHeaderCells"].get("processlist") or []
    assert "Command" in headers, f"got {headers!r}"
    assert "VIRT" in headers, f"got {headers!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_command_survives_the_full_processlist_cascade():
    """`_DROP_ORDER`'s eight columns (processlist/render_curses_v5.py:89)
    all go on a sufficiently narrow block, but `Command` is the protected
    TAIL here -- the deliberate opposite of `containers`, where `command` is
    the FIRST column dropped."""
    payload = _run_render_probe("processlist-narrow")
    headers = payload["pluginHeaderCells"].get("processlist") or []
    assert "Command" in headers, f"got {headers!r}"
    for dropped in ("VIRT", "TIME+", "RES", "USER", "PID", "THR", "S", "NI"):
        assert dropped not in headers, f"{dropped} must be gone on the narrowest pass: {headers!r}"
    for kept in ("CPU%", "MEM%", "R/s", "W/s"):
        assert kept in headers, f"{kept} must never be dropped: {headers!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_row_budget_caps_the_process_block():
    """AppShell.refitVertical()'s row_budget.js solver (Task 4) hands this
    block a quota through `rowBudget` (provide()/inject, AppShell.vue:114-126)
    -- `budget-short`'s cramped viewport shrinks the ladder below the
    fixture's 30 rows."""
    payload = _run_render_probe("budget-short")
    rows = payload["pluginRowGroups"]["processlist"][0]
    assert len(rows) == payload["rowBudget"]["processlist"], (
        f"got {len(rows)} rows, budget was {payload['rowBudget']!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_config_cap_still_wins_when_it_is_lower():
    """`[outputs] max_processes_display` is a hard ceiling that available
    height may never raise (design 4.7). `budget-tall-with-config-cap` reuses
    `budget-tall`'s generous height -- the solver would otherwise grow the
    block to all 30 rows -- with a CONFIG_FIXTURES cap of 5."""
    payload = _run_render_probe("budget-tall-with-config-cap")
    rows = payload["pluginRowGroups"]["processlist"][0]
    assert len(rows) == 5, f"got {len(rows)} rows: {rows!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_process_table_declares_the_terminal_column_widths():
    """The <colgroup> carries the character counts
    (process_widths.js's WEBUI_COL_WIDTHS/FIXED_COL_KEYS), so a wider PID
    at the next refresh cannot re-lay the table out. `pluginColWidths`
    (Task 7) lets this be observed; nothing before this test asserts that a
    colgroup is rendered at all.

    Each `<col>` is `WEBUI_COL_WIDTHS[key] + COL_SEPARATOR`, not the bare
    content width: under `table-layout: fixed` the <col> is the column's
    WHOLE box, and the `:not(:last-child)` separator's `padding-right` comes
    out of that same box, so a <col> of exactly N characters would leave only
    N - COL_SEPARATOR for content -- every fixed column would crop early
    (invisibly so for `S`, N=1). CPU% is 7, not 5: a 5-wide field fits
    `100.0` but not `9999.9`, a value a process spread over many cores can
    genuinely reach. MEM% is 6 where the terminal budgets 5, because
    `formatPercent()` appends a `%` curses never prints and `100.0%` is six
    characters -- see WEBUI_COL_WIDTHS' own comment.
    """
    payload = _run_render_probe("processlist-wide")
    assert payload["pluginColWidths"]["processlist"] == [
        f"calc({n + 2} * var(--gl-col))" for n in (7, 6, 5, 5, 7, 10, 3, 3, 1, 8, 5, 5)
    ]
    assert "gl-process-table" in payload["pluginTableClasses"]["processlist"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_column_box_reserves_the_separator_inside_it():
    """`colStyle()` used to return the content width alone, under-sizing every
    column's usable content space by the separator -- under
    `table-layout: fixed` the <col> is the column's WHOLE box, and
    `.gl-process-table td:not(:last-child)`'s `padding-right` comes out of
    that same box. A maintainer browser smoke test caught it (every fixed
    column cropped early; invisibly so for `S`, whose content width of 1 made
    the column disappear rather than merely narrow); the PREVIOUS version of
    this test (test_the_process_table_declares_the_terminal_column_widths) did
    not, because its expected numbers were hand-copied from the same (buggy)
    `colStyle()` output it was meant to check -- consistent with itself and
    wrong.

    This DOM-less probe has no CSS box model and no real layout engine, so it
    cannot observe actual rendered content space the way a browser can --
    that would need something like Playwright or headless Chrome measuring
    real pixel widths, which this test suite does not have. What it CAN do,
    and what the previous test did not, is pin the FORMULA independently of
    `colStyle()`'s own source: `WEBUI_COL_WIDTHS`/`FIXED_COL_KEYS`/
    `COL_SEPARATOR` are re-extracted here straight from process_widths.js by
    regex (the same technique test_webui_v5_width_drift.py uses), never by
    importing or calling colStyle -- so a future edit that silently drops the
    offset changes only production code, not this independently-sourced
    expectation, and the two are compared instead of copied from one another.
    """
    widths_path = _BUNDLE_PATH.parent.parent / "js" / "v5" / "process_widths.js"
    source = widths_path.read_text()
    order_match = re.search(r"export const FIXED_COL_KEYS\s*=\s*\[(.*?)\];", source, re.S)
    assert order_match, f"FIXED_COL_KEYS is not exported from {widths_path}"
    keys = re.findall(r'"([^"]+)"', order_match.group(1))
    widths_match = re.search(r"export const WEBUI_COL_WIDTHS\s*=\s*\{(.*?)\};", source, re.S)
    assert widths_match, f"WEBUI_COL_WIDTHS is not exported from {widths_path}"
    content_widths = {k: int(v) for k, v in re.findall(r'"([^"]+)"\s*:\s*(\d+)', widths_match.group(1))}
    separator_match = re.search(r"export const COL_SEPARATOR\s*=\s*(\d+)\s*;", source)
    assert separator_match, f"COL_SEPARATOR is not exported from {widths_path}"
    separator = int(separator_match.group(1))

    payload = _run_render_probe("processlist-wide")
    col_widths = payload["pluginColWidths"]["processlist"]
    assert len(col_widths) == len(keys), f"got {col_widths!r} for keys {keys!r}"
    for key, declared in zip(keys, col_widths):
        expected = content_widths[key] + separator  # content chars + the separator inside the box
        assert declared == f"calc({expected} * var(--gl-col))", (
            f"{key}: got {declared!r}, expected content ({content_widths[key]}) + {separator} separator = {expected}"
        )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_long_user_name_is_cropped_not_wrapped():
    """`formatUsername` (format.js) crops at PROCESS_COL_WIDTHS.USER=10 and
    marks the crop with a trailing `+` -- the fixed-layout table no longer
    wraps a long name onto a second line (defect P4)."""
    payload = _run_render_probe("processlist-wide")
    headers = payload["pluginColumnHeaders"]["processlist"]
    idx = headers.index("USER")
    rows = payload["pluginRowGroups"]["processlist"][0]
    cells = [row[idx] for row in rows]
    assert all(len(text) <= 10 for text in cells), cells
    assert any(text.endswith("+") for text in cells), cells


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_command_column_carries_no_character_cap():
    """Defect P2: Command takes whatever is left. Its floor is reserved by the
    table's min-width (--gl-fixed-cols), not by a cap on the cell -- the cap
    belongs to `containers`, which keeps the measure-driven `.gl-command`
    cascade; here the column width truncates instead.

    `gl-command` lives on the value <span> inside the <td>, never on the <td>
    itself -- `pluginValueClasses` (webui_render_probe.js's `values.map((cell)
    => cell.className)`) reads only `<td>`/`<dd>` classNames and would prove
    nothing here: a mutation test confirmed it (re-adding `gl-command` to the
    span left that assertion passing). `pluginTableCells[i]["value"]` is that
    span's own class list -- the same accessor
    test_raid_colours_the_values_and_the_status_lines_from_levels already uses
    for the identical reason ("`pluginValueClasses` would give the cell's
    ('gl-num') and prove nothing").
    """
    payload = _run_render_probe("processlist-wide")
    spans = [cell["value"] for cell in payload["pluginTableCells"]["processlist"]]
    assert spans, "the scenario must actually render process rows"
    assert not any("gl-command" in (span or "") for span in spans), spans


# ------------------------------------------------- programlist TUI parity (G9-9B Task 8)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_programlist_renders_the_tui_columns_and_rows():
    """programlist/render_curses_v5.py :99-113 -- identical to processlist's
    13 headers except `PID` (index 4) is replaced by `NPROCS` (no single pid
    on an aggregated program row)."""
    payload = _run_render_probe("programlist")
    assert payload["pluginHeaderCells"].get("programlist") == [
        "CPU%",
        "MEM%",
        "VIRT",
        "RES",
        "NPROCS",
        "USER",
        "THR",
        "NI",
        "S",
        "TIME+",
        "R/s",
        "W/s",
        "Command",
    ], f"got {payload['pluginHeaderCells'].get('programlist')!r}"
    rows = _table_rows(payload, "programlist", 13)
    # VIRT is "120M", not "120.0M": programlist/render_curses_v5.py imports
    # processlist's OWN `_format_bytes` verbatim (its docstring says every
    # cell builder but the identity column is shared), so VIRT/RES/R/s/W/s
    # render through `formatProcessBytes` here too, the same formatter
    # processlist's own parity test distinguishes on this exact value.
    assert rows[0] == [
        "78.4%",
        "3.1%",
        "120M",
        "32.0M",
        "3",
        "alice",
        "4",
        "0",
        "S",
        "0:12",
        "512B",
        "512B",
        "python3 myscript.py --verbose",
    ], f"got {rows[0]!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_programlist_shows_the_placeholder_for_every_missing_value_and_the_kernel_thread_fallback():
    """Row 1 of the `programlist` fixture carries every optional field
    (including `nprocs`) as null. VIRT/RES/R/s/W/s (`formatProcessBytes`) and
    USER (`formatUsername`) mirror the TUI's OWN per-column marker `?` for a
    missing value, exactly like processlist's own row 1 -- `nprocs` (index 4)
    is not one of them: it renders through the same plain `fmt()` as
    processlist's PID column, so its placeholder is the WebUI's ordinary `-`.
    The Command cell falls back to the kernel-thread bracket form from
    `name`."""
    payload = _run_render_probe("programlist")
    rows = _table_rows(payload, "programlist", 13)
    row = rows[1]
    # VIRT, RES, USER, R/s, W/s -- the five columns that render through a
    # formatter that answers "?" for a missing value.
    question_mark_columns = {2, 3, 5, 10, 11}
    for i, cell in enumerate(row[:12]):
        if i in question_mark_columns:
            assert cell == "?", f"column {i} must mirror the TUI's own marker, got {row!r}"
        else:
            assert cell == "-", f"column {i} must be the WebUI placeholder, got {row!r}"
    assert row[12] == "[kthread0]", f"got {row!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_programlist_colours_cpu_and_mem_from_levels():
    """`_levels` is keyed by `name` (programlist/render_curses_v5.py
    `levels_index.get(name)`) -- the fixture's "python3" row carries a
    warning CPU% and an ok MEM%."""
    payload = _run_render_probe("programlist")
    cells = payload["pluginTableCells"]["programlist"]
    assert _tier_classes(cells[0]["value"]) == {"gl-level-warning"}, cells[0]
    assert _tier_classes(cells[0]["cell"]) == set(), f"the <td> itself carries no tier class: {cells[0]!r}"
    assert _tier_classes(cells[1]["value"]) == {"gl-level-ok"}, cells[1]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_programlist_caps_at_max_processes_display_in_payload_order():
    """Same config key and the same AppShell provide() as processlist's own
    cap (task 8): `[outputs] max_processes_display=2` slices the FIRST two
    of three payload-order rows, never the top two by `cpu_percent` (the
    highest, "first" at 50, sits in the middle and must not be pulled to
    the front)."""
    payload = _run_render_probe("programlist-cap")
    headers = payload["pluginHeaderCells"]["programlist"]
    rows = _table_rows(payload, "programlist", len(headers))
    assert len(rows) == 2, f"expected exactly 2 rows (the cap), got {len(rows)}: {rows!r}"
    command_index = headers.index("Command")
    assert [r[command_index] for r in rows] == ["third", "first"], f"got {rows!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_programlist_underlines_the_active_sort_column_and_no_other():
    """`serverArgs.sort_processes_key` names the column the engine sorts by,
    shared with processlist's `_HEADER_SORT_KEY` mapping -- `NPROCS` has no
    entry (programlist/render_curses_v5.py's own docstring, :22) and must
    never be underlined."""
    payload = _run_render_probe("programlist-sorted")
    headers = payload["pluginColumnHeaders"]["programlist"]
    classes = payload["pluginColumnClasses"]["programlist"]
    sorted_indices = [i for i, cls in enumerate(classes) if "gl-sorted" in cls.split()]
    assert sorted_indices == [headers.index("CPU%")], f"got headers={headers!r} classes={classes!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_programlist_underlines_nothing_without_a_sort_key():
    """The `programlist` scenario carries `--programs` but no
    `sort_processes_key` -- no header may be underlined."""
    payload = _run_render_probe("programlist")
    classes = payload["pluginColumnClasses"]["programlist"]
    assert not any("gl-sorted" in cls.split() for cls in classes), f"got {classes!r}"


# --------------------------------------------------- programlist has no width cascade (Task 9)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_program_block_uses_nprocs_where_processes_use_pid():
    """process_widths.js's PROGRAM_FIXED_COL_KEYS is FIXED_COL_KEYS with
    NPROCS (NPROCS_WIDTH=7) in PID's place -- same width as PID (both 7), so
    the expected tuple is numerically identical to processlist's own
    (test_the_process_table_declares_the_terminal_column_widths), column for
    column. Each `<col>` is content width + COL_SEPARATOR, same formula as
    processlist's own `colStyle()`."""
    payload = _run_render_probe("programlist-wide")
    widths = payload["pluginColWidths"]["programlist"]
    assert widths == [f"calc({n + 2} * var(--gl-col))" for n in (7, 6, 5, 5, 7, 10, 3, 3, 1, 8, 5, 5)]
    assert "gl-process-table" in payload["pluginTableClasses"]["programlist"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_program_block_takes_the_same_row_budget_as_the_process_block():
    """row_budget.js's `planRightColumn()` feeds `state.processes` into both
    `rowBudget.processlist` and `rowBudget.programlist` unconditionally, so
    the two numbers are always equal regardless of which block `slots()`
    actually shows. The real assertion is the second one: the RENDERED row
    count must track the budget the component was actually handed through
    its own `rowBudget` inject, not just that the number exists."""
    payload = _run_render_probe("budget-short-programs")
    assert payload["rowBudget"]["programlist"] == payload["rowBudget"]["processlist"]
    rows = payload["pluginRowGroups"]["programlist"][0]
    assert len(rows) == payload["rowBudget"]["programlist"], (
        f"got {len(rows)} rows, budget was {payload['rowBudget']!r}"
    )


# --------------------------------- processlist / programlist exclusivity (G9-9B Task 8)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_programlist_renders_and_processlist_does_not_with_programs():
    """AppShell.vue `slots()`, the same shape as the `cpu`/`percpu`
    exclusion: `serverArgs.programs` true (the "programlist" scenario) hides
    `processlist` from the `right` slot even though the shell never sees
    processlist's own payload absent -- it is the flag alone that decides."""
    payload = _run_render_probe("programlist")
    right = payload["slots"].get("right", [])
    assert "programlist" in right, f"got {right!r}"
    assert "processlist" not in right, f"got {right!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_processlist_renders_and_programlist_does_not_without_programs():
    """The other half: no `--programs` (the "processlist" scenario, whose
    ARGS_FIXTURES entry is absent -> `{}`), so the default thread view
    renders and `programlist` does not -- the terminal's own default (v4
    parity, `programs: bool = False`)."""
    payload = _run_render_probe("processlist")
    right = payload["slots"].get("right", [])
    assert "processlist" in right, f"got {right!r}"
    assert "programlist" not in right, f"got {right!r}"


# ------------------------------------------------ plugin registry count (G9-9B Task 8)


def test_the_registry_holds_all_32_plugins():
    """G9 closes here: programlist was the last of the 32 v5 plugins to reach
    the WebUI. A file-level count (rather than a render-probe one) because
    the registry's total membership is independent of any one scenario's
    exclusivity outcome (processlist XOR programlist, cpu XOR percpu) --
    exactly the `grep -c 'component: Plugin'` check the task brief names."""
    text = (
        Path(__file__).parent.parent / "glances" / "outputs" / "static" / "js" / "v5" / "plugins" / "index.js"
    ).read_text()
    count = len(re.findall(r"component: Plugin", text))
    assert count == 32, f"expected 32 registered plugins, got {count}"


# ------------------------------------------------------- right column vertical fit (Task 4)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_tall_viewport_grows_the_process_block_past_its_nominal():
    payload = _run_render_probe("budget-tall")
    assert payload["rowBudget"]["processlist"] > 20, f"got {payload['rowBudget']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_short_viewport_shrinks_it():
    payload = _run_render_probe("budget-short")
    assert payload["rowBudget"]["processlist"] < 20, f"got {payload['rowBudget']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_unmeasurable_viewport_budgets_nothing():
    """degrade.js's rule, applied on the vertical axis: a DOM without layout, a
    hidden tab or a detached node must never hide the user's stats."""
    assert _run_render_probe("budget-unmeasurable")["rowBudget"] == {}


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_second_tick_rebudgets_against_its_own_alert_state():
    """Fix round 2, Important 1: `tick()` must read `this.results.alert`
    AFTER that tick's own alert fetch resolves, not before -- otherwise
    every periodic poll budgets against the PREVIOUS cycle's alert state,
    forever (not just at startup, where `mounted()`'s own extra refit/
    refitVertical pass after `tick()` papers over it).

    The `budget-tick-shift` scenario (webui_render_fixtures.js) holds
    viewport geometry (bodyHeight=14 rows, same as `budget-short`) and the
    30-row processlist fixture CONSTANT, and varies only the alert payload
    across two `api/5/alert/incidents` calls: tick 1 sees no incidents,
    tick 2 sees five ONGOING ones. row_budget.js's `floorAlerts` reserves
    rows for an ongoing incident out of the SAME shared pool `processlist`
    draws from, so the two ticks' correct budgets are visibly different:
    tick 1 -> `{processlist: 9, alert: 3}`, tick 2 -> `{processlist: 3,
    alert: 5}` (both hand-verified by calling `planRightColumn()` directly
    with the matching inputs).

    The render probe fires tick 1 via AppShell's own `mounted()`, then a
    SECOND tick via the `__glancesTick` hook (fix round 3) -- something no
    other test in this file does; every other render-probe test drives the
    vertical pass through `__glancesRefit()`, which calls `refit()` then
    `refitVertical()` directly with no alert refetch in between, and could
    never have caught this class of bug.

    Before the round 2 fix, `refitVertical()` ran BEFORE the alert fetch
    inside `tick()`, so tick 2 would read `this.results.alert` as it stood
    at the END of tick 1 -- still tick 1's zero-incident envelope, since
    tick 2's own fetch had not yet landed -- and produce tick 1's budget
    again: `{processlist: 9, alert: 3}`. This test asserts the FIXED value;
    it was run against the reverted ordering and confirmed to fail with
    exactly that stale value (see the fix round 3 report for both outputs).
    """
    payload = _run_render_probe("budget-tick-shift")
    assert payload["rowBudget"] == {
        "vms": 0,
        "containers": 0,
        "processlist": 3,
        "programlist": 3,
        "alert": 5,
    }, f"got {payload['rowBudget']!r} -- {{'processlist': 9, 'alert': 3, ...}} is tick 1's STALE value"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_block_with_neither_new_input_renders_its_table_unchanged():
    """CollectionBlock's `#cols` slot and `tableClass` prop (Task 7) are both
    optional and default to nothing. `processlist` is the first real
    consumer (colgroup + `gl-process-table`; see
    test_the_process_table_declares_the_terminal_column_widths for its exact
    widths), so it is excluded from the loop below. `programlist` is not
    checked here either way: it does not render in this scenario's default
    process view (`ARGS_FIXTURES`' `programs: true` is what turns it on,
    scenario `budget-short-programs`). `alert` is a THIRD fixed-layout
    consumer (its own hand-rolled `<table>`, not CollectionBlock's)
    -- unlike programlist it renders in every scenario (`ownEndpoint`), so it
    is excluded from the loop below too, rather than silently never being
    iterated over. `containers` is the FOURTH, and is excluded on its own line
    for the same reason as programlist: this scenario gives it no payload, so
    it paints no table here and the loop would pass on it by accident -- see
    test_the_container_table_declares_the_terminal_column_widths, which runs
    the `containers` scenario, for its widths. Every OTHER plugin still shows no <colgroup>
    (pluginColWidths == []) and carries only the base
    `.gl-table` class (pluginTableClasses == ["gl-table"]), proving the two
    new inputs are additive rather than a silent behaviour change for the
    remaining consumers.
    """
    payload = _run_render_probe("processlist")
    col_widths = payload["pluginColWidths"]
    table_classes = payload["pluginTableClasses"]
    assert "processlist" in col_widths and "processlist" in table_classes
    assert len(col_widths["processlist"]) == 12, col_widths["processlist"]
    assert table_classes["processlist"] == ["gl-table", "gl-process-table"], table_classes["processlist"]
    assert table_classes["alert"] == ["gl-table", "gl-process-table"], table_classes["alert"]
    for name in payload["pluginNames"]:
        if name in ("processlist", "alert", "containers"):
            continue
        assert col_widths[name] == [], f"{name} rendered a <colgroup> with no consumer yet: {col_widths[name]!r}"
        # [] for a plugin whose article has no <table> at all (a scalar-grid
        # block, <dl>-based); ["gl-table"] -- the unconditional base class,
        # nothing appended -- for every plugin that does.
        assert table_classes[name] in ([], ["gl-table"]), f"{name} table class drifted: {table_classes[name]!r}"


# ------------------------------------------------- workload blocks and the row budget solver


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_workload_block_honours_its_row_quota():
    """The solver splits a shared pool between vms and containers
    (`_split_workloads`, curses_renderer_v5.py:923-942). Nothing consumed that
    split before this task, so the solver reserved rows the browser then
    overspent."""
    payload = _run_render_probe("budget-workloads-capped")
    assert len(payload["pluginRowGroups"]["containers"][0]) == payload["rowBudget"]["containers"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_zero_quota_hides_the_block_header_included():
    """Ladder steps g and l make a block VANISH, and `cost()` charges it zero
    rows (curses_renderer_v5.py:1035-1044). A header row left on screen is one
    row the solver did not budget."""
    payload = _run_render_probe("budget-processlist-zeroed")
    assert payload["rowBudget"]["processlist"] == 0
    assert payload["pluginHidden"]["processlist"] is True


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_vms_block_honours_its_own_row_quota_alongside_containers():
    """`test_a_workload_block_honours_its_row_quota` above only ever
    populates `containers` -- a scenario that never gives `vms` any data
    cannot tell "the block reads its own quota" apart from "the block was
    never at risk of overflowing". `budget-workloads-both-capped` populates
    BOTH blocks (10 vms, 30 containers) under the same cramped viewport, so
    `_split_workloads`'s max-min fairness rule (curses_renderer_v5.py:923-942)
    actually has two competing blocks to divide a pool between -- confirmed
    against `planRightColumn()` directly: `{vms: 3, containers: 2, ...}`,
    neither the full count nor an even half, which an even-split or
    vms-ignored implementation could not produce by accident.
    """
    payload = _run_render_probe("budget-workloads-both-capped")
    assert payload["rowBudget"]["vms"] == 3, f"got {payload['rowBudget']!r}"
    assert payload["rowBudget"]["containers"] == 2, f"got {payload['rowBudget']!r}"
    assert len(payload["pluginRowGroups"]["vms"][0]) == payload["rowBudget"]["vms"]
    assert len(payload["pluginRowGroups"]["containers"][0]) == payload["rowBudget"]["containers"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_engine_column_reads_the_full_vms_list_not_the_budgeted_one():
    """vms/render_curses_v5.py:157 decides `show_engine` from the FULL item
    list, BEFORE its own `items[:budget]` slice (:169) -- a component that
    decided the flag from the already-sliced rows instead would flip Engine
    off whenever the budget crops the row carrying the second engine.
    `budget-vms-column-parity`'s five VMs carry two distinct engines, but
    only the first three (one engine) survive the scenario's 3-row quota
    (confirmed against `planRightColumn()` directly): the Engine column must
    still render.
    """
    payload = _run_render_probe("budget-vms-column-parity")
    assert payload["rowBudget"]["vms"] == 3, f"got {payload['rowBudget']!r}"
    headers = payload["pluginHeaderCells"].get("vms") or []
    assert "Engine" in headers, f"got {headers!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_pod_column_reads_the_full_containers_list_not_the_budgeted_one():
    """containers/render_curses_v5.py:265 decides `show_pod` from the FULL
    item list, BEFORE its own `items[:budget]` slice (:273) -- the same class
    of bug as vms' own Engine column above, on containers_columns.js's OTHER
    data-driven flag family. `budget-containers-column-parity`'s five
    containers have a pod on two of them, but both sit past the scenario's
    3-row quota (confirmed against `planRightColumn()` directly): the Pod
    column must still render.
    """
    payload = _run_render_probe("budget-containers-column-parity")
    assert payload["rowBudget"]["containers"] == 3, f"got {payload['rowBudget']!r}"
    headers = payload["pluginHeaderCells"].get("containers") or []
    assert "Pod" in headers, f"got {headers!r}"


# ----------------------------------------------------- SHOW/HIDE hotkeys
#
# The key table itself is compared to the TUI's in
# tests/test_webui_v5_hotkeys_drift.py, and the toggle logic is unit-tested in
# tests/js/hotkeys.test.mjs. What is left, and only the probe can show it, is
# that pressing a key actually removes the block from the rendered DOM.


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
@pytest.mark.parametrize(
    ("key", "gone"),
    [
        ("n", {"network"}),
        ("d", {"diskio"}),
        ("s", {"sensors"}),
        ("f", {"fs", "folders"}),  # compound: one key, two plugins
    ],
)
def test_a_show_hide_key_removes_its_blocks_from_the_page(key, gone):
    before = set(_run_render_probe("default")["pluginNames"])
    assert gone <= before, f"vacuous: {sorted(gone - before)} was not rendered to begin with"

    after = set(_run_render_probe("default", key)["pluginNames"])
    assert not (gone & after), f"{key!r} left {sorted(gone & after)} on the page"
    # Only the named plugins go.
    assert before - gone == after


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_pressing_a_key_twice_brings_the_block_back():
    before = set(_run_render_probe("default")["pluginNames"])
    after = set(_run_render_probe("default", "n,n")["pluginNames"])
    assert after == before


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_slot_keys_clear_their_whole_column():
    """`2` and `5` resolve against the live registry, so they cover exactly the
    plugins the page actually renders in that slot."""
    baseline = _run_render_probe("default")
    left = set(baseline["slots"].get("left", []))
    top = set(baseline["slots"].get("top", []))
    assert left and top, "vacuous: the fixture has no left/top column"

    after_2 = _run_render_probe("default", "2")
    assert after_2["slots"].get("left", []) == []
    assert set(after_2["slots"].get("top", [])) == top, "`2` must not touch the top row"

    after_5 = _run_render_probe("default", "5")
    assert after_5["slots"].get("top", []) == []
    assert set(after_5["slots"].get("left", [])) == left, "`5` must not touch the sidebar"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_slot_key_then_a_plugin_key_acts_on_that_one_plugin():
    """Slot keys are expanded to their members, so a later single-plugin key
    un-hides that plugin alone — the TUI's behaviour (design section 5.4), and
    the reason `2` is not carried as indivisible slot state."""
    left = set(_run_render_probe("default")["slots"].get("left", []))
    assert "network" in left

    after = _run_render_probe("default", "2,n")
    assert set(after["slots"].get("left", [])) == {"network"}


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_unbound_key_changes_nothing():
    """`y` is bound by neither v4 nor v5. A page that reacted to it would be
    swallowing keystrokes the browser should keep."""
    before = _run_render_probe("default")
    after = _run_render_probe("default", "y")
    assert after["pluginNames"] == before["pluginNames"]
    assert after["userHidden"] == []


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_h_opens_and_closes_the_help_overlay():
    assert _run_render_probe("default", "h")["showHelp"] is True
    assert _run_render_probe("default", "h,h")["showHelp"] is False
    # The overlay does not hide anything by itself.
    assert _run_render_probe("default", "h")["userHidden"] == []


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_help_overlay_renders_every_bound_key():
    """Not just the flag: the rows must actually reach the DOM. The TUI
    generates its overlay from `_HOTKEYS`, so a bound key cannot go
    undocumented; `helpRows()` gives the browser the same property, and this is
    what proves it survives the template."""
    from glances.outputs.glances_curses_v5 import TuiV5

    rendered = _run_render_probe("default", "h")["helpRows"]
    bound = {
        key: spec["desc"]
        for key, spec in TuiV5._HOTKEYS.items()
        if "hide" in spec or spec.get("group") == "TOGGLE VIEW"
    }
    # One row per bound key (24 SHOW/HIDE + 7 TOGGLE VIEW), plus `h` itself.
    assert len(rendered) == len(bound) + 1 == 32

    joined = " ".join(rendered)
    for key, desc in bound.items():
        assert f"{key}{desc}" in joined, f"{key} is missing from the overlay: {rendered!r}"
    assert any("help" in row for row in rendered), "`h` must document itself"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_help_overlay_is_absent_until_asked_for():
    """v-if, not v-show: a closed overlay must not sit in the DOM, where the
    degradation cascade would measure it."""
    assert _run_render_probe("default")["helpRows"] == []


# ----------------------------------------------------- TOGGLE VIEW hotkeys
#
# `1`, `j`, `4`, `/`. Unlike SHOW/HIDE these do not remove a block: they flip
# HOW something is shown, over a default the server supplies in /api/5/args.


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_key_1_swaps_cpu_for_percpu():
    before = set(_run_render_probe("default")["pluginNames"])
    assert "cpu" in before and "percpu" not in before

    after = set(_run_render_probe("default", "1")["pluginNames"])
    assert "percpu" in after and "cpu" not in after


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_key_j_swaps_processlist_for_programlist():
    before = set(_run_render_probe("default")["pluginNames"])
    assert "processlist" in before and "programlist" not in before

    after = set(_run_render_probe("default", "j")["pluginNames"])
    assert "programlist" in after and "processlist" not in after


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_key_4_empties_the_top_row_but_for_quicklook():
    """The same set the TUI hides since 2026-09-22 — `_FULL_QUICKLOOK_HIDDEN`,
    mirrored in full_quicklook.js and pinned by its own drift test."""
    assert _run_render_probe("default", "4")["slots"]["top"] == ["quicklook"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_key_slash_switches_the_command_column_to_the_full_path():
    """`/` is not a visibility toggle: it changes what the Command column
    renders. The browser had only the short form before this key existed."""
    short = _run_render_probe("processlist")["pluginText"]["processlist"]
    full = _run_render_probe("processlist", "/")["pluginText"]["processlist"]

    assert "python3 myscript.py" in short
    assert "/usr/bin/python3" not in short
    assert "/usr/bin/python3 myscript.py" in full


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
@pytest.mark.parametrize(
    ("scenario", "key", "flag"),
    [
        ("cpu-percpu-on", "1", "percpu"),
        ("quicklook-full", "4", "full_quicklook"),
    ],
)
def test_a_toggle_view_key_flips_the_servers_value_not_a_false_default(scenario, key, flag):
    """The override starts from what the server reported, so the FIRST press
    always visibly changes something. A server started with `--percpu` or
    `--full-quicklook` must see that key turn the mode OFF — an override
    initialised to `false` would make the first press a no-op."""
    assert _run_render_probe(scenario)["effectiveArgs"] is None, "vacuous: no key pressed yet"

    after = _run_render_probe(scenario, key)["effectiveArgs"]
    assert after[flag] is False, f"{key!r} did not turn {flag} off: {after!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_toggle_view_key_is_reversible():
    assert _run_render_probe("default", "1")["effectiveArgs"]["percpu"] is True
    assert _run_render_probe("default", "1,1")["effectiveArgs"]["percpu"] is False


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_untouched_toggle_still_follows_the_server():
    """Only the pressed key is overridden. The others keep reading
    `serverArgs`, which is re-read on every tick — a viewer who never pressed
    `4` must still follow a server that has `--full-quicklook` on."""
    args = _run_render_probe("quicklook-full", "1")["effectiveArgs"]
    assert args["percpu"] is False, "`1` flipped the server's percpu=True"
    assert args["full_quicklook"] is True, "`4` was never pressed; it must still follow the server"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_footer_offers_hotkeys_before_github():
    """The keys are otherwise undiscoverable: nothing on the page says `h`
    exists. The link sits before GitHub, where a reader looking for what this
    page can do finds it before the external links."""
    about = _run_render_probe("default")["footerAbout"]
    assert "Hotkeys" in about, about
    assert about.index("Hotkeys") < about.index("GitHub")
    # It is the first thing after the version, not buried at the end.
    assert about[1] == "Hotkeys", about


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_footer_link_opens_the_same_overlay_as_h():
    """Both go through `toggleHelp()`, so the overlay they raise is the same
    one. Asserted on the RENDERED rows, not just the flag.

    NOTE on what this does and does not cover: the probe drives the method,
    because its fake document dispatches no events, so it cannot see the
    button's `@click` binding. That the button is bound to `toggleHelp` rather
    than setting `showHelp` itself is pinned in test_webui_v5_tokens.py
    (`test_the_footer_hotkeys_control_is_a_button_dressed_as_a_link`). The two
    tests together are the coverage; neither is sufficient alone.
    """
    by_click = _run_render_probe("default", "click:hotkeys")
    by_key = _run_render_probe("default", "h")

    assert by_click["showHelp"] is True
    assert by_click["helpRows"] == by_key["helpRows"]
    assert by_click["helpRows"], "vacuous: the overlay rendered no rows"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_footer_link_toggles_rather_than_only_opening():
    assert _run_render_probe("default", "click:hotkeys,click:hotkeys")["showHelp"] is False
    # And the two entry points are interchangeable, in either order.
    assert _run_render_probe("default", "click:hotkeys,h")["showHelp"] is False
    assert _run_render_probe("default", "h,click:hotkeys")["showHelp"] is False


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
@pytest.mark.parametrize(("key", "flag"), [("b", "byte"), ("6", "meangpu"), ("F", "fs_free_space")])
def test_a_data_type_key_flips_its_flag(key, flag):
    """2.X-c: `b`, `6` and `F` change HOW a value is shown. They ride the same
    override mechanism as the other TOGGLE VIEW keys."""
    before = _run_render_probe("default")
    assert before["effectiveArgs"] is None, "vacuous: no key pressed yet"

    after = _run_render_probe("default", key)["effectiveArgs"]
    assert flag in after, f"{key!r} published no {flag!r}: {sorted(after)!r}"
    assert _run_render_probe("default", f"{key},{key}")["effectiveArgs"][flag] == (not after[flag])


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_fs_free_space_key_starts_from_the_payload_not_from_serverargs():
    """`--fs-free-space` AND `[fs] free_space` both resolve into the fs
    plugin's own payload metadata, while /api/5/args dumps only the raw CLI
    namespace. Seeding `F` from `serverArgs` would therefore read `false` on a
    server whose CONFIG set it, and the first press would do nothing visible.
    """
    seeded = _run_render_probe("default", "F")["effectiveArgs"]["fs_free_space"]
    # The `default` fixture's fs payload carries no `free_space`, so the
    # effective value starts false and one press turns it on.
    assert seeded is True
