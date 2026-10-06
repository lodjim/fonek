"""Apple account session handling and report fetching (via FindMy.py)."""

import asyncio
import logging
from collections.abc import Sequence

from aiohttp import ClientSession, ClientTimeout
from findmy import AsyncAppleAccount, KeyPair, LocalAnisetteProvider, LocationReport, LoginState

from .config import settings

logger = logging.getLogger(__name__)

# FindMy.py hardcodes a 5 s total timeout, which Apple's report endpoint regularly exceeds.
HTTP_TIMEOUT_S = 30
FETCH_ATTEMPTS = 3


def new_account() -> AsyncAppleAccount:
    """A fresh, logged-out account. Anisette data is generated locally."""
    return AsyncAppleAccount(LocalAnisetteProvider(libs_path=settings.anisette_libs_path))


class AccountManager:
    """
    Holds the Apple session restored from `account.json`.

    The session file is written by `python -m app.cli login` (a separate process), so it is
    re-read whenever its mtime changes.
    """

    def __init__(self) -> None:
        self._account: AsyncAppleAccount | None = None
        self._mtime: float | None = None

    async def get(self) -> AsyncAppleAccount | None:
        """Return a logged-in account, or None if a login is needed."""
        path = settings.account_path
        if not path.exists():
            await self.close()
            return None

        mtime = path.stat().st_mtime
        if self._account is None or mtime != self._mtime:
            await self.close()
            try:
                self._account = AsyncAppleAccount.from_json(
                    path, anisette_libs_path=settings.anisette_libs_path
                )
            except Exception:
                logger.exception("Could not restore Apple session from %s", path)
                return None
            # No public knob for the timeout, so hand the library a session of our own.
            self._account._http._session = ClientSession(  # noqa: SLF001
                timeout=ClientTimeout(total=HTTP_TIMEOUT_S)
            )
            self._mtime = mtime

        if self._account.login_state != LoginState.LOGGED_IN:
            return None
        return self._account

    async def fetch_history(self, keys: Sequence[KeyPair]) -> dict[KeyPair, list[LocationReport]]:
        account = await self.get()
        if account is None:
            raise NeedsLoginError
        for attempt in range(1, FETCH_ATTEMPTS + 1):
            try:
                result = await account.fetch_location_history(list(keys))
                break
            except TimeoutError:
                if attempt == FETCH_ATTEMPTS:
                    raise
                logger.warning("Apple timed out (attempt %d/%d), retrying", attempt, FETCH_ATTEMPTS)
                await asyncio.sleep(5 * attempt)
        self._save()
        return result  # type: ignore[return-value]

    def _save(self) -> None:
        # Persist refreshed tokens / anisette state so the session survives restarts.
        if self._account is not None:
            self._account.to_json(settings.account_path)
            self._mtime = settings.account_path.stat().st_mtime

    async def close(self) -> None:
        if self._account is not None:
            await self._account.close()
        self._account = None
        self._mtime = None


class NeedsLoginError(Exception):
    pass
