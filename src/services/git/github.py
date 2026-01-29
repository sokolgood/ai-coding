from github import Github
from github.Issue import Issue
from github.PullRequest import PullRequest

from src.config import Settings


class GitHubService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.github = Github(settings.gh_token)
        self.repo = self.github.get_repo(settings.repo)

    def get_issue(self, issue_number: int) -> Issue:
        return self.repo.get_issue(issue_number)

    def get_pull_request(self, pr_number: int) -> PullRequest:
        return self.repo.get_pull(pr_number)

    def create_pull_request(
        self,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> PullRequest:
        return self.repo.create_pull(
            title=title,
            body=body,
            head=head,
            base=base,
        )

    def update_pull_request(self, pr_number: int, body: str) -> None:
        pr = self.get_pull_request(pr_number)
        pr.edit(body=body)

    def add_comment_to_pr(self, pr_number: int, comment: str) -> None:
        pr = self.get_pull_request(pr_number)
        pr.create_issue_comment(comment)

    def add_label_to_pr(self, pr_number: int, label: str) -> None:
        pr = self.get_pull_request(pr_number)
        pr.add_to_labels(label)

    def get_pr_diff(self, pr_number: int) -> str:
        pr = self.get_pull_request(pr_number)
        return pr.diff()

    def get_pr_files(self, pr_number: int) -> list[str]:
        pr = self.get_pull_request(pr_number)
        return [file.filename for file in pr.get_files()]

    def find_pr_by_branch(self, branch_name: str) -> PullRequest | None:
        pulls = self.repo.get_pulls(state="open", head=f"{self.settings.repo_owner}:{branch_name}")
        for pr in pulls:
            if pr.head.ref == branch_name:
                return pr
        return None
