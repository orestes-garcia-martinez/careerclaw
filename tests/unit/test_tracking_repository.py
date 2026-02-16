from pathlib import Path

from careerclaw.models import ApplicationStatus
from careerclaw.tracking import JsonTrackingRepository


def test_tracking_rehydrates_enum_status(tmp_path: Path) -> None:
    repo = JsonTrackingRepository(tmp_path)

    created, already = repo.upsert_saved_jobs(["job-1"])
    assert created == 1
    assert already == 0

    tracking = repo.load_tracking()
    assert "job-1" in tracking
    assert tracking["job-1"].status == ApplicationStatus.SAVED  # enum instance, not raw string
