from typing import Any

from rich.console import Console
from rich.panel import Panel

from src.prompts.registry import PromptsRegistry
from src.services.llm.engine import LLM
from src.services.llm.tools import GrepSearchTool, ListDirectoryTool, ReadFileTool
from src.services.llm.tools.base import Tool
from src.types.main import Message, ToolResult
from src.types.review import ReviewReport

console = Console()


class ReviewerAgent:
    def __init__(self, llm: LLM, prompts_registry: PromptsRegistry, repo_path: str = ".") -> None:
        self.llm = llm
        self.prompts_registry = prompts_registry
        self.repo_path = repo_path

        self.tools: dict[str, Tool] = {
            "list_directory": ListDirectoryTool(base_path=repo_path),
            "read_file": ReadFileTool(base_path=repo_path),
            "grep_search": GrepSearchTool(base_path=repo_path),
        }

    async def run(self, pr_diff: str, issue_description: str, ci_results: str = "", max_iterations: int = 5) -> str:
        diff_preview = pr_diff[:200] + "..." if len(pr_diff) > 200 else pr_diff
        console.print(
            Panel(
                f"[bold]🔍 Reviewer Agent started[/bold]\nDiff preview: {diff_preview}",
                title="Reviewer",
                border_style="yellow",
            )
        )

        system_prompt = self.prompts_registry.reviewer.system.render(
            issue_description=issue_description,
            pr_diff=pr_diff,
            ci_results=ci_results,
        )
        user_prompt = self.prompts_registry.reviewer.user.render(
            issue_description=issue_description,
            pr_diff=pr_diff,
            ci_results=ci_results,
        )

        messages: list[Message] = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt),
        ]

        available_tools = list(self.tools.values())

        for iteration in range(max_iterations):
            console.print(f"[dim]Iteration {iteration + 1}/{max_iterations}[/dim]")

            use_structured_output = iteration == max_iterations - 1

            completion = await self.llm.invoke(
                messages=messages,
                model="gpt-4o-mini",
                tools=available_tools if not use_structured_output else None,
                response_format=ReviewReport if use_structured_output else None,
            )

            message = completion.choices[0].message
            assistant_content = message.content or ""

            if use_structured_output and message.content:
                try:
                    import json

                    review_data = json.loads(message.content)
                    review_report = ReviewReport(**review_data)
                    msg = "[bold green]✓ Review completed with structured output[/bold green]"
                    console.print(Panel(msg, border_style="green"))
                    return review_report.model_dump_json(indent=2)
                except Exception as e:
                    console.print(f"[yellow]Failed to parse structured output: {e}, falling back to text[/yellow]")

            if message.tool_calls:
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
                if not use_structured_output:
                    console.print(Panel("[bold green]✓ Review completed[/bold green]", border_style="green"))
                    return assistant_content

        console.print(Panel("[bold red]✗ Max iterations reached[/bold red]", border_style="red"))
        fail_summary = "Max iterations reached. Reviewer did not complete the review."
        fail_json = f'{{"verdict": "FAIL", "summary": "{fail_summary}", "changes": []}}'
        return fail_json

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
