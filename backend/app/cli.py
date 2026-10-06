"""
Maintenance commands.

    python -m app.cli login    # interactive Apple ID login (with 2FA), saves the session
    python -m app.cli logout   # delete the saved session
    python -m app.cli seed     # add a demo device with a fake track (for UI work)
"""

import argparse
import asyncio
import math
import random
from getpass import getpass

from findmy import (
    KeyPair,
    LoginState,
    SmsSecondFactorMethod,
    TrustedDeviceSecondFactorMethod,
)
from sqlmodel import Session

from .apple import new_account
from .config import settings
from .db import engine, init_db
from .models import Device, Location, now_ts


async def login() -> None:
    account = new_account()
    try:
        email = input("Apple ID email: ").strip()
        password = getpass("Password: ")
        state = await account.login(email, password)

        if state == LoginState.REQUIRE_2FA:
            methods = await account.get_2fa_methods()
            for i, method in enumerate(methods):
                if isinstance(method, TrustedDeviceSecondFactorMethod):
                    print(f"  {i} - Trusted device")
                elif isinstance(method, SmsSecondFactorMethod):
                    print(f"  {i} - SMS ({method.phone_number})")
            method = methods[int(input("2FA method: "))]
            await method.request()
            await method.submit(input("Code: ").strip())

        if account.login_state != LoginState.LOGGED_IN:
            raise SystemExit(f"Login failed (state: {account.login_state})")

        account.to_json(settings.account_path)
        settings.account_path.chmod(0o600)
        print(f"Logged in as {account.account_name}. Session saved to {settings.account_path}")
    finally:
        await account.close()


def logout() -> None:
    settings.account_path.unlink(missing_ok=True)
    print("Session removed.")


def seed() -> None:
    init_db()
    key = KeyPair.new()
    rng = random.Random(7)
    with Session(engine) as session:
        device = Device(
            name="Demo tag",
            color="#ef4444",
            private_key_b64=key.private_key_b64,
            adv_key_b64=key.adv_key_b64,
            hashed_adv_key_b64=key.hashed_adv_key_b64,
        )
        session.add(device)
        session.commit()
        session.refresh(device)

        # A wandering loop around central Paris over the last five days.
        now = now_ts()
        points = 80
        for i in range(points):
            angle = i / points * 4 * math.pi
            session.add(
                Location(
                    device_id=device.id,
                    ts=now - (points - i) * 90 * 60 + rng.randint(-600, 600),
                    lat=48.8566 + 0.02 * math.sin(angle) + rng.uniform(-0.002, 0.002),
                    lon=2.3522 + 0.035 * math.cos(angle / 2) + rng.uniform(-0.002, 0.002),
                    accuracy=rng.choice([10, 25, 40, 65, 120]),
                    confidence=rng.randint(1, 3),
                    status=0,
                )
            )
        session.commit()
        print(f"Seeded device {device.id} with {points} locations.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    parser.add_argument("command", choices=["login", "logout", "seed"])
    command = parser.parse_args().command
    if command == "login":
        asyncio.run(login())
    elif command == "logout":
        logout()
    else:
        seed()


if __name__ == "__main__":
    main()
