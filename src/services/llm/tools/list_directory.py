from pathlib import Path
from typing import Any

from src.services.llm.tools.base import Tool
from src.types.main import ToolResult


class ListDirectoryTool(Tool):
    name = "list_directory"
    description = "List files and directories in a given path. Returns directory structure."

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
                            "description": (
                                "Path to list. Can be relative or absolute. "
                                "Defaults to current directory if not provided."
                            ),
                        },
                    },
                    "required": [],
                },
            },
        }

    async def run(self, path: str = ".") -> ToolResult:
        try:
            target_path = Path(path)
            if not target_path.is_absolute():
                target_path = self.base_path / target_path

            if not target_path.exists():
                return ToolResult(success=False, error=f"Path does not exist: {path}")

            if not target_path.is_dir():
                return ToolResult(success=False, error=f"Path is not a directory: {path}")

            items = []
            for item in sorted(target_path.iterdir()):
                item_type = "DIR" if item.is_dir() else "FILE"
                size = item.stat().st_size if item.is_file() else 0
                items.append(f"{item_type:4s} {item.name:50s} {size:>10} bytes")

            content = f"Contents of {path}:\n" + "\n".join(items)
            return ToolResult(success=True, content=content)

        except Exception as e:
            return ToolResult(success=False, error=f"Error listing directory: {e!s}")
