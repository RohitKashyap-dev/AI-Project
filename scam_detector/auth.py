import os
import time
import typing

import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = "HS256"
_bearer = HTTPBearer(auto_error=False)


def create_token(subject: str, role: str = "user", expires_minutes: int = 60) -> str:
    payload = {"sub": subject, "role": role, "exp": int(time.time()) + expires_minutes * 60}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str) -> typing.Dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def require_jwt(credentials: HTTPAuthorizationCredentials = Depends(_bearer)):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return decode_token(credentials.credentials)


def require_role(role: str):
    def _checker(claims = Depends(require_jwt)):
        if claims.get("role") != role:
            raise HTTPException(status_code=403, detail="Insufficient privileges")
        return claims

    return _checker
