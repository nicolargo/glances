#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the one place v5 reads its release and its API version from.

`glances/__init__.py` still serves v4 on `develop-v5` (its `__apiversion__`
mounts v4's `/api/4`), so v5 keeps its own pair until the merge
`develop-v5 → develop`: there, these two lines move into
`glances/__init__.py` and this module goes (architecture §10, Phase 4).
"""

__version__ = "5.0.0a1"
__apiversion__ = "5"
