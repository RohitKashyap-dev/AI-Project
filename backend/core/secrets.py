import os
from pathlib import Path


def get_secret(name: str, default: str | None = None, *, required: bool = False) -> str | None:
    value = os.getenv(name)
    if value is not None and value != "":
        return value

    if required:
        raise RuntimeError(f"Missing required secret: {name}")

    if default is not None:
        return default

    if Path("/run/secrets").exists():
        secret_path = Path("/run/secrets") / name.lower()
        if secret_path.exists():
            return secret_path.read_text().strip()

    return default
