import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gh_token: str
    repo: str
    llm_api_key: str = ""
    llm_base_url: str | None = None
    llm_model_name: str = "gpt-4o-mini"
    repo_path: str = "/repo"
    ci_conclusion: str | None = None
    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_base_url: str = "https://cloud.langfuse.com"

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
        llm_model_name="gpt-4o-mini",  # os.getenv("LLM_MODEL_NAME", "gpt-4o-mini"),
        repo_path=os.getenv("REPO_PATH", "/repo"),
        ci_conclusion=os.getenv("CI_CONCLUSION") or None,
        langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
        langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
        langfuse_base_url=os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com"),
    )
