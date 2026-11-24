"""Estimate caption recoverability from real encoded frames at the same physical display width."""

import argparse
import hashlib
import collections
import difflib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from PIL import Image, ImageDraw, ImageFont, ImageOps

ED = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ED))
from edit import write_json
from render_cut import FONT_DIR, wrap


def expected(text, w, h, progress):
    canvas = Image.new("RGB", (w, h))
    font = ImageFont.truetype(str(FONT_DIR / "Georgia.ttf"), max(16, round(h * 0.038)))
    lines = wrap(ImageDraw.Draw(canvas), text, font, w - round(w * 0.05) * 2)
    if len(lines) <= 3:
        return text
    groups = [lines[k : k + 2] for k in range(0, len(lines), 2)]
    weights = [sum(len(x.split()) for x in g) for g in groups]
    target = sum(weights) * progress
    for g, n in zip(groups, weights):
        if target < n:
            return " ".join(g)
        target -= n
    return " ".join(groups[-1])


def inspect(binary, out):
    with tempfile.TemporaryDirectory(prefix="town-readability-") as tmpname:
        tmp = Path(tmpname)
        targets = {}
        examples = []
        for fmt, folder, dest_width in [
            ("landscape_projector", "wednesday-couch", 1280),
            ("landscape_phone", "wednesday-couch", 390),
            ("portrait_phone", "phone-cut", 390),
        ]:
            loc = ED / folder
            t = json.loads((loc / "timing.json").read_text())
            w, h = t["size"]
            for idx in (0, 6, 7, 8):
                shot = next(s for s in t["shots"] if s["event_index"] == idx and s["view"] == "action")
                q = shot["speech"][0]
                for k, frac in enumerate((0.22, 0.67)):
                    sec = q["start_s"] + frac * (q["end_s"] - q["start_s"])
                    data = subprocess.check_output(
                        [
                            "ffmpeg",
                            "-nostdin",
                            "-v",
                            "error",
                            "-ss",
                            str(sec),
                            "-i",
                            str(loc / "film.mp4"),
                            "-frames:v",
                            "1",
                            "-f",
                            "image2pipe",
                            "-c:v",
                            "png",
                            "-",
                        ]
                    )
                    im = Image.open(io.BytesIO(data)).convert("RGB")
                    new_h = round(h * dest_width / w)
                    im = im.resize((dest_width, new_h), Image.Resampling.LANCZOS)
                    # Crop out the source ID, HUD and character name; leave the physical glyphs at display scale.
                    crop = im.crop((0, round(new_h * 0.85), dest_width, round(new_h * 0.968)))
                    crop = ImageOps.expand(crop, border=(6, 18, 6, 18), fill="#101e25")
                    name = tmp / f"{fmt}-{idx}-{k}.png"
                    crop.save(name)
                    targets[str(name)] = (fmt, idx, k, expected(q["text"], w, h, frac))
                    if idx == 7 and k == 1 and "phone" in fmt:
                        examples.append((fmt, im.copy()))
        read = json.loads(subprocess.check_output([str(binary), *targets]))
        rows = []
        totals = collections.defaultdict(lambda: [0, 0])
        for item in read:
            fmt, idx, k, wanted = targets[item["path"]]
            got = " ".join(item["observations"])
            tokens = lambda x: re.findall(r"[a-z0-9]+", x.lower())
            a = tokens(wanted)
            b = tokens(got)
            matched = sum(
                m.size for m in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks()
            )
            totals[fmt][0] += matched
            totals[fmt][1] += len(a)
            rows.append(
                {
                    "layout": fmt,
                    "event_index": idx,
                    "sample": k,
                    "expected": wanted,
                    "ocr": got,
                    "ordered_token_recall": round(matched / len(a), 3),
                }
            )
        if examples:
            sheet = Image.new("RGB", (808, 760), "#11272a")
            d = ImageDraw.Draw(sheet)
            for j, (fmt, im) in enumerate(examples):
                x = 10 + j * 400
                sheet.paste(im, (x, 42))
                d.text((x, 12), fmt.replace("_", " "), fill="#f3ddb4")
            sheet.save(out.with_name("same-width.jpg"), quality=92)
        result = {
            "media_sha256": {
                folder: hashlib.sha256((ED / folder / "film.mp4").read_bytes()).hexdigest()
                for folder in ("wednesday-couch", "phone-cut")
            },
            "method": "Apple Vision accurate English OCR without language correction. Eight real frames per layout, same four lines at 22% and 67% of speech. Resize full frame to target width then crop dialogue band without upsampling. Score ordered matched word tokens against displayed cue. Machine-only screen legibility proxy. Some repeated tokens and redisplay of the same sentence occur.",
            "summary": {
                key: {"matching_tokens": v[0], "expected_tokens": v[1], "recall": round(v[0] / v[1], 3)}
                for key, v in totals.items()
            },
            "frames": rows,
        }
        write_json(out, result)
        print(result["summary"])


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("binary", type=Path)
    p.add_argument("out", type=Path)
    a = p.parse_args()
    inspect(a.binary, a.out)
