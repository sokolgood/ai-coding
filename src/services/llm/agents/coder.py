import json
from typing import Any

from langfuse.decorators import observe
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from src.prompts.registry import PromptsRegistry
from src.services.llm.agents.sgr.coder import SGRCoderAgent
from src.services.llm.engine import LLM
from src.services.llm.tools import (
    CreateFileTool,
    GrepSearchTool,
    ListDirectoryTool,
    ReadFileTool,
    UpdateFileTool,
)
from src.services.llm.tools.base import Tool
from src.types.coder_result import CoderResult
from src.types.context import CoderContext
from src.types.main import Message, ToolResult

console = Console()


class CoderAgent:
    def __init__(
        self, llm: LLM, prompts_registry: PromptsRegistry, repo_path: str = ".", model_name: str = "gpt-4o-mini"
    ) -> None:
        self.llm = llm
        self.prompts_registry = prompts_registry
        self.repo_path = repo_path
        self.model_name = model_name
        self.sgr = SGRCoderAgent(llm, prompts_registry, model_name)

        self.tools: dict[str, Tool] = {
            "list_directory": ListDirectoryTool(base_path=repo_path),
            "read_file": ReadFileTool(base_path=repo_path),
            "update_file": UpdateFileTool(base_path=repo_path),
            "create_file": CreateFileTool(base_path=repo_path),
            "grep_search": GrepSearchTool(base_path=repo_path),
            # NOTE: run_command tool is disabled - runtime checks (linting/tests) are handled by CI/CD
        }

    @observe(name="CoderAgent")
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

        max_tool_iterations = 20
        tool_iterations = 0

        while tool_iterations < max_tool_iterations:
            completion = await self.llm.invoke(
                messages=messages,
                model=self.model_name,
                tools=available_tools,
            )

            message = completion.choices[0].message
            assistant_content = message.content or ""

            if message.tool_calls:
                tool_iterations += 1
                iter_info = f"iteration {tool_iterations}/{max_tool_iterations}"
                console.print(f"\n[yellow]🔧 Tool calls ({iter_info})[/yellow]")
                tool_calls_serialized = self._serialize_tool_calls(message.tool_calls)
                messages.append(Message(role="assistant", content=assistant_content, tool_calls=tool_calls_serialized))

                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = self._parse_tool_args(tool_call.function.arguments)

                    # Format tool call with full parameters
                    args_json = json.dumps(tool_args, indent=2, ensure_ascii=False)
                    console.print(
                        Panel(
                            Syntax(args_json, "json", theme="monokai", line_numbers=False),
                            title=f"[bold cyan]Tool: {tool_name}[/bold cyan]",
                            border_style="cyan",
                        )
                    )

                    if tool_name not in self.tools:
                        tool_result = ToolResult(success=False, error=f"Unknown tool: {tool_name}")
                        console.print(Panel(f"[red]✗ Unknown tool: {tool_name}[/red]", border_style="red"))
                    else:
                        tool = self.tools[tool_name]
                        tool_result = await tool.run(**tool_args)

                        if tool_result.success:
                            # Show result content (truncated if too long)
                            result_preview = tool_result.content or "Success"
                            if len(result_preview) > 500:
                                result_preview = result_preview[:500] + "\n... [truncated]"
                            console.print(
                                Panel(
                                    result_preview,
                                    title=f"[bold green]✓ {tool_name} succeeded[/bold green]",
                                    border_style="green",
                                )
                            )
                        else:
                            console.print(
                                Panel(
                                    tool_result.error or "Unknown error",
                                    title=f"[bold red]✗ {tool_name} failed[/bold red]",
                                    border_style="red",
                                )
                            )

                    error_msg = f"Error: {tool_result.error}" if not tool_result.success else None
                    messages.append(
                        Message(
                            role="tool",
                            content=tool_result.content if tool_result.success else error_msg,
                            tool_call_id=tool_call.id,
                        )
                    )
            else:
                # No more tool calls - show final response
                if assistant_content:
                    console.print(
                        Panel(
                            assistant_content,
                            title="[bold]LLM Response[/bold]",
                            border_style="blue",
                        )
                    )
                messages.append(Message(role="assistant", content=assistant_content))
                break

        if tool_iterations >= max_tool_iterations:
            max_iter_msg = f"Reached max tool iterations ({max_tool_iterations})"
            console.print(f"[yellow]⚠️ {max_iter_msg}, proceeding to summary[/yellow]")
            messages.append(
                Message(
                    role="user",
                    content=(
                        f"Maximum tool iterations ({max_tool_iterations}) reached. "
                        "Please provide a summary of what was accomplished so far."
                    ),
                )
            )

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
            model=self.model_name,
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
        try:
            return json.loads(arguments)
        except json.JSONDecodeError:
            return {}
