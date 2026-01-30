import ast
import asyncio
import difflib
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from langfuse.decorators import observe
from rich.console import Console

from src.services.llm.tools.base import Tool
from src.types.main import ToolResult

console = Console()


class ApplyPatchTool(Tool):
    name = "apply_patch"
    description = (
        "Apply a unified diff patch to a file. "
        "This is the preferred and most reliable way to edit files. "
        "The patch format must be a standard unified diff with context lines. "
        "Returns the applied diff for verification."
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
                            "description": "The target file to modify (relative or absolute path).",
                        },
                        "patch": {
                            "type": "string",
                            "description": (
                                "Unified diff patch in STRICT standard format. "
                                "CRITICAL: The patch must be raw unified diff text, "
                                "NOT wrapped in markdown code blocks. "
                                "Format requirements:\n"
                                "1. Start with: `--- a/<filepath>\\n`\n"
                                "2. Then: `+++ b/<filepath>\\n`\n"
                                "3. One or more hunks: `@@ -<old_start>,<old_count> +<new_start>,<new_count> @@\\n`\n"
                                "4. Hunk lines MUST start with exactly one of: space ' ', plus '+', or minus '-'\n"
                                "5. NO markdown code fences (```), NO extra whitespace, NO comments\n"
                                "Example (raw text, no markdown):\n"
                                "--- a/src/main.py\n"
                                "+++ b/src/main.py\n"
                                "@@ -5,3 +5,5 @@\n"
                                " from fastapi import FastAPI\n"
                                "-old_line\n"
                                "+new_line_1\n"
                                "+new_line_2\n"
                                " from src.core.config import settings\n"
                            ),
                        },
                    },
                    "required": ["target_file", "patch"],
                },
            },
        }

    @observe()
    async def run(self, target_file: str, patch: str) -> ToolResult:
        # Security: prevent path traversal and absolute paths
        if Path(target_file).is_absolute():
            return ToolResult(
                success=False,
                error=f"Invalid file path: {target_file}. Absolute paths are not allowed. Use relative paths only.",
            )

        # Resolve path and check it's within base_path
        try:
            file_path = (self.base_path / target_file).resolve()
            base_resolved = self.base_path.resolve()

            # Check that file_path is within base_path using commonpath
            try:
                common = os.path.commonpath([str(base_resolved), str(file_path)])
                if common != str(base_resolved):
                    return ToolResult(
                        success=False,
                        error=f"Invalid file path: {target_file}. Path traversal not allowed.",
                    )
            except ValueError:
                # Paths on different drives (Windows) or invalid
                return ToolResult(
                    success=False,
                    error=f"Invalid file path: {target_file}. Path traversal not allowed.",
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Invalid file path: {target_file}. {e!s}",
            )

        if not file_path.exists():
            return ToolResult(
                success=False,
                error=f"File does not exist: {target_file}",
            )

        try:
            original_content = file_path.read_text(encoding="utf-8")

            # Check for markdown code fences
            if "```" in patch:
                error_msg = (
                    f"Invalid patch format for {target_file}.\n"
                    "Error: Patch contains markdown code fences (```). "
                    "Do NOT wrap the patch in markdown code blocks.\n\n"
                    "The patch must be raw unified diff text. "
                    "Remove any markdown code fences (```) and provide the patch directly.\n\n"
                    f"Example format (raw text, no markdown):\n"
                    f"--- a/{target_file}\n"
                    f"+++ b/{target_file}\n"
                    f"@@ -5,3 +5,5 @@\n"
                    f" existing line\n"
                    f"-deleted line\n"
                    f"+new line 1\n"
                    f"+new line 2\n"
                    f" existing line\n"
                )
                return ToolResult(success=False, error=error_msg)

            # Validate patch format before applying
            validation_error = self._validate_patch_format(patch, target_file)
            if validation_error:
                error_msg = (
                    f"Invalid patch format for {target_file}.\n"
                    f"Error: {validation_error}\n\n"
                    "The patch must be a valid unified diff. "
                    f"Make sure it starts with '--- a/{target_file}' and '+++ b/{target_file}', "
                    "has hunk headers '@@ -l,s +l,s @@', "
                    "and all hunk lines start with ' ', '+', or '-' (no markdown code blocks).\n\n"
                    f"Example format (raw text, no markdown):\n"
                    f"--- a/{target_file}\n"
                    f"+++ b/{target_file}\n"
                    f"@@ -5,3 +5,5 @@\n"
                    f" existing line\n"
                    f"-deleted line\n"
                    f"+new line 1\n"
                    f"+new line 2\n"
                    f" existing line\n"
                )
                return ToolResult(success=False, error=error_msg)

            # Use git apply for reliable patch application
            apply_result = await self._apply_with_git(file_path, patch, target_file)

            if not apply_result["success"]:
                error_output = apply_result["error"]
                preview = self._get_file_preview(original_content, 30)

                # Detect if it's a format error vs context mismatch
                if "corrupt patch" in error_output.lower() or "invalid patch" in error_output.lower():
                    error_msg = (
                        f"Invalid patch format for {target_file}.\n"
                        f"Git apply error: {error_output}\n\n"
                        "The patch format is invalid. Make sure:\n"
                        f"1. Patch starts with '--- a/{target_file}' and '+++ b/{target_file}'\n"
                        "2. Has valid hunk headers '@@ -l,s +l,s @@'\n"
                        "3. All hunk lines start with ' ', '+', or '-' (no markdown, no extra spaces)\n"
                        "4. Patch is raw text, NOT wrapped in markdown code blocks\n\n"
                        f"Example format:\n"
                        f"--- a/{target_file}\n"
                        f"+++ b/{target_file}\n"
                        f"@@ -5,3 +5,5 @@\n"
                        f" existing line\n"
                        f"-deleted line\n"
                        f"+new line 1\n"
                        f"+new line 2\n"
                        f" existing line\n"
                    )
                else:
                    # Context mismatch - show file preview to help model understand current state
                    error_msg = (
                        f"Failed to apply patch to {target_file}.\n"
                        f"Error: {error_output}\n\n"
                        f"Current file content (first 30 lines):\n{preview}\n\n"
                        "The patch does not match the current file content. "
                        "Please read the file using read_file tool to see the current state, "
                        "then generate a new patch that matches the current content exactly."
                    )
                return ToolResult(success=False, error=error_msg)

            # Read the modified file
            new_content = file_path.read_text(encoding="utf-8")

            # Validate Python syntax if it's a Python file
            syntax_error = self._validate_python_syntax(new_content, file_path.suffix)
            if syntax_error:
                preview = self._get_file_preview(new_content, 50)
                error_msg = (
                    f"Syntax error after applying patch to {target_file}:\n{syntax_error}\n\n"
                    f"Current file content (first 50 lines):\n{preview}\n\n"
                    "Please read the file and generate a corrected patch."
                )
                console.print(f"[red]✗ Syntax error in {target_file}[/red]")
                console.print(f"[red]{syntax_error}[/red]")
                # Restore original content
                file_path.write_text(original_content, encoding="utf-8")
                return ToolResult(success=False, error=error_msg)

            # Generate diff of what was actually applied
            applied_diff = self._generate_diff(original_content, new_content, target_file)

            console.print(f"[green]✓ Applied patch to {target_file}[/green]")
            patch_preview = patch[:300] + "..." if len(patch) > 300 else patch
            console.print(f"[dim]Patch preview:\n{patch_preview}[/dim]")

            # Return limited diff, not full patch
            diff_preview = applied_diff[:1000] + "..." if len(applied_diff) > 1000 else applied_diff
            return ToolResult(
                success=True,
                content=f"Successfully applied patch to {target_file}.\n\nApplied changes:\n{diff_preview}",
            )
        except Exception as e:
            error_msg = f"Failed to apply patch to {target_file}: {e!s}"
            console.print(f"[red]✗ {error_msg}[/red]")
            return ToolResult(success=False, error=error_msg)

    def _validate_patch_format(self, patch: str, target_file: str) -> str | None:
        """Validate patch format. Returns error message if invalid, None if valid."""
        lines = patch.splitlines()

        if not lines:
            return "Patch is empty"

        # Check for --- header with correct path
        minus_index = None
        for i, line in enumerate(lines[:20]):
            if line.startswith("--- "):
                expected_path = f"a/{target_file}"
                if not line.startswith(f"--- {expected_path}"):
                    return (
                        f"Invalid '---' header at line {i + 1}: '{line}'. "
                        f"Expected '--- {expected_path}' (path must match target_file exactly)"
                    )
                minus_index = i
                break

        if minus_index is None:
            return f"Missing '--- a/{target_file}' header at the start of patch"

        # Check for +++ header with correct path (must be after ---)
        found_plus = False
        for i, line in enumerate(lines[minus_index + 1 : minus_index + 11], start=minus_index + 1):
            if line.startswith("+++ "):
                found_plus = True
                expected_path = f"b/{target_file}"
                if not line.startswith(f"+++ {expected_path}"):
                    return (
                        f"Invalid '+++' header at line {i + 1}: '{line}'. "
                        f"Expected '+++ {expected_path}' (path must match target_file exactly)"
                    )
                break

        if not found_plus:
            return f"Missing '+++ b/{target_file}' header after '---' header"

        # Check for at least one hunk header
        has_hunk = False
        for line in lines:
            if re.match(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@", line):
                has_hunk = True
                break

        if not has_hunk:
            return "Missing hunk header '@@ -l,s +l,s @@' in patch"

        # Check that hunk lines have valid prefixes
        in_hunk = False
        for i, line in enumerate(lines):
            if re.match(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@", line):
                in_hunk = True
                continue

            if in_hunk:
                # Check if we hit the next hunk or end of patch
                if line.startswith("--- ") or line.startswith("+++ "):
                    in_hunk = False
                    continue

                # Hunk lines must start with space, +, or -
                if line and not line.startswith((" ", "+", "-", "\\")):
                    return (
                        f"Invalid line in hunk at line {i + 1}: '{line[:50]}'. "
                        "Hunk lines must start with ' ' (context), '+' (added), or '-' (removed)"
                    )

        return None

    async def _apply_with_git(self, file_path: Path, patch: str, target_file: str) -> dict[str, Any]:
        """Apply patch using git apply. Returns {'success': bool, 'error': str}."""
        try:
            # Normalize patch: ensure it ends with newline (git apply requirement)
            patch_normalized = patch
            if not patch_normalized.endswith("\n"):
                patch_normalized += "\n"

            # Create a temporary patch file with normalized content
            with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False, encoding="utf-8") as patch_file:
                patch_file.write(patch_normalized)
                patch_file_path = patch_file.name

            try:
                # First, validate patch with --check (dry-run)
                check_process = await asyncio.create_subprocess_exec(
                    "git",
                    "apply",
                    "--check",
                    "--unsafe-paths",
                    "--recount",
                    "--whitespace=nowarn",
                    patch_file_path,
                    cwd=str(self.base_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                check_stdout, check_stderr = await check_process.communicate()

                if check_process.returncode != 0:
                    error_output = check_stderr.decode("utf-8", errors="replace").strip()
                    return {"success": False, "error": error_output}

                # Patch is valid, now apply it
                process = await asyncio.create_subprocess_exec(
                    "git",
                    "apply",
                    "--unsafe-paths",
                    "--recount",
                    "--whitespace=nowarn",
                    patch_file_path,
                    cwd=str(self.base_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await process.communicate()

                if process.returncode == 0:
                    return {"success": True, "error": ""}
                else:
                    error_output = stderr.decode("utf-8", errors="replace").strip()
                    return {"success": False, "error": error_output}
            finally:
                # Clean up temp file
                Path(patch_file_path).unlink(missing_ok=True)

        except FileNotFoundError:
            return {
                "success": False,
                "error": "git not found. Please ensure git is installed in the environment.",
            }
        except Exception as e:
            return {"success": False, "error": f"Error running git apply: {e!s}"}

    def _generate_diff(self, original: str, modified: str, filename: str) -> str:
        """Generate unified diff between original and modified content."""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm="",
        )
        return "".join(diff)

    def _validate_python_syntax(self, content: str, file_extension: str) -> str | None:
        """Validate Python syntax. Returns error message if invalid, None if valid."""
        if file_extension != ".py":
            return None

        try:
            ast.parse(content)
            return None
        except SyntaxError as e:
            return f"Line {e.lineno}: {e.msg}\n{e.text}"

    def _get_file_preview(self, content: str, max_lines: int = 50) -> str:
        """Get preview of file content with line numbers."""
        lines = content.splitlines()
        preview_lines = lines[:max_lines]
        result = []
        for i, line in enumerate(preview_lines, 1):
            result.append(f"{i:4d} | {line}")
        if len(lines) > max_lines:
            result.append(f"... ({len(lines) - max_lines} more lines)")
        return "\n".join(result)
