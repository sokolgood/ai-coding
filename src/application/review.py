import asyncio

from github import PullRequest

from src.config import Settings, get_settings
from src.services.git.github import GitHubService
from src.services.llm.agents.reviewer import ReviewerAgent
from src.services.llm.factory import create_llm, create_prompts_registry
from src.types import IterationState


class ReviewWorker:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.github_service = GitHubService(self.settings)

    def run(self, pr_number: int) -> None:
        asyncio.run(self._run_async(pr_number))

    async def _run_async(self, pr_number: int) -> None:
        pr = self.github_service.get_pull_request(pr_number)
        # files = self.github_service.get_pr_files(pr_number)
        # files_count = len(files)

        state = IterationState.from_pr_body(pr.body or "")

        if not self.settings.llm_api_key:
            raise ValueError("No `LLM_API_KEY` found. Please specify one")
        comment = await self._run_ai_reviewer(pr, state)

        self.github_service.add_comment_to_pr(pr_number, comment)

        verdict = "PASS" if "verdict: PASS" in comment.upper() else "FAIL"
        if verdict == "PASS":
            self.github_service.add_label_to_pr(pr_number, "agent:approved")
        else:
            self.github_service.add_label_to_pr(pr_number, "agent:fix")

    async def _run_ai_reviewer(self, pr: PullRequest, state: IterationState | None) -> str:
        llm = create_llm(self.settings.llm_api_key, self.settings.llm_base_url)

        prompts_registry = create_prompts_registry()
        agent = ReviewerAgent(llm, prompts_registry, self.settings.repo_path)

        pr_diff = self.github_service.get_pr_diff(pr.number)
        issue_description = pr.body or f"PR #{pr.number}"

        review_result = await agent.run(pr_diff, issue_description)
        return review_result
