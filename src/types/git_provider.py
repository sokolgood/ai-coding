from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

from github.Issue import Issue
from github.PullRequest import PullRequest


@dataclass
class PRFile:
    filename: str
    status: str
    additions: int
    deletions: int
    patch: str | None = None


@dataclass
class CISummary:
    conclusion: Literal["success", "failure", "cancelled", "neutral"] | None
    details: str = ""


class GitProvider(ABC):
    @abstractmethod
    def get_issue(self, number: int) -> Issue:
        raise NotImplementedError

    @abstractmethod
    def find_pr_by_branch(self, branch: str) -> PullRequest | None:
        raise NotImplementedError

    @abstractmethod
    def create_pr(self, title: str, body: str, head: str, base: str = "main") -> PullRequest:
        raise NotImplementedError

    @abstractmethod
    def update_pr(self, number: int, body: str, title: str | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_pr(self, number: int) -> PullRequest:
        raise NotImplementedError

    @abstractmethod
    def get_pr_diff(self, number: int) -> str:
        raise NotImplementedError

    @abstractmethod
    def list_pr_files(self, number: int) -> list[PRFile]:
        raise NotImplementedError

    @abstractmethod
    def comment_pr(self, number: int, body: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def review_pr(
        self,
        number: int,
        event: Literal["APPROVE", "REQUEST_CHANGES", "COMMENT"],
        body: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_labels_pr(self, number: int, add: list[str] | None = None, remove: list[str] | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_ci_summary(self, pr: PullRequest) -> CISummary:
        raise NotImplementedError


class AuthProvider(ABC):
    @abstractmethod
    def get_token(self, identity: Literal["coder", "reviewer"]) -> str:
        raise NotImplementedError
