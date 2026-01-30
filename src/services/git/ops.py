import subprocess
from pathlib import Path

from rich.console import Console

console = Console()


class GitOps:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)

    def _run_git(self, *args: str, check: bool = True) -> str:
        console.print(f"[dim]git {' '.join(args)}[/dim]")
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=check,
        )
        if result.stderr and result.returncode != 0:
            console.print(f"[red]Git error: {result.stderr}[/red]")
        return result.stdout.strip()

    def checkout_branch(self, branch_name: str, base_branch: str = "main") -> None:
        self._run_git("fetch", "origin", base_branch)
        try:
            self._run_git("fetch", "origin", branch_name)
            self._run_git("checkout", "-B", branch_name, f"origin/{branch_name}")
        except subprocess.CalledProcessError:
            self._run_git("checkout", "-B", branch_name, f"origin/{base_branch}")

    def add_file(self, file_path: str) -> None:
        full_path = self.repo_path / file_path
        if not full_path.exists():
            console.print(f"[yellow]Warning: File does not exist: {file_path}[/yellow]")
            return
        self._run_git("add", file_path)
        console.print(f"[green]✓ Added to staging: {file_path}[/green]")

    def add_all(self) -> None:
        console.print("[bold]Adding all changes to staging...[/bold]")
        self._run_git("add", "-A")
        status = self._run_git("status", "--short", check=False)
        if status:
            console.print(f"[cyan]Staged files:\n{status}[/cyan]")
        else:
            console.print("[yellow]No files to stage[/yellow]")

    def has_changes(self) -> bool:
        try:
            staged_result = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )
            if staged_result.returncode != 0:
                staged_files = self._run_git("diff", "--cached", "--name-only", check=False)
                console.print(f"[cyan]Staged changes: {staged_files or 'none'}[/cyan]")
                return True

            unstaged_result = subprocess.run(
                ["git", "diff", "--quiet"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )
            if unstaged_result.returncode != 0:
                unstaged_files = self._run_git("diff", "--name-only", check=False)
                console.print(f"[yellow]Unstaged changes: {unstaged_files or 'none'}[/yellow]")
                return True

            console.print("[dim]No changes detected[/dim]")
            return False
        except Exception as e:
            console.print(f"[red]Error checking changes: {e}[/red]")
            return True

    def commit(self, message: str, allow_empty: bool = False) -> None:
        if not allow_empty and not self.has_changes():
            console.print("[yellow]No changes to commit, skipping[/yellow]")
            return

        args = ["commit", "-m", message]
        if allow_empty:
            args.append("--allow-empty")
            console.print("[yellow]Creating empty commit (--allow-empty)[/yellow]")

        try:
            self._run_git(*args)
            console.print(f"[green]✓ Committed: {message}[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]✗ Commit failed: {e}[/red]")
            console.print(f"[red]stderr: {e.stderr if hasattr(e, 'stderr') else 'unknown'}[/red]")
            raise

    def push(self, branch_name: str, force: bool = False) -> None:
        args = ["push", "origin", branch_name]
        if force:
            args.append("--force")
        self._run_git(*args)

    def get_current_branch(self) -> str:
        return self._run_git("rev-parse", "--abbrev-ref", "HEAD")

    def setup_safe_directory(self) -> None:
        self._run_git("config", "--global", "--add", "safe.directory", str(self.repo_path.absolute()))

    def setup_remote(self, token: str, repo: str) -> None:
        remote_url = f"https://x-access-token:{token}@github.com/{repo}.git"
        self._run_git("remote", "set-url", "origin", remote_url)

    def setup_user(self) -> None:
        self._run_git("config", "user.name", "github-actions[bot]")
        self._run_git("config", "user.email", "github-actions[bot]@users.noreply.github.com")
