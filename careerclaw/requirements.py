from __future__ import annotations

from dataclasses import dataclass
from typing import List, Set

from careerclaw.models import NormalizedJob
from careerclaw.core.text_processing import tokenize, tokenize_stream, extract_phrases


@dataclass(frozen=True)
class JobRequirements:
    """
    Deterministic, domain-agnostic "requirements signals" extracted from a job posting.
    We intentionally avoid trying to classify required vs. preferred in Phase-5C.
    """
    keywords: Set[str]
    phrases: List[str]


def extract_job_requirements(job: NormalizedJob, *, max_phrases: int = 40) -> JobRequirements:
    """
    Extract keywords + phrases from job title + description (and tags if present).
    - Keywords: set() for fast overlap checks.
    - Phrases: ordered list (first-seen), deterministic bigrams/trigrams.
    """
    text_parts = [job.title or "", job.description or ""]
    if job.tags:
        text_parts.append(" ".join(job.tags))
    text = "\n".join(text_parts)

    stream = tokenize_stream(text)
    keywords = tokenize(text)
    phrases = extract_phrases(stream, ngrams=(2, 3), max_phrases=max_phrases)
    return JobRequirements(keywords=keywords, phrases=phrases)
