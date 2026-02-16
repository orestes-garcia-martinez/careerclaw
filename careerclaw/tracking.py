from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Tuple

from careerclaw.models import ApplicationStatus, BriefingRun, TrackingEntry


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _best_effort_lockdown_file_permissions(path: Path) -> None:
    """
    Best-effort privacy: on Unix, set 600. On Windows, no-op.
    """
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    return date.fromisoformat(value)


class TrackingRepository(Protocol):
    def load_tracking(self) -> Dict[str, TrackingEntry]:
        ...

    def upsert_saved_jobs(self, job_ids: List[str]) -> Tuple[int, int]:
        """
        Returns: (created_count, already_present_count)
        """
        ...

    def record_run(self, run: BriefingRun, *, meta: Optional[dict] = None) -> None:
        ...


class JsonTrackingRepository:
    """
    MVP persistence using local JSON files.

    Layout:
      <base_dir>/
        tracking.json -> { "<job_id>": {TrackingEntry...}, ... }
        runs.jsonl    -> JSON lines: {"user_id": "...", "ran_at": "...", "meta": {...}}
    """

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.tracking_path = base_dir / "tracking.json"
        self.runs_path = base_dir / "runs.jsonl"
        _ensure_dir(self.base_dir)

    def load_tracking(self) -> Dict[str, TrackingEntry]:
        if not self.tracking_path.exists():
            return {}

        raw_text = self.tracking_path.read_text(encoding="utf-8").strip()
        if not raw_text:
            return {}

        data = json.loads(raw_text)
        tracking: Dict[str, TrackingEntry] = {}

        for job_id, entry in data.items():
            # Coerce enum + parse timestamps (safe for future expansion)
            raw_status = entry.get("status") or ApplicationStatus.SAVED.value
            status = ApplicationStatus(raw_status)

            tracking[job_id] = TrackingEntry(
                job_id=entry["job_id"],
                status=status,
                saved_at=_parse_dt(entry.get("saved_at")) or TrackingEntry(job_id=entry["job_id"]).saved_at,
                applied_at=_parse_dt(entry.get("applied_at")),
                notes=entry.get("notes"),
                next_action_date=_parse_date(entry.get("next_action_date")),
            )

        return tracking

    def _write_tracking(self, tracking: Dict[str, TrackingEntry]) -> None:
        payload = {job_id: entry.to_dict() for job_id, entry in tracking.items()}
        self.tracking_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        _best_effort_lockdown_file_permissions(self.tracking_path)

    def upsert_saved_jobs(self, job_ids: List[str]) -> Tuple[int, int]:
        tracking = self.load_tracking()
        created = 0
        already = 0

        for job_id in job_ids:
            if job_id in tracking:
                already += 1
                continue
            tracking[job_id] = TrackingEntry(job_id=job_id, status=ApplicationStatus.SAVED)
            created += 1

        self._write_tracking(tracking)
        return created, already

    def record_run(self, run: BriefingRun, *, meta: Optional[dict] = None) -> None:
        record = {
            "user_id": run.user_id,
            "ran_at": run.ran_at.isoformat(),
            "meta": meta or {},
        }
        line = json.dumps(record, sort_keys=True)
        with self.runs_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        _best_effort_lockdown_file_permissions(self.runs_path)


def default_repo_dir() -> Path:
    """
    Default local persistence dir. Safe for MVP.
    """
    return Path(".careerclaw")
