from langfuse.decorators import observe
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from openai.types.chat.parsed_chat_completion import ParsedChatCompletion
from pydantic import BaseModel
from rich.console import Console

from src.services.llm.tools.base import Tool
from src.types.main import Message

console = Console()


class LLM:
    def __init__(self, allm_client: AsyncOpenAI) -> None:
        self.allm_client = allm_client

    @observe(as_type="generation")
    async def invoke(
        self,
        messages: list[Message],
        model: str,
        tools: list[Tool] | None = None,
        response_format: type[BaseModel] | None = None,
        **kwargs,
    ) -> ChatCompletion | ParsedChatCompletion:
        serialized_messages = self._serialize(messages)

        # Minimal logging - details are handled by agents
        tools_info = f", {len(tools)} tools" if tools else ""
        format_info = f", format={response_format.__name__}" if response_format else ""
        console.print(f"[dim]🤖 LLM Request: model={model}{tools_info}{format_info}[/dim]")

        common_params = {
            "messages": serialized_messages,
            "model": model,
            **kwargs,
        }

        if tools:
            common_params["tools"] = [tool.json() for tool in tools]
            common_params["tool_choice"] = "auto"

        if response_format:
            completion = await self.allm_client.chat.completions.parse(
                response_format=response_format,
                **common_params,
            )
        else:
            completion = await self.allm_client.chat.completions.create(**common_params)

        # Minimal response logging - details are handled by agents
        message = completion.choices[0].message
        tool_calls_count = len(message.tool_calls) if message.tool_calls else 0
        is_parsed = isinstance(completion, ParsedChatCompletion) and completion.choices[0].message.parsed

        if is_parsed:
            parsed_type = type(completion.choices[0].message.parsed).__name__
            console.print(f"[dim]✓ LLM Response: parsed={parsed_type}[/dim]")
        elif tool_calls_count > 0:
            console.print(f"[dim]✓ LLM Response: {tool_calls_count} tool call(s)[/dim]")
        else:
            has_content = bool(message.content)
            console.print(f"[dim]✓ LLM Response: {'with content' if has_content else 'empty'}[/dim]")

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
