from langchain_google_genai import ChatGoogleGenerativeAI

from scam_detector.config import GOOGLE_API_KEY, MODEL_NAME

_llm = None


def get_model_candidates(model_name: str | None = None):
    selected = model_name or MODEL_NAME or "gemini-3.1-flash-lite"
    preferred = [selected]
    fallbacks = [
        "gemini-3.1-flash-lite",
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash",
    ]
    for candidate in fallbacks:
        if candidate not in preferred:
            preferred.append(candidate)
    return preferred


def get_llm(model_name: str | None = None) -> ChatGoogleGenerativeAI:
    global _llm
    selected = model_name or MODEL_NAME or "gemini-3.1-flash-lite"
    candidates = get_model_candidates(selected)
    last_error = None

    for candidate in candidates:
        try:
            if _llm is None or getattr(_llm, "model", None) != candidate:
                if not GOOGLE_API_KEY:
                    raise RuntimeError("GOOGLE_API_KEY is not set. Add it to your .env file.")
                _llm = ChatGoogleGenerativeAI(model=candidate, api_key=GOOGLE_API_KEY)
            return _llm
        except Exception as exc:  # pragma: no cover - exercised in production via runtime fallback
            last_error = exc
            continue

    raise last_error or RuntimeError(f"Failed to initialize Gemini model: {selected}")
