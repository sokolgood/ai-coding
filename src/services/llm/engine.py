from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel

from src.services.llm.tools.base import Tool
from src.types.main import Message

console = Console()


class LLM:
    def __init__(self, allm_client: AsyncOpenAI) -> None:
        self.allm_client = allm_client

    async def invoke(
        self,
        messages: list[Message],
        model: str,
        tools: list[Tool] | None = None,
        response_format: BaseModel | None = None,
        **kwargs,
    ) -> ChatCompletion:
        request_params = {
            "messages": self._serialize(messages),
            "model": model,
            **kwargs,
        }

        if tools:
            request_params["tools"] = [tool.json() for tool in tools]
            request_params["tool_choice"] = "auto"

        if response_format:
            request_params["response_format"] = {
                "type": "json_schema",
                "json_schema": {"schema": response_format.model_json_schema()},
            }

        console.print(f"[bold blue]🤖 LLM Request[/bold blue] model={model}, tools={len(tools) if tools else 0}")
        if tools:
            tool_names = [tool.name for tool in tools]
            console.print(f"[dim]Available tools: {', '.join(tool_names)}[/dim]")

        completion = await self.allm_client.chat.completions.create(**request_params)

        message = completion.choices[0].message
        tool_calls_count = len(message.tool_calls) if message.tool_calls else 0
        content_preview = (
            (message.content or "")[:100] + "..."
            if message.content and len(message.content) > 100
            else message.content or ""
        )

        console.print(
            Panel(
                f"[green]✓ Response received[/green]\n"
                f"Tool calls: {tool_calls_count}\n"
                f"Content: {content_preview}",
                title="LLM Response",
                border_style="green",
            )
        )

        return completion

    def _serialize(self, messages: list[Message]) -> list[dict]:
        result = []
        for message in messages:
            if isinstance(message, Message):
                msg_dict = {"role": message.role, "content": message.content}
                if message.name:
                    msg_dict["name"] = message.name
                if message.tool_calls:
                    msg_dict["tool_calls"] = message.tool_calls
                if message.tool_call_id:
                    msg_dict["tool_call_id"] = message.tool_call_id
                result.append(msg_dict)
            else:
                result.append(message)
        return result
