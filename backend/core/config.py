from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


def sanitize_database_url(url: str) -> str:
    """Remove query params that are not accepted by asyncpg/psycopg in Render/Neon setups."""
    if not url:
        return url

    split = urlsplit(url)
    query = []
    for key, value in parse_qsl(split.query, keep_blank_values=True):
        if key in {"sslmode", "channel_binding"}:
            continue
        query.append((key, value))

    return urlunsplit(split._replace(query=urlencode(query)))


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

    DATABASE_URL: str | None = None
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
        if self.DATABASE_URL:
            safe_url = sanitize_database_url(self.DATABASE_URL)
            jdbc_url = safe_url.replace("postgres://", "postgresql+psycopg://", 1)
            return jdbc_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def postgres_async_dsn(self) -> str:
        if self.DATABASE_URL:
            safe_url = sanitize_database_url(self.DATABASE_URL)
            psql_url = safe_url.replace("postgres://", "postgresql+asyncpg://", 1)
            return psql_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
