import asyncio
import json
import uuid

from github import PullRequest
from rich.console import Console

from src.config import Settings, get_settings
from src.services.git.github import GitHubService
from src.services.llm.agents.reviewer import ReviewerAgent
from src.services.llm.factory import create_llm, create_prompts_registry
from src.services.repo.context_builder import RepoContextBuilder
from src.types import IterationState
from src.types.context import ReviewerContext
from src.types.review import ReviewReport

console = Console()


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

        review_result_json = await self._run_ai_reviewer(pr, state)

        try:
            cleaned_json = review_result_json.strip()
            if cleaned_json.startswith("```"):
                import re

                match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned_json, re.DOTALL)
                if match:
                    cleaned_json = match.group(1)
                else:
                    cleaned_json = cleaned_json.replace("```json", "").replace("```", "").strip()

            review_data = json.loads(cleaned_json)
            review_report = ReviewReport(**review_data)
        except Exception as e:
            console.print(f"[red]Failed to parse review report: {e}[/red]")
            console.print(f"[dim]Raw response: {review_result_json[:500]}[/dim]")
            review_report = ReviewReport(verdict="FAIL", summary="Failed to parse review report")

        comment = self._format_review_comment(review_report, review_result_json)
        self.github_service.add_comment_to_pr(pr_number, comment)

        if review_report.verdict == "PASS":
            self.github_service.set_labels_pr(pr_number, add=["agent:approved"], remove=["agent:fix"])
        else:
            self.github_service.set_labels_pr(pr_number, add=["agent:fix"], remove=["agent:approved"])

    async def _run_ai_reviewer(self, pr: PullRequest, state: IterationState | None) -> str:
        llm = create_llm(self.settings.llm_api_key, self.settings.llm_base_url)

        prompts_registry = create_prompts_registry()
        agent = ReviewerAgent(llm, prompts_registry, self.settings.repo_path)

        pr_diff = self.github_service.get_pr_diff(pr.number)
        issue_description = pr.body or f"PR #{pr.number}"

        ci_summary = self.github_service.get_ci_summary(pr)
        ci_results = f"CI Conclusion: {ci_summary.conclusion}\n{ci_summary.details}" if ci_summary.conclusion else ""

        console.print("[bold]Building repository context...[/bold]")
        repo_context = RepoContextBuilder.build(self.settings.repo_path)

        ctx = ReviewerContext(
            trace_id=str(uuid.uuid4()),
            repo=repo_context,
            pr_number=pr.number,
            issue_body=issue_description,
            pr_diff=pr_diff,
            ci_summary=ci_results,
        )

        review_result = await agent.run(ctx)
        return review_result

    def _format_review_comment(self, review_report: ReviewReport, json_data: str) -> str:
        parts = []

        parts.append("## Review Report\n\n")
        parts.append(f"**Verdict:** {review_report.verdict}\n\n")
        parts.append(f"**Summary:**\n{review_report.summary}\n\n")

        if review_report.positives:
            parts.append("### ✅ Positives\n")
            for positive in review_report.positives:
                parts.append(f"- {positive}\n")
            parts.append("\n")

        if review_report.changes:
            parts.append("### 🔧 Requested Changes\n")
            for change in review_report.changes:
                severity_emoji = {"blocker": "🚫", "major": "⚠️", "minor": "💡"}.get(change.severity, "⚠️")
                file_info = f"**File:** `{change.file}`\n" if change.file else ""
                rationale = f"\n*Rationale:* {change.rationale}\n" if change.rationale else ""
                parts.append(
                    f"{severity_emoji} **{change.severity.upper()}** - {change.description}\n{file_info}{rationale}\n"
                )

        if review_report.risks:
            parts.append("### ⚠️ Risks\n")
            for risk in review_report.risks:
                parts.append(f"- {risk}\n")
            parts.append("\n")

        parts.append(f"\n<!-- AGENT_REVIEW_JSON:{json_data} -->")

        return "".join(parts)
