#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

from typing import Any, Protocol


class ContainerEngineMonitor(Protocol):
    """
    Abstraction for any container engine monitor that needs to be supported by glances

    Each Monitor instance would be monitoring one instance of an engine. A system may contain multiple engine instances
    running parallely
    """

    def stop(self) -> None:
        raise NotImplementedError

    def update(self, all_tag) -> tuple[dict, list[dict[str, Any]]]:
        raise NotImplementedError
