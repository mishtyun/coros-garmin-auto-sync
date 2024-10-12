import hashlib

from pydantic_settings import BaseSettings, SettingsConfigDict


class CorosConfiguration(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="coros_", env_file="../.env", extra="allow"
    )

    api_url: str
    email: str
    password: str

    access_token: str | None = None

    @property
    def hashed_password(self):
        return hashlib.md5(self.password.encode()).hexdigest()
