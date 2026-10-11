from __future__ import annotations

import re


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    cleaned = (text or "").strip()
    if not cleaned:
        return []

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", cleaned) if s.strip()]
    if not sentences:
        return [cleaned]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        sentence_len = len(sentence)
        if current and current_len + sentence_len > chunk_size:
            chunks.append(" ".join(current))
            overlap_words = current[-1].split()
            current = overlap_words[: max(1, min(len(overlap_words), overlap // 5))]
            current_len = sum(len(w) for w in current)

        current.append(sentence)
        current_len += sentence_len

    if current:
        chunks.append(" ".join(current))

    return chunks if chunks else [cleaned]
