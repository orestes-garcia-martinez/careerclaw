from __future__ import annotations

import re
from typing import Iterable, Set, List

# NOTE: This module is intentionally "core infrastructure".
# Matching, resume intelligence, requirements extraction, and gap analysis
# should all depend on this module rather than re-implementing tokenization.

_WORD_RE = re.compile(r"[a-z0-9]+(?:[#+.-][a-z0-9]+)*", re.IGNORECASE)

# Keep this small + stable for deterministic MVP
_STOPWORDS = {
    "the", "and", "or", "to", "of", "in", "for", "on", "with", "a", "an", "as",
    "is", "are", "be", "by", "at", "from", "this", "that", "it", "you", "we",
    "our", "your", "they", "their", "will", "can", "may", "must",
    "role", "roles", "job", "jobs", "position", "positions",
}

def tokenize(text: str) -> Set[str]:
    """
    Deterministic, lightweight tokenizer:
    - lowercases
    - extracts alnum-ish tokens, allowing + # . - inside tokens (e.g., c#, c++, node.js)
    - removes short noise + stopwords
    """
    if not text:
        return set()

    tokens: Set[str] = set()
    for m in _WORD_RE.finditer(text.lower()):
        tok = m.group(0).strip(".-")
        if len(tok) < 2:
            continue
        if tok in _STOPWORDS:
            continue
        tokens.add(tok)
    return tokens


def tokenize_stream(text: str) -> List[str]:
    """
    Ordered token stream (deterministic) using the same rules as tokenize().
    Useful for phrase extraction (bigrams/trigrams) and other ordered analyses.
    """
    if not text:
        return []

    out: List[str] = []
    for m in _WORD_RE.finditer(text.lower()):
        tok = m.group(0).strip(".-")
        if len(tok) < 2:
            continue
        if tok in _STOPWORDS:
            continue
        out.append(tok)
    return out


def tokens_from_list(items: Iterable[str]) -> Set[str]:
    out: Set[str] = set()
    for it in items or []:
        out |= tokenize(it)
    return out
