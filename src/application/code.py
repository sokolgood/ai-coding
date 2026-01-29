from pathlib import Path

from src.config import Settings, get_settings
from src.services.git.github import GitHubService
from src.services.git.ops import GitOps
from src.types import IterationState


class CodeWorker:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.github_service = GitHubService(self.settings)
        self.git_ops = GitOps(self.settings.repo_path)

    def run(self, issue_number: int, base_branch: str = "main", max_iter: int = 5) -> None:
        issue = self.github_service.get_issue(issue_number)
        branch_name = f"agent/issue-{issue_number}"

        self.git_ops.setup_safe_directory()
        self.git_ops.setup_remote(self.settings.gh_token, self.settings.repo)
        self.git_ops.setup_user()
        self.git_ops.checkout_branch(branch_name, base_branch)

        existing_pr = self.github_service.find_pr_by_branch(branch_name)

        iteration = 1
        if existing_pr:
            state = IterationState.from_pr_body(existing_pr.body)
            if state:
                iteration = state.iteration + 1
                if iteration > max_iter:
                    raise ValueError(f"Max iterations ({max_iter}) reached for issue {issue_number}")

        file_path = Path(self.settings.repo_path) / "AGENT_WAS_HERE.md"
        content = f"Agent was here for issue #{issue_number}, iteration {iteration}\nTimestamp: {iteration}\n"
        file_path.write_text(content)
        self.git_ops.add_file(str(file_path.relative_to(self.settings.repo_path)))

        has_changes = self.git_ops.has_changes()
        self.git_ops.commit(
            f"agent: implement issue #{issue_number} (iter {iteration})",
            allow_empty=not has_changes,
        )
        self.git_ops.push(branch_name)

        state = IterationState(
            issue_number=issue_number,
            iteration=iteration,
            max_iterations=max_iter,
        )

        pr_body = f"{state.to_pr_body_comment()}\n\n{issue.body or ''}"

        if existing_pr:
            self.github_service.update_pull_request(existing_pr.number, pr_body)
        else:
            self.github_service.create_pull_request(
                title=f"Agent: Fix issue #{issue_number}",
                body=pr_body,
                head=branch_name,
                base=base_branch,
            )
