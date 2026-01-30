from typing import Any

from rich.console import Console
from rich.panel import Panel

from src.prompts.registry import PromptsRegistry
from src.services.llm.agents.sgr.coder import SGRCoderAgent
from src.services.llm.engine import LLM
from src.services.llm.tools import (
    ApplyPatchTool,
    GrepSearchTool,
    ListDirectoryTool,
    ReadFileTool,
    WriteFileTool,
)
from src.services.llm.tools.base import Tool
from src.types.coder_result import CoderResult
from src.types.context import CoderContext
from src.types.main import Message, ToolResult

console = Console()


class CoderAgent:
    def __init__(self, llm: LLM, prompts_registry: PromptsRegistry, repo_path: str = ".") -> None:
        self.llm = llm
        self.prompts_registry = prompts_registry
        self.repo_path = repo_path
        self.sgr = SGRCoderAgent(llm, prompts_registry)

        self.tools: dict[str, Tool] = {
            "list_directory": ListDirectoryTool(base_path=repo_path),
            "read_file": ReadFileTool(base_path=repo_path),
            "write_file": WriteFileTool(base_path=repo_path),
            "apply_patch": ApplyPatchTool(base_path=repo_path),
            "grep_search": GrepSearchTool(base_path=repo_path),
        }

    async def run(self, ctx: CoderContext) -> str:
        desc_preview = ctx.issue_body[:200] + "..." if len(ctx.issue_body) > 200 else ctx.issue_body
        console.print(Panel(f"[bold]🚀 Coder Agent started[/bold]\n{desc_preview}", title="Agent", border_style="blue"))

        available_tools = list(self.tools.values())

        console.print("[bold cyan]📋 Generating execution plan...[/bold cyan]")
        plan = await self.sgr.run(ctx, available_tools)

        console.print(Panel(f"[bold]Plan: {plan.objective}[/bold]\nSteps: {len(plan.steps)}", border_style="cyan"))
        for step in plan.steps:
            tools_str = ", ".join([t.name for t in step.suggested_tools]) if step.suggested_tools else "none"
            console.print(f"  {step.id}: {step.goal} (tools: {tools_str})")

        repo_context_str = ctx.repo.to_string()
        system_prompt = self.prompts_registry.coder.system.render(
            repo_context=repo_context_str,
        )
        user_prompt = self.prompts_registry.coder.user.render(
            issue_description=ctx.issue_body,
            sgr_plan_json=plan.model_dump_json(indent=2),
        )

        messages: list[Message] = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt),
        ]

        console.print("[bold yellow]🔧 Executing plan...[/bold yellow]")

        while True:
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

                    args_preview = str(tool_args)[:50] + "..." if len(str(tool_args)) > 50 else str(tool_args)
                    console.print(f"[cyan]→ {tool_name}[/cyan] {args_preview}")

                    if tool_name not in self.tools:
                        tool_result = ToolResult(success=False, error=f"Unknown tool: {tool_name}")
                        console.print(f"[red]✗ Unknown tool: {tool_name}[/red]")
                    else:
                        tool = self.tools[tool_name]
                        tool_result = await tool.run(**tool_args)
                        if tool_result.success:
                            console.print(f"[green]✓ {tool_name} succeeded[/green]")
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
                break

        console.print("[bold magenta]📊 Generating final summary...[/bold magenta]")

        summary_instruction = (
            "Now provide a structured summary of what was implemented:\n"
            "- success: whether the task was completed successfully\n"
            "- summary: brief summary of what was implemented\n"
            "- files_modified: list of file paths that were modified or created"
        )
        messages.append(Message(role="user", content=summary_instruction))

        final_completion = await self.llm.invoke(
            messages=messages,
            model="gpt-4o-mini",
            tools=None,
            response_format=CoderResult,
        )

        message = final_completion.choices[0].message

        if message.refusal:
            console.print(f"[yellow]Model refused: {message.refusal}[/yellow]")
            return CoderResult(
                success=False,
                summary=f"Model refused to provide summary: {message.refusal}",
                files_modified=[],
            ).model_dump_json(indent=2)

        if message.parsed:
            result = message.parsed
            console.print(Panel("[bold green]✓ Execution completed[/bold green]", border_style="green"))
            console.print(f"[bold]Summary:[/bold] {result.summary}")
            if result.files_modified:
                console.print(f"[bold]Files modified:[/bold] {', '.join(result.files_modified)}")
            return result.model_dump_json(indent=2)

        console.print("[yellow]Failed to get structured result, returning text[/yellow]")
        return CoderResult(
            success=True,
            summary=assistant_content[:200] if assistant_content else "Task completed",
            files_modified=[],
        ).model_dump_json(indent=2)

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
