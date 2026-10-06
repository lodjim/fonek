import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence

from findmy import KeyPair, LocationReport, UnauthorizedError
from sqlalchemy.dialects.sqlite import insert
from sqlmodel import Session, select

from .apple import AccountManager, NeedsLoginError
from .config import settings
from .db import engine
from .models import Device, Location, now_ts

logger = logging.getLogger(__name__)

FetchHistory = Callable[[Sequence[KeyPair]], Awaitable[dict[KeyPair, list[LocationReport]]]]


async def poll_devices(session: Session, devices: Sequence[Device], fetch: FetchHistory) -> int:
    """Fetch reports for `devices` and store the new ones. Returns the number inserted."""
    if not devices:
        return 0

    keys = {d.id: KeyPair.from_b64(d.private_key_b64) for d in devices}
    reports = await fetch(list(keys.values()))

    inserted = 0
    polled_ts = now_ts()
    for device in devices:
        rows = [
            {
                "device_id": device.id,
                "ts": int(r.timestamp.timestamp()),
                "lat": r.latitude,
                "lon": r.longitude,
                "accuracy": r.horizontal_accuracy,
                "confidence": r.confidence,
                "status": r.status,
            }
            for r in reports.get(keys[device.id], [])
        ]
        if rows:
            # Apple returns overlapping history on every call; the unique constraint dedups.
            result = session.exec(insert(Location).values(rows).on_conflict_do_nothing())  # type: ignore[call-overload]
            inserted += result.rowcount
        device.last_polled_ts = polled_ts
        session.add(device)
    session.commit()
    return inserted


class Poller:
    def __init__(self, accounts: AccountManager) -> None:
        self.accounts = accounts
        self.last_poll_ts: int | None = None
        self.last_error: str | None = None
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None

    async def poll(self, device_id: int | None = None) -> int:
        """Poll one device, or all of them. Raises NeedsLoginError if there is no session."""
        async with self._lock:
            if await self.accounts.get() is None:
                raise NeedsLoginError
            with Session(engine) as session:
                query = select(Device)
                if device_id is not None:
                    query = query.where(Device.id == device_id)
                devices = session.exec(query).all()
                try:
                    inserted = await poll_devices(session, devices, self.accounts.fetch_history)
                except NeedsLoginError:
                    raise
                except UnauthorizedError as e:
                    self.last_error = "Apple rejected the session; log in again."
                    raise NeedsLoginError from e
                except TimeoutError:
                    self.last_error = "Apple's servers timed out; will retry on the next poll."
                    raise
                except Exception as e:
                    self.last_error = f"{type(e).__name__}: {e}".removesuffix(": ")
                    raise
            self.last_poll_ts = now_ts()
            self.last_error = None
            return inserted

    async def _run(self) -> None:
        while True:
            try:
                inserted = await self.poll()
                logger.info("Poll finished, %d new location(s)", inserted)
            except NeedsLoginError:
                logger.warning("No Apple session; run `python -m app.cli login`")
            except Exception:
                logger.exception("Poll failed")
            await asyncio.sleep(settings.poll_interval_min * 60)

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
