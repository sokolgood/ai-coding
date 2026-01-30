import ast
import os
from pathlib import Path
from typing import Any

from langfuse.decorators import observe
from rich.console import Console

from src.services.llm.tools.base import Tool
from src.types.main import ToolResult

console = Console()


class UpdateFileTool(Tool):
    name = "update_file"
    description = (
        "Update an existing file with new content. "
        "Provide the COMPLETE file content (not a diff or patch). "
        "CRITICAL: new_content must contain the ENTIRE file, including all unchanged code. "
        "Do NOT omit unchanged parts - include the full file content. "
        "IMPORTANT: Make MINIMAL changes - only modify what is necessary for the task. "
        "Preserve existing code exactly as-is except for the specific changes needed. "
        "Do NOT refactor unrelated functions, change function signatures, or rewrite working code."
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
                        "path": {
                            "type": "string",
                            "description": "The path to the file to update (relative or absolute path).",
                        },
                        "new_content": {
                            "type": "string",
                            "description": (
                                "The COMPLETE new content of the file. "
                                "Must include the entire file, not just changes. "
                                "Preserve formatting, blank lines, and comments. "
                                "Do NOT omit unchanged code - provide the full file content. "
                                "CRITICAL: Make MINIMAL changes - only modify what is required by the task. "
                                "Copy all unchanged code exactly as-is. Do NOT refactor or improve unrelated code."
                            ),
                        },
                    },
                    "required": ["path", "new_content"],
                },
            },
        }

    @observe()
    async def run(self, path: str, new_content: str) -> ToolResult:
        # Security: prevent path traversal and absolute paths
        if Path(path).is_absolute():
            return ToolResult(
                success=False,
                error=f"Invalid file path: {path}. Absolute paths are not allowed. Use relative paths only.",
            )

        # Resolve path and check it's within base_path
        try:
            file_path = (self.base_path / path).resolve()
            base_resolved = self.base_path.resolve()

            # Check that file_path is within base_path using commonpath
            try:
                common = os.path.commonpath([str(base_resolved), str(file_path)])
                if common != str(base_resolved):
                    return ToolResult(
                        success=False,
                        error=f"Invalid file path: {path}. Path traversal not allowed.",
                    )
            except ValueError:
                # Paths on different drives (Windows) or invalid
                return ToolResult(
                    success=False,
                    error=f"Invalid file path: {path}. Path traversal not allowed.",
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Invalid file path: {path}. {e!s}",
            )

        if not file_path.exists():
            return ToolResult(
                success=False,
                error=f"File does not exist: {path}. Use create_file to create new files.",
            )

        try:
            original_content = file_path.read_text(encoding="utf-8")

            # Check if content actually changed
            if original_content == new_content:
                console.print(f"[dim]No changes detected in {path}[/dim]")
                return ToolResult(success=True, content=f"No changes detected in {path}.")

            # Validate Python syntax if it's a Python file (before writing)
            syntax_error = self._validate_python_syntax(new_content, file_path.suffix)
            if syntax_error:
                error_msg = (
                    f"Syntax error in new content for {path}:\n{syntax_error}\n\n"
                    "Please provide corrected new_content with valid syntax."
                )
                console.print(f"[red]✗ Syntax error in {path}[/red]")
                console.print(f"[red]{syntax_error}[/red]")
                return ToolResult(success=False, error=error_msg)

            # Atomically write the new content
            tmp_path = file_path.with_suffix(file_path.suffix + ".tmp")
            try:
                tmp_path.write_text(new_content, encoding="utf-8")
                tmp_path.replace(file_path)
            except Exception:
                # Clean up temp file on error
                if tmp_path.exists():
                    tmp_path.unlink()
                raise

            console.print(f"[green]✓ Updated file: {path}[/green]")

            # Calculate changes summary for logging
            old_lines = original_content.splitlines()
            new_lines = new_content.splitlines()
            added = len(new_lines) - len(old_lines)
            changes_summary = f"Lines: {len(old_lines)} → {len(new_lines)} ({added:+d})"

            return ToolResult(
                success=True,
                content=f"Successfully updated {path}. {changes_summary}",
            )
        except Exception as e:
            error_msg = f"Failed to update file {path}: {e!s}"
            console.print(f"[red]✗ {error_msg}[/red]")
            return ToolResult(success=False, error=error_msg)

    def _validate_python_syntax(self, content: str, file_extension: str) -> str | None:
        """Validate Python syntax. Returns error message if invalid, None if valid."""
        if file_extension != ".py":
            return None

        try:
            ast.parse(content)
            return None
        except SyntaxError as e:
            return f"Line {e.lineno}: {e.msg}\n{e.text}"
