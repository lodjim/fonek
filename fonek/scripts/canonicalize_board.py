"""Normalize generated board fields with KiCad's own parser before routing."""

from pathlib import Path

import pcbnew


BOARD = Path(__file__).resolve().parents[1] / "kicad" / "fonek.kicad_pcb"


def main() -> None:
    board = pcbnew.LoadBoard(str(BOARD))
    if board is None:
        raise RuntimeError(f"KiCad cannot read {BOARD}")
    for footprint in board.GetFootprints():
        footprint.Reference().SetVisible(False)
        footprint.Value().SetVisible(False)
        if footprint.GetReference().startswith("TP"):
            for item in footprint.GraphicalItems():
                if isinstance(item, pcbnew.PCB_TEXT) and item.GetLayer() == pcbnew.B_Fab:
                    item.SetMirrored(True)
    pcbnew.SaveBoard(str(BOARD), board)
    print(f"Normalized {BOARD} with {len(board.GetFootprints())} footprints")


if __name__ == "__main__":
    main()
