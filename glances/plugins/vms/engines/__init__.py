#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

from typing import Any, Dict, List, Protocol, Tuple


class VmsExtension(Protocol):
    def stop(self) -> None:
        raise NotImplementedError

    def update(self, all_tag) -> Tuple[Dict, List[Dict[str, Any]]]:
        raise NotImplementedError
