#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — `--api-restful-doc` (maintainer decision, 2026-09-26)."""

from __future__ import annotations

import io
import json
import os
from typing import Any, ClassVar

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.outputs import restful_doc_v5
from glances.plugins.plugin.base_v5 import GlancesPluginBase


@pytest.fixture
def config(tmp_path, monkeypatch):
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    for key in list(os.environ):
        if key.startswith("GLANCES_"):
            monkeypatch.delenv(key, raising=False)
    return GlancesConfigV5()


class _Disk(GlancesPluginBase[list]):
    plugin_name: ClassVar[str] = "fakedisk"
    IS_COLLECTION: ClassVar[bool] = True
    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "name": {"description": "Disk *name*, e.g. sda_1.", "unit": "string", "primary_key": True},
        "percent": {
            "description": "Used space.",
            "unit": "percent",
            "history": True,
            "watched": True,
            "default_thresholds": {"careful": 50.0, "warning": 70.0, "critical": 90.0},
        },
    }

    async def _grab_stats(self) -> list:
        return [{"name": f"sd{c}", "percent": 12.5} for c in "abcd"]


@pytest.fixture
def page(config, monkeypatch):
    """The page for one fake plugin, generated the way `make docs` does."""
    from glances import main_v5

    monkeypatch.setattr(main_v5, "discover_plugins", lambda store, cfg: [_Disk(store, cfg)])
    out = io.StringIO()
    assert restful_doc_v5.run(config, out=out, wait=0) == 0
    return out.getvalue()


def test_the_page_parses_without_a_docutils_warning(page):
    import docutils.core

    warnings = io.StringIO()
    docutils.core.publish_doctree(page, settings_overrides={"report_level": 2, "warning_stream": warnings})
    assert warnings.getvalue() == ""


def test_the_route_index_is_the_openapi_schema(page, config):
    """A route added, renamed or removed changes the page."""
    from glances.stats_store_v5 import StatsStoreV5
    from glances.webserver_v5 import build_app

    schema = build_app(config=config, store=StatsStoreV5()).openapi()
    for path in schema["paths"]:
        assert f"``{path}``" in page, path


def test_examples_are_real_responses(page):
    block = page.split("# curl http://localhost:61208/api/5/pluginslist\n", 1)[1].split("\n\n", 1)[0]
    assert json.loads(block) == ["fakedisk"]


def test_a_plugin_section_has_its_payload_fields_limits_and_history(page):
    section = page.split("GET fakedisk\n", 1)[1]
    assert '"name": "sda"' in section
    assert '"... 2 more"' in section, "a collection example keeps two items"
    assert "* ``percent``: Used space. (unit is *percent*)" in section
    assert "curl http://localhost:61208/api/5/fakedisk/limits" in section
    assert "curl http://localhost:61208/api/5/fakedisk/history?nb=2" in section


def test_descriptions_are_escaped(page):
    assert r"Disk \*name\*, e.g. sda\_1." in page


def test_the_page_documents_api_5_not_4(page):
    assert "/api/4" not in page
    assert "glances-v5 -s" in page


def test_restful_doc_flag_and_its_exclusions():
    from glances.main_v5 import build_parser, validate_args

    assert build_parser().parse_args(["--api-restful-doc"]).api_restful_doc is True
    for extra in (["-s"], ["--fetch"], ["--issue"], ["--stdout", "cpu"]):
        with pytest.raises(SystemExit):
            validate_args(build_parser().parse_args(["--api-restful-doc", *extra]))
