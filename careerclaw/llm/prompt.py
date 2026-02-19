"""
careerclaw/llm/prompt.py

Builds the enhancement prompt from ResumeIntelligence + GapAnalysis + job.

Design constraints (from PR-6 spec):
- System prompt: ~150 tokens
- Context (job + resume signals): ~200 tokens
- Instructions: ~100 tokens
- Total input target: <600 tokens
- Output constraint: 150-200 words
"""
from __future__ import annotations

from careerclaw.gap import GapAnalysis
from careerclaw.models import NormalizedJob
from careerclaw.resume_intel import ResumeIntelligence

_SYSTEM_PROMPT = """\
You are a career advisor writing a targeted job outreach email on behalf of a candidate.
Your goal is to write a concise, specific, and compelling email that references real experience \
from the candidate's background — not generic phrases.
The candidate may be in any field: technology, healthcare, education, finance, trades, or any other profession.
CRITICAL: Only reference experience, skills, and achievements that appear in the provided resume signals. \
Do NOT invent metrics, percentages, project names, or accomplishments not explicitly present in the input.
Never use filler language like "I am excited", "I am passionate", or "I would love to".
Write in first person, professional tone, 150-200 words total (subject line excluded).\
"""


def build_enhance_prompt(
        *,
        job: NormalizedJob,
        resume: ResumeIntelligence,
        gap: GapAnalysis,
) -> str:
    """
    Assemble the user-turn prompt from job context, resume signals, and gap analysis.
    Returns a single string ready to send as the user message.
    """
    # Company context: first sentence of description (capped at 150 chars)
    raw_desc = (job.description or "").strip()
    first_sentence = raw_desc.split(".")[0].strip()
    company_context = (first_sentence[:150] + "…") if len(first_sentence) > 150 else first_sentence

    # Job signals: matched keywords + phrases from gap analysis (top 5 each)
    matched_kw = gap.matched_keywords[:5]
    matched_ph = gap.matched_phrases[:3]
    job_signals = matched_kw + matched_ph
    job_signals_str = ", ".join(job_signals) if job_signals else "(none detected)"

    # Resume highlights: keyword_stream entries that overlap with job signals
    kw_stream = resume.keyword_stream or []
    signal_set = set(matched_kw) | set(matched_ph)
    resume_highlights = [k for k in kw_stream if k in signal_set]
    # Fallback: just take top of keyword_stream if no overlap found
    if not resume_highlights:
        resume_highlights = kw_stream[:5]
    resume_highlights = resume_highlights[:5]
    resume_highlights_str = ", ".join(resume_highlights) if resume_highlights else "(see resume summary)"

    prompt = f"""\
Write a targeted outreach email for the following job. Use the resume signals to make it specific.

JOB DETAILS:
- Title: {job.title or "the position"}
- Company: {job.company or "the company"}
- Context: {company_context}

MATCHED SIGNALS (skills/phrases the job and resume share):
{job_signals_str}

CANDIDATE RESUME HIGHLIGHTS (relevant to this role):
{resume_highlights_str}

REQUIREMENTS:
- Reference at least 2 specific professional signals from the resume in the opening paragraph
- Do NOT include a subject line — write body only (start with "Hi {job.company or 'team'}," or similar)
- 150-200 words
- No filler phrases ("excited to", "passionate about", "would love to")
- End with a clear, low-pressure call to action
- CRITICAL: Do NOT invent metrics, percentages, achievements, or project names. Only use what is in the resume signals above.\
"""
    return prompt


def estimate_token_count(text: str) -> int:
    """
    Rough token estimate: ~4 chars per token (conservative for English code/prose).
    Used for budget checks in tests; not used at runtime.
    """
    return len(text) // 4
