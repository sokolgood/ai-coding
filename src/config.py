import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gh_token: str
    repo: str
    llm_api_key: str = ""
    repo_path: str = "/repo"

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
        repo_path=os.getenv("REPO_PATH", "/repo"),
    )
