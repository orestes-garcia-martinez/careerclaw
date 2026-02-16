from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from careerclaw import config
import html as html_module
import json
import re

from careerclaw.models import JobSource, NormalizedJob, normalize_whitespace


HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
HN_ITEM_WEB_URL = "https://news.ycombinator.com/item?id={item_id}"

_TAG_RE = re.compile(r"</?\w+(?:\s+[^<>]*?)?>")
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_WHITESPACE_RUN_RE = re.compile(r"[ \t]{2,}")
_BLANK_LINES_RE = re.compile(r"\n{3,}")

def _fetch_json(url: str, timeout_seconds: int = config.HTTP_TIMEOUT_SECONDS) -> Dict[str, Any]:
    req = Request(
        url,
        headers={
            "User-Agent": config.USER_AGENT
        },
    )
    try:
        with urlopen(req, timeout=timeout_seconds) as resp:
            data = resp.read().decode("utf-8", errors="replace")
            return json.loads(data)
    except (HTTPError, URLError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Failed to fetch HN JSON: {e}") from e


def _hn_item(item_id: int) -> Dict[str, Any]:
    return _fetch_json(HN_ITEM_URL.format(item_id=item_id))


def _unix_to_utc(ts: Optional[int]) -> Optional[datetime]:
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def fetch_hn_whos_hiring_jobs_default(limit_comments: int = config.HN_MAX_COMMENTS) -> List[NormalizedJob]:
    thread_id = config.HN_WHO_IS_HIRING_THREAD_ID
    if not thread_id or thread_id <= 0:
        raise ValueError("HN_WHO_IS_HIRING_THREAD_ID is not set in careerclaw/config.py")
    return fetch_hn_whos_hiring_jobs(thread_id, limit_comments=limit_comments)


def fetch_hn_whos_hiring_jobs(
        whos_hiring_thread_id: int,
        limit_comments: int = 200,
) -> List[NormalizedJob]:
    """
    Fetch jobs from a HN 'Who is hiring?' thread.

    Args:
        whos_hiring_thread_id: HN item id for the monthly thread post.
        limit_comments: max number of top-level comments to process (MVP guardrail).

    Returns:
        List[NormalizedJob]
    """
    thread = _hn_item(whos_hiring_thread_id)
    kids = thread.get("kids") or []
    kids = kids[: max(0, limit_comments)]

    jobs: List[NormalizedJob] = []

    for comment_id in kids:
        try:
            c = _hn_item(int(comment_id))
        except Exception:
            continue

        # Skip deleted/dead comments
        if c.get("deleted") or c.get("dead"):
            continue

        text_html = c.get("text") or ""
        text = _strip_hn_html(text_html)
        text = normalize_whitespace(text)

        if not text:
            continue

        posted_at = _unix_to_utc(c.get("time"))
        canonical_url = HN_ITEM_WEB_URL.format(item_id=int(comment_id))

        title, company, location = _best_effort_parse_header(text)

        jobs.append(
            NormalizedJob(
                source=JobSource.HN_WHO_IS_HIRING,
                title=title,
                company=company,
                description=text,
                location=location,
                tags=[],  # HN is freeform; tags can be added later via NLP or heuristics
                posted_at=posted_at,
                canonical_url=canonical_url,
                source_ref=str(comment_id),
            )
        )

    return jobs


def _normalize_multiline(text: str) -> str:
    """
    Whitespace normalization that preserves paragraph breaks.
    Use for long-form content like job descriptions.
    """
    if not text:
        return ""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = "\n".join(line.strip() for line in t.split("\n"))
    t = _WHITESPACE_RUN_RE.sub(" ", t)
    t = _BLANK_LINES_RE.sub("\n\n", t)
    return t.strip()


def _strip_hn_html(raw_html: str) -> str:
    """
    HN comment 'text' is HTML. MVP-grade conversion:
    - Convert <p> and <br> to newlines
    - Strip tags safely
    - Decode ALL HTML entities (e.g., &#x2F; -> /)
    - Normalize whitespace
    """
    if not raw_html:
        return ""

    raw = (
        raw_html.replace("<p>", "\n\n")
        .replace("<br>", "\n")
        .replace("<br/>", "\n")
        .replace("<br />", "\n")
    )

    raw = _COMMENT_RE.sub(" ", raw)
    raw = _TAG_RE.sub(" ", raw)

    # This fixes Kotlin&#x2F;Java... -> Kotlin/Java...
    raw = html_module.unescape(raw)
    return _normalize_multiline(raw)


def _best_effort_parse_header(text: str) -> Tuple[str, str, Optional[str]]:
    """
    HN 'Who is hiring' conventions vary, but many follow:
    "Company | Location | Remote | Role | ..."

    We try:
    - first line / first sentence split on '|'
    - company = first segment
    - role/title = best matching segment (heuristic)
    - location = segment containing common location cues
    Fallbacks:
    - company="Unknown"
    - title="Hiring"
    """
    # Take the first ~200 chars as "header zone"
    header_zone = text.split("\n", 1)[0]
    header_zone = header_zone[:200]

    parts = [normalize_whitespace(p) for p in header_zone.split("|")]
    parts = [p for p in parts if p]

    company = "Unknown"
    title = "Hiring"
    location: Optional[str] = None

    if parts:
        company = parts[0] if len(parts[0]) <= 80 else parts[0][:80]

        # Identify location-ish tokens
        location = _pick_location(parts[1:]) if len(parts) > 1 else None

        # Identify role-ish token: look for common role keywords
        role = _pick_role(parts[1:])
        if role:
            title = role

    # If company still unknown and text begins with something like "ACME (YC W23)"
    if company == "Unknown":
        m = re.match(r"^([A-Za-z0-9&.,'()\-\s]{2,80})\s*\|", header_zone)
        if m:
            company = normalize_whitespace(m.group(1))

    return title, company, location


def _pick_location(parts: List[str]) -> Optional[str]:
    """
    Simple location heuristic:
    - Look for strings containing typical location patterns or remote markers
    """
    if not parts:
        return None

    # Prefer explicit remote markers if present
    for p in parts:
        pl = p.lower()
        if "remote" in pl or "anywhere" in pl or "worldwide" in pl:
            return p

    # Otherwise, pick something that looks like a city/country/region
    for p in parts:
        if _looks_like_location(p):
            return p

    return None


def _looks_like_location(value: str) -> bool:
    v = value.lower()
    # Exclude obvious non-locations
    if any(k in v for k in ["full-time", "part-time", "contract", "visa", "salary", "equity", "onsite", "hybrid"]):
        return False
    # The presence of comma or country/state abbreviations often indicates location
    if "," in value:
        return True
    if re.search(r"\b(usa|us|uk|eu|europe|canada|australia|germany|france|spain|india|singapore)\b", v):
        return True
    return False


def _pick_role(parts: List[str]) -> Optional[str]:
    """
    Find a segment that likely describes the role/title.
    """
    if not parts:
        return None

    role_keywords = [
        "engineer", "developer", "frontend", "backend", "full stack", "fullstack",
        "data", "ml", "ai", "platform", "devops", "sre", "security", "product",
        "designer", "qa", "ios", "android"
    ]

    for p in parts:
        pl = p.lower()
        if any(k in pl for k in role_keywords):
            # Keep it short and role-like
            return p[:120]

    return None
