from abc import ABC, abstractmethod
from typing import Any

__all__ = ["Repository"]


class Repository(ABC):
    @abstractmethod
    async def get(self, **filters: Any) -> Any:
        pass

    @abstractmethod
    async def add_access_key(self, email: str | None) -> bool:
        pass
