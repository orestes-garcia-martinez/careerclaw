# CareerClaw

AI-powered job search assistant for OpenClaw.

CareerClaw turns your agent into a structured career workflow:

Daily Shortlist → Ranked Matches → Draft Message → Track Status

---

## 🚧 Status

MVP in development (v0.1.x)

Phase 4 complete:
- End-to-end Daily Briefing orchestration
- Profile-driven ranking
- Draft generation
- Persistent tracking
- Run instrumentation

Sources:
- RemoteOK RSS
- Hacker News “Who’s Hiring”

---

## 🎯 MVP Goal

Validate:

1. Install demand
2. Weekly repeat usage
3. Pro-tier upgrade interest

---

## 🧱 Architecture Overview

CareerClaw is structured into:

- **Adapters** (source ingestion)
- **Normalized Job Schema**
- **Deterministic Matching Engine**
- **Drafting Layer**
- **Tracking Repository**
- **Daily Briefing Orchestrator**

Entry point:
```powershell
python -m careerclaw.briefing
```

---

## 📊 Success Metrics (30-Day Target)
- ≥ 100 installs
- ≥ 20 weekly active users
- ≥ 30% of active users run briefing 2+ times
- ≥ 5 paid upgrade inquiries

---

## 🔐 Security Principles
- Minimal permission model
- No credential storage
- Signed commits
- Transparent source code
- Versioned releases
- Local-only runtime state

---

## 🧪 Development

## ⚙️ Installation (Recommended)

Create a virtual environment (PowerShell):
```powershell
    python -m venv .venv
    .\.venv\Scripts\Activate
```


Install in editable mode with dev dependencies:
```powershell
    python -m pip install -e ".[dev]"
```

This ensures:
- Proper package imports
- Editable source linkage
- pytest works reliably

---

## 👤 Profile Setup
Create a runtime directory:
```powershell
    mkdir .careerclaw
```

Create .careerclaw/profile.json
Example:
```json
    {
      "version": 1,
      "user_id": "orestes",
      "skills": ["react", "typescript", "python", "aws", "observability"],
      "target_roles": ["frontend engineer", "software engineer"],
      "experience_years": 8,
      "work_mode": "remote",
      "resume_summary": "Senior engineer focused on systems thinking and reliability.",
      "location": "United States",
      "salary_min": 140000,
      "salary_max": 190000
    }
```

Run Daily Briefing:
```powershell
    python -m careerclaw.briefing   
    python -m careerclaw.briefing --dry-run
    python -m careerclaw.briefing --json --dry-run
    python -m careerclaw.briefing --profile ..careerclaw\profile.json --top-k 3
```

## 📂 Runtime Artifacts
Stored locally under:
.careerclaw/

Files:
- profile.json — user configuration
- tracking.json — saved jobs (deduped)
- runs.jsonl — append-only run log (analytics stream)

---

## 🧪 Testing
Run tests:
```powershell
pytest
```

Run smoke test (live sources):
- python -m scripts.smoke_test_sources

---

## 📌 License

TBD — will be added before public release.
