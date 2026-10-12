# Setup and operation

## Requirements

- Docker with the Compose plugin
- An ESP32 with Bluetooth LE to act as the tag
- An Apple ID with two-factor authentication enabled. **Create a dedicated one.** fonek uses
  a private Apple API, and an account could be rate-limited or locked.

## Install

```bash
git clone https://github.com/lodjim/fonek.git && cd fonek
cp .env.example .env          # optional, only to change the defaults
docker compose up -d --build
```

This starts two containers:

| Service | Port | Purpose |
| --- | --- | --- |
| `web` | 3000 | The dashboard. Open http://localhost:3000 |
| `backend` | 8000 | The API. Interactive docs at http://localhost:8000/docs |

Runtime state is written to `./data` on the host.

## Log in to Apple

```bash
docker compose run --rm backend python -m app.cli login
```

Enter the Apple ID, its password and the 2FA code (trusted device or SMS). The session is
saved to `data/account.json` and picked up by the running backend without a restart. The
dashboard shows whether the session is valid.

If Apple later rejects the session, the dashboard reports that a login is required: run the
same command again. `python -m app.cli logout` deletes the saved session.

## Add a tag

1. In the dashboard click **Add device**, choose a name and colour. fonek generates a key
   pair. To reuse a key from OpenHaystack, paste its Base64 private key instead.
2. Copy the advertisement key and flash it onto the ESP32:
   [firmware/README.md](../firmware/README.md).
3. Wait. A location appears once an iPhone has passed near the tag and the next poll has
   run. Press **Refresh** on a device to fetch immediately.

## Configuration

Set these in `.env` next to `docker-compose.yml`, or in the environment.

| Variable | Default | Meaning |
| --- | --- | --- |
| `FONEK_POLL_INTERVAL_MIN` | `15` | Minutes between fetches from Apple. Keep it conservative |
| `FONEK_DATA_DIR` | `data` (`/data` in Docker) | Where the database and Apple session live |
| `FONEK_NO_POLL` | unset | Set to any value to disable the background poller (tests, UI work) |
| `BACKEND_URL` | `http://backend:8000` | Build argument of the web image: where `/api` is proxied. Changing it needs a rebuild |

## Keeping it private

The web app and API have no login. Anyone who can reach them can read locations and delete
devices. By default Compose publishes ports 3000 and 8000 on all interfaces, so:

- Do not forward those ports from your router.
- On a shared network, bind them to localhost (`"127.0.0.1:3000:3000"`) or put a reverse
  proxy with authentication in front.
- For remote access, prefer a VPN to your home network.
- To give a third party access, generate an API key in **Settings** and expose only
  `/api/public/` through a reverse proxy. The key protects that path and nothing else: a
  third party who can reach the rest of `/api` does not need a key at all.

## Backups

Everything worth keeping is in `data/`. Losing `fonek.db` means losing the private keys, and
with them the ability to locate tags that are already flashed.

```bash
docker compose stop backend
sudo tar czf fonek-data-$(date +%F).tar.gz data
docker compose start backend
```

The archive contains private keys and Apple session tokens. Store it somewhere safe.

## Updating

```bash
git pull
docker compose up -d --build
```

The database schema is created on startup. There are no migrations yet, so read the release
notes before updating across versions that change the models.

## Troubleshooting

**"Apple login required" / status shows `needs_login`.** Run the login command again. Check
`docker compose logs backend` for the reason the session could not be restored.

**No locations appear.** Confirm the tag is advertising (see the scanner check in
[firmware/README.md](../firmware/README.md)), that the key on the tag is the one shown for
the device, and that iPhones actually pass within Bluetooth range. Reports can take hours.

**"Apple's servers timed out".** The report endpoint is slow at times. The backend retries
three times and tries again at the next poll.

**The backend cannot reach Apple from Docker.** `docker-compose.yml` sets explicit DNS
resolvers (1.1.1.1, 8.8.8.8) because Docker gets none when the host has no
`/etc/resolv.conf`. Change them if your network blocks public resolvers.

**Files in `data/` are owned by root.** The containers run as root, so use `sudo` to back up
or remove them from the host.
