from typing import Literal

from src.config import Settings
from src.types.git_provider import AuthProvider


class SimpleAuthProvider(AuthProvider):
    def __init__(self, settings: Settings):
        self.settings = settings

    def get_token(self, identity: Literal["coder", "reviewer"]) -> str:
        return self.settings.gh_token
