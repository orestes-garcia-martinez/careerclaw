from __future__ import annotations

import argparse
import json
import time
import sys
from pathlib import Path
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from careerclaw.models import BriefingRun, NormalizedJob, UserProfile
from careerclaw.sources import fetch_all_jobs
from careerclaw.matching.engine import rank_jobs
from careerclaw.drafting import DraftResult, draft_outreach
from careerclaw.tracking import JsonTrackingRepository, TrackingRepository, default_repo_dir
from careerclaw.io.resume_loader import load_resume_text
from careerclaw.resume_intel import build_resume_intelligence, cache_resume_intelligence, resume_intelligence_to_dict, ResumeIntelligence
from careerclaw.requirements import extract_job_requirements
from careerclaw.gap import GapAnalysis, analyze_gap
from careerclaw import config
from careerclaw.llm.enhancer import LLMDraftEnhancer, DraftEnhancerError


@dataclass(frozen=True)
class RankedMatch:
    job: NormalizedJob
    score: float
    explanation: Dict[str, Any]  # mapped from MatchBreakdown.details
    analysis: Dict[str, Any] | None = None
    gap: GapAnalysis | None = None  # raw object for LLM prompt builder


@dataclass(frozen=True)
class DailyBriefingResult:
    user_id: str
    fetched_jobs: int
    considered_jobs: int
    top_matches: List[RankedMatch]
    drafts: List[DraftResult]
    tracking_created: int
    tracking_already_present: int
    duration_ms: int
    dry_run: bool
    resume_intelligence: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "fetched_jobs": self.fetched_jobs,
            "considered_jobs": self.considered_jobs,
            "top_matches": [
                {
                    "job": m.job.to_dict(),
                    "score": m.score,
                    "explanation": m.explanation,
                    "analysis": m.analysis,
                }
                for m in self.top_matches
            ],
            "drafts": [{"job_id": d.job_id, "channel": d.channel, "draft": d.draft, "enhanced": d.enhanced} for d in self.drafts],
            "tracking": {
                "created": self.tracking_created,
                "already_present": self.tracking_already_present,
            },
            "duration_ms": self.duration_ms,
            "dry_run": self.dry_run,
            "resume_intelligence": self.resume_intelligence,
        }


def _dedupe_jobs(jobs: List[NormalizedJob]) -> List[NormalizedJob]:
    seen = set()    # tracks job_ids we've already encountered
    out: List[NormalizedJob] = []
    for j in jobs:
        if j.job_id in seen:    # skip if we've seen this ID before
            continue
        seen.add(j.job_id)      # mark as seen
        out.append(j)           # keep this job
    return out


def _extract_top_skill_signals(explanation: Dict[str, Any], max_items: int = 2) -> List[str]:
    """
    Best-effort: pull a couple of human-friendly signals from breakdown.details.
    We don’t assume a strict schema for keyword_details beyond it being dict-like.
    """
    kd = explanation.get("keyword_details")
    if isinstance(kd, dict):
        # Look for any list-like key that smells like matched terms
        for key in ("matched", "matches", "overlap", "hits", "top_hits", "tokens"):
            v = kd.get(key)
            if isinstance(v, list) and v:
                return [str(x) for x in v[:max_items]]
        # Otherwise: any list in the dict
        for v in kd.values():
            if isinstance(v, list) and v:
                return [str(x) for x in v[:max_items]]
    return []


