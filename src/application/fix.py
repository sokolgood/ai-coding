from pathlib import Path

from src.config import Settings, get_settings
from src.services.git.github import GitHubService
from src.services.git.ops import GitOps
from src.types import IterationState


class FixWorker:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.github_service = GitHubService(self.settings)
        self.git_ops = GitOps(self.settings.repo_path)

    def run(self, pr_number: int) -> None:
        pr = self.github_service.get_pull_request(pr_number)
        state = IterationState.from_pr_body(pr.body or "")

        if not state:
            raise ValueError(f"PR #{pr_number} does not have iteration state")

        if state.iteration >= state.max_iterations:
            raise ValueError(f"Max iterations ({state.max_iterations}) reached for PR #{pr_number}")

        branch_name = pr.head.ref

        self.git_ops.setup_safe_directory()
        self.git_ops.setup_remote(self.settings.gh_token, self.settings.repo)
        self.git_ops.setup_user()
        self.git_ops.checkout_branch(branch_name, pr.base.ref)

        file_path = Path(self.settings.repo_path) / "AGENT_WAS_HERE.md"
        if file_path.exists():
            content = file_path.read_text()
            file_path.write_text(
                f"{content}\nAgent fixed issue #{state.issue_number}, iteration {state.iteration + 1}\n"
            )
        else:
            file_path.write_text(f"Agent fixed issue #{state.issue_number}, iteration {state.iteration + 1}\n")

        self.git_ops.add_file(str(file_path.relative_to(self.settings.repo_path)))
        has_changes = self.git_ops.has_changes()
        self.git_ops.commit(
            f"agent: fix issue #{state.issue_number} (iter {state.iteration + 1})",
            allow_empty=not has_changes,
        )
        self.git_ops.push(branch_name)

        new_state = IterationState(
            issue_number=state.issue_number,
            iteration=state.iteration + 1,
            max_iterations=state.max_iterations,
        )

        new_body = pr.body.replace(state.to_pr_body_comment(), new_state.to_pr_body_comment())
        self.github_service.update_pull_request(pr_number, new_body)
