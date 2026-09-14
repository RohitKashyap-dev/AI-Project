import json


def extract_text_from_response(raw) -> str:
    """Extract the inner text (JSON) from various SDK response shapes."""
    if isinstance(raw, str):
        return raw

    if isinstance(raw, dict):
        for key in ("content", "choices", "output", "text"):
            if key in raw:
                content = raw[key]
                if isinstance(content, list) and content:
                    first = content[0]
                    if isinstance(first, dict):
                        return first.get("text") or first.get("content") or str(first)
                    return str(first)
                if isinstance(content, dict):
                    return content.get("text") or str(content)
                if isinstance(content, str):
                    return content
        for value in raw.values():
            if isinstance(value, str) and value.strip().startswith("{"):
                return value

    if isinstance(raw, list) and raw:
        first = raw[0]
        if isinstance(first, dict):
            if "content" in first:
                content = first["content"]
                if isinstance(content, list) and content and isinstance(content[0], dict):
                    return content[0].get("text") or content[0].get("content") or str(content[0])
            for key in ("text", "content"):
                if key in first:
                    return first[key]
        return str(first)

    if hasattr(raw, "content"):
        content = getattr(raw, "content")
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict):
                return first.get("text") or first.get("content") or str(first)
            return str(first)
        if isinstance(content, str):
            return content

    if hasattr(raw, "choices"):
        choices = getattr(raw, "choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                return first.get("text") or str(first)
            return str(first)

    try:
        return str(raw)
    except Exception:
        return ""


def parse_model_output(parser, inner: str):
    try:
        return parser.parse(inner)
    except Exception:
        obj = json.loads(inner)
        try:
            return parser.parse(obj)
        except Exception:
            return parser.parse(json.dumps(obj))
