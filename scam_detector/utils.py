def normalize_label(s: str) -> str:
    """Normalize a label by converting to str, stripping, and replacing spaces with underscores.

    Falls back to 'Other' on error.
    """
    try:
        return str(s).strip().replace(" ", "_")
    except Exception:
        return "Other"
