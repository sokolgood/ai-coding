import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gh_token: str
    repo: str
    llm_api_key: str = ""
    llm_base_url: str | None = None
    repo_path: str = "/repo"
    ci_conclusion: str | None = None

    class Config:
        env_prefix = ""
        case_sensitive = False

    @property
    def repo_owner(self) -> str:
        return self.repo.split("/")[0]

    @property
    def repo_name(self) -> str:
        return self.repo.split("/")[1]


def get_settings() -> Settings:
    return Settings(
        gh_token=os.getenv("GH_TOKEN", ""),
        repo=os.getenv("REPO", ""),
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        llm_base_url=os.getenv("LLM_BASE_URL") or None,
        repo_path=os.getenv("REPO_PATH", "/repo"),
        ci_conclusion=os.getenv("CI_CONCLUSION") or None,
    )
