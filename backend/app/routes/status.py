from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlmodel import Session, select

from ..config import settings
from ..db import get_session
from ..models import Location, LocationRead, iso

router = APIRouter(prefix="/api", tags=["status"])


@router.get("/status")
async def status(request: Request):
    poller = request.app.state.poller
    account = await poller.accounts.get()
    return {
        "apple": "ok" if account is not None else "needs_login",
        "account": account.account_name if account is not None else None,
        "last_poll_at": iso(poller.last_poll_ts),
        "last_error": poller.last_error,
        "poll_interval_min": settings.poll_interval_min,
    }


@router.get("/locations/latest", response_model=list[LocationRead])
def latest_locations(session: Session = Depends(get_session)):
    """The most recent location of every device that has one."""
    newest = (
        select(Location.device_id, func.max(Location.ts).label("ts"))
        .group_by(Location.device_id)
        .subquery()
    )
    query = (
        select(Location)
        .join(
            newest,
            (Location.device_id == newest.c.device_id) & (Location.ts == newest.c.ts),
        )
        .group_by(Location.device_id)
    )
    return session.exec(query).all()
