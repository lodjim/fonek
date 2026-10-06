import os
import tempfile

# Must be set before `app` is imported: settings and the engine are created at import time.
os.environ["FONEK_DATA_DIR"] = tempfile.mkdtemp(prefix="fonek-test-")
os.environ["FONEK_NO_POLL"] = "1"

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app.db import engine
from app.main import app


@pytest.fixture
def client():
    SQLModel.metadata.drop_all(engine)
    with TestClient(app) as c:
        yield c
