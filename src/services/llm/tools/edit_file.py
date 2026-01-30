import re
from pathlib import Path
from typing import Any

from rich.console import Console

from src.services.llm.tools.base import Tool
from src.types.main import ToolResult

console = Console()


class EditFileTool(Tool):
    name = "edit_file"
    description = (
        "Propose an edit to an existing file. "
        "Use the special comment `// ... existing code ...` (or `# ... existing code ...` for Python) "
        "to represent unchanged code between edited lines. "
        "Specify only the precise lines you wish to edit, never write out unchanged code."
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
                        "target_file": {
                            "type": "string",
                            "description": (
                                "The target file to modify. "
                                "You can use either a relative path in the workspace or an absolute path."
                            ),
                        },
                        "instructions": {
                            "type": "string",
                            "description": (
                                "A single sentence instruction describing what you are going to do for the edit. "
                                "Use first person."
                            ),
                        },
                        "code_edit": {
                            "type": "string",
                            "description": (
                                "Specify ONLY the precise lines of code that you wish to edit. "
                                "NEVER specify or write out unchanged code. "
                                "Instead, represent all unchanged code using the comment "
                                "`// ... existing code ...` (or `# ... existing code ...` for Python). "
                                "Make sure it is clear what the edit should be and where it should be applied."
                            ),
                        },
                    },
                    "required": ["target_file", "instructions", "code_edit"],
                },
            },
        }

    async def run(self, target_file: str, instructions: str, code_edit: str) -> ToolResult:
        file_path = self.base_path / target_file

        if not file_path.exists():
            return ToolResult(
                success=False,
                error=f"File does not exist: {target_file}",
            )

        try:
            original_content = file_path.read_text(encoding="utf-8")
            original_lines = original_content.splitlines(keepends=True)

            new_content = self._apply_edit(original_lines, code_edit, file_path.suffix)

            file_path.write_text(new_content, encoding="utf-8")

            console.print(f"[green]✓ Edited file: {target_file}[/green]")
            console.print(f"[dim]Instructions: {instructions}[/dim]")

            return ToolResult(
                success=True,
                content=f"Successfully edited {target_file}. {instructions}",
            )
        except Exception as e:
            error_msg = f"Failed to edit file {target_file}: {e!s}"
            console.print(f"[red]✗ {error_msg}[/red]")
            return ToolResult(success=False, error=error_msg)

    def _apply_edit(self, original_lines: list[str], code_edit: str, file_extension: str) -> str:
        comment_pattern = r"^\s*(//|#|--|<!--)\s*\.\.\.\s*existing\s+code\s*\.\.\.\s*(-->)?\s*$"
        existing_code_marker = re.compile(comment_pattern, re.IGNORECASE)

        edit_lines = code_edit.splitlines(keepends=True)
        result_lines: list[str] = []
        edit_index = 0
        original_index = 0

        while edit_index < len(edit_lines):
            edit_line = edit_lines[edit_index]

            if existing_code_marker.match(edit_line.strip()):
                edit_index += 1
                if edit_index < len(edit_lines):
                    next_edit_line = edit_lines[edit_index]
                    next_edit_stripped = next_edit_line.strip()

                    while original_index < len(original_lines):
                        original_line = original_lines[original_index]
                        original_stripped = original_line.strip()

                        if original_stripped == next_edit_stripped:
                            result_lines.append(original_line)
                            original_index += 1
                            edit_index += 1
                            break
                        else:
                            result_lines.append(original_line)
                            original_index += 1
                else:
                    while original_index < len(original_lines):
                        result_lines.append(original_lines[original_index])
                        original_index += 1
                    break
            else:
                result_lines.append(edit_line)
                edit_index += 1

        while original_index < len(original_lines):
            result_lines.append(original_lines[original_index])
            original_index += 1

        return "".join(result_lines)
