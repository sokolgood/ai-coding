import asyncio
from pathlib import Path
from typing import Any

from langfuse.decorators import observe
from rich.console import Console

from src.services.llm.tools.base import Tool
from src.types.main import ToolResult

console = Console()


class RunCommandTool(Tool):
    name = "run_command"
    description = (
        "Run a terminal command in the repository directory. "
        "Use this to run linters, tests, or other build/check commands. "
        "The command will be executed in the repository root directory."
    )

    def __init__(self, base_path: str = ".") -> None:
        self.base_path = Path(base_path)

    def json(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": (
                                "The terminal command to execute (e.g., 'ruff check .', 'pytest', 'make lint')"
                            ),
                        },
                        "explanation": {
                            "type": "string",
                            "description": (
                                "One sentence explanation of why this command needs to be run "
                                "and how it contributes to the goal"
                            ),
                        },
                    },
                    "required": ["command", "explanation"],
                },
            },
        }

    @observe()
    async def run(self, command: str, explanation: str) -> ToolResult:
        console.print(f"[cyan]→ Running command: {command}[/cyan]")
        console.print(f"[dim]Reason: {explanation}[/dim]")

        try:
            process = await asyncio.create_subprocess_exec(
                *command.split(),
                cwd=str(self.base_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            stdout_text = stdout.decode("utf-8")
            stderr_text = stderr.decode("utf-8")

            if process.returncode == 0:
                output = stdout_text if stdout_text else "Command completed successfully (no output)"
                console.print("[green]✓ Command succeeded[/green]")
                if stdout_text:
                    console.print(f"[dim]{stdout_text[:500]}[/dim]")
                return ToolResult(
                    success=True,
                    content=f"Command '{command}' completed successfully.\n{output}",
                )
            else:
                error_output = stderr_text if stderr_text else stdout_text or "Command failed with no output"
                if stdout_text and stderr_text:
                    full_output = f"STDOUT:\n{stdout_text}\n\nSTDERR:\n{stderr_text}"
                else:
                    full_output = error_output
                console.print(f"[red]✗ Command failed (exit code {process.returncode})[/red]")
                console.print(f"[red]{error_output[:500]}[/red]")

                error_message = (
                    f"Command '{command}' failed with exit code {process.returncode}.\n\n"
                    f"{full_output}\n\n"
                    "Please check the error output above. Common issues:\n"
                    "- Dependencies not installed (run 'make install' or 'poetry install' first)\n"
                    "- Command not found (check if the tool is installed)\n"
                    "- Syntax errors or configuration issues"
                )
                return ToolResult(
                    success=False,
                    error=error_message,
                )
        except FileNotFoundError:
            error_msg = f"Command not found: {command.split()[0] if command.split() else command}"
            console.print(f"[red]✗ {error_msg}[/red]")
            return ToolResult(success=False, error=error_msg)
        except Exception as e:
            error_msg = f"Error running command '{command}': {e!s}"
            console.print(f"[red]✗ {error_msg}[/red]")
            return ToolResult(success=False, error=error_msg)
