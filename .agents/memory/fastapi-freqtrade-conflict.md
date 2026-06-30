---
name: FastAPI / freqtrade version conflict in HER backend
description: Installing freqtrade overrides the pinned FastAPI version with an incompatible one; backend crashes on import.
---

# FastAPI / freqtrade Version Conflict

**Symptom:** After `pip install -r requirements.txt`, backend fails on startup:
```
ImportError: cannot import name 'PYDANTIC_V2' from 'fastapi._compat'
```

**Why:** `freqtrade==2026.6` pulls in `fastapi==0.138.2`. That version removed `PYDANTIC_V2` from `fastapi._compat`, breaking HER's pinned `fastapi==0.104.1` + `pydantic==2.5.0` setup.

**Fix:** After the full requirements install, force-reinstall the correct versions:
```bash
pip install "fastapi==0.104.1" "pydantic==2.5.0" "pydantic-settings==2.1.0" --force-reinstall
```

**How to apply:** Any time the backend is set up on a fresh container (new Replit, CI, teammate onboarding), run the two-step install. This is documented in `knowledge_base/RUNBOOK.md` and `backend/requirements.txt` comment.

**Long-term fix needed:** Restructure to a two-stage install or use `--no-deps` for freqtrade so version resolution doesn't override explicit pins. Tracked as a proposed follow-up task.
