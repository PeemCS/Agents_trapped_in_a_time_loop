#!/usr/bin/env python3
"""Read the visible subtitle body from the encoded Rialto film and compare to source text."""

import argparse, hashlib, json, re, subprocess, tempfile
from pathlib import Path
from PIL import Image
from check_note_frames import jpg_frame


def norm(s):
    return re.sub(r"[^a-z0-9]+", "", s.lower().replace("’", "'"))


def screen(out, ocr):
    ledger = json.loads((out / "shot-evidence.json").read_text())
    qa = json.loads((out / "verification.json").read_text())
    vid = out / "film.mp4"
    assert hashlib.sha256(vid.read_bytes()).hexdigest() == qa["mp4_sha256"]
    checks = []
    with tempfile.TemporaryDirectory(prefix="rialto-projection-") as tmp:
        paths = []
        for i, s in enumerate(ledger["shots"]):
            t = (s["start_s"] + s["end_s"]) / 2
            im = jpg_frame(vid, t)
            crop = im.crop(
                (52, 239, 1197, 530) if s["kind"] == "note" else (42, 614, 1240, 699)
            )
            p = Path(tmp) / (str(i) + ".png")
            crop.save(p)
            paths.append(str(p))
        records = json.loads(subprocess.check_output([str(ocr), *paths]))
        assert len(records) == len(ledger["shots"])
        for s, r, path in zip(ledger["shots"], records, paths):
            got = " ".join(r["observations"])
            initial = got
            if norm(got) != norm(s["text"]):
                im = Image.open(path)
                im.resize((2 * im.width, 2 * im.height), Image.Resampling.LANCZOS).save(
                    path
                )
                got = " ".join(
                    json.loads(subprocess.check_output([str(ocr), path]))[0][
                        "observations"
                    ]
                )
            checks.append(
                {
                    "event": s["event_id"],
                    "kind": s["kind"],
                    "source": s["text"],
                    "encoded_ocr": got,
                    "native_size_ocr": initial,
                    "normalized_exact": norm(got) == norm(s["text"]),
                }
            )
    result = {
        "sha256": qa["mp4_sha256"],
        "exact_frames": sum(c["normalized_exact"] for c in checks),
        "sampled_frames": len(checks),
        "checks": checks,
        "method": "From the actual final MP4, decode one midpoint frame per shot and OCR the main subtitle region (or the large model note). Compare after punctuation, whitespace and case normalization.",
    }
    (out / "projection-readback.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    )
    print(result["exact_frames"], "/", len(checks))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder", type=Path)
    p.add_argument("ocr", type=Path)
    a = p.parse_args()
    screen(a.folder, a.ocr)
