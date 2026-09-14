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

    try:
        logger.info("Invoking LLM for classification")
        raw = get_llm(model_name).invoke(prompt)
        inner = extract_text_from_response(raw)
        parsed = parse_model_output(output_parser, inner)
        logger.info("Successfully parsed response: %s", parsed.is_scam)
        return parsed
    except Exception as exc:
        logger.error("Failed to parse model output: %s", str(exc), exc_info=True)
        print("Failed to parse model output:", exc)
        return None
