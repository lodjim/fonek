import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .apple import AccountManager
from .db import init_db
from .poller import Poller
from .routes import devices, keys, status

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    accounts = AccountManager()
    app.state.poller = poller = Poller(accounts)
    # FONEK_NO_POLL disables the background loop (tests, offline UI work).
    if not os.environ.get("FONEK_NO_POLL"):
        poller.start()
    yield
    await poller.stop()
    await accounts.close()


app = FastAPI(title="fonek", lifespan=lifespan)
app.include_router(devices.router)
app.include_router(status.router)
app.include_router(keys.router)
app.include_router(keys.public)
