from pathlib import Path
from typing import Any

from src.services.llm.tools.base import Tool
from src.types.main import ToolResult


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read contents of a file. Returns file content as text."

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
                            "description": "Path to the file to read. Can be relative or absolute.",
                        },
                    },
                    "required": ["path"],
                },
            },
        }

    async def run(self, path: str) -> ToolResult:
        try:
            target_path = Path(path)
            if not target_path.is_absolute():
                target_path = self.base_path / target_path

            if not target_path.exists():
                return ToolResult(success=False, error=f"File does not exist: {path}")

            if not target_path.is_file():
                return ToolResult(success=False, error=f"Path is not a file: {path}")

            content = target_path.read_text(encoding="utf-8")
            return ToolResult(success=True, content=content)

        except UnicodeDecodeError:
            error_msg = f"File is not a text file (binary): {path}"
            return ToolResult(success=False, error=error_msg)
        except Exception as e:
            return ToolResult(success=False, error=f"Error reading file: {e!s}")
