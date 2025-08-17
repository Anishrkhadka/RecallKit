from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json
import os
from typing import Dict, Any

# Where progress JSON files are stored
DATA_DIR = Path(os.getenv("RECALLKIT_DATA_DIR", "/app/data/progress"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Simple bearer token (optional)
API_TOKEN = os.getenv("RECALLKIT_API_TOKEN", "").strip()

app = FastAPI(title="RecallKit API")

# allow Streamlit (8501) to talk to API (8502)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for LAN use; tighten if you deploy publicly
    allow_credentials=True,
    allow_methods=["GET", "PUT", "OPTIONS"],
    allow_headers=["*"],
)


def _path_for(profile: str) -> Path:
    """Ensure a safe filename for the profile."""
    safe = "".join(c for c in profile if c.isalnum() or c in ("-", "_", "."))
    if not safe:
        raise HTTPException(status_code=400, detail="Invalid profile")
    return DATA_DIR / f"{safe}.json"


@app.get("/api/progress/{profile}")
def get_progress(profile: str):
    p = _path_for(profile)
    if not p.exists():
        return {}  # empty progress
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(status_code=500, detail="Corrupt progress file")


@app.put("/api/progress/{profile}")
def put_progress(profile: str, body: Dict[str, Any], authorization: str = Header(default="")):
    # Simple bearer token check
    token = ""
    if authorization.lower().startswith("bearer "):
        token = authorization[7:]
    if not API_TOKEN or token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    p = _path_for(profile)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)
    return {"ok": True}
