from pathlib import Path
from typing import Any

from langfuse.decorators import observe
from rich.console import Console

from src.services.llm.tools.base import Tool
from src.types.main import ToolResult

console = Console()


class CreateFileTool(Tool):
    name = "create_file"
    description = (
        "Create a new file with the specified content. "
        "Use this tool ONLY for creating completely new files that do not exist yet. "
        "If the file already exists, this tool will fail. "
        "For modifying existing files, use apply_patch instead."
    )

    def __init__(self, base_path: str | None = None):
        self.base_path = Path(base_path) if base_path else Path.cwd()

    def json(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path to the new file to create. Can be relative or absolute.",
                        },
                        "content": {
                            "type": "string",
                            "description": "The content to write to the new file.",
                        },
                    },
                    "required": ["path", "content"],
                },
            },
        }

    @observe()
    async def run(self, path: str, content: str) -> ToolResult:
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = self.base_path / path

        if file_path.exists():
            return ToolResult(
                success=False,
                error=(
                    f"File already exists: {path}. "
                    "Use apply_patch tool to modify existing files instead of create_file."
                ),
            )

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

            console.print(f"[green]✓ Created file: {path}[/green]")
            console.print(f"[dim]Size: {len(content)} bytes[/dim]")

            return ToolResult(
                success=True,
                content=f"Successfully created file {path} ({len(content)} bytes).",
            )
        except Exception as e:
            error_msg = f"Error creating file {path}: {e!s}"
            console.print(f"[red]✗ {error_msg}[/red]")
            return ToolResult(success=False, error=error_msg)
