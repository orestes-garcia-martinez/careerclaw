from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Set, List, Sequence, Tuple

# NOTE: This module is intentionally "core infrastructure".
# Matching, resume intelligence, requirements extraction, and gap analysis
# should all depend on this module rather than re-implementing tokenization.

# Token pattern:
# - alphanumerics
# - allows internal separators like + # . - (e.g., c#, c++, node.js, customer-service)
_WORD_RE = re.compile(r"[a-z0-9]+(?:[#+.-][a-z0-9]+)*", re.IGNORECASE)

# Domain-agnostic stopwords. Keep stable; tune conservatively.
_STOPWORDS = {
    "a", "an", "the", "and", "or", "to", "of", "in", "for", "on", "with", "as", "at", "by", "from",
    "is", "are", "be", "been", "being", "was", "were", "am",
    "this", "that", "these", "those", "it", "its", "they", "them", "their", "you", "your", "we", "our", "i", "me", "my",
    "will", "can", "may", "must", "should", "could", "would",
    "not", "no", "yes",
    "into", "over", "under", "between", "within", "without", "across", "per",
    "about", "also", "such", "than", "then", "there", "here",
    # common boilerplate words in listings
    "role", "roles", "job", "jobs", "position", "positions", "responsibilities", "responsibility",
    "requirements", "required", "preferred", "skills", "skill", "experience", "team", "work",
    # Phase-5E: recruitment process noise — these carry zero signal value for matching
    # and pollute gap keyword lists and score denominators.
    "apply", "applying", "applicant", "applicants", "application", "applications", "submit", "submission",
    "candidate", "candidates", "qualified", "successful", "shortlisted",
    "interview", "interviewing", "hire", "hiring", "onboard", "onboarding",
    "competitive", "opportunity", "opportunities", "benefit", "benefits", "package",
    "responsible", "seeking", "looking", "welcome", "encouraged",
    "bonus", "nice", "have",
    # URL noise — appear in resume headers (LinkedIn, GitHub links) and HN posts
    "https", "http", "www",
    # Contact info noise from resume headers
    "linkedin", "github", "gmail",
}


def normalize_text(text: str) -> str:
    """
    Deterministic normalization for downstream tokenization/phrase extraction.

    Goals:
    - stable across platforms
    - remove unicode quirks (smart quotes, non-breaking spaces)
    - collapse whitespace
    """
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", text)
    # Common whitespace normalization (NBSP)
    t = t.replace(" ", " ")
    # Normalize common unicode dashes to '-'
    t = re.sub(r"[‐-―]", "-", t)
    # Collapse whitespace
    t = " ".join(t.split())
    return t


def tokenize_stream(text: str) -> List[str]:
    """Ordered token stream (deterministic)."""
    if not text:
        return []
    normalized = normalize_text(text).lower()
    out: List[str] = []
    for m in _WORD_RE.finditer(normalized):
        tok = m.group(0).strip(".-")
        if len(tok) < 2:
            continue
        if tok in _STOPWORDS:
            continue
        out.append(tok)
    return out


def tokenize(text: str) -> Set[str]:
    """Token set (deterministic), derived from tokenize_stream."""
    return set(tokenize_stream(text))


def tokens_from_list(items: Iterable[str]) -> Set[str]:
    out: Set[str] = set()
    for it in items or []:
        out |= tokenize(it)
    return out


def extract_phrases(
        tokens: Sequence[str],
        *,
        ngrams: Tuple[int, ...] = (2, 3),
        max_phrases: int = 50,
) -> List[str]:
    """
    Deterministic phrase extraction from an ordered token stream.

    - Generates n-grams (default: bigrams + trigrams)
    - Preserves first-seen order
    - Filters phrases that start/end with stopwords
    - Filters phrases that are mostly numeric
    """
    if not tokens:
        return []

    out: List[str] = []
    seen = set()

    def _is_mostly_numeric(phrase_tokens: Sequence[str]) -> bool:
        if not phrase_tokens:
            return True
        numeric = sum(1 for t in phrase_tokens if t.isdigit())
        return numeric >= max(1, len(phrase_tokens) - 1)

    for n in ngrams:
        if n < 2:
            continue
        if len(tokens) < n:
            continue
        for i in range(0, len(tokens) - n + 1):
            chunk = tokens[i : i + n]
            if not chunk:
                continue
            # tokens are already filtered, but keep this safeguard
            if chunk[0] in _STOPWORDS or chunk[-1] in _STOPWORDS:
                continue
            if _is_mostly_numeric(chunk):
                continue
            phrase = " ".join(chunk)
            if phrase in seen:
                continue
            seen.add(phrase)
            out.append(phrase)
            if len(out) >= max_phrases:
                return out

    return out
