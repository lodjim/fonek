"""Export a Specctra DSN or import a routed SES and fill ground copper.

Run in KiCad 9's Python environment. A route is only accepted after DRC/visual
inspection; this script does not assert manufacturing readiness.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pcbnew


ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "kicad" / "fonek.kicad_pcb"


def vector(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def load_board() -> pcbnew.BOARD:
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    if board is None:
        raise RuntimeError(f"KiCad cannot read {BOARD_PATH}")
    return board


def prepare(output: Path) -> None:
    board = load_board()
    if len(board.GetTracks()) != 0:
        raise ValueError("Expected the unrouted source board")
    output.parent.mkdir(parents=True, exist_ok=True)
    if not pcbnew.ExportSpecctraDSN(board, str(output)):
        raise RuntimeError("KiCad rejected DSN export")
    print(f"Exported {output}")


def fill_ground(board: pcbnew.BOARD) -> None:
    ground = board.FindNet("GND")
    if ground is None:
        raise ValueError("GND net missing")
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        zone = pcbnew.ZONE(board)
        zone.SetLayer(layer)
        zone.SetNet(ground)
        zone.SetLocalClearance(pcbnew.FromMM(0.2))
        zone.Outline().NewOutline()
        for x, y in ((0.5, 0.5), (49.5, 0.5), (49.5, 49.5), (0.5, 49.5)):
            zone.Outline().Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
        board.Add(zone)
    # One USB ground pad cannot fit two thermal spokes because the connector
    # contacts are tightly pitched. A solid local tie is intentional here.
    for footprint in board.GetFootprints():
        if footprint.GetReference() == "J1":
            for pad in footprint.Pads():
                if pad.GetNumber() == "B12":
                    pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    if not pcbnew.ZONE_FILLER(board).Fill(board.Zones()):
        raise RuntimeError("KiCad failed to fill ground zones")


def import_route(session: Path) -> None:
    board = load_board()
    if len(board.GetTracks()) != 0:
        raise ValueError("Expected the unrouted source board")
    if not pcbnew.ImportSpecctraSES(board, str(session)):
        raise RuntimeError(f"KiCad rejected route session {session}")
    complete_vbat(board)
    fill_ground(board)
    add_silkscreen(board)
    pcbnew.SaveBoard(str(BOARD_PATH), board)
    print(f"Imported {session}: {len(board.GetTracks())} traces/vias")


def complete_vbat(board: pcbnew.BOARD) -> None:
    """Complete the single battery path the 2-layer auto-router could not fit."""
    net = board.FindNet("VBAT")
    if net is None:
        raise ValueError("VBAT net missing")
    segments = [
        ((4.96, 44.0), (4.96, 41.2), pcbnew.B_Cu),
        ((4.96, 41.2), (11.5, 41.2), pcbnew.B_Cu),
        ((11.5, 41.2), (11.5, 43.0), pcbnew.B_Cu),
        ((11.5, 43.0), (19.4, 43.0), pcbnew.B_Cu),
        ((19.4, 43.0), (19.4, 42.5), pcbnew.B_Cu),
        ((19.4, 42.5), (34.8, 42.5), pcbnew.B_Cu),
        ((34.8, 42.5), (36.3, 42.1), pcbnew.B_Cu),
        ((36.3, 42.1), (38.3675, 40.1143), pcbnew.B_Cu),
    ]
    for start, end, layer in segments:
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(vector(*start))
        track.SetEnd(vector(*end))
        track.SetWidth(pcbnew.FromMM(0.2))
        track.SetLayer(layer)
        track.SetNet(net)
        board.Add(track)


def add_silkscreen(board: pcbnew.BOARD) -> None:
    """Add the few functional markings needed for hand assembly and use."""
    labels = (
        ("fonek A", 25.0, 29.0, 1.0),
        ("CHG", 28.0, 34.0, 0.8),
        ("PWR", 33.0, 48.1, 0.8),
        ("+", 4.96, 47.7, 0.9),
        ("-", 7.5, 47.7, 0.9),
        ("T", 10.04, 47.7, 0.9),
        ("ON", 39.0, 48.3, 0.8),
        ("OFF", 45.0, 48.3, 0.8),
    )
    for label, x, y, size in labels:
        item = pcbnew.PCB_TEXT(board)
        item.SetText(label)
        item.SetPosition(vector(x, y))
        item.SetLayer(pcbnew.F_SilkS)
        item.SetTextSize(vector(size, size))
        item.SetTextThickness(pcbnew.FromMM(0.12))
        board.Add(item)


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--export-dsn", type=Path)
    mode.add_argument("--import-ses", type=Path)
    args = parser.parse_args()
    if args.export_dsn:
        prepare(args.export_dsn)
    else:
        import_route(args.import_ses)


if __name__ == "__main__":
    main()
