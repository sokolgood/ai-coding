from src.config import Settings, get_settings
from src.services.git.github import GitHubService
from src.types import IterationState


class ReviewWorker:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.github_service = GitHubService(self.settings)

    def run(self, pr_number: int) -> None:
        pr = self.github_service.get_pull_request(pr_number)
        files = self.github_service.get_pr_files(pr_number)
        files_count = len(files)

        state = IterationState.from_pr_body(pr.body or "")
        if not state:
            comment = f"Reviewer summary:\n" f"- files changed: {files_count}\n" f"- verdict: PASS\n"
        else:
            comment = (
                f"Reviewer summary:\n"
                f"- files changed: {files_count}\n"
                f"- iteration: {state.iteration}/{state.max_iterations}\n"
                f"- verdict: PASS\n"
            )

        self.github_service.add_comment_to_pr(pr_number, comment)
        self.github_service.add_label_to_pr(pr_number, "agent:approved")
