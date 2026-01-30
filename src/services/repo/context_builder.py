from pathlib import Path
from typing import ClassVar

from src.types.context import RepoContext


class RepoContextBuilder:
    MAX_FILE_SIZE: ClassVar[int] = 12 * 1024
    TRUNCATE_SIZE: ClassVar[int] = 4000

    @classmethod
    def build(cls: type["RepoContextBuilder"], repo_path: str) -> RepoContext:
        repo = Path(repo_path)

        tree_summary = cls._build_tree_summary(repo)
        readme = cls._read_if_exists(repo / "README.md")
        agents_md = cls._read_if_exists(repo / "AGENTS.md")
        build_files = cls._summarize_build_files(repo)
        tests_hint = cls._summarize_tests(repo)

        return RepoContext(
            repo_path=str(repo),
            tree_summary=tree_summary,
            readme=readme,
            agents_md=agents_md,
            build_files=build_files,
            tests_hint=tests_hint,
        )

    @classmethod
    def _build_tree_summary(cls: type["RepoContextBuilder"], repo: Path) -> str:
        items = []
        for item in sorted(repo.iterdir()):
            if item.name.startswith("."):
                continue
            if item.is_dir():
                items.append(f"📁 {item.name}/")
            else:
                items.append(f"📄 {item.name}")
        return "\n".join(items) if items else "Empty repository"

    @classmethod
    def _read_if_exists(cls: type["RepoContextBuilder"], file_path: Path) -> str | None:
        if not file_path.exists() or not file_path.is_file():
            return None

        try:
            content = file_path.read_text(encoding="utf-8")
            if len(content) > cls.MAX_FILE_SIZE:
                first_part = content[: cls.TRUNCATE_SIZE]
                last_part = content[-cls.TRUNCATE_SIZE :]
                truncated = len(content) - cls.TRUNCATE_SIZE * 2
                return f"{first_part}\n\n... [truncated {truncated} chars] ...\n\n{last_part}"
            return content
        except Exception:
            return None

    @classmethod
    def _summarize_build_files(cls: type["RepoContextBuilder"], repo: Path) -> str | None:
        build_files = []
        for pattern in ["pyproject.toml", "requirements.txt", "setup.py", "setup.cfg", "Makefile", "package.json"]:
            if (repo / pattern).exists():
                build_files.append(pattern)

        if build_files:
            return f"Build files found: {', '.join(build_files)}"
        return None

    @classmethod
    def _summarize_tests(cls: type["RepoContextBuilder"], repo: Path) -> str | None:
        hints = []
        if (repo / "tests").exists() or (repo / "test").exists():
            hints.append("tests/ directory exists")
        if (repo / "pytest.ini").exists() or (repo / "pytest.ini.py").exists():
            hints.append("pytest.ini found")
        if (repo / "tox.ini").exists():
            hints.append("tox.ini found")

        if hints:
            return "; ".join(hints)
        return None
