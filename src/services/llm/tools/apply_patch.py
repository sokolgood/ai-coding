import asyncio
from pathlib import Path
from typing import Any

from src.services.llm.tools.base import Tool
from src.types.main import ToolResult


class ApplyPatchTool(Tool):
    name = "apply_patch"
    description = (
        "Apply a unified diff patch to files. "
        "This is safer than rewriting entire files as it makes minimal, controlled changes. "
        "The patch should be in unified diff format."
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
                        "patch": {
                            "type": "string",
                            "description": "Unified diff patch to apply. Should start with 'diff --git' or '---'.",
                        },
                    },
                    "required": ["patch"],
                },
            },
        }

    async def run(self, patch: str) -> ToolResult:
        try:
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as tmp_file:
                tmp_file.write(patch)
                tmp_patch_path = tmp_file.name

            try:
                process = await asyncio.create_subprocess_exec(
                    "git",
                    "apply",
                    "--ignore-whitespace",
                    "--verbose",
                    tmp_patch_path,
                    cwd=str(self.base_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await process.communicate()

                if process.returncode == 0:
                    applied_files = stdout.decode("utf-8").strip()
                    return ToolResult(
                        success=True,
                        content=f"Patch applied successfully.\n{applied_files}",
                    )
                else:
                    error_msg = stderr.decode("utf-8") or stdout.decode("utf-8") or "Unknown error"
                    return ToolResult(
                        success=False,
                        error=f"Failed to apply patch:\n{error_msg}",
                    )
            finally:
                Path(tmp_patch_path).unlink(missing_ok=True)

        except Exception as e:
            return ToolResult(success=False, error=f"Error applying patch: {e!s}")