def run_daily_briefing(
        *,
        user_id: str,
        profile: UserProfile,
        top_k: int = 3,
        repo: Optional[TrackingRepository] = None,
        dry_run: bool = False,
        resume_intel: Optional[ResumeIntelligence] = None,
        no_enhance: bool = False,
) -> DailyBriefingResult:
    """
    Skill-first the entry point:
      - accepts profile as input
      - returns structured JSON-serializable result
    """
    start = time.time()

    resume_intel_dict = resume_intelligence_to_dict(resume_intel) if resume_intel else None

    jobs = fetch_all_jobs()
    fetched = len(jobs)

    jobs = _dedupe_jobs(jobs)
    considered = len(jobs)

    ranked = rank_jobs(profile=profile, jobs=jobs, top_n=top_k)

    # --- Pro tier gate (evaluated once per run) ---
    is_pro = config.pro_licensed()

    matches: List[RankedMatch] = []
    for item in ranked:
        gap_obj = None
        analysis = None
        # Gap analysis and resume intel are Pro-only features.
        if is_pro and resume_intel is not None:
            req = extract_job_requirements(item.job)
            gap_obj = analyze_gap(resume=resume_intel, job=req)
            analysis = gap_obj.to_dict().get("analysis")
        matches.append(
            RankedMatch(
                job=item.job,
                score=float(item.score),
                explanation=item.breakdown.details,
                analysis=analysis,
                gap=gap_obj,
            )
        )

    # --- Draft generation (deterministic baseline + optional LLM enhancement) ---
    # LLM enhancement requires both a valid Pro license AND an LLM API key.
    use_llm = (
            not no_enhance
            and is_pro
            and config.llm_configured()
            and resume_intel is not None
    )

    enhancer = None
    if use_llm:
        try:
            enhancer = LLMDraftEnhancer(
                api_key=config.CAREERCLAW_LLM_KEY,
                provider=config.CAREERCLAW_LLM_PROVIDER,
                resume=resume_intel,
            )
        except Exception:
            enhancer = None  # fall back silently

    drafts: List[DraftResult] = []
    for m in matches:
        base = draft_outreach(profile=profile, job=m.job)
        if enhancer is not None and m.gap is not None:
            try:
                enhanced_text = enhancer.enhance(job=m.job, gap=m.gap)
                # Prepend subject line from deterministic draft (first line)
                subject_line = base.draft.split("\n")[0]
                full_draft = subject_line + "\n\n" + enhanced_text
                from careerclaw.drafting import DraftResult as DR
                drafts.append(DR(job_id=m.job.job_id, draft=full_draft, enhanced=True))
            except Exception:
                # Any failure: fall back to deterministic, log warning
                import sys
                print("[CareerClaw] LLM enhancement failed for one draft, using deterministic fallback.", file=sys.stderr)
                drafts.append(base)
        else:
            drafts.append(base)

    tracking_created = 0
    tracking_already = 0

    if not dry_run:
        repo = repo or JsonTrackingRepository(default_repo_dir())
        tracking_created, tracking_already = repo.upsert_saved_jobs([m.job.job_id for m in matches])
        repo.record_run(
            BriefingRun(user_id=user_id),
            meta={
                "fetched_jobs": fetched,
                "considered_jobs": considered,
                "top_n": top_k,
                "created": tracking_created,
                "already_present": tracking_already,
            },
        )

    duration_ms = int((time.time() - start) * 1000)

    return DailyBriefingResult(
        user_id=user_id,
        fetched_jobs=fetched,
        considered_jobs=considered,
        top_matches=matches,
        drafts=drafts,
        tracking_created=tracking_created,
        tracking_already_present=tracking_already,
        duration_ms=duration_ms,
        dry_run=dry_run,
        resume_intelligence=resume_intel_dict,
    )


def print_human_summary(result: DailyBriefingResult, profile: UserProfile, *, analysis_mode: str = "summary") -> None:
    print("\n=== CareerClaw Daily Briefing ===")
    print(f"User: {result.user_id}")
    print(f"Fetched jobs: {result.fetched_jobs} | After dedupe: {result.considered_jobs}")
    if result.dry_run:
        print("Mode: DRY RUN (no tracking written)")
    else:
        print(f"Tracking: +{result.tracking_created} new saved, {result.tracking_already_present} already saved")
    print(f"Duration: {result.duration_ms}ms")

    print("\nTop Matches:")
    for idx, m in enumerate(result.top_matches, start=1):
        j = m.job
        loc = f" — {j.location}" if j.location else ""
        print(f"\n{idx}) {j.title} @ {j.company}{loc}  [{j.source.value}]")
        print(f"   score: {m.score}")

        if analysis_mode != "off" and m.analysis:
            fit = m.analysis.get("fit_score")
            if isinstance(fit, (int, float)):
                print(f"   fit: {int(fit * 100)}%")

            if analysis_mode == "summary":
                summary = (m.analysis.get("summary") or {})
                top = summary.get("top_signals") or {}
                top_ph = top.get("phrases") or []
                top_kw = top.get("keywords") or []
                preview = []
                preview.extend(top_ph[:2])
                preview.extend(top_kw[:2])
                preview = [p for p in preview if p]
                if preview:
                    print(f"   highlights: {', '.join(preview)}")
            else:  # full
                sig = m.analysis.get("signals") or {}
                gaps = m.analysis.get("gaps") or {}
                sig_ph = (sig.get("phrases") or [])[:10]
                sig_kw = (sig.get("keywords") or [])[:10]
                gap_ph = (gaps.get("phrases") or [])[:10]
                gap_kw = (gaps.get("keywords") or [])[:10]
                if sig_ph or sig_kw:
                    print(f"   matched phrases: {', '.join(sig_ph)}" if sig_ph else "   matched phrases: -")
                    print(f"   matched keywords: {', '.join(sig_kw)}" if sig_kw else "   matched keywords: -")
                if gap_ph or gap_kw:
                    print(f"   missing phrases: {', '.join(gap_ph)}" if gap_ph else "   missing phrases: -")
                    print(f"   missing keywords: {', '.join(gap_kw)}" if gap_kw else "   missing keywords: -")

        signals = _extract_top_skill_signals(m.explanation, max_items=2)
        if signals:
            print(f"   matches: {', '.join(signals)}")
        else:
            # fallback: show two likely relevant profile skills (inexpensive + useful)
            fallback = []
            hay = f"{j.title} {j.description} {' '.join(j.tags or [])}".lower()
            for s in profile.skills:
                sl = (s or "").lower()
                if sl and len(sl) >= 3 and ((" " in sl and sl in hay) or (" " not in sl and sl in hay.split())):
                    fallback.append(s)
                if len(fallback) >= 2:
                    break
            if fallback:
                print(f"   matches: {', '.join(fallback)}")

    print("\nDrafts:")
    for idx, d in enumerate(result.drafts, start=1):
        tag = " [LLM enhanced]" if d.enhanced else ""
        print(f"\n--- Draft #{idx} (job_id={d.job_id}){tag} ---")
        print(d.draft)


