from __future__ import annotations

from dataclasses import dataclass
from typing import List, Set

from careerclaw.models import NormalizedJob
from careerclaw.core.text_processing import tokenize, tokenize_stream, extract_phrases


def _dedupe_first_seen(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for it in items:
        if it and it not in seen:
            out.append(it)
            seen.add(it)
    return out


@dataclass(frozen=True)
class JobRequirements:
    """
    Deterministic, domain-agnostic "requirement signals" extracted from a job posting.

    Phase-5C introduced keywords(set) + phrases(list). Phase-5D adds ordered keyword_stream
    so downstream outputs can preserve JOB order deterministically (better for agent contexts).
    """
    keywords: Set[str]
    keyword_stream: List[str]  # ordered, first-seen, deduped
    phrases: List[str]         # ordered, first-seen (bigrams/trigrams)


def extract_job_requirements(job: NormalizedJob, *, max_phrases: int = 40) -> JobRequirements:
    """
    Extract keywords + phrases from job title + description (and tags if present).
    - keywords: set() for fast overlap checks
    - keyword_stream: ordered tokens (first-seen, deduped) for stable human/agent presentation
    - phrases: ordered list (first-seen), deterministic bigrams/trigrams
    """
    text_parts = [job.title or "", job.description or ""]
    if job.tags:
        text_parts.append(" ".join(job.tags))
    text = "\n".join(text_parts)

    stream = tokenize_stream(text)
    keyword_stream = _dedupe_first_seen(stream)
    keywords = tokenize(text)
    phrases = extract_phrases(stream, ngrams=(2, 3), max_phrases=max_phrases)
    return JobRequirements(keywords=keywords, keyword_stream=keyword_stream, phrases=phrases)
