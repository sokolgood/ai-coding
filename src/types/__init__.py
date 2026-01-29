from dataclasses import dataclass
from typing import Optional


@dataclass
class IterationState:
    issue_number: int
    iteration: int
    max_iterations: int

    @classmethod
    def from_pr_body(cls: type["IterationState"], pr_body: str) -> Optional["IterationState"]:
        if not pr_body:
            return None

        issue_match = None
        iter_match = None
        max_match = None

        for line in pr_body.split("\n"):
            if "<!-- agent:" in line:
                parts = line.replace("<!-- agent:", "").replace("-->", "").strip().split()
                for part in parts:
                    if part.startswith("issue="):
                        issue_match = int(part.split("=")[1])
                    elif part.startswith("iter="):
                        iter_match = int(part.split("=")[1])
                    elif part.startswith("max="):
                        max_match = int(part.split("=")[1])

        if issue_match is not None and iter_match is not None and max_match is not None:
            return cls(
                issue_number=issue_match,
                iteration=iter_match,
                max_iterations=max_match,
            )
        return None

    def to_pr_body_comment(self) -> str:
        return f"<!-- agent:issue={self.issue_number} iter={self.iteration} max={self.max_iterations} -->"
