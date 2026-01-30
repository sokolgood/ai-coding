from abc import ABC, abstractmethod
from typing import Any

from src.types.main import ToolResult


class Tool(ABC):
    name: str = "base-tool"
    description: str = "Base Tool Description"

    @abstractmethod
    def json(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def run(self, **kwargs) -> ToolResult:
        raise NotImplementedError

    async def __call__(self, **kwargs) -> ToolResult:
        return await self.run(**kwargs)
