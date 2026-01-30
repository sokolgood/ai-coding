from pathlib import Path
from typing import Any

from src.services.llm.tools.base import Tool
from src.types.main import ToolResult


class WriteFileTool(Tool):
    name = "write_file"
    description = "Write content to a file. Creates file if it doesn't exist, overwrites if it does."

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
                            "description": "Path to the file to write. Can be relative or absolute.",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file.",
                        },
                    },
                    "required": ["path", "content"],
                },
            },
        }

    async def run(self, path: str, content: str) -> ToolResult:
        try:
            target_path = Path(path)
            if not target_path.is_absolute():
                target_path = self.base_path / target_path

            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")

            msg = f"Successfully wrote {len(content)} characters to {path}"
            return ToolResult(success=True, content=msg)

        except Exception as e:
            return ToolResult(success=False, error=f"Error writing file: {e!s}")
