from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pypdf import PdfReader


@dataclass(frozen=True)
class LoadedResume:
    text: str
    source: str  # "text" | "pdf" | "none"
    path: Optional[str] = None


def load_resume_text(*, resume_text_path: Optional[str], resume_pdf_path: Optional[str]) -> LoadedResume:
    """
    Load resume content locally.
    Precedence:
      1) resume_text_path (.txt)
      2) resume_pdf_path (.pdf)
      3) none
    Best-effort: failures return source='none' and empty text (caller should fallback to resume_summary).
    """
    if resume_text_path:
        p = Path(resume_text_path)
        try:
            return LoadedResume(text=p.read_text(encoding="utf-8"), source="text", path=str(p))
        except Exception:
            return LoadedResume(text="", source="none", path=str(p))

    if resume_pdf_path:
        p = Path(resume_pdf_path)
        try:
            reader = PdfReader(str(p))
            parts = []
            for page in reader.pages:
                t = page.extract_text() or ""
                if t.strip():
                    parts.append(t)
            text = "\n".join(parts).strip()
            if not text:
                return LoadedResume(text="", source="none", path=str(p))
            return LoadedResume(text=text, source="pdf", path=str(p))
        except Exception:
            return LoadedResume(text="", source="none", path=str(p))

    return LoadedResume(text="", source="none", path=None)
