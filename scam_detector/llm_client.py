from langchain_google_genai import ChatGoogleGenerativeAI

from scam_detector.config import GOOGLE_API_KEY, MODEL_NAME

_llm = None


def get_llm(model_name: str | None = None) -> ChatGoogleGenerativeAI:
    global _llm
    selected = model_name or MODEL_NAME
    if _llm is None or getattr(_llm, "model", None) != selected:
        if not GOOGLE_API_KEY:
            raise RuntimeError("GOOGLE_API_KEY is not set. Add it to your .env file.")
        _llm = ChatGoogleGenerativeAI(model=selected, api_key=GOOGLE_API_KEY)
    return _llm
