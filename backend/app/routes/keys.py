import hashlib
import secrets
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from ..db import get_session
from ..models import (
    ApiKey,
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyRead,
    Device,
    PublicLocation,
    now_ts,
)
from .status import latest_locations

router = APIRouter(prefix="/api/keys", tags=["api keys"])

bearer = HTTPBearer(auto_error=False)

# shortcut: fixed one-minute windows held in memory, so counters reset on restart and a
# client can burst up to 2x across a window edge. Move to the database or Redis if the
# backend ever runs more than one process.
_windows: dict[str, tuple[int, int]] = {}
_lock = Lock()


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def require_key(
    response: Response,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_session),
) -> None:
    key = creds and session.exec(
        select(ApiKey).where(ApiKey.key_hash == hash_key(creds.credentials))
    ).first()
    if not key:
        raise HTTPException(
            401, "Missing or invalid API key", headers={"WWW-Authenticate": "Bearer"}
        )

    now = now_ts()
    window = now // 60
    with _lock:
        start, count = _windows.get(key.key_hash, (window, 0))
        if start != window:
            count = 0
        limit = key.rate_limit_per_min
        if count >= limit:
            raise HTTPException(
                429,
                "Rate limit exceeded",
                headers={
                    "Retry-After": str(60 - now % 60),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )
        _windows[key.key_hash] = (window, count + 1)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(limit - count - 1)

    key.last_used_ts = now
    session.add(key)
    session.commit()


@router.get("", response_model=list[ApiKeyRead])
def list_keys(session: Session = Depends(get_session)):
    return session.exec(select(ApiKey).order_by(ApiKey.id)).all()


@router.post("", response_model=ApiKeyCreated, status_code=201)
def create_key(body: ApiKeyCreate, session: Session = Depends(get_session)):
    key = f"fonek_{secrets.token_urlsafe(32)}"
    row = ApiKey(
        name=body.name,
        prefix=key[:12],
        key_hash=hash_key(key),
        rate_limit_per_min=body.rate_limit_per_min,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return {**row.model_dump(), "key": key}


@router.delete("/{key_id}", status_code=204)
def delete_key(key_id: int, session: Session = Depends(get_session)):
    row = session.get(ApiKey, key_id)
    if row is None:
        raise HTTPException(404, "API key not found")
    _windows.pop(row.key_hash, None)
    session.delete(row)
    session.commit()


# The only routes meant to be reachable by third parties.
public = APIRouter(prefix="/api/public", tags=["public"], dependencies=[Depends(require_key)])


@public.get("/locations", response_model=list[PublicLocation])
def public_locations(session: Session = Depends(get_session)):
    """The most recent location of every device that has one, with the device name."""
    names = dict(session.exec(select(Device.id, Device.name)).all())
    return [
        {**loc.model_dump(), "name": names[loc.device_id]} for loc in latest_locations(session)
    ]
