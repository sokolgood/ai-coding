from abc import ABC, abstractmethod

from src.prompts.registry import PromptsRegistry
from src.services.llm.engine import LLM
from src.types.main import Message


class Agent(ABC):
    def __init__(self, llm: LLM, prompts_registry: PromptsRegistry) -> None:
        self.llm = llm
        self.prompts_registry = prompts_registry

    @abstractmethod
    async def run(self, input: str) -> str:
        raise NotImplementedError

    async def __call__(self, input: str) -> str:
        return await self.run(input=input)

    def _resolve_context(self) -> list[Message]:
        raise NotImplementedError
