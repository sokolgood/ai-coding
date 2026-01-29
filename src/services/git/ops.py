import subprocess
from pathlib import Path


class GitOps:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)

    def _run_git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def checkout_branch(self, branch_name: str, base_branch: str = "main") -> None:
        self._run_git("fetch", "origin", base_branch)
        try:
            self._run_git("fetch", "origin", branch_name)
            self._run_git("checkout", "-B", branch_name, f"origin/{branch_name}")
        except subprocess.CalledProcessError:
            self._run_git("checkout", "-B", branch_name, f"origin/{base_branch}")

    def add_file(self, file_path: str) -> None:
        self._run_git("add", file_path)

    def has_changes(self) -> bool:
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                result = subprocess.run(
                    ["git", "diff", "--quiet"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                )
                return result.returncode != 0
            return True
        except Exception:
            return True

    def commit(self, message: str, allow_empty: bool = False) -> None:
        args = ["commit", "-m", message]
        if allow_empty:
            args.append("--allow-empty")
        self._run_git(*args)

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
