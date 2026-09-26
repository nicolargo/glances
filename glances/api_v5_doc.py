#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — generate ``docs/api/python.rst`` from the Python API itself.

Run by ``make docs`` (design 2026-09-26 §5.7), not a user-facing option:

    python -m glances.api_v5_doc -C conf/glances.conf > docs/api/python.rst

Every example is a real read on the machine that builds the docs, as v4's
generator did, and every field list comes from the plugin's own
``fields_description``, so the page cannot drift from the code.
"""

from __future__ import annotations

import argparse
import inspect
from collections.abc import Callable
from pprint import pformat
from typing import Any

from glances.api_v5 import GlancesAPI, PluginView

# The import users write. Becomes `from glances import api` at the merge,
# when api_v5 replaces the v4 module (design §1, decision 3).
_IMPORT = "from glances import api_v5 as api"

_HEADER = """\
.. _api:

Python API documentation
========================

This page describes the Glances v5 Python API. Every example below is a real
read, taken when the page was generated.

.. note::

    During the Glances 5 alphas the module is ``glances.api_v5``. It becomes
    ``glances.api`` with Glances 5.0.0, replacing the Glances 4 API.
"""

_MODES = """\
On demand, or in the background
-------------------------------

By default the API collects **on demand**: reading ``gl.<plugin>`` updates
that plugin when its last update is older than ``[global] refresh`` (2 seconds
by default), and nothing runs between two reads. That suits a script.

With ``background=True`` the Glances scheduler runs in a thread: the stats stay
fresh, and the history and the alerts fill up between reads. That suits a
notebook or a long-running tool.

.. code-block:: python

    >>> with api.GlancesAPI(background=True) as gl:
    ...     time.sleep(60)
    ...     gl.cpu.history(nb=30)
    ...     gl.alerts()

In both modes the API reads ``glances.conf`` as Glances does (``config_path``
adds a file on top), never the command line of the script that uses it.
``plugins=["cpu", "mem"]`` builds only those plugins, plus what they depend
on. Alerts are recorded, but the actions ``glances.conf`` configures for them
never run, and no exporter is started.

Close the API when done, or use it as a context manager: some plugins hold
background resources until then.
"""

_VIEWS = """\
Plugin views
------------

``gl.<plugin>`` returns a read-only snapshot of the plugin, taken when it was
read. It is a mapping: ``[]``, ``get``, ``keys``, ``items``, ``len``, ``in``.
A collection plugin (network interfaces, file systems, processes...) is keyed
by its primary key; a scalar plugin by its field names.

* ``raw``: the payload, as ``/api/5/<plugin>`` serves it
* ``fields``: each field's description and unit
* ``limits``: the thresholds in effect
* ``levels``: the alert level of each watched field
* ``history()``: the recorded history, as ``/api/5/<plugin>/history`` serves it

Changing a view changes nothing Glances, or a later read, sees. Read
``gl.<plugin>`` again for fresh values.
"""


def _escape(text: str) -> str:
    """Make free text inert in RST (a stray `*` or `_` is markup there)."""
    for char in ("\\", "*", "`", "_", "|"):
        text = text.replace(char, "\\" + char)
    return text


def _title(text: str, underline: str = "-") -> list[str]:
    return [text, underline * len(text), ""]


def _code(lines: list[str], language: str = "python") -> list[str]:
    return [f".. code-block:: {language}", ""] + ["    " + line for line in "\n".join(lines).split("\n")] + [""]


def _tldr(gl: GlancesAPI) -> list[str]:
    net = gl.network
    first = net.keys()[0] if len(net) else None
    lines = [
        f">>> {_IMPORT}",
        ">>> gl = api.GlancesAPI()",
        ">>> gl.cpu",
        pformat(dict(gl.cpu)),
        '>>> gl.cpu["total"]',
        repr(gl.cpu["total"]),
        '>>> gl.mem["used"]',
        repr(gl.mem["used"]),
        '>>> gl.auto_unit(gl.mem["used"])',
        repr(gl.auto_unit(gl.mem["used"])),
        ">>> gl.network.keys()",
        repr(net.keys()),
    ]
    if first is not None:
        lines += [f'>>> gl.network["{first}"]', pformat(net[first])]
    return _title("TL;DR") + _code(lines)


def _reference() -> list[str]:
    """Signature and docstring of every public name, straight from the code."""
    out = _title("Reference")
    members: list[tuple[str, Callable[..., Any] | type]] = [("GlancesAPI", GlancesAPI)]
    members += [
        (f"GlancesAPI.{name}", member)
        for name, member in inspect.getmembers(GlancesAPI, inspect.isfunction)
        if not name.startswith("_")
    ]
    members += [("PluginView", PluginView), ("PluginView.history", PluginView.history)]
    for name, member in members:
        target = member.__init__ if inspect.isclass(member) else member
        signature = str(inspect.signature(target)).replace("(self, ", "(").replace("(self)", "()")
        out += _code([f"{name}{signature}"])
        out += _code((inspect.getdoc(member) or "").split("\n"), language="text")
    return out


def _plugin(gl: GlancesAPI, name: str) -> list[str]:
    view = getattr(gl, name)
    out = _title(f"Glances {name}")
    if isinstance(view.raw, list):
        keys = view.keys()
        lines = [f">>> gl.{name}.keys()", pformat(keys, compact=True)]
        if keys:
            lines += [f">>> gl.{name}[{keys[0]!r}]", pformat(view[keys[0]])]
    else:
        lines = [f">>> gl.{name}", pformat(dict(view))]
    out += _code(lines)
    if view.fields:
        out += [f"{name.capitalize()} fields:", ""]
        for field, schema in view.fields.items():
            unit = schema.get("unit")
            description = _escape(str(schema.get("description", "")).strip())
            out.append(f"* ``{field}``: {description}" + (f" (unit is *{_escape(unit)}*)" if unit else ""))
        out.append("")
    if view.limits:
        out += [f"{name.capitalize()} limits:", ""]
        out += _code([f">>> gl.{name}.limits", pformat(view.limits)])
    return out


def _helpers(gl: GlancesAPI) -> list[str]:
    out = _title("Helpers")
    out += ["Human-readable units, as the terminal interface shows them:", ""]
    out += _code(['>>> gl.auto_unit(gl.mem["used"])', repr(gl.auto_unit(gl.mem["used"]))])
    out += ["A percentage as a text bar:", ""]
    out += _code(['>>> gl.bar(gl.mem["percent"])', repr(gl.bar(gl.mem["percent"]))])
    if "processlist" in gl.plugins():
        out += ["The top processes (the API's own process is left out):", ""]
        top = [{k: p.get(k) for k in ("pid", "name", "cpu_percent", "memory_percent")} for p in gl.top_process()]
        out += _code([">>> gl.top_process()", pformat(top)])
    return out


def render(gl: GlancesAPI) -> str:
    """The whole ``python.rst`` page, from reads on `gl`."""
    lines = [_HEADER]
    lines += _tldr(gl)
    lines += [_MODES, _VIEWS]
    lines += _title("Plugins list")
    lines += _code([">>> gl.plugins()", pformat(gl.plugins(), compact=True)])
    for name in gl.plugins():
        lines += _plugin(gl, name)
    lines += _helpers(gl)
    lines += _reference()
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Print docs/api/python.rst for the Glances v5 Python API.")
    parser.add_argument("-C", "--config", dest="config_path", help="Path to an additional glances.conf file.")
    args = parser.parse_args()
    with GlancesAPI(config_path=args.config_path) as gl:
        print(render(gl), end="")


if __name__ == "__main__":
    main()
