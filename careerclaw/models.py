from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, date
from enum import Enum
from typing import Any, Dict, List, Optional
import hashlib


class JobSource(str, Enum):
    REMOTEOK = "remoteok"
    HN_WHO_IS_HIRING = "hn_who_is_hiring"


class ApplicationStatus(str, Enum):
    SAVED = "saved"
    APPLIED = "applied"
    INTERVIEW = "interview"
    REJECTED = "rejected"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_whitespace(text: str) -> str:
    return " ".join((text or "").split()).strip()


def stable_job_id(
        source: JobSource,
        canonical_url: Optional[str],
        title: str,
        company: str,
        posted_at: Optional[datetime],
) -> str:
    """
    Stable ID based on the source + canonical_url (if any) + title + company + posted_at (date).
    This lets you dedupe across runs and keeps tracking stable.
    """
    posted_key = posted_at.date().isoformat() if posted_at else "unknown-date"
    base = "|".join(
        [
            source.value,
            (canonical_url or "").strip().lower(),
            normalize_whitespace(title).lower(),
            normalize_whitespace(company).lower(),
            posted_key,
        ]
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class NormalizedJob:
    """
    The canonical job record used across CareerClaw.
    Adapters MUST return this shape.
    """
    source: JobSource
    title: str
    company: str
    description: str

    # Optional fields (not guaranteed from all sources)
    location: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    posted_at: Optional[datetime] = None

    # Provenance / links
    canonical_url: Optional[str] = None
    source_ref: Optional[str] = None  # e.g., HN item id, RemoteOK slug, etc.

    # Stable ID for tracking/dedupe
    job_id: str = field(init=False)

    def __post_init__(self) -> None:
        # Normalize core strings
        object.__setattr__(self, "title", normalize_whitespace(self.title))
        object.__setattr__(self, "company", normalize_whitespace(self.company))
        object.__setattr__(self, "description", normalize_whitespace(self.description))
        if self.location is not None:
            object.__setattr__(self, "location", normalize_whitespace(self.location))

        # Normalize tags (lowercase, trimmed, unique)
        cleaned_tags = []
        seen = set()
        for t in self.tags or []:
            nt = normalize_whitespace(t).lower()
            if nt and nt not in seen:
                cleaned_tags.append(nt)
                seen.add(nt)
        object.__setattr__(self, "tags", cleaned_tags)

        # Normalize posted_at to UTC if present
        if self.posted_at is not None and self.posted_at.tzinfo is None:
            object.__setattr__(self, "posted_at", self.posted_at.replace(tzinfo=timezone.utc))

        jid = stable_job_id(
            source=self.source,
            canonical_url=self.canonical_url,
            title=self.title,
            company=self.company,
            posted_at=self.posted_at,
        )
        object.__setattr__(self, "job_id", jid)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Serialize datetime to ISO
        if d.get("posted_at"):
            d["posted_at"] = self.posted_at.isoformat()  # type: ignore[union-attr]
        return d


@dataclass(frozen=True)
class UserProfile:
    """
    Minimal profile for MVP matching and drafting.
    """
    skills: List[str]
    target_roles: List[str]
    experience_years: int
    work_mode: str  # "remote" | "onsite" | "hybrid"
    resume_summary: str

    location: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "skills", [normalize_whitespace(s) for s in self.skills if normalize_whitespace(s)])
        object.__setattr__(self, "target_roles", [normalize_whitespace(r) for r in self.target_roles if normalize_whitespace(r)])
        object.__setattr__(self, "resume_summary", normalize_whitespace(self.resume_summary))
        if self.location is not None:
            object.__setattr__(self, "location", normalize_whitespace(self.location))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TrackingEntry:
    """
    Simple persistence record for MVP.
    """
    job_id: str
    status: ApplicationStatus = ApplicationStatus.SAVED
    saved_at: datetime = field(default_factory=utc_now)

    applied_at: Optional[datetime] = None
    notes: Optional[str] = None
    next_action_date: Optional[date] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["saved_at"] = self.saved_at.isoformat()
        if self.applied_at:
            d["applied_at"] = self.applied_at.isoformat()
        if self.next_action_date:
            d["next_action_date"] = self.next_action_date.isoformat()
        return d


@dataclass(frozen=True)
class BriefingRun:
    """
    Instrumentation primitive: how we measure stickiness.
    """
    user_id: str
    ran_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {"user_id": self.user_id, "ran_at": self.ran_at.isoformat()}
