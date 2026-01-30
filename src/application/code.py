import asyncio
import uuid
from pathlib import Path

from github import Issue
from rich.console import Console

from src.config import Settings, get_settings
from src.services.git.github import GitHubService
from src.services.git.ops import GitOps
from src.services.llm.agents.coder import CoderAgent
from src.services.llm.factory import create_llm, create_prompts_registry
from src.services.repo.context_builder import RepoContextBuilder
from src.types import IterationState
from src.types.context import CoderContext

console = Console()


class CodeWorker:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.github_service = GitHubService(self.settings)
        self.git_ops = GitOps(self.settings.repo_path)

    def run(self, issue_number: int, base_branch: str = "main", max_iter: int = 5) -> None:
        asyncio.run(self._run_async(issue_number, base_branch, max_iter))

    async def _run_async(self, issue_number: int, base_branch: str = "main", max_iter: int = 5) -> None:
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

        console.print(f"[bold]Working in: {self.settings.repo_path}[/bold]")
        console.print(f"[bold]Current branch: {self.git_ops.get_current_branch()}[/bold]")

        if self.settings.llm_api_key:
            await self._run_ai_agent(issue, iteration)
        else:
            self._run_simple_implementation(issue_number, iteration)

        console.print("[bold]Adding all changes to staging...[/bold]")
        self.git_ops.add_all()

        console.print("[bold]Checking for changes...[/bold]")
        has_changes = self.git_ops.has_changes()

        if has_changes:
            console.print("[bold]Committing changes...[/bold]")
            self.git_ops.commit(
                f"agent: implement issue #{issue_number} (iter {iteration})",
                allow_empty=False,
            )
            console.print("[bold]Pushing changes...[/bold]")
            self.git_ops.push(branch_name)
        else:
            console.print("[yellow]No changes detected after agent run[/yellow]")

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

    async def _run_ai_agent(self, issue: Issue, iteration: int) -> None:
        llm = create_llm(self.settings.llm_api_key, self.settings.llm_base_url)

        console.print("[bold]Building repository context...[/bold]")
        repo_context = RepoContextBuilder.build(self.settings.repo_path)

        ctx = CoderContext(
            trace_id=str(uuid.uuid4()),
            repo=repo_context,
            issue_number=issue.number,
            issue_title=issue.title,
            issue_body=issue.body or f"Issue #{issue.number}",
        )

        prompts_registry = create_prompts_registry()
        agent = CoderAgent(llm, prompts_registry, self.settings.repo_path)

        result = await agent.run(ctx)
        console.print(f"[green]AI Agent completed: {result[:200]}...[/green]")

        console.print("[bold]Checking what files were modified...[/bold]")
        status = self.git_ops._run_git("status", "--short", check=False)
        if status:
            console.print(f"[cyan]Git status:\n{status}[/cyan]")
        else:
            console.print("[yellow]No files in git status (files may not have been created or are ignored)[/yellow]")

    def _run_simple_implementation(self, issue_number: int, iteration: int) -> None:
        file_path = Path(self.settings.repo_path) / "AGENT_WAS_HERE.md"
        content = f"Agent was here for issue #{issue_number}, iteration {iteration}\nTimestamp: {iteration}\n"
        file_path.write_text(content)
        self.git_ops.add_file(str(file_path.relative_to(self.settings.repo_path)))
