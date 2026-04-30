from __future__ import annotations


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, round(len(text) / 4))
