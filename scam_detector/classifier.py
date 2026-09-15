from langchain_core.output_parsers import PydanticOutputParser

from scam_detector.llm_client import get_llm
from scam_detector.logging_config import get_logger
from scam_detector.prompts import SYSTEM_PROMPT
from scam_detector.response_parser import extract_text_from_response, parse_model_output
from scam_detector.schemas import ScamDetector

logger = get_logger(__name__)
output_parser = PydanticOutputParser(pydantic_object=ScamDetector)


def classify_message(message: str, model_name: str | None = None) -> ScamDetector | None:
    logger.info("Classifying message: %s...", message[:100])
    fmt = output_parser.get_format_instructions()
    prompt = f"{SYSTEM_PROMPT}\n\nFormat instructions:\n{fmt}\n\nMessage:\n{message}\n"

    candidate_names = []
    if model_name:
        candidate_names.append(model_name)
    candidate_names.extend([
        "gemini-3.1-flash-lite",
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
    ])

    seen = set()
    ordered_models = []
    for name in candidate_names:
        if name and name not in seen:
            ordered_models.append(name)
            seen.add(name)

    last_error = None
    for candidate in ordered_models:
        try:
            logger.info("Invoking LLM for classification with model: %s", candidate)
            raw = get_llm(candidate).invoke(prompt)
            inner = extract_text_from_response(raw)
            parsed = parse_model_output(output_parser, inner)
            logger.info("Successfully parsed response: %s", parsed.is_scam)
            return parsed
        except Exception as exc:
            last_error = exc
            logger.warning("Model %s failed; trying fallback model. Error: %s", candidate, exc)

    logger.error("All model attempts failed: %s", last_error, exc_info=True)
    print("Failed to parse model output:", last_error)
    return None
