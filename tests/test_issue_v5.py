#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — `--issue` (mockups validated by the maintainer, 2026-09-26)."""

from __future__ import annotations

import io
import json
import re
from typing import Any, ClassVar

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.outputs import issue_v5
from glances.outputs.issue_v5 import REDACTED, Environment, PluginResult, excerpt, redact, render
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5

# ---------------------------------------------------------------- redaction


def test_identifying_fields_are_redacted_per_plugin():
    assert redact("system", {"hostname": "box", "os_name": "Linux"}) == {"hostname": REDACTED, "os_name": "Linux"}
    assert redact("ip", {"address": "10.0.0.2", "mask": "255.255.255.0"})["address"] == REDACTED
    assert redact("folders", [{"path": "/home/alice", "size": 1}]) == [{"path": REDACTED, "size": 1}]
    assert redact("ports", [{"host": "10.0.0.1", "port": 22}])[0]["host"] == REDACTED


def test_a_command_line_keeps_its_program_name_only():
    item = {"name": "python", "username": "alice", "cmdline": ["/usr/bin/python3", "-m", "secret"]}
    assert redact("processlist", [item]) == [{"name": "python", "username": REDACTED, "cmdline": ["python3", REDACTED]}]
    assert redact("processlist", [{"cmdline": ["/bin/sleep"]}]) == [{"cmdline": ["sleep"]}]


def test_empty_values_stay_empty_and_other_plugins_are_untouched():
    assert redact("ip", {"public_address": None}) == {"public_address": None}
    assert redact("cpu", {"total": 1.0, "hostname": "not-a-real-field"}) == {
        "total": 1.0,
        "hostname": "not-a-real-field",
    }


def test_excerpt_keeps_the_first_item_of_a_list():
    assert excerpt([1, 2, 3]) == [1, "... 2 more"]
    assert excerpt([1]) == [1]
    assert excerpt({"a": 1}) == {"a": 1}


# ---------------------------------------------------------------- rendering


def _report(results, warnings=()):
    return render(Environment(rows=[("Glances", "5.0.0a1 (v5)"), ("OS", "Linux")]), list(results), list(warnings))


def test_the_report_is_markdown_without_ansi_escapes():
    text = _report([PluginResult("cpu", "ok", 0.001, payload={"total": 1.0})])
    assert "\x1b" not in text
    assert text.startswith("## Glances --issue report")
    assert "| Component | Version |" in text and "| Plugin | Status | Update | Items |" in text


def test_errors_come_first_then_update_time():
    text = _report(
        [
            PluginResult("fast", "ok", 0.001),
            PluginResult("slow", "ok", 0.010),
            PluginResult("broken", "error", 0.0001, error="OSError: nope (x.py:3)"),
        ]
    )
    rows = [line.split("|")[1].strip() for line in text.splitlines() if re.match(r"\| (fast|slow|broken) ", line)]
    assert rows == ["broken", "slow", "fast"]
    assert "ERROR: OSError: nope (x.py:3)" in text


def test_disabled_plugins_share_one_row():
    text = _report(
        [PluginResult("vms", "disabled"), PluginResult("cloud", "disabled"), PluginResult("cpu", "ok", 0.001)]
    )
    assert "| cloud, vms | disabled | | |" in text
    assert "1 OK, 2 disabled, 0 error" in text


def test_warnings_are_listed_and_cells_are_escaped():
    text = _report([PluginResult("cpu", "ok", 0.001)], ["glances.x: key 'a|b' unrecognised"])
    assert "**Warnings logged during the run (1)**" in text
    assert "- glances.x: key 'a\\|b' unrecognised" in text


def test_payloads_are_folded_redacted_and_valid_json():
    text = _report([PluginResult("system", "ok", 0.001, payload={"hostname": "box", "os_name": "Linux"})])
    assert "<details><summary>" in text
    body = text.split("```json\n", 1)[1].split("\n```", 1)[0]
    assert json.loads(body) == {"system": {"hostname": REDACTED, "os_name": "Linux"}}


