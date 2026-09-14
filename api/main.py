from typing import Optional

from fastapi import FastAPI, HTTPException, Body, Depends
from pydantic import BaseModel, Field

from scam_detector.service import analyze_message
from scam_detector.auth import create_token, require_jwt
from scam_detector.users import verify_user

app = FastAPI(title="Scam Detector API", version="1.0.0")


class AnalyzeRequest(BaseModel):
    message: str = Field(min_length=1)
    model_name: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


# Simple token endpoint (demo). Replace _verify_user with real user store.
def _verify_user(username: str, password: str) -> Optional[dict]:
    # Delegate to the users module (in-memory demo store)
    return verify_user(username, password)


@app.post("/token")
def token(username: str = Body(...), password: str = Body(...)):
    user = _verify_user(username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user["username"], role=user["role"])
    return {"access_token": token, "token_type": "bearer"}


@app.post("/analyze")
def analyze(request: AnalyzeRequest, claims=Depends(require_jwt)):
    try:
        # claims is the decoded token payload (sub, role, exp)
        return analyze_message(request.message, model_name=request.model_name)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
