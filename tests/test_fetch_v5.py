#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — `--fetch`: v4's layout in the TUI's colours (maintainer, 2026-09-27)."""

from __future__ import annotations

import io
import os
from pathlib import Path

import pytest

from glances import api_v5 as api
from glances.config_v5 import GlancesConfigV5
from glances.outputs import fetch_v5
from glances.outputs.fetch_v5 import DEFAULT_TEMPLATE, FetchUI, render, visible_len

_TEMPLATES = Path(__file__).resolve().parent.parent / "conf" / "fetch-templates"
_PLUGINS = ["system", "ip", "uptime", "core", "cpu", "mem", "load", "network", "fs", "processlist"]


@pytest.fixture(autouse=True)
def _hermetic_config(tmp_path, monkeypatch):
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    for key in list(os.environ):
        if key.startswith("GLANCES_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture(scope="module")
def gl():
    with api.GlancesAPI(plugins=_PLUGINS) as instance:
        yield instance


@pytest.fixture
def critical_mem(tmp_path):
    """MEM above its critical threshold whatever the host: the colour must follow."""
    conf = tmp_path / "critical.conf"
    conf.write_text("[mem]\ncareful=0.001\nwarning=0.002\ncritical=0.003\n")
    with api.GlancesAPI(config_path=str(conf), plugins=["mem"]) as instance:
        yield instance


# --------------------------------------------------------------- colours


def test_a_value_takes_the_colour_of_its_level(critical_mem):
    ui = FetchUI(critical_mem, color=True)
    assert ui.level("mem", "percent") == "critical"
    assert ui.percent("mem", "percent").startswith("\x1b[31m")
    assert ui.bar("mem", "percent").startswith("\x1b[31m")


@pytest.mark.parametrize(("level", "code"), [("ok", "32"), ("careful", "34"), ("warning", "35"), ("critical", "31")])
def test_the_levels_are_the_tui_ansi_colours(level, code):
    """Green, blue, magenta (kept by the maintainer), red."""
    assert FetchUI(None, color=True).color("x", level) == f"\x1b[{code}mx\x1b[0m"


def test_titles_are_bold_and_no_level_means_no_colour():
    ui = FetchUI(None, color=True)
    assert ui.title("MEM") == "\x1b[1mMEM\x1b[0m"
    assert ui.color("x", None) == "x"


def test_no_colour_means_no_escape(critical_mem):
    ui = FetchUI(critical_mem, color=False)
    assert "\x1b" not in ui.percent("mem", "percent") + ui.bar("mem", "percent") + ui.title("MEM")


# ---------------------------------------------------------------- helpers


def test_bar_is_v4s_bar_and_ascii_without_unicode(gl):
    assert set(FetchUI(gl, color=False).bar("mem", "percent")) <= {"■", "□"}
    assert set(FetchUI(gl, color=False, unicode=False).bar("mem", "percent")) <= {"#", "-"}
    assert len(FetchUI(gl, color=False).bar("mem", "percent", size=10)) == 10


def test_a_collection_value_is_read_per_item(gl):
    ui = FetchUI(gl, color=False)
    mount = gl.fs.keys()[0]
    assert ui.percent("fs", "percent", mount) == f"{gl.fs[mount]['percent']:.1f}%"


def test_bits_is_the_tui_network_unit(gl):
    ui = FetchUI(gl, color=False)
    iface = gl.network.keys()[0]
    assert ui.bits("network", "bytes_recv", iface).endswith("b")


def test_pad_ignores_colour_escapes():
    ui = FetchUI(None, color=True)
    padded = ui.pad(ui.color("12.3", "ok"), 8)
    assert visible_len(padded) == 8
    assert FetchUI(None, color=False).pad("a-very-long-process-name", 5) == "a-ver"


def test_rule_is_v4s_heavy_rule_or_ascii():
    assert FetchUI(None).rule(3) == "━━━"
    assert FetchUI(None, unicode=False).rule(3) == "==="


def test_uptime_is_formatted_as_the_tui_header(gl):
    assert FetchUI(gl, color=False).uptime()[-1] == "s"


# -------------------------------------------------------------- templates


def test_the_default_template_is_v4s_layout(gl):
    text = render(DEFAULT_TEMPLATE, gl, FetchUI(gl, color=False))
    for marker in (
        "✨",
        "💡 LOAD",
        "⚡ CPU",
        "🧠 MEM",
        "💾 DISK",
        "📡 NET",
        "🔥 TOP PROCESS by CPU",
        "🔥 TOP PROCESS by MEM",
    ):
        assert marker in text, marker
    assert text.startswith("━")


@pytest.mark.parametrize("name", ["short.jinja", "with-logo.jinja"])
def test_the_shipped_templates_render(name, gl):
    assert "⚡ CPU" in render((_TEMPLATES / name).read_text(), gl, FetchUI(gl, color=False))


def test_an_undefined_name_fails_loudly(gl):
    import jinja2

    with pytest.raises(jinja2.UndefinedError):
        render("{{ nope }}", gl, FetchUI(gl, color=False))


# -------------------------------------------------------------------- run


def test_run_prints_the_summary_without_escapes_when_piped():
    out, err = io.StringIO(), io.StringIO()
    assert fetch_v5.run(None, None, out=out, err=err, wait=0) == 0
    assert "\x1b" not in out.getvalue()
    assert "🧠 MEM" in out.getvalue()


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
