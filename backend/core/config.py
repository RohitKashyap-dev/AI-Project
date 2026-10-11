from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_api_url(base_url: str) -> str:
    """Normalize the API base URL to include the FastAPI v1 prefix."""
    cleaned = (base_url or "").strip()
    if not cleaned:
        return ""

    cleaned = cleaned.rstrip("/")
    if cleaned.endswith("/api/v1"):
        return cleaned
    if cleaned.endswith("/api"):
        return f"{cleaned}/v1"
    return f"{cleaned}/api/v1"


class Settings(BaseSettings):
    APP_NAME: str = "Scam Detector API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    JWT_SECRET: str = "change-me-super-secret-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "scamdetector"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    REDIS_URL: str = "redis://localhost:6379/0"
    GOOGLE_API_KEY: str | None = None

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "password"

    VECTOR_BACKEND: str = "pgvector"
    PINECONE_API_KEY: str | None = None
    PINECONE_INDEX_NAME: str = "scam-detector"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def postgres_async_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
