from typing import Any, Dict, Protocol, Tuple


class ContainersExtension(Protocol):
    def stop(self) -> None:
        raise NotImplementedError

    def update(self, all_tag) -> Tuple[Dict, list[Dict[str, Any]]]:
        raise NotImplementedError
