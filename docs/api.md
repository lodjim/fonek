# API reference

The backend serves a small JSON API under `/api`. The web app reaches it through the
Next.js proxy on port 3000; the backend itself listens on port 8000, where FastAPI also
serves interactive documentation at `/docs` and the OpenAPI schema at `/openapi.json`.

Only `/api/public/*` is authenticated, with an API key; everything else has no
authentication (see [Keeping it private](setup.md#keeping-it-private)).
Timestamps are ISO-8601 in UTC, for example `2026-10-04T18:33:39Z`. Errors use FastAPI's
format: `{"detail": "message"}`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | [`/api/status`](#get-apistatus) | Apple session state and last fetch |
| GET | [`/api/devices`](#get-apidevices) | List devices |
| POST | [`/api/devices`](#post-apidevices) | Create a device |
| PATCH | [`/api/devices/{id}`](#patch-apidevicesid) | Rename or recolour |
| DELETE | [`/api/devices/{id}`](#delete-apidevicesid) | Delete a device and its history |
| GET | [`/api/devices/{id}/locations`](#get-apidevicesidlocations) | Location history |
| POST | [`/api/devices/{id}/refresh`](#post-apidevicesidrefresh) | Fetch from Apple now |
| GET | [`/api/locations/latest`](#get-apilocationslatest) | Latest location of every device |
| GET | [`/api/keys`](#api-keys) | List API keys |
| POST | [`/api/keys`](#api-keys) | Generate an API key |
| DELETE | [`/api/keys/{id}`](#api-keys) | Revoke an API key |
| GET | [`/api/public/locations`](#get-apipubliclocations) | Latest locations, for third parties (API key) |

## Objects

**Device**

```json
{
  "id": 1,
  "name": "Bike",
  "color": "#ef4444",
  "adv_key_b64": "<28-byte advertisement key, Base64>",
  "created_at": "2026-10-04T18:33:39Z",
  "last_polled_at": "2026-10-06T01:28:39Z"
}
```

`last_polled_at` is `null` until the device has been polled. The private key is never
returned.

**Location**

```json
{
  "device_id": 1,
  "timestamp": "2026-10-05T09:12:44Z",
  "lat": 48.8566,
  "lon": 2.3522,
  "accuracy": 25,
  "confidence": 2,
  "status": 0
}
```

`accuracy` is the horizontal accuracy in metres as reported by the finding iPhone.
`confidence` and `status` are passed through from the Find My report. All three can be
`null`.

## Endpoints

### GET /api/status

```json
{
  "apple": "ok",
  "account": "you@example.com",
  "last_poll_at": "2026-10-06T01:28:39Z",
  "last_error": null,
  "poll_interval_min": 15
}
```

`apple` is `"ok"` or `"needs_login"`. `last_poll_at` is the last successful fetch since the
backend started; `last_error` describes the most recent failed one, or is `null`.

### GET /api/devices

Returns an array of devices ordered by id.

### POST /api/devices

| Field | Required | Notes |
| --- | --- | --- |
| `name` | yes | 1 to 64 characters |
| `color` | no | `#rrggbb`, default `#3b82f6` |
| `private_key_b64` | no | Import an existing OpenHaystack private key (28 bytes, Base64). Omit to generate a new key pair |

```bash
curl -X POST localhost:8000/api/devices \
  -H 'Content-Type: application/json' -d '{"name": "Bike"}'
```

Returns `201` with the device. `409` if the key already belongs to a device, `422` if a
field or the key is invalid.

### PATCH /api/devices/{id}

Body: `name` and/or `color`, same rules as above. Returns the updated device, or `404`.

### DELETE /api/devices/{id}

Deletes the device, its private key and all its locations. Returns `204`, or `404`.
This cannot be undone: without the private key, reports for a tag that is already flashed
can no longer be decrypted.

### GET /api/devices/{id}/locations

| Query | Default | Notes |
| --- | --- | --- |
| `since` | none | ISO-8601 datetime, inclusive. Naive values are read as UTC |
| `until` | none | ISO-8601 datetime, inclusive |
| `limit` | `2000` | 1 to 10000 |

Returns locations oldest first. When there are more than `limit`, the newest ones are kept.

```bash
curl 'localhost:8000/api/devices/1/locations?since=2026-10-05T00:00:00Z&limit=500'
```

### POST /api/devices/{id}/refresh

Fetches reports for one device from Apple immediately and stores the new ones.

```json
{ "inserted": 3 }
```

`409` if an Apple login is required, `502` if the fetch from Apple failed. Each call is a
request to Apple, so do not call it in a loop.

### GET /api/locations/latest

Returns an array with the most recent location of every device that has at least one.

### API keys

Keys are managed from **Settings** in the web app, or with `/api/keys`.

`POST /api/keys` takes `name` (1 to 64 characters) and `rate_limit_per_min` (1 to 6000,
default `60`) and returns `201`:

```json
{
  "id": 1,
  "name": "Partner",
  "prefix": "fonek_Ab3dEf",
  "rate_limit_per_min": 60,
  "created_at": "2026-10-12T10:00:00Z",
  "last_used_at": null,
  "key": "fonek_Ab3dEf..."
}
```

`key` is returned only here: the backend stores its SHA-256 hash. `GET /api/keys` returns
the same objects without `key`. `DELETE /api/keys/{id}` revokes a key immediately (`204`,
or `404`).

### GET /api/public/locations

The endpoint to hand to a third party. Send the key as a bearer token:

```bash
curl -H 'Authorization: Bearer fonek_Ab3dEf...' localhost:8000/api/public/locations
```

Returns the same array as [`/api/locations/latest`](#get-apilocationslatest), with the
device `name` added to each location. `401` if the key is missing, unknown or revoked.
`429` with a `Retry-After` header (seconds) once the key has made more than its
`rate_limit_per_min` requests in the current clock minute; counters reset when the backend
restarts. Every response carries `X-RateLimit-Limit` and `X-RateLimit-Remaining`.

The **Settings** page of the web app has the same documentation for third parties and a
playground to send a request with a key.
