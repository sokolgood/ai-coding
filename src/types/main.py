from functools import cached_property
from typing import Literal

from jinja2 import Template
from pydantic import BaseModel

Role = Literal["system", "user", "assistant", "tool"]


class Prompt(BaseModel):
    text: str

    @cached_property
    def jinja_template(self) -> Template:
        return Template(self.text)

    def render(self, *args, **kwargs) -> str:
        return self.jinja_template.render(*args, **kwargs)


class PromptRoles(BaseModel):
    system: Prompt
    user: Prompt


class Message(BaseModel):
    role: Role
    content: str | None
    name: str | None = None
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None


class ToolResult(BaseModel):
    success: bool
    error: str | None = None
    content: str | None = None
