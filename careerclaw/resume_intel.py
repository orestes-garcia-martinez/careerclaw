from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import re

from careerclaw.core.text_processing import tokenize_stream, extract_phrases


_IMPACT_RE = re.compile(
    r"(\b\d{1,3}%|\$\s?\d[\d,]*\b|\b\d+\s?(?:years?|months?|weeks?)\b|\b\d+\s?x\b)",
    re.IGNORECASE,
)

# Best-effort section headings. Domain-agnostic.
_SECTION_ALIASES = {
    "skills": {"skills", "core skills", "key skills", "technical skills", "professional skills", "competencies"},
    "summary": {"summary", "professional summary", "profile", "about", "objective"},
    "experience": {"experience", "work experience", "professional experience", "employment"},
    "projects": {"projects", "project experience"},
    "education": {"education", "certifications", "certification", "training"},
    "interests": {"interests", "volunteering", "activities", "hobbies"},
}

_SECTION_WEIGHTS = {
    "skills": 1.0,
    "summary": 0.8,
    "experience": 0.7,
    "projects": 0.7,
    "education": 0.4,
    "interests": 0.2,
    "other": 0.6,
}


@dataclass(frozen=True)
class ResumeIntelligence:
    # Ordered, deterministic signals (first-seen order from combined text)
    extracted_keywords: List[str]
    extracted_phrases: List[str]

    # Optional streams for future UX/agent summaries (kept redundant for clarity)
    keyword_stream: List[str] = field(default_factory=list)
    phrase_stream: List[str] = field(default_factory=list)

    # Impact-like numeric signals for later features (unchanged)
    impact_signals: List[str] = field(default_factory=list)

    # Section weighting maps (signal -> max weight by section)
    keyword_weights: Dict[str, float] = field(default_factory=dict)
    phrase_weights: Dict[str, float] = field(default_factory=dict)

    # provenance
    source: str = "summary_only"  # "summary_only" | "summary_plus_file"


def _extract_impacts(text: str, *, max_items: int = 20) -> List[str]:
    found: List[str] = []
    for m in _IMPACT_RE.finditer(text or ""):
        s = (m.group(0) or "").strip()
        if s and s not in found:
            found.append(s)
        if len(found) >= max_items:
            break
    return found


def _normalize_heading(line: str) -> Optional[str]:
    raw = (line or "").strip()
    if not raw:
        return None
    raw = raw.rstrip(":").strip()
    lowered = raw.lower()
    if len(lowered) > 60:
        return None
    for key, aliases in _SECTION_ALIASES.items():
        if lowered in aliases:
            return key
    return None


def _split_into_sections(resume_text: str) -> Dict[str, str]:
    """
    Best-effort section splitter based on single-line headings.
    Works for .txt reliably; for PDFs it's best-effort.
    """
    if not resume_text or not resume_text.strip():
        return {}

    current = "other"
    sections: Dict[str, List[str]] = {"other": []}

    for line in resume_text.splitlines():
        h = _normalize_heading(line)
        if h:
            current = h
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)

    return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip()}


def _dedupe_first_seen(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for it in items:
        if it and it not in seen:
            out.append(it)
            seen.add(it)
    return out


def build_resume_intelligence(
    *,
    resume_summary: str,
    resume_text: str,
    skills: Optional[List[str]] = None,
    target_roles: Optional[List[str]] = None,
) -> ResumeIntelligence:
    """
    Build resume intelligence from available signal sources.

    Signal priority (highest weight first):
      1. skills / target_roles from UserProfile  → synthetic "skills" section (weight 1.0)
      2. resume_summary                           → "summary" section (weight 0.8)
      3. sections parsed from resume_text         → weighted by section type

    Phase-5E: skills + target_roles are now injected as a synthetic "Skills"
    section so that profile-declared skills always appear in extracted_keywords
    with maximum weight and are correctly treated as *signals* (not gaps) in
    GapAnalysis.
    """
    combined = (resume_summary or "").strip()
    source = "summary_only"

    if resume_text and resume_text.strip():
        combined = (combined + "\n\n" + resume_text.strip()).strip() if combined else resume_text.strip()
        source = "summary_plus_file"

    # Build synthetic skills text from profile lists so they participate in
    # phrase extraction alongside the summary/resume text.
    skills_tokens: List[str] = list(skills or [])
    roles_tokens: List[str] = list(target_roles or [])
    synthetic_skills_text = " ".join(skills_tokens + roles_tokens).strip()
    if synthetic_skills_text:
        # Prepend so profile skills appear first in keyword_stream ordering.
        combined = (synthetic_skills_text + "\n\n" + combined).strip() if combined else synthetic_skills_text

    stream = tokenize_stream(combined)
    keyword_stream = _dedupe_first_seen(stream)
    keywords = keyword_stream  # kept ordered for agent readability
    phrases = extract_phrases(stream, ngrams=(2, 3), max_phrases=30)
    phrase_stream = phrases[:]

    impacts = _extract_impacts(combined)

    # Section weighting maps
    # NOTE: synthetic "skills" section must be inserted FIRST so its weight (1.0)
    # is established before summary (0.8) and resume sections can only raise it, not lower.
    sections: Dict[str, str] = {}
    if synthetic_skills_text:
        sections["skills"] = synthetic_skills_text
    if resume_summary and resume_summary.strip():
        sections["summary"] = resume_summary.strip()
    sections.update(_split_into_sections(resume_text))

    kw_weights: Dict[str, float] = {}
    ph_weights: Dict[str, float] = {}

    for sec_name, sec_text in sections.items():
        w = _SECTION_WEIGHTS.get(sec_name, _SECTION_WEIGHTS["other"])
        sec_stream = tokenize_stream(sec_text)
        sec_kw_stream = _dedupe_first_seen(sec_stream)
        sec_phr = extract_phrases(sec_stream, ngrams=(2, 3), max_phrases=60)

        for k in sec_kw_stream:
            kw_weights[k] = max(kw_weights.get(k, 0.0), w)
        for p in sec_phr:
            ph_weights[p] = max(ph_weights.get(p, 0.0), w)

    return ResumeIntelligence(
        extracted_keywords=keywords,
        extracted_phrases=phrases,
        keyword_stream=keyword_stream,
        phrase_stream=phrase_stream,
        impact_signals=impacts,
        keyword_weights=kw_weights,
        phrase_weights=ph_weights,
        source=source,
    )


def cache_resume_intelligence(path: Path, intel: ResumeIntelligence) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(intel), indent=2), encoding="utf-8")


def resume_intelligence_to_dict(intel: ResumeIntelligence) -> Dict[str, Any]:
    return asdict(intel)
