#!/usr/bin/env python3
"""Read the actual encoded note cards, then keep a contact sheet with their paired physical shots."""

import argparse
import io
import json
from pathlib import Path
import re
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont


def jpg_frame(video, at):
    data = subprocess.check_output(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-ss",
            str(at),
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-f",
            "image2pipe",
            "-c:v",
            "png",
            "-",
        ]
    )
    return Image.open(io.BytesIO(data)).convert("RGB")


def run(folder, ocr):
    report = json.loads((folder / "verification.json").read_text())
    video = folder / "film.mp4"
    seg = report["segments"]
    pairs = [(s, seg[k + 1]) for k, s in enumerate(seg) if s["kind"] == "unspoken model note"]
    cols = 2
    cellw = 450
    cellh = 284
    sheet = Image.new("RGB", (cols * cellw, len(pairs) * cellh), "#14282c")
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 17)
    checks = []
    with tempfile.TemporaryDirectory(prefix="actual-note-ocr-") as temp:
        paths = []
        for i, (note, act) in enumerate(pairs):
            assert act["event_id"] == note["event_id"] and act["kind"] == "committed action"
            a = jpg_frame(video, note["absolute_start_s"] + 0.55 * note["duration"])
            b = jpg_frame(video, act["absolute_start_s"] + 0.68 * act["duration"])
            raw = Path(temp) / (str(i) + ".png")
            a.crop((39, 151, 689, 563)).save(raw)
            paths.append(raw)
            for k, img, label in ((0, a, "Unspoken note"), (1, b, act["action"].replace("_", " "))):
                img.thumbnail((443, 250))
                x = k * cellw
                y = i * cellh
                sheet.paste(img, (x, y))
                d.text((x + 8, y + 253), f"{note['event_id']}    /    {label}", font=f, fill="#e9eedf")
        recognized = json.loads(subprocess.check_output([str(ocr), *map(str, paths)]))
        normalize = lambda s: re.sub(r"[^a-z0-9]+", "", s.lower())
        for (note, act), result in zip(pairs, recognized):
            heard = " ".join(result["observations"])
            checks.append(
                {
                    "event": note["event_id"],
                    "expected": note["quote"],
                    "ocr_text": heard,
                    "normalized_character_match": normalize(heard) == normalize(note["quote"]),
                }
            )
    sheet.save(folder / "contact-sheet.jpg", quality=92)
    (folder / "encoded-note-check.json").write_text(
        json.dumps(
            {
                "method": "Apple Vision OCR on the body of each actual decoded note card at 1280×720. Normalization removes punctuation, whitespace and case. The adjacent image in the contact sheet comes from the very next committed shot.",
                "mp4_sha256": report["mp4_sha256"],
                "cards": checks,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    print(
        sum(c["normalized_character_match"] for c in checks), "/", len(checks), "exact after normalization"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder", type=Path)
    p.add_argument("ocr", type=Path)
    a = p.parse_args()
    run(a.folder, a.ocr)
