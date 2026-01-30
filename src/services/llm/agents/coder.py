from typing import Any

from rich.console import Console
from rich.panel import Panel

from src.prompts.registry import PromptsRegistry
from src.services.llm.engine import LLM
from src.services.llm.tools import (
    GrepSearchTool,
    ListDirectoryTool,
    ReadFileTool,
    WriteFileTool,
)
from src.services.llm.tools.base import Tool
from src.types.main import Message, ToolResult

console = Console()


class CoderAgent:
    def __init__(self, llm: LLM, prompts_registry: PromptsRegistry, repo_path: str = ".") -> None:
        self.llm = llm
        self.prompts_registry = prompts_registry
        self.repo_path = repo_path

        self.tools: dict[str, Tool] = {
            "list_directory": ListDirectoryTool(base_path=repo_path),
            "read_file": ReadFileTool(base_path=repo_path),
            "write_file": WriteFileTool(base_path=repo_path),
            "grep_search": GrepSearchTool(base_path=repo_path),
        }

    async def run(self, issue_description: str, max_iterations: int = 10) -> str:
        desc_preview = issue_description[:200] + "..." if len(issue_description) > 200 else issue_description
        console.print(Panel(f"[bold]🚀 Coder Agent started[/bold]\n{desc_preview}", title="Agent", border_style="blue"))

        system_prompt = self.prompts_registry.coder.system.render(
            issue_description=issue_description,
        )
        user_prompt = self.prompts_registry.coder.user.render(
            issue_description=issue_description,
        )

        messages: list[Message] = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt),
        ]

        available_tools = list(self.tools.values())

        for iteration in range(max_iterations):
            console.print(f"[dim]Iteration {iteration + 1}/{max_iterations}[/dim]")

            completion = await self.llm.invoke(
                messages=messages,
                model="gpt-4o-mini",
                tools=available_tools,
            )

            message = completion.choices[0].message
            assistant_content = message.content or ""

            if message.tool_calls:
                console.print(f"[yellow]🔧 Using {len(message.tool_calls)} tool(s)[/yellow]")
                tool_calls_serialized = self._serialize_tool_calls(message.tool_calls)
                messages.append(Message(role="assistant", content=assistant_content, tool_calls=tool_calls_serialized))

                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = self._parse_tool_args(tool_call.function.arguments)

                    console.print(f"[cyan]→ {tool_name}[/cyan] {tool_args}")

                    if tool_name not in self.tools:
                        tool_result = ToolResult(success=False, error=f"Unknown tool: {tool_name}")
                        console.print(f"[red]✗ Unknown tool: {tool_name}[/red]")
                    else:
                        tool = self.tools[tool_name]
                        tool_result = await tool.run(**tool_args)
                        if tool_result.success:
                            result_preview = (
                                (tool_result.content or "")[:150] + "..."
                                if tool_result.content and len(tool_result.content) > 150
                                else tool_result.content or ""
                            )
                            console.print(f"[green]✓ {tool_name} succeeded[/green] [dim]{result_preview}[/dim]")
                        else:
                            console.print(f"[red]✗ {tool_name} failed: {tool_result.error}[/red]")

                    error_msg = f"Error: {tool_result.error}" if not tool_result.success else None
                    messages.append(
                        Message(
                            role="tool",
                            content=tool_result.content if tool_result.success else error_msg,
                            tool_call_id=tool_call.id,
                        )
                    )
            else:
                messages.append(Message(role="assistant", content=assistant_content))
                console.print(Panel("[bold green]✓ Agent completed successfully[/bold green]", border_style="green"))
                return assistant_content

        console.print(Panel("[bold red]✗ Max iterations reached[/bold red]", border_style="red"))
        return "Max iterations reached. Agent did not complete the task."

    def _serialize_tool_calls(self, tool_calls: list[Any]) -> list[dict]:
        result = []
        for tool_call in tool_calls:
            result.append(
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {"name": tool_call.function.name, "arguments": tool_call.function.arguments},
                }
            )
        return result

    def _parse_tool_args(self, arguments: str) -> dict[str, Any]:
        import json

        try:
            return json.loads(arguments)
        except json.JSONDecodeError:
            return {}
