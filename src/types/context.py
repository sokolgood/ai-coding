from typing import Any

from pydantic import BaseModel, Field


class RepoContext(BaseModel):
    repo_path: str
    tree_summary: str = Field(description="Top-level directories and files summary")
    readme: str | None = Field(default=None, description="README.md content (trimmed if too long)")
    agents_md: str | None = Field(default=None, description="AGENTS.md content if exists")
    build_files: str | None = Field(
        default=None, description="Summary of build files (pyproject.toml, requirements.txt, etc.)"
    )
    tests_hint: str | None = Field(
        default=None, description="Tests configuration summary (pytest.ini, tox.ini, tests/ dir)"
    )

    def to_string(self) -> str:
        parts = [f"Repository structure:\n{self.tree_summary}"]

        if self.build_files:
            parts.append(f"\n{self.build_files}")

        if self.tests_hint:
            parts.append(f"\n{self.tests_hint}")

        if self.agents_md:
            parts.append(f"\n\nREPOSITORY RULES (AGENTS.md):\n{self.agents_md}")

        return "\n".join(parts)


class AgentContext(BaseModel):
    trace_id: str
    repo: RepoContext
    metadata: dict[str, Any] = {}


class CoderContext(AgentContext):
    issue_number: int
    issue_title: str | None = None
    issue_body: str


class ReviewerContext(AgentContext):
    pr_number: int
    issue_body: str
    pr_diff: str
    ci_summary: str = ""
