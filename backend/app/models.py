from datetime import datetime, timezone

from pydantic import BaseModel, computed_field
from pydantic import Field as PField
from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint
from sqlmodel import Field, SQLModel


def now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def iso(ts: int | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


# All times are stored as unix seconds (UTC) and serialised as ISO-8601 strings.


class Device(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    color: str = "#3b82f6"
    private_key_b64: str
    adv_key_b64: str
    hashed_adv_key_b64: str = Field(index=True, unique=True)
    created_ts: int = Field(default_factory=now_ts)
    last_polled_ts: int | None = None


class Location(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("device_id", "ts", "lat", "lon"),)

    id: int | None = Field(default=None, primary_key=True)
    device_id: int = Field(
        sa_column=Column(
            Integer, ForeignKey("device.id", ondelete="CASCADE"), index=True, nullable=False
        )
    )
    ts: int = Field(index=True)
    lat: float
    lon: float
    accuracy: int | None = None
    confidence: int | None = None
    status: int | None = None


class DeviceCreate(BaseModel):
    name: str = PField(min_length=1, max_length=64)
    color: str = PField(default="#3b82f6", pattern=r"^#[0-9a-fA-F]{6}$")
    # Import an existing OpenHaystack private key instead of generating a new one.
    private_key_b64: str | None = None


class DeviceUpdate(BaseModel):
    name: str | None = PField(default=None, min_length=1, max_length=64)
    color: str | None = PField(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class DeviceRead(BaseModel):
    """Public view of a device. Never includes the private key."""

    id: int
    name: str
    color: str
    adv_key_b64: str
    created_ts: int = PField(exclude=True)
    last_polled_ts: int | None = PField(default=None, exclude=True)

    @computed_field
    @property
    def created_at(self) -> str:
        return iso(self.created_ts)  # type: ignore[return-value]

    @computed_field
    @property
    def last_polled_at(self) -> str | None:
        return iso(self.last_polled_ts)


class LocationRead(BaseModel):
    device_id: int
    ts: int = PField(exclude=True)
    lat: float
    lon: float
    accuracy: int | None
    confidence: int | None
    status: int | None

    @computed_field
    @property
    def timestamp(self) -> str:
        return iso(self.ts)  # type: ignore[return-value]


class ApiKey(SQLModel, table=True):
    """Third-party access to /api/public. Only the SHA-256 of the key is stored."""

    id: int | None = Field(default=None, primary_key=True)
    name: str
    prefix: str  # start of the key, shown in the UI to tell keys apart
    key_hash: str = Field(index=True, unique=True)
    rate_limit_per_min: int = 60
    created_ts: int = Field(default_factory=now_ts)
    last_used_ts: int | None = None


class ApiKeyCreate(BaseModel):
    name: str = PField(min_length=1, max_length=64)
    rate_limit_per_min: int = PField(default=60, ge=1, le=6000)


class ApiKeyRead(BaseModel):
    """Never includes the key itself: it is only returned once, on creation."""

    id: int
    name: str
    prefix: str
    rate_limit_per_min: int
    created_ts: int = PField(exclude=True)
    last_used_ts: int | None = PField(default=None, exclude=True)

    @computed_field
    @property
    def created_at(self) -> str:
        return iso(self.created_ts)  # type: ignore[return-value]

    @computed_field
    @property
    def last_used_at(self) -> str | None:
        return iso(self.last_used_ts)


class ApiKeyCreated(ApiKeyRead):
    key: str


class PublicLocation(LocationRead):
    name: str
