from pathlib import Path

from openai import AsyncOpenAI

from src.prompts.registry import PromptsRegistry
from src.services.llm.engine import LLM


def create_llm(api_key: str, base_url: str | None = None) -> LLM:
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    return LLM(client)


def create_prompts_registry(prompts_path: str | None = None) -> PromptsRegistry:
    if prompts_path is None:
        base_path = Path(__file__).parent.parent.parent
        prompts_path = str(base_path / "prompts" / "prompts.yaml")

    return PromptsRegistry(prompts_path)
