from abc import ABC, abstractmethod
from typing import Any

__all__ = ["Repository"]


class Repository(ABC):
    @abstractmethod
    async def get(self, **filters: Any) -> Any:
        pass

    @abstractmethod
    async def set(self, key: str, value: str) -> Any:
        pass
