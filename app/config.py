"""Application settings loaded from environment / .env file."""

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    # AWS Cognito
    cognito_region: str          # e.g. "us-east-1"
    cognito_user_pool_id: str    # e.g. "us-east-1_XXXXXXX"
    cognito_client_id: str       # App client ID (used for ID-token audience check)

    # Database
    database_url: str            # asyncpg DSN, e.g. "postgresql+asyncpg://app:app@db/app"

    # Optional
    app_base_url: str = "http://localhost:8001"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def cognito_jwks_url(self) -> str:
        return (
            f"https://cognito-idp.{self.cognito_region}.amazonaws.com"
            f"/{self.cognito_user_pool_id}/.well-known/jwks.json"
        )

    @property
    def cognito_issuer(self) -> str:
        return (
            f"https://cognito-idp.{self.cognito_region}.amazonaws.com"
            f"/{self.cognito_user_pool_id}"
        )


settings = Settings()
