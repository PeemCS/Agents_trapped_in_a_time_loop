#!/usr/bin/env python3
"""Build a file-protocol-friendly director's view of the verified five-trip edit."""

import json
from pathlib import Path


def generate(folder):
    timing = json.loads((folder / "timing.json").read_text())
    chain = json.loads((folder / "backward-search.json").read_text())
    rows = []
    for shot in timing["shots"]:
        i = shot["montage_index"] - 1
        if len(rows) == i:
            rows.append([])
        rows[i].append(
            {
                "label": shot["montage_part"],
                "time": round(shot["first_frame"] / timing["fps"], 4),
                "id": shot["event_id"],
            }
        )
    payload = json.dumps({"rows": rows, "proof": chain}, ensure_ascii=False).replace(
        "<", "\\u003c"
    )
    raw = (Path(__file__).parent / "five-trips-player.html").read_text()
    (folder / "index.html").write_text(raw.replace("/* DATA */ null", payload))


if __name__ == "__main__":
    generate(Path(__file__).parent / "five-trips")
