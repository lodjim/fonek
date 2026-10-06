import base64
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from findmy import KeyPair
from sqlmodel import Session, select

from ..apple import NeedsLoginError
from ..db import get_session
from ..models import Device, DeviceCreate, DeviceRead, DeviceUpdate, Location, LocationRead

router = APIRouter(prefix="/api/devices", tags=["devices"])


def get_device(device_id: int, session: Session = Depends(get_session)) -> Device:
    device = session.get(Device, device_id)
    if device is None:
        raise HTTPException(404, "Device not found")
    return device


def to_ts(value: datetime) -> int:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp())


@router.get("", response_model=list[DeviceRead])
def list_devices(session: Session = Depends(get_session)):
    return session.exec(select(Device).order_by(Device.id)).all()


@router.post("", response_model=DeviceRead, status_code=201)
def create_device(body: DeviceCreate, session: Session = Depends(get_session)):
    if body.private_key_b64:
        try:
            raw = base64.b64decode(body.private_key_b64, validate=True)
            if len(raw) != 28:  # P-224 scalar
                raise ValueError
            key = KeyPair(raw)
            key.adv_key_b64  # an invalid scalar only fails once the public key is derived
        except Exception:
            raise HTTPException(422, "private_key_b64 is not a valid Find My private key") from None
    else:
        key = KeyPair.new()

    exists = session.exec(
        select(Device).where(Device.hashed_adv_key_b64 == key.hashed_adv_key_b64)
    ).first()
    if exists:
        raise HTTPException(409, f"This key already belongs to device '{exists.name}'")

    device = Device(
        name=body.name,
        color=body.color,
        private_key_b64=key.private_key_b64,
        adv_key_b64=key.adv_key_b64,
        hashed_adv_key_b64=key.hashed_adv_key_b64,
    )
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


@router.patch("/{device_id}", response_model=DeviceRead)
def update_device(
    body: DeviceUpdate,
    device: Device = Depends(get_device),
    session: Session = Depends(get_session),
):
    for field, value in body.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(device, field, value)
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


@router.delete("/{device_id}", status_code=204)
def delete_device(device: Device = Depends(get_device), session: Session = Depends(get_session)):
    session.delete(device)
    session.commit()


@router.get("/{device_id}/locations", response_model=list[LocationRead])
def list_locations(
    device: Device = Depends(get_device),
    session: Session = Depends(get_session),
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(default=2000, ge=1, le=10000),
):
    """Location history, oldest first. When truncated by `limit`, the newest points are kept."""
    query = select(Location).where(Location.device_id == device.id)
    if since is not None:
        query = query.where(Location.ts >= to_ts(since))
    if until is not None:
        query = query.where(Location.ts <= to_ts(until))
    rows = session.exec(query.order_by(Location.ts.desc()).limit(limit)).all()  # type: ignore[attr-defined]
    return rows[::-1]


@router.post("/{device_id}/refresh")
async def refresh_device(request: Request, device: Device = Depends(get_device)):
    try:
        inserted = await request.app.state.poller.poll(device.id)
    except NeedsLoginError:
        raise HTTPException(409, "Apple login required") from None
    except Exception as e:
        raise HTTPException(502, f"Fetching from Apple failed: {e}") from None
    return {"inserted": inserted}
