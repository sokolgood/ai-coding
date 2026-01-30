from typing import Literal

from github import Github
from github.Issue import Issue
from github.PullRequest import PullRequest

from src.config import Settings
from src.types.git_provider import CISummary, GitProvider, PRFile


class GitHubService(GitProvider):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.github = Github(settings.gh_token)
        self.repo = self.github.get_repo(settings.repo)

    def get_issue(self, issue_number: int) -> Issue:
        return self.repo.get_issue(issue_number)

    def get_pull_request(self, pr_number: int) -> PullRequest:
        return self.repo.get_pull(pr_number)

    def get_pr(self, number: int) -> PullRequest:
        return self.get_pull_request(number)

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

    def create_pr(self, title: str, body: str, head: str, base: str = "main") -> PullRequest:
        return self.create_pull_request(title, body, head, base)

    def update_pull_request(self, pr_number: int, body: str) -> None:
        pr = self.get_pull_request(pr_number)
        pr.edit(body=body)

    def update_pr(self, number: int, body: str, title: str | None = None) -> None:
        pr = self.get_pull_request(number)
        if title:
            pr.edit(title=title, body=body)
        else:
            pr.edit(body=body)

    def add_comment_to_pr(self, pr_number: int, comment: str) -> None:
        pr = self.get_pull_request(pr_number)
        pr.create_issue_comment(comment)

    def comment_pr(self, number: int, body: str) -> None:
        self.add_comment_to_pr(number, body)

    def add_label_to_pr(self, pr_number: int, label: str) -> None:
        pr = self.get_pull_request(pr_number)
        pr.add_to_labels(label)

    def get_pr_diff(self, pr_number: int) -> str:
        pr = self.get_pull_request(pr_number)
        files = pr.get_files()

        diff_parts = []
        for file in files:
            diff_parts.append(f"diff --git a/{file.filename} b/{file.filename}")
            diff_parts.append(f"--- a/{file.filename}")
            diff_parts.append(f"+++ b/{file.filename}")
            if file.patch:
                diff_parts.append(file.patch)
            else:
                diff_parts.append("Binary file or no changes")

        return "\n".join(diff_parts)

    def get_pr_files(self, pr_number: int) -> list[str]:
        pr = self.get_pull_request(pr_number)
        return [file.filename for file in pr.get_files()]

    def list_pr_files(self, number: int) -> list[PRFile]:
        pr = self.get_pull_request(number)
        files = pr.get_files()
        return [
            PRFile(
                filename=file.filename,
                status=file.status,
                additions=file.additions,
                deletions=file.deletions,
                patch=file.patch,
            )
            for file in files
        ]

    def review_pr(
        self,
        number: int,
        event: Literal["APPROVE", "REQUEST_CHANGES", "COMMENT"],
        body: str,
    ) -> None:
        pr = self.get_pull_request(number)
        pr.create_review(event=event, body=body)

    def set_labels_pr(self, number: int, add: list[str] | None = None, remove: list[str] | None = None) -> None:
        pr = self.get_pull_request(number)
        existing_labels = {label.name for label in pr.get_labels()}

        if add:
            for label in add:
                if label not in existing_labels:
                    pr.add_to_labels(label)

        if remove:
            for label in remove:
                if label in existing_labels:
                    try:
                        pr.remove_from_labels(label)
                    except Exception:
                        pass

    def get_ci_summary(self, pr: PullRequest) -> CISummary:
        if self.settings.ci_conclusion:
            conclusion = self.settings.ci_conclusion.lower()
            if conclusion in ["success", "failure", "cancelled", "neutral"]:
                return CISummary(
                    conclusion=conclusion,
                    details=f"CI Conclusion: {self.settings.ci_conclusion}",
                )

        return CISummary(conclusion=None, details="CI information unavailable")

    def find_pr_by_branch(self, branch_name: str) -> PullRequest | None:
        pulls = self.repo.get_pulls(state="open", head=f"{self.settings.repo_owner}:{branch_name}")
        for pr in pulls:
            if pr.head.ref == branch_name:
                return pr
        return None
