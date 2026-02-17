from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import re

from careerclaw.core.text_processing import tokenize, tokenize_stream


_IMPACT_RE = re.compile(
    r"(\b\d{1,3}%|\$\s?\d[\d,]*\b|\b\d+\s?(?:years?|months?|weeks?)\b|\b\d+\s?x\b)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ResumeIntelligence:
    extracted_keywords: List[str]
    extracted_phrases: List[str]
    impact_signals: List[str]
    source: str  # "summary_only" | "summary_plus_file"


def _extract_phrases(tokens: List[str], *, max_phrases: int = 30) -> List[str]:
    """Deterministic bigram phrases."""
    if len(tokens) < 2:
        return []
    counts: Dict[str, int] = {}
    for i in range(len(tokens) - 1):
        bg = f"{tokens[i]} {tokens[i+1]}"
        counts[bg] = counts.get(bg, 0) + 1
    # sort: frequency desc, then lexicographic for determinism
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [p for p, _ in ordered[:max_phrases]]


def _extract_impacts(text: str, *, max_items: int = 20) -> List[str]:
    found = []
    for m in _IMPACT_RE.finditer(text or ""):
        s = (m.group(0) or "").strip()
        if s and s not in found:
            found.append(s)
        if len(found) >= max_items:
            break
    return found


def build_resume_intelligence(*, resume_summary: str, resume_text: str) -> ResumeIntelligence:
    combined = (resume_summary or "").strip()
    source = "summary_only"
    if resume_text and resume_text.strip():
        combined = (combined + "\n\n" + resume_text.strip()).strip() if combined else resume_text.strip()
        source = "summary_plus_file"

    kw = sorted(tokenize(combined))
    stream = tokenize_stream(combined)
    phrases = _extract_phrases(stream)
    impacts = _extract_impacts(combined)

    return ResumeIntelligence(
        extracted_keywords=kw,
        extracted_phrases=phrases,
        impact_signals=impacts,
        source=source,
    )


def cache_resume_intelligence(path: Path, intel: ResumeIntelligence) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(intel), indent=2), encoding="utf-8")


def resume_intelligence_to_dict(intel: ResumeIntelligence) -> Dict[str, Any]:
    return asdict(intel)
