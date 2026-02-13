from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from careerclaw import config
import re
import xml.etree.ElementTree as ET

from careerclaw.models import JobSource, NormalizedJob, normalize_whitespace


REMOTEOK_DEFAULT_RSS_URL = config.REMOTEOK_RSS_URL


def _fetch_text(url: str, timeout_seconds: int = config.HTTP_TIMEOUT_SECONDS) -> str:
    """
    Fetch a URL and return decoded text. RemoteOK blocks some default clients,
    so we send a browser-ish User-Agent.
    """
    req = Request(
        url,
        headers={
            "User-Agent": config.USER_AGENT,
        },
    )
    try:
        with urlopen(req, timeout=timeout_seconds) as resp:
            data = resp.read()
            # RSS is typically UTF-8
            return data.decode("utf-8", errors="replace")
    except (HTTPError, URLError) as e:
        raise RuntimeError(f"Failed to fetch RemoteOK RSS: {e}") from e


def _strip_html(html: str) -> str:
    """
    MVP-grade HTML stripping for RSS item descriptions.
    Good enough for scoring and drafting.
    """
    if not html:
        return ""
    # Remove script/style
    html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    # Remove tags
    text = re.sub(r"(?s)<.*?>", " ", html)
    # Decode a few common entities (minimal)
    text = (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    return normalize_whitespace(text)


def _parse_rfc822_date(value: str) -> Optional[datetime]:
    """
    RemoteOK RSS uses RFC822-ish pubDate, e.g.:
    'Mon, 12 Feb 2026 10:00:00 +0000'
    We'll parse best-effort.
    """
    if not value:
        return None

    # Common format: "%a, %d %b %Y %H:%M:%S %z"
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%d %b %Y %H:%M:%S %z"):
        try:
            dt = datetime.strptime(value.strip(), fmt)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass
    return None


def _text(el: Optional[ET.Element]) -> str:
    return (el.text or "").strip() if el is not None else ""


def fetch_remoteok_jobs(
        rss_url: str = config.REMOTEOK_DEFAULT_RSS_URL,
        limit: int = config.REMOTEOK_MAX_ITEMS,
) -> List[NormalizedJob]:
    """
    Fetch RemoteOK RSS and return normalized jobs.
    limit: max number of items returned (MVP guardrail)
    """
    xml_text = _fetch_text(rss_url)
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise RuntimeError(f"Failed to parse RemoteOK RSS XML: {e}") from e

    channel = root.find("channel")
    if channel is None:
        return []

    items = channel.findall("item")
    jobs: List[NormalizedJob] = []

    for item in items[: max(0, limit)]:
        title_raw = _text(item.find("title"))
        link = _text(item.find("link"))
        pub_date_raw = _text(item.find("pubDate"))
        desc_raw = _text(item.find("description"))

        # RemoteOK commonly formats title like: "Senior Frontend Engineer at Company"
        # We'll try to split, but fall back safely.
        title, company = _split_title_company(title_raw)

        # Categories often contain tags
        tags = [normalize_whitespace(_text(c)).lower() for c in item.findall("category")]
        tags = [t for t in tags if t]

        # Attempt to infer location from tags (RemoteOK often includes region tags)
        # MVP heuristic: if the tag looks like a location marker.
        location = _infer_location_from_tags(tags)

        posted_at = _parse_rfc822_date(pub_date_raw)
        description = _strip_html(desc_raw)

        # Skip empty essentials
        if not title or not company or not description:
            continue

        jobs.append(
            NormalizedJob(
                source=JobSource.REMOTEOK,
                title=title,
                company=company,
                description=description,
                location=location,
                tags=tags,
                posted_at=posted_at,
                canonical_url=link or None,
                source_ref=None,  # can be filled later if RemoteOK exposes a stable id/slug
            )
        )

    return jobs


def _split_title_company(title_raw: str) -> tuple[str, str]:
    """
    Best-effort parsing:
    - Common: "<Role> at <Company>"
    - Sometimes: "<Company>: <Role>"
    Fallback: company="Unknown"
    """
    t = normalize_whitespace(title_raw)

    if " at " in t:
        left, right = t.split(" at ", 1)
        role = normalize_whitespace(left)
        company = normalize_whitespace(right)
        return role or t, company or "Unknown"

    if ": " in t:
        left, right = t.split(": ", 1)
        # Heuristic: left is the company, right is the role
        company = normalize_whitespace(left)
        role = normalize_whitespace(right)
        if company and role:
            return role, company

    return t, "Unknown"


def _infer_location_from_tags(tags: List[str]) -> Optional[str]:
    """
    Very lightweight location inference:
    - If tags contain strings like "worldwide" / "usa" / "europe" / "uk" etc.
    - Otherwise None (do not invent)
    """
    if not tags:
        return None

    known = {
        "worldwide": "Worldwide",
        "anywhere": "Anywhere",
        "usa": "USA",
        "us": "USA",
        "united states": "USA",
        "uk": "UK",
        "united kingdom": "UK",
        "europe": "Europe",
        "canada": "Canada",
        "australia": "Australia",
        "latin america": "Latin America",
        "latam": "Latin America",
    }
    for t in tags:
        key = t.lower()
        if key in known:
            return known[key]

    return None
