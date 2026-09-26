#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — `--fetch` (mockups and decisions of 2026-09-26)."""

from __future__ import annotations

import io
import os
from pathlib import Path

import pytest

from glances import api_v5 as api
from glances.config_v5 import GlancesConfigV5
from glances.outputs import fetch_v5
from glances.outputs.curses_renderer_v5 import Cell, ColorRole, Row, render_plugin_rows
from glances.outputs.fetch_v5 import DEFAULT_TEMPLATE, FetchUI, render, visible_len

_TEMPLATES = Path(__file__).resolve().parent.parent / "conf" / "fetch-templates"


@pytest.fixture(autouse=True)
def _hermetic_config(tmp_path, monkeypatch):
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    for key in list(os.environ):
        if key.startswith("GLANCES_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture(scope="module")
def gl():
    with api.GlancesAPI(
        plugins=["system", "ip", "uptime", "quicklook", "mem", "load", "network", "fs", "processlist"]
    ) as instance:
        yield instance


# ------------------------------------------------------------- painting


def test_the_tui_roles_become_the_tui_ansi_colours():
    """Green, blue, magenta (the maintainer kept it), red; titles bold."""
    ui = FetchUI(gl=None, color=True)
    cells = [
        Cell(text=role.value, color=role)
        for role in (ColorRole.OK, ColorRole.CAREFUL, ColorRole.WARNING, ColorRole.CRITICAL, ColorRole.HEADER)
    ]
    painted = ui._paint(Row(cells=cells))
    for code, text in (("32", "ok"), ("34", "careful"), ("35", "warning"), ("31", "critical"), ("1", "header")):
        assert f"\x1b[{code}m{text}\x1b[0m" in painted


def test_prominent_is_the_filled_badge_and_glue_has_no_space():
    ui = FetchUI(gl=None, color=True)
    painted = ui._paint(
        Row(cells=[Cell("/usr/bin/"), Cell("python3", glue=True), Cell("99%", ColorRole.CRITICAL, prominent=True)])
    )
    assert "/usr/bin/python3 " in painted
    assert "\x1b[31;7m99%\x1b[0m" in painted


def test_no_colour_means_no_escape():
    ui = FetchUI(gl=None, color=False)
    assert ui._paint(Row(cells=[Cell("x", ColorRole.CRITICAL, bold=True)])) == "x"
    assert ui.title("MEM") == "MEM" and ui.color("1", "critical") == "1"


# ---------------------------------------------------------------- blocks


def test_a_block_is_the_tui_block(gl):
    """Drawn by the renderer the TUI uses, not by a copy of it."""
    ui = FetchUI(gl, color=False)
    payload = gl._payload("mem")
    rows = render_plugin_rows("mem", payload, gl.mem.fields, False, {"unicode": True})
    expected = "\n".join(ui._paint(row) for row in rows)
    assert ui.block("mem").split("\n")[0].split()[0] == "MEM"
    assert len(ui.block("mem").split("\n")) == len(expected.split("\n"))


def test_an_absent_plugin_is_an_empty_block(gl):
    assert FetchUI(gl, color=False).block("cpu") == ""


def test_row_puts_blocks_side_by_side_and_leaves_out_what_does_not_fit(gl):
    wide = FetchUI(gl, color=False, width=400).row("mem", "load")
    assert "MEM" in wide.split("\n")[0] and "LOAD" in wide.split("\n")[0]
    mem_width = max(visible_len(line) for line in FetchUI(gl, color=False).block("mem").split("\n"))
    narrow = FetchUI(gl, color=False, width=mem_width + 3).row("mem", "load")
    assert "LOAD" not in narrow


def test_max_rows_cuts_a_long_block(gl):
    assert len(FetchUI(gl, color=False).row("fs", max_rows=2).split("\n")) <= 2


def test_rule_is_the_tui_separator_or_ascii(gl):
    assert FetchUI(gl, width=5).rule() == "─────"
    assert FetchUI(gl, width=5, unicode=False).rule() == "-----"


def test_ascii_mode_draws_ascii_quicklook_bars(gl):
    text = FetchUI(gl, color=False, unicode=False).block("quicklook")
    assert "▪" not in text and "[" in text


def test_top_lists_processes_without_this_one(gl):
    text = FetchUI(gl, color=False).top(limit=3)
    assert text.split("\n")[0].startswith("TOP CPU")
    assert "TOP MEM" in text.split("\n")[0]
    assert len(text.split("\n")) <= 4


# -------------------------------------------------------------- templates


def test_the_default_template_renders(gl):
    text = render(DEFAULT_TEMPLATE, gl, FetchUI(gl, color=False))
    assert "MEM" in text and "TOP CPU" in text and "─" in text


@pytest.mark.parametrize("name", ["short.jinja", "with-logo.jinja"])
def test_the_shipped_templates_render(name, gl):
    text = render((_TEMPLATES / name).read_text(), gl, FetchUI(gl, color=False))
    assert "LOAD" in text


def test_an_undefined_name_fails_loudly(gl):
    import jinja2

    with pytest.raises(jinja2.UndefinedError):
        render("{{ nope }}", gl, FetchUI(gl, color=False))


# -------------------------------------------------------------------- run


def test_run_prints_the_default_summary_without_escapes_when_piped():
    out, err = io.StringIO(), io.StringIO()
    assert fetch_v5.run(None, None, out=out, err=err, wait=0) == 0
    assert "\x1b" not in out.getvalue()
    assert "MEM" in out.getvalue()


def test_a_v4_template_fails_with_a_hint(tmp_path):
    """v4 templates break on purpose (maintainer, 2026-09-26): say why."""
    template = tmp_path / "v4.jinja"
    template.write_text("{% for n in gl.network.keys() %}{{ gl.network[n]['bytes_recv_rate_per_sec'] }}{% endfor %}")
    out, err = io.StringIO(), io.StringIO()
    assert fetch_v5.run(None, str(template), out=out, err=err, wait=0) == 2
    assert "bytes_recv_rate_per_sec" in err.getvalue()
    assert "v4 templates need updating" in err.getvalue()
    assert out.getvalue() == ""


def test_a_missing_template_file_is_reported(tmp_path):
    err = io.StringIO()
    assert fetch_v5.run(None, str(tmp_path / "nope.jinja"), out=io.StringIO(), err=err, wait=0) == 2
    assert "cannot read" in err.getvalue()


# -------------------------------------------------------------------- CLI


def test_fetch_flags_parse_with_their_v4_aliases():
    from glances.main_v5 import build_parser

    args = build_parser().parse_args(["--stdout-fetch", "--stdout-fetch-template", "t.jinja"])
    assert args.fetch is True and args.fetch_template == "t.jinja"


@pytest.mark.parametrize("extra", [["-s"], ["--stdout", "cpu"], ["--memory-leak"], ["--issue"]])
def test_fetch_runs_on_its_own(extra):
    from glances.main_v5 import build_parser, validate_args

    with pytest.raises(SystemExit):
        validate_args(build_parser().parse_args(["--fetch", *extra]))


def test_a_template_needs_fetch():
    from glances.main_v5 import build_parser, validate_args

    with pytest.raises(SystemExit):
        validate_args(build_parser().parse_args(["--fetch-template", "t.jinja"]))
