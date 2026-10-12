import base64
import hashlib
from datetime import datetime, timezone

from findmy import KeyPair
from sqlmodel import Session, select

from app.db import engine
from app.models import Device, Location
from app.poller import poll_devices


class FakeReport:
    def __init__(self, ts: int, lat: float, lon: float):
        self.timestamp = datetime.fromtimestamp(ts, tz=timezone.utc)
        self.latitude, self.longitude = lat, lon
        self.horizontal_accuracy, self.confidence, self.status = 30, 2, 0


def make_fetch(reports):
    async def fetch(keys):
        return {k: reports for k in keys}

    return fetch


def test_status_needs_login(client):
    body = client.get("/api/status").json()
    assert body["apple"] == "needs_login"
    assert body["last_poll_at"] is None


def test_create_device_generates_key(client):
    r = client.post("/api/devices", json={"name": "Bike"})
    assert r.status_code == 201
    body = r.json()
    assert "private_key_b64" not in body
    adv = base64.b64decode(body["adv_key_b64"])
    assert len(adv) == 28

    with Session(engine) as s:
        device = s.get(Device, body["id"])
        assert KeyPair.from_b64(device.private_key_b64).adv_key_b64 == body["adv_key_b64"]
        assert device.hashed_adv_key_b64 == base64.b64encode(hashlib.sha256(adv).digest()).decode()


def test_import_key_and_duplicates(client):
    key = KeyPair.new()
    r = client.post("/api/devices", json={"name": "A", "private_key_b64": key.private_key_b64})
    assert r.status_code == 201 and r.json()["adv_key_b64"] == key.adv_key_b64
    assert client.post("/api/devices", json={"name": "B", "private_key_b64": key.private_key_b64}).status_code == 409
    assert client.post("/api/devices", json={"name": "C", "private_key_b64": "nope"}).status_code == 422


def test_update_delete(client):
    id_ = client.post("/api/devices", json={"name": "A"}).json()["id"]
    r = client.patch(f"/api/devices/{id_}", json={"name": "B", "color": "#00ff00"})
    assert r.json()["name"] == "B" and r.json()["color"] == "#00ff00"
    assert client.patch(f"/api/devices/{id_}", json={"color": "red"}).status_code == 422
    assert client.delete(f"/api/devices/{id_}").status_code == 204
    assert client.get("/api/devices").json() == []
    assert client.get(f"/api/devices/{id_}/locations").status_code == 404


async def _poll(device_id, reports):
    with Session(engine) as s:
        return await poll_devices(s, [s.get(Device, device_id)], make_fetch(reports))


def test_poll_dedup_and_queries(client):
    import asyncio

    id_ = client.post("/api/devices", json={"name": "A"}).json()["id"]
    other = client.post("/api/devices", json={"name": "Empty"}).json()["id"]
    reports = [FakeReport(1_700_000_000 + i * 3600, 48.0 + i, 2.0) for i in range(3)]

    assert asyncio.run(_poll(id_, reports)) == 3
    # Overlapping history plus one new report
    assert asyncio.run(_poll(id_, reports + [FakeReport(1_700_020_000, 60.0, 2.0)])) == 1

    locs = client.get(f"/api/devices/{id_}/locations").json()
    assert [l["lat"] for l in locs] == [48.0, 49.0, 50.0, 60.0]
    assert locs[0]["timestamp"] == "2023-11-14T22:13:20Z"

    since = client.get(f"/api/devices/{id_}/locations", params={"since": "2023-11-14T23:00:00Z"}).json()
    assert len(since) == 3
    assert [l["lat"] for l in client.get(f"/api/devices/{id_}/locations", params={"limit": 2}).json()] == [50.0, 60.0]

    latest = client.get("/api/locations/latest").json()
    assert len(latest) == 1 and latest[0]["lat"] == 60.0 and latest[0]["device_id"] == id_
    assert client.get("/api/devices").json()[0]["last_polled_at"] is not None

    assert client.post(f"/api/devices/{other}/refresh").status_code == 409  # no Apple session

    client.delete(f"/api/devices/{id_}")
    with Session(engine) as s:
        assert s.exec(select(Location)).all() == []


def test_api_keys_and_public_locations(client):
    import asyncio

    id_ = client.post("/api/devices", json={"name": "Bike"}).json()["id"]
    asyncio.run(_poll(id_, [FakeReport(1_700_000_000, 48.0, 2.0)]))

    assert client.get("/api/public/locations").status_code == 401
    assert client.get("/api/public/locations", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.post("/api/keys", json={"name": "x", "rate_limit_per_min": 0}).status_code == 422

    created = client.post("/api/keys", json={"name": "Partner", "rate_limit_per_min": 2}).json()
    auth = {"Authorization": f"Bearer {created['key']}"}
    listed = client.get("/api/keys").json()
    assert len(listed) == 1 and "key" not in listed[0] and "key_hash" not in listed[0]
    assert created["key"].startswith(listed[0]["prefix"]) and listed[0]["last_used_at"] is None

    r = client.get("/api/public/locations", headers=auth)
    assert r.status_code == 200
    assert r.json()[0]["name"] == "Bike" and r.json()[0]["lat"] == 48.0
    assert r.headers["X-RateLimit-Limit"] == "2" and r.headers["X-RateLimit-Remaining"] == "1"
    assert client.get("/api/public/locations", headers=auth).status_code == 200
    limited = client.get("/api/public/locations", headers=auth)
    assert limited.status_code == 429 and "Retry-After" in limited.headers
    assert client.get("/api/keys").json()[0]["last_used_at"] is not None

    assert client.delete(f"/api/keys/{created['id']}").status_code == 204
    assert client.get("/api/public/locations", headers=auth).status_code == 401
