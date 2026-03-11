from abc import ABC, abstractmethod
from typing import Any, List

from hmi.models.tag_models import TagDefinition


class BasePlcDriver(ABC):
    @abstractmethod
    def connect(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_connected(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def read_tags(self, tags: List[TagDefinition]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def write_tag(self, tag: TagDefinition, value: Any) -> bool:
        raise NotImplementedError