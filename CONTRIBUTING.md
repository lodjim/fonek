# Contributing

Bug reports, fixes and improvements are welcome. For anything larger than a small fix, open
an issue first so the approach can be discussed.

Please do not include real advertisement keys, private keys, Apple account details or
location data in issues, pull requests or test fixtures.

## Backend

Python 3.11 or newer.

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
FONEK_DATA_DIR=../data .venv/bin/uvicorn app.main:app --reload
.venv/bin/pytest
```

- `FONEK_DATA_DIR=../data .venv/bin/python -m app.cli seed` adds a demo device with a fake
  track, so the UI can be worked on without an Apple account or a tag.
- `FONEK_NO_POLL=1` disables the background poller.
- Tests run against a temporary data directory and never contact Apple. New behaviour in the
  API or the poller should come with a test in `backend/tests/`.

## Web

Node.js 22.

```bash
cd web
npm install
npm run dev      # http://localhost:3000, proxies /api to http://localhost:8000
npm run lint
```

The project uses a recent Next.js with breaking changes from earlier versions; read
`web/AGENTS.md` before changing framework-level code.

## Hardware

The tag design lives in `fonek/` and needs KiCad 9.

```bash
cd fonek
python3 -m unittest discover -s tests     # electrical design invariants
python3 scripts/generate.py               # refresh the BOM and netlist CSVs
bash scripts/export_pcbway.sh             # ERC, DRC, Gerbers, drills, ZIP (needs kicad-cli)
```

With the KiCad flatpak, `kicad-cli` is
`flatpak run --command=kicad-cli org.kicad.KiCad`.

`design/fonek_rev_a.json` is the source of truth for the circuit. A change to the board must
leave ERC and DRC clean, and the regenerated `reports/`, `pcbway/gerbers/` and fabrication
ZIP belong in the same commit. `scripts/generate_board.py` produces a fresh unrouted board
and overwrites the routed one; only run it to redo the layout on purpose.

## Firmware

fonek uses the upstream OpenHaystack ESP32 firmware unchanged, so firmware fixes belong
[upstream](https://github.com/seemoo-lab/openhaystack). Improvements to the build and flash
instructions in `firmware/README.md` are welcome here.

## Pull requests

- Keep each pull request to one topic.
- Run the tests for the part you changed.
- Update the documentation when behaviour, configuration or the API changes.
