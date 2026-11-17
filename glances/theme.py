#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""The ``[outputs] theme`` option, shared by the TUI and the WebUI.

Three kinds of value:

* ``dark`` (default)
* ``light``, or its alias ``white``
* the path of a ``.css`` file: a user theme. The WebUI loads it, the TUI
  stays on ``dark`` (it is bound by the terminal's own palette).

A user theme is one block of ``--gl-*`` custom properties (see
``glances/outputs/static/css/glances.css`` and ``conf/sample_theme.css``).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_THEME = "dark"
# The name the WebUI gets for a user theme: it matches none of the shipped
# `data-theme` blocks, so only the dark defaults sit under the user's CSS.
CUSTOM_THEME = "custom"

_BUILTIN = {"dark": "dark", "light": "light", "white": "light"}

# A theme is a few dozen custom properties. The cap keeps a wrong path (a log
# file, a database) from being read whole and served to every WebUI client.
MAX_CSS_BYTES = 64 * 1024


def builtin_theme(value: Any) -> str | None:
    """Return ``dark`` or ``light`` for a built-in theme value, else None."""
    return _BUILTIN.get(str(value).strip().lower())


def tui_theme(value: Any) -> str:
    """Return ``dark`` or ``light``: a user theme (or a typo) is ``dark`` in the TUI."""
    return builtin_theme(value) or DEFAULT_THEME


def webui_theme(value: Any) -> dict[str, str | None]:
    """Resolve the theme the WebUI applies: ``{"name": ..., "css": ...}``.

    ``name`` is ``dark``, ``light`` or ``custom``; ``css`` holds the file's
    content for ``custom`` and is None otherwise. A path that cannot be used
    is logged and falls back to ``dark``, never to an unstyled page.
    """
    name = builtin_theme(value)
    if name is not None:
        return {"name": name, "css": None}
    path = str(value).strip()
    css = _read_css(path) if path else None
    if css is None:
        return {"name": DEFAULT_THEME, "css": None}
    return {"name": CUSTOM_THEME, "css": css}


def _read_css(value: str) -> str | None:
    path = Path(value).expanduser()
    if path.suffix.lower() != ".css":
        logger.warning("[outputs] theme is neither dark, light nor a .css file: using the dark theme")
        return None
    try:
        # `open()` inside the try: Snap's strict confinement refuses at open, not at read.
        with path.open("rb") as css_file:
            data = css_file.read(MAX_CSS_BYTES + 1)
        if len(data) > MAX_CSS_BYTES:
            logger.warning("[outputs] theme is larger than %d bytes: using the dark theme", MAX_CSS_BYTES)
            return None
        return data.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        logger.warning("[outputs] theme cannot be read: falling back to the dark theme")
        return None
