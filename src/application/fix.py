import asyncio
import json
import re
import uuid

from github import PullRequest
from rich.console import Console

from src.config import Settings, get_settings
from src.services.git.github import GitHubService
from src.services.git.ops import GitOps
from src.services.llm.agents.coder import CoderAgent
from src.services.llm.factory import create_llm, create_prompts_registry, init_langfuse
from src.services.repo.context_builder import RepoContextBuilder
from src.types import IterationState
from src.types.context import CoderContext
from src.types.review import ReviewReport

console = Console()


class FixWorker:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.github_service = GitHubService(self.settings)
        self.git_ops = GitOps(self.settings.repo_path)
        # Initialize Langfuse
        init_langfuse(
            self.settings.langfuse_secret_key,
            self.settings.langfuse_public_key,
            self.settings.langfuse_base_url,
        )

    def run(self, pr_number: int) -> None:
        asyncio.run(self._run_async(pr_number))

    async def _run_async(self, pr_number: int) -> None:
        pr = self.github_service.get_pr(pr_number)
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

        console.print(f"[bold]Working in: {self.settings.repo_path}[/bold]")
        console.print(f"[bold]Current branch: {self.git_ops.get_current_branch()}[/bold]")

        review_feedback = self._get_latest_review_feedback(pr_number)
        if not review_feedback:
            raise ValueError(f"No review feedback found for PR #{pr_number}")

        if not self.settings.llm_api_key:
            raise ValueError("LLM_API_KEY is required for fix operation")

        console.print(f"[bold]Found review feedback with {len(review_feedback.changes)} requested changes[/bold]")

        await self._run_ai_fix(pr, state, review_feedback)

        self.git_ops.add_all()

        console.print("[bold]Checking for changes...[/bold]")
        has_changes = self.git_ops.has_changes()

        if has_changes:
            console.print("[bold]Committing changes...[/bold]")
            self.git_ops.commit(
                f"agent: fix issue #{state.issue_number} (iter {state.iteration + 1})",
                allow_empty=False,
            )
            console.print("[bold]Pushing changes...[/bold]")
            self.git_ops.push(branch_name)
        else:
            console.print("[yellow]No changes detected after fix[/yellow]")

        new_state = IterationState(
            issue_number=state.issue_number,
            iteration=state.iteration + 1,
            max_iterations=state.max_iterations,
        )

        updated_pr = self.github_service.get_pr(pr.number)
        new_body = updated_pr.body.replace(state.to_pr_body_comment(), new_state.to_pr_body_comment())
        self.github_service.update_pr(pr.number, new_body)

    async def _run_ai_fix(self, pr: PullRequest, state: IterationState, review_feedback: ReviewReport) -> None:
        llm = create_llm(self.settings.llm_api_key, self.settings.llm_base_url)

        console.print("[bold]Building repository context...[/bold]")
        repo_context = RepoContextBuilder.build(self.settings.repo_path)

        issue = self.github_service.get_issue(state.issue_number)

        feedback_text = self._format_review_feedback(review_feedback)

        ctx = CoderContext(
            trace_id=str(uuid.uuid4()),
            repo=repo_context,
            issue_number=state.issue_number,
            issue_title=issue.title,
            issue_body=f"{issue.body or f'Issue #{state.issue_number}'}\n\n## Review Feedback:\n{feedback_text}",
        )

        prompts_registry = create_prompts_registry()
        agent = CoderAgent(llm, prompts_registry, self.settings.repo_path, self.settings.llm_model_name)

        result = await agent.run(ctx)
        console.print(f"[green]AI Fix completed: {result[:200]}...[/green]")

        console.print("[bold]Checking what files were modified...[/bold]")
        status = self.git_ops._run_git("status", "--short", check=False)
        if status:
            console.print(f"[cyan]Git status:\n{status}[/cyan]")
        else:
            console.print("[yellow]No files in git status[/yellow]")

    def _get_latest_review_feedback(self, pr_number: int) -> ReviewReport | None:
        pr = self.github_service.get_pr(pr_number)
        comments = pr.get_issue_comments()

        for comment in reversed(list(comments)):
            if "AGENT_REVIEW_JSON:" in comment.body:
                match = re.search(r"<!-- AGENT_REVIEW_JSON:(.+?) -->", comment.body, re.DOTALL)
                if match:
                    try:
                        json_data = match.group(1).strip()
                        json_data = re.sub(r"```json\n(.*)\n```", r"\1", json_data, flags=re.DOTALL)
                        review_data = json.loads(json_data)
                        return ReviewReport(**review_data)
                    except Exception as e:
                        console.print(f"[yellow]Failed to parse review JSON: {e}[/yellow]")
                        continue

        return None

    def _format_review_feedback(self, review_report: ReviewReport) -> str:
        parts = [f"Review Verdict: {review_report.verdict}", f"Summary: {review_report.summary}"]

        if review_report.changes:
            parts.append("\nRequested Changes:")
            for change in review_report.changes:
                parts.append(f"- [{change.severity.upper()}] {change.description}")
                if change.file:
                    parts.append(f"  File: {change.file}")
                if change.rationale:
                    parts.append(f"  Rationale: {change.rationale}")

        if review_report.risks:
            parts.append("\nRisks:")
            for risk in review_report.risks:
                parts.append(f"- {risk}")

        return "\n".join(parts)
