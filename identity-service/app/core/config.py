from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Modélise la structure "Settings"."""

    service_name: str = Field(default="identity-service", alias="SERVICE_NAME")
    service_version: str = Field(default="0.1.0", alias="SERVICE_VERSION")

    database_url: str = Field(default="sqlite:///./identity.db", alias="DATABASE_URL")

    jwt_secret_key: str = Field(default="dev-secret-change-me", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expires_seconds: int = Field(
        default=900,
        alias="JWT_ACCESS_TOKEN_EXPIRES_SECONDS",
    )
    jwt_issuer: str = Field(default="identity-service", alias="JWT_ISSUER")
    jwt_audience: str = Field(default="gf-task-management", alias="JWT_AUDIENCE")

    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)


settings = Settings()