def _load_profile_from_json(path: Path) -> UserProfile:
    data = json.loads(path.read_text(encoding="utf-8"))
    return UserProfile(
        skills=data["skills"],
        target_roles=data["target_roles"],
        experience_years=int(data["experience_years"]),
        work_mode=data["work_mode"],
        resume_summary=data["resume_summary"],
        location=data.get("location"),
        salary_min=data.get("salary_min"),
        salary_max=data.get("salary_max"),
    )


def _resolve_profile_path(raw: str) -> Path:
    p = Path(raw)

    # 1) The user provided path
    if raw and p.exists():
        return p

    # 2) common defaults if the user gave "profile.json" but it isn't in cwd
    candidates = [
        Path("profile.json"),
        Path(".careerclaw") / "profile.json",
        ]
    for c in candidates:
        if c.exists():
            return c

    # 3) not found
    return p  # for error message

def main() -> None:
    parser = argparse.ArgumentParser(description="CareerClaw Phase-4 Daily Briefing (MVP)")
    parser.add_argument("--user-id", default="local-user", help="User identifier for run tracking")
    parser.add_argument("--profile", type=str, default="", help="Path to a profile.json for CLI usage")
    parser.add_argument("--top-k", type=int, default=3, help="How many matches to return")
    parser.add_argument("--json", action="store_true", help="Print JSON only (machine-readable)")
    parser.add_argument("--dry-run", action="store_true", help="Run without writing tracking/runs")
    parser.add_argument("--resume-text", type=str, default="", help="Optional path to resume .txt")
    parser.add_argument("--resume-pdf", type=str, default="", help="Optional path to resume .pdf")
    parser.add_argument("--analysis", choices=["off","summary","full"], default="summary", help="Gap analysis output in CLI (off|summary|full)")
    parser.add_argument("--no-enhance", action="store_true", help="Force deterministic drafts even when CAREERCLAW_LLM_KEY is set")
    args = parser.parse_args()

    profile: UserProfile

    if args.profile:
        profile_path = _resolve_profile_path(args.profile)
        if not profile_path.exists():
            print(f"\n[CareerClaw] Profile file not found: {profile_path}")
            print("Tip: pass an absolute path or place profile.json in the repo root or .careerclaw/profile.json\n")
            raise SystemExit(2)
        profile = _load_profile_from_json(profile_path)
    else:
        # Auto-discover default profile
        default_path = Path(".careerclaw") / "profile.json"
        if default_path.exists():
            profile = _load_profile_from_json(default_path)
        else:
            profile = UserProfile(
                skills=["communication", "problem solving", "teamwork"],
                target_roles=["your target role here"],
                experience_years=5,
                work_mode="remote",
                resume_summary="Experienced professional with a strong track record of delivering results.",
            )


    # Resume Intelligence (Phase 5A foundation)
    loaded = load_resume_text(
        resume_text_path=(args.resume_text or None) if hasattr(args, "resume_text") else None,
        resume_pdf_path=(args.resume_pdf or None) if hasattr(args, "resume_pdf") else None,
    )
    intel = build_resume_intelligence(
        resume_summary=profile.resume_summary,
        resume_text=loaded.text,
        skills=profile.skills,
        target_roles=profile.target_roles,
    )

    # Cache only when not dry-run (keeps tests + safety behavior consistent)
    if not args.dry_run:
        try:
            cache_path = default_repo_dir() / "resume_intel.json"
            cache_resume_intelligence(cache_path, intel)
        except Exception:
            # best-effort cache; never fail the run
            pass

    result = run_daily_briefing(
        user_id=args.user_id,
        profile=profile,
        top_k=args.top_k,
        dry_run=args.dry_run,
        resume_intel=intel,
        no_enhance=args.no_enhance,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print_human_summary(result, profile=profile, analysis_mode=args.analysis)
        print("\nJSON Output (for skills/agents):")
        print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
