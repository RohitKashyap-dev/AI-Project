from backend.core.config import Settings


def test_postgres_async_dsn_removes_asyncpg_unsupported_params():
    settings = Settings(
        DATABASE_URL="postgresql://user:pass@host:5432/db?sslmode=require&channel_binding=require"
    )

    dsn = settings.postgres_async_dsn

    assert dsn.startswith("postgresql+asyncpg://")
    assert "sslmode=require" not in dsn
    assert "channel_binding=require" not in dsn


def test_postgres_dsn_removes_unsupported_params():
    settings = Settings(
        DATABASE_URL="postgresql://user:pass@host:5432/db?sslmode=require&channel_binding=require"
    )

    dsn = settings.postgres_dsn

    assert dsn.startswith("postgresql+psycopg://")
    assert "sslmode=require" not in dsn
    assert "channel_binding=require" not in dsn