# ---------------------------------------------------------------- the run


class _Ok(GlancesPluginBase[dict]):
    plugin_name: ClassVar[str] = "fakeok"
    IS_COLLECTION: ClassVar[bool] = False
    fields_description: ClassVar[dict[str, dict[str, Any]]] = {"value": {"description": "v", "unit": "number"}}
    stopped = False

    async def _grab_stats(self) -> dict:
        import logging

        logging.getLogger("glances.fake").warning("unrecognised threshold key 'rx_careful'")
        return {"value": 1}

    def stop(self) -> None:
        type(self).stopped = True


class _Broken(GlancesPluginBase[dict]):
    plugin_name: ClassVar[str] = "fakebroken"
    IS_COLLECTION: ClassVar[bool] = False
    fields_description: ClassVar[dict[str, dict[str, Any]]] = {"value": {"description": "v", "unit": "number"}}

    async def _grab_stats(self) -> dict:
        raise PermissionError("no access to /dev/thing")


@pytest.fixture
def config(tmp_path, monkeypatch):
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


def test_a_run_reports_each_plugin_with_the_real_exception(config):
    store = StatsStoreV5()
    out, err = io.StringIO(), io.StringIO()
    plugins = [_Ok(store, config), _Broken(store, config)]
    assert issue_v5.run(plugins, ["vms"], "5.0.0a1", [], out=out, err=err, wait=0) == 0
    text = out.getvalue()
    assert "| fakeok | OK |" in text
    assert re.search(r"\| fakebroken \| ERROR: PermissionError: no access to /dev/thing \(\S+\.py:\d+\) \|", text)
    assert "| vms | disabled | | |" in text
    # The warning is reported once, though logged on both cycles; the
    # swallowed update failure is in the table, not in the warnings.
    assert text.count("unrecognised threshold key") == 1
    assert "update failed" not in text


def test_progress_goes_to_stderr_and_only_the_report_to_stdout(config):
    out, err = io.StringIO(), io.StringIO()
    issue_v5.run([_Ok(StatsStoreV5(), config)], [], "5.0.0a1", [], out=out, err=err, wait=0)
    assert out.getvalue().startswith("## Glances --issue report")
    assert "testing 1 plugins" in err.getvalue()
    assert "Review it before posting." in err.getvalue()


def test_a_run_stops_the_plugins(config):
    _Ok.stopped = False
    issue_v5.run([_Ok(StatsStoreV5(), config)], [], "5.0.0a1", [], out=io.StringIO(), err=io.StringIO(), wait=0)
    assert _Ok.stopped


# ---------------------------------------------------------------- the CLI


def test_issue_flag_parses():
    from glances.main_v5 import build_parser

    assert build_parser().parse_args([]).issue is False
    assert build_parser().parse_args(["--issue"]).issue is True


@pytest.mark.parametrize("extra", [["-s"], ["--stdout", "cpu"], ["--memory-leak"]])
def test_issue_runs_on_its_own(extra):
    from glances.main_v5 import build_parser, validate_args

    with pytest.raises(SystemExit):
        validate_args(build_parser().parse_args(["--issue", *extra]))


def test_run_issue_builds_what_glances_v5_builds(config, monkeypatch):
    """Enabled plugins are tested, disabled ones listed, `--disable-plugin` honoured."""
    from glances import main_v5

    seen = {}
    monkeypatch.setattr(
        issue_v5,
        "run",
        lambda plugins, disabled, version, sources: (
            seen.update(plugins=[p.plugin_name for p in plugins], disabled=disabled, version=version) or 0
        ),
    )
    assert main_v5.run_issue(main_v5.build_parser().parse_args(["--issue", "--disable-plugin", "cpu"]), config) == 0
    assert "mem" in seen["plugins"] and "cpu" not in seen["plugins"]
    assert "cpu" in seen["disabled"]
    assert seen["version"] == main_v5._VERSION
