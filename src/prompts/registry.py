from functools import cached_property
from pathlib import Path

import yaml

from src.types.main import Prompt, PromptRoles


class PromptsRegistry:
    text2sql: PromptRoles

    def __init__(self, path: str):
        self.path = Path(path)
        self.prompts = self._load_prompts()

        self.coder = self._build_prompt_set("coder")
        self.reviewer = self._build_prompt_set("reviewer")
        self.fixer = self._build_prompt_set("fixer")

    @cached_property
    def _collection(self) -> dict:
        try:
            with self.path.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format in prompts file: {self.path}") from e

    def _load_prompts(self) -> dict:
        return self._collection

    def _build_prompt_set(self, name: str) -> PromptRoles:
        if name not in self.prompts:
            raise ValueError(f"Prompt '{name}' not found in YAML file.")

        data = self.prompts[name]
        return PromptRoles(system=Prompt(text=data["system"]), user=Prompt(text=data["user"]))
