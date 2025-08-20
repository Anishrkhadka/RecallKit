"""RecallKit Progress API.

This FastAPI service stores and retrieves spaced-repetition progress per
'user profile' as JSON files on disk. It supports optional bearer-token
authentication for mutating operations.

Environment variables:
    RECALLKIT_DATA_DIR: Directory to store JSON files. Default: '/app/data/progress'.
    RECALLKIT_API_TOKEN: Optional bearer token. If set, PUT/DELETE require it.
    RECALLKIT_CORS_ORIGINS: Optional CSV of allowed origins for CORS.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Body, Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import logging

# --------------------------------------------------------------------------- #
# Configuration & app setup
# --------------------------------------------------------------------------- #

logger = logging.getLogger("uvicorn.error")

DATA_DIR = Path(os.getenv("RECALLKIT_DATA_DIR", "/app/data/progress"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

API_TOKEN = os.getenv("RECALLKIT_API_TOKEN", "").strip()  # optional
CORS_ORIGINS_ENV = os.getenv("RECALLKIT_CORS_ORIGINS", "").strip()

app = FastAPI(title="RecallKit API", version="1.0.0")

allow_origins = (
    [o.strip() for o in CORS_ORIGINS_ENV.split(",") if o.strip()]
    if CORS_ORIGINS_ENV
    else ["*"]  # for LAN/dev; tighten for production
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------- #
# Auth dependency
# --------------------------------------------------------------------------- #

security = HTTPBearer(auto_error=False)

def require_bearer_token(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> None:
    """Enforce bearer token for mutating routes *only if* a token is configured.

    If RECALLKIT_API_TOKEN is unset/empty, this dependency allows the request.

    Raises:
        HTTPException: 401 when a token is configured and missing/incorrect.
    """
    if not API_TOKEN:
        return  # auth disabled
    token = (creds.credentials if creds else "").strip()
    if token != API_TOKEN:
        logger.warning("Auth failed: invalid/missing token.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token",
        )

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

_PROFILE_SAFE_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")

def _path_for(profile: str) -> Path:
    """Return a safe filesystem path for a profile JSON.

    Args:
        profile: Profile identifier from the URL path.

    Returns:
        Path to the profile JSON file under DATA_DIR.

    Raises:
        HTTPException: 400 if the profile name is invalid.
    """
    if not _PROFILE_SAFE_RE.match(profile):
        raise HTTPException(status_code=400, detail="Invalid profile name")
    return DATA_DIR / f"{profile}.json"

def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    """Atomically write JSON to disk.

    Writes to a temporary file then replaces the target to avoid partial writes.

    Args:
        path: Destination path.
        payload: JSON-serialisable dictionary.

    Raises:
        HTTPException: 500 if writing fails.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
    except Exception as exc:
        logger.exception("Failed to write JSON for %s", path)
        # Best effort cleanup
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="Failed to persist progress") from exc

# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #

@app.get("/api/progress/{profile}", response_model=Dict[str, Any])
def get_progress(profile: str) -> Dict[str, Any]:
    """Get progress JSON for a profile.

    Args:
        profile: Profile identifier (alphanumerics, dot, underscore, hyphen).

    Returns:
        dict: Stored progress object, or empty dict if not present.

    Errors:
        400: Invalid profile name.
        500: Corrupt/unreadable file.
    """
    p = _path_for(profile)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Corrupt progress file for %s", profile)
        raise HTTPException(status_code=500, detail="Corrupt progress file")

@app.put(
    "/api/progress/{profile}",
    status_code=status.HTTP_200_OK,
    response_model=Dict[str, bool],
)
def put_progress(
    profile: str,
    body: Dict[str, Any] = Body(..., description="Arbitrary progress JSON"),
    _auth: None = Depends(require_bearer_token),
) -> Dict[str, bool]:
    """Create or replace progress JSON for a profile.

    Requires bearer token **only** if `RECALLKIT_API_TOKEN` is configured.

    Args:
        profile: Profile identifier.
        body: Progress object to persist.

    Returns:
        {"ok": True} on success.

    Errors:
        400: Invalid profile name.
        401: Missing/invalid token (when enforced).
        500: Write failure.
    """
    p = _path_for(profile)
    _atomic_write_json(p, body)
    return {"ok": True}

@app.delete(
    "/api/progress/{profile}",
    status_code=status.HTTP_200_OK,
    response_model=Dict[str, bool],
)
def delete_progress(
    profile: str,
    _auth: None = Depends(require_bearer_token),
) -> Dict[str, bool]:
    """Delete stored progress for a profile.

    Requires bearer token **only** if `RECALLKIT_API_TOKEN` is configured.

    Args:
        profile: Profile identifier.

    Returns:
        {"deleted": True} whether or not the file existed.

    Errors:
        400: Invalid profile name.
        401: Missing/invalid token (when enforced).
        500: Filesystem error during delete.
    """
    p = _path_for(profile)
    try:
        if p.exists():
            p.unlink()
        return {"deleted": True}
    except Exception as exc:
        logger.exception("Failed to delete %s", p)
        raise HTTPException(status_code=500, detail="Failed to delete progress") from exc
