#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Jeongwoo Kim <corc411@gmail.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Regression tests for WebUI template rendering."""

# pylint: disable=invalid-name,protected-access,too-few-public-methods

from types import SimpleNamespace

from fastapi.templating import Jinja2Templates

from glances.outputs.glances_restful_api import GlancesRestfulApi


class QueryParamsStub(dict):
    """Provide the subset of request query params used by the handlers."""

    def get(self, key, default=None):
        """Mirror dict.get for request stub compatibility."""
        return super().get(key, default)


class OldStyleTemplates:
    """Mimic the legacy Starlette TemplateResponse signature."""

    def __init__(self):
        self.calls = []

    def TemplateResponse(self, name, context):
        """Record legacy TemplateResponse calls."""
        self.calls.append((name, context))
        return context


class NewStyleTemplates:
    """Mimic the current Starlette TemplateResponse signature."""

    def __init__(self):
        self.calls = []

    def TemplateResponse(self, request, name, context=None):
        """Record request-first TemplateResponse calls."""
        self.calls.append((request, name, context))
        return context


def make_api(templates):
    """Build a lightweight GlancesRestfulApi instance for template tests."""
    api = GlancesRestfulApi.__new__(GlancesRestfulApi)
    api._templates = templates
    api.args = SimpleNamespace(time='3')
    return api


def test_template_response_supports_old_starlette_signature():
    """Use the legacy signature when the template backend expects it."""
    api = make_api(OldStyleTemplates())
    request = object()
    context = {"request": request, "refresh_time": "5"}

    assert api._template_response_requires_request() is False  # nosec B101
    assert api._template_response(request, "index.html", context) == context  # nosec B101
    assert api._templates.calls == [("index.html", context)]  # nosec B101


def test_template_response_supports_new_starlette_signature():
    """Use the request-first signature when the backend requires it."""
    api = make_api(NewStyleTemplates())
    request = object()
    context = {"request": request, "refresh_time": "5"}

    assert api._template_response_requires_request() is True  # nosec B101
    assert api._template_response(request, "index.html", context) == context  # nosec B101
    assert api._templates.calls == [(request, "index.html", context)]  # nosec B101


def test_index_uses_template_helper_for_new_starlette_signature():
    """Route the index view through the compatibility helper."""
    api = make_api(NewStyleTemplates())
    request = SimpleNamespace(query_params=QueryParamsStub(refresh='7'))

    response = api._index(request)

    assert response["refresh_time"] == '7'  # nosec B101
    assert api._templates.calls == [  # nosec B101
        (request, "index.html", {"request": request, "refresh_time": '7'})
    ]


def test_browser_uses_template_helper_for_old_starlette_signature():
    """Keep browser view rendering compatible with the legacy signature."""
    api = make_api(OldStyleTemplates())
    request = SimpleNamespace(query_params=QueryParamsStub())

    response = api._browser(request)

    assert response["refresh_time"] == 3  # nosec B101
    assert api._templates.calls == [  # nosec B101
        ("browser.html", {"request": request, "refresh_time": 3})
    ]


def test_index_renders_with_installed_jinja2_templates(tmp_path):
    """Render the index view with the installed Jinja2Templates backend."""
    (tmp_path / "index.html").write_text(
        "refresh={{ refresh_time }}", encoding="utf-8"
    )
    api = make_api(Jinja2Templates(directory=tmp_path))
    request = SimpleNamespace(query_params=QueryParamsStub(refresh='9'))

    response = api._index(request)

    assert response.template.name == "index.html"  # nosec B101
    assert response.context["request"] is request  # nosec B101
    assert response.context["refresh_time"] == '9'  # nosec B101
