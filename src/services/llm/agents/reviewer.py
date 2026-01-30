from typing import Any

from rich.console import Console
from rich.panel import Panel

from src.prompts.registry import PromptsRegistry
from src.services.llm.agents.sgr.reviewer import SGRReviewerAgent
from src.services.llm.engine import LLM
from src.services.llm.tools import GrepSearchTool, ListDirectoryTool, ReadFileTool
from src.services.llm.tools.base import Tool
from src.types.context import ReviewerContext
from src.types.main import Message, ToolResult
from src.types.review import ReviewReport

console = Console()


class ReviewerAgent:
    def __init__(self, llm: LLM, prompts_registry: PromptsRegistry, repo_path: str = ".") -> None:
        self.llm = llm
        self.prompts_registry = prompts_registry
        self.repo_path = repo_path
        self.sgr = SGRReviewerAgent(llm, prompts_registry)

        self.tools: dict[str, Tool] = {
            "list_directory": ListDirectoryTool(base_path=repo_path),
            "read_file": ReadFileTool(base_path=repo_path),
            "grep_search": GrepSearchTool(base_path=repo_path),
        }

    async def run(self, ctx: ReviewerContext) -> str:
        diff_preview = ctx.pr_diff[:200] + "..." if len(ctx.pr_diff) > 200 else ctx.pr_diff
        console.print(
            Panel(
                f"[bold]🔍 Reviewer Agent started[/bold]\nDiff preview: {diff_preview}",
                title="Reviewer",
                border_style="yellow",
            )
        )

        available_tools = list(self.tools.values())

        console.print("[bold cyan]📋 Generating review plan...[/bold cyan]")
        plan = await self.sgr.run(ctx, available_tools)

        console.print(Panel(f"[bold]Plan: {plan.objective}[/bold]\nSteps: {len(plan.steps)}", border_style="cyan"))
        for step in plan.steps:
            tools_str = ", ".join([t.name for t in step.suggested_tools]) if step.suggested_tools else "none"
            console.print(f"  {step.id}: {step.goal} (tools: {tools_str})")

        repo_context_str = ctx.repo.to_string()
        system_prompt = self.prompts_registry.reviewer.system.render(
            repo_context=repo_context_str,
        )
        user_prompt = self.prompts_registry.reviewer.user.render(
            issue_description=ctx.issue_body,
            pr_diff=ctx.pr_diff,
            ci_results=ctx.ci_summary,
            sgr_plan_json=plan.model_dump_json(indent=2),
        )

        messages: list[Message] = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt),
        ]

        console.print("[bold yellow]🔧 Executing review plan...[/bold yellow]")

        tool_iterations = 0
        max_tool_iterations = 10

        while tool_iterations < max_tool_iterations:
            completion = await self.llm.invoke(
                messages=messages,
                model="gpt-4o-mini",
                tools=available_tools,
            )

            message = completion.choices[0].message
            assistant_content = message.content or ""

            if message.tool_calls:
                tool_iterations += 1
                console.print(f"[yellow]🔧 Using {len(message.tool_calls)} tool(s)[/yellow]")
                tool_calls_serialized = self._serialize_tool_calls(message.tool_calls)
                messages.append(Message(role="assistant", content=assistant_content, tool_calls=tool_calls_serialized))

                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = self._parse_tool_args(tool_call.function.arguments)

                    args_str = str(tool_args)
                    args_preview = args_str[:50] + "..." if len(args_str) > 50 else args_str
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

        console.print("[bold magenta]📊 Generating final review report...[/bold magenta]")

        final_completion = await self.llm.invoke(
            messages=messages,
            model="gpt-4o-mini",
            tools=None,
            response_format=ReviewReport,
        )

        message = final_completion.choices[0].message

        if message.refusal:
            console.print(f"[yellow]Model refused: {message.refusal}[/yellow]")
            return ReviewReport(
                verdict="FAIL",
                summary=f"Model refused to provide review: {message.refusal}",
                changes=[],
            ).model_dump_json(indent=2)

        if message.parsed:
            console.print(Panel("[bold green]✓ Review completed[/bold green]", border_style="green"))
            return message.parsed.model_dump_json(indent=2)

        console.print("[yellow]Failed to get structured review, returning text[/yellow]")
        return ReviewReport(
            verdict="FAIL",
            summary="Failed to get parsed review report",
            changes=[],
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
