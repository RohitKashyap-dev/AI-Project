"""Simple in-memory user store for demo purposes.

This is NOT production-ready. Replace with a proper user database
and password hashing + salting in real deployments.
"""
import os
import hashlib
import hmac
from typing import Optional, Dict

# Helper: create a salted SHA256 hash (demo only)
def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


# Pre-populated demo users. Passwords are 'password' by default.
# Change these or load from a secure store for real usage.
_USERS: Dict[str, Dict] = {}

def _add_demo_user(username: str, raw_password: str, role: str = "user"):
    salt = os.getenv(f"{username.upper()}_SALT") or os.urandom(8).hex()
    pwd_hash = _hash_password(raw_password, salt)
    _USERS[username] = {"salt": salt, "password_hash": pwd_hash, "role": role}


# Ensure admin and user exist for local testing
if "admin" not in _USERS:
    _add_demo_user("admin", os.getenv("ADMIN_PASSWORD", "password"), role="admin")
if "user" not in _USERS:
    _add_demo_user("user", os.getenv("USER_PASSWORD", "password"), role="user")


def verify_user(username: str, password: str) -> Optional[dict]:
    entry = _USERS.get(username)
    if not entry:
        return None
    expected = entry["password_hash"]
    salt = entry["salt"]
    candidate = _hash_password(password, salt)
    if hmac.compare_digest(expected, candidate):
        return {"username": username, "role": entry.get("role", "user")}
    return None


def create_user(username: str, password: str, role: str = "user"):
    if username in _USERS:
        raise ValueError("User already exists")
    salt = os.urandom(8).hex()
    _USERS[username] = {"salt": salt, "password_hash": _hash_password(password, salt), "role": role}
