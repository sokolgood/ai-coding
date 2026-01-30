from pathlib import Path
from typing import Any

from langfuse.decorators import observe

from src.services.llm.tools.base import Tool
from src.types.main import ToolResult


class GrepSearchTool(Tool):
    name = "grep_search"
    description = "Search for a pattern in files. Supports recursive search in directories."

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
                        "pattern": {
                            "type": "string",
                            "description": "Text pattern to search for (case-sensitive).",
                        },
                        "path": {
                            "type": "string",
                            "description": (
                                "Path to search in. Can be a file or directory. " "Defaults to current directory."
                            ),
                        },
                        "recursive": {
                            "type": "boolean",
                            "description": "Search recursively in subdirectories. Defaults to true.",
                        },
                    },
                    "required": ["pattern"],
                },
            },
        }

    @observe()
    async def run(self, pattern: str, path: str = ".", recursive: bool = True) -> ToolResult:
        try:
            target_path = Path(path)
            if not target_path.is_absolute():
                target_path = self.base_path / target_path

            if not target_path.exists():
                return ToolResult(success=False, error=f"Path does not exist: {path}")

            matches = []

            if target_path.is_file():
                files_to_search = [target_path]
            elif recursive:
                files_to_search = list(target_path.rglob("*"))
                files_to_search = [f for f in files_to_search if f.is_file()]
            else:
                files_to_search = [f for f in target_path.iterdir() if f.is_file()]

            for file_path in files_to_search:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    lines = content.split("\n")
                    for line_num, line in enumerate(lines, 1):
                        if pattern in line:
                            matches.append(f"{file_path}:{line_num}: {line.strip()}")
                except (UnicodeDecodeError, PermissionError):
                    continue

            if not matches:
                return ToolResult(success=True, content=f"No matches found for pattern '{pattern}' in {path}")

            result = f"Found {len(matches)} matches for pattern '{pattern}':\n" + "\n".join(matches[:100])
            if len(matches) > 100:
                result += f"\n... and {len(matches) - 100} more matches"

            return ToolResult(success=True, content=result)

        except Exception as e:
            return ToolResult(success=False, error=f"Error searching: {e!s}")
