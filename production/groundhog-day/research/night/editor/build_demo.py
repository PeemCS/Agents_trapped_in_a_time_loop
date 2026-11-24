#!/usr/bin/env python3
"""Create a private 2-minute presentation from two verified, identically configured lives."""

from pathlib import Path
import hashlib
import json
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont
from edit import write_json

ROOT = Path(__file__).resolve().parent
TAKES = ROOT.parent / "takes" / "q27" / "film-transcript"
W, H, FPS = 1280, 720, 16
FONTS = Path("/System/Library/Fonts/Supplemental")


def font(name, n):
    return ImageFont.truetype(str(FONTS / name), n)


def linewrap(pen, s, ft, width):
    lines = []
    for word in s.split():
        if lines and pen.textlength(lines[-1] + " " + word, font=ft) <= width:
            lines[-1] += " " + word
        else:
            lines.append(word)
    return lines


def card(path, heading, subheading, context):
    im = Image.new("RGB", (W, H), "#14282c")
    d = ImageDraw.Draw(im)
    d.rectangle((72, 103, 163, 109), fill="#edc075")
    d.text((72, 165), heading, font=font("Georgia.ttf", 76), fill="#fff5da")
    d.text((76, 303), subheading, font=font("Arial.ttf", 35), fill="#ecede1")
    d.text((76, 554), context, font=font("Arial.ttf", 23), fill="#a6bcaf")
    im.save(path)


def evidence(path, edits, receipt):
    im = Image.new("RGB", (W, H), "#14282c")
    d = ImageDraw.Draw(im)
    d.text((62, 55), "Two decisions at one o’clock", font=font("Georgia.ttf", 60), fill="#fff5da")
    d.text(
        (65, 150),
        "SAME SIXTH TUESDAY     ·     SAME TICKET     ·     INDEPENDENT RUNS",
        font=font("Arial Bold.ttf", 20),
        fill="#e6b46d",
    )
    d.line((641, 227, 641, 547), fill="#566b65", width=2)
    for col, (trace, film, title, seed) in enumerate(edits):
        e = trace["events"][22]
        x = 65 + col * 618
        d.text((x, 230), title, font=font("Georgia.ttf", 39), fill="#fff5da")
        d.text((x, 316), "PHIL’S STATED INTENTION", font=font("Arial Bold.ttf", 17), fill="#e6b46d")
        body = font("Arial.ttf", 26)
        for n, l in enumerate(linewrap(d, "“" + e["decision"]["intention"] + "”", body, 510)):
            d.text((x, 353 + n * 35), l, font=body, fill="#e9ede0")
        d.text((x, 529), f"Take {seed}   ·   {e['id']}", font=font("Courier New.ttf", 17), fill="#adbfba")
    rows = receipt["ledger"]["rows"]
    total = sum(row[1] for row in rows)
    d.line((65, 591, W - 65, 591), fill="#5e7269", width=1)
    d.text(
        (65, 615),
        f"Local Bruin run  ·  {total} actor decisions  ·  2 assets  ·  3 quality checks passed",
        font=font("Arial.ttf", 22),
        fill="#d2dfd2",
    )
    im.save(path)


def ff(args):
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", *args], check=True)


def build():
    takes = []
    sources = []
    for folder, seed, title in [
        ("wednesday-couch", 701, "He boards the coach."),
        ("afternoon-coach", 702, "He walks to the depot."),
    ]:
        loc = ROOT / folder
        tracefile = TAKES / f"seed-{seed}.json"
        trace = json.loads(tracefile.read_text())
        film = loc / "film.mp4"
        q = json.loads((loc / "qa.json").read_text())
        assert (
            q["source_sha256"] == hashlib.sha256(tracefile.read_bytes()).hexdigest()
            and q["mp4_sha256"] == hashlib.sha256(film.read_bytes()).hexdigest()
        )
        takes.append((trace, film, title, seed))
        sources.append({"seed": seed, "source_sha256": q["source_sha256"], "film_sha256": q["mp4_sha256"]})
    receipt_file = ROOT / "matched-film-bruin.json"
    receipt = json.loads(receipt_file.read_text())
    assert set(receipt["input_hashes"]) == {s["source_sha256"] for s in sources}
    assert "2 succeeded" in receipt["run_log"] and "3 succeeded" in receipt["run_log"]
    assert (
        takes[0][0]["events"][22]["decision"]["action"] == "take_coach_to_Pittsburgh"
        and takes[1][0]["events"][22]["decision"]["action"] == "go_to_depot"
    )
    t = [json.loads((f.parent / "timing.json").read_text()) for _, f, _, _ in takes]
    cut_start = next(s["first_frame"] / FPS for s in t[1]["shots"] if s["event_index"] == 18)
    out = ROOT / "two-takes-demo.mp4"
    records = []
    with tempfile.TemporaryDirectory(prefix="town-presentation-") as directory:
        tmp = Path(directory)
        vid = lambda n: str(tmp / (n + ".mp4"))
        card(
            tmp / "a.png",
            "The Wednesday Couch",
            "Phil has a coach ticket. His sister has a couch to move.",
            "A private rehearsal with three independently deciding agents.",
        )
        card(
            tmp / "b.png",
            "The other ticket",
            "Same hotel, same crew, same one o’clock coach.",
            "A second run with a different sampling seed.",
        )
        evidence(tmp / "c.png", takes, receipt)
        parts = [
            ("opener", tmp / "a.png", 0, 4.0),
            ("take701", takes[0][1], 0, t[0]["seconds"]),
            ("fork", tmp / "b.png", 0, 4.0),
            ("take702", takes[1][1], cut_start, t[1]["seconds"] - cut_start),
            ("proof", tmp / "c.png", 0, 12.0),
        ]
        for n, source, start, duration in parts:
            if source.suffix == ".png":
                inputs = [
                    "-loop",
                    "1",
                    "-framerate",
                    str(FPS),
                    "-i",
                    str(source),
                    "-f",
                    "lavfi",
                    "-i",
                    "anullsrc=r=48000:cl=mono",
                ]
            else:
                inputs = ["-ss", str(start), "-i", str(source)]
            ff(
                [
                    *inputs,
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0" if source.suffix == ".png" else "0:a:0",
                    "-t",
                    str(duration),
                    "-c:v",
                    "libx264",
                    "-r",
                    str(FPS),
                    "-pix_fmt",
                    "yuv420p",
                    "-crf",
                    "19",
                    "-preset",
                    "veryfast",
                    "-c:a",
                    "aac",
                    "-ar",
                    "48000",
                    "-ac",
                    "1",
                    "-b:a",
                    "144k",
                    vid(n),
                ]
            )
            records.append({"component": n, "source_seconds_in": start, "duration_s": duration})
        # Decode and concatenate the five already normalized streams, trimming each on its own clock.
        inputs = []
        filters = []
        labels = []
        for j, (n, _, _, duration) in enumerate(parts):
            inputs.extend(["-i", vid(n)])
            filters.extend(
                [
                    f"[{j}:v]trim=duration={duration},setpts=PTS-STARTPTS[v{j}]",
                    f"[{j}:a]atrim=duration={duration},asetpts=PTS-STARTPTS[a{j}]",
                ]
            )
            labels.append(f"[v{j}][a{j}]")
        filters.append("".join(labels) + f"concat=n={len(parts)}:v=1:a=1[v][a]")
        tmpout = tmp / "presentation.mp4"
        ff(
            [
                *inputs,
                "-filter_complex",
                ";".join(filters),
                "-map",
                "[v]",
                "-map",
                "[a]",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "19",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                "-b:a",
                "144k",
                "-movflags",
                "+faststart",
                str(tmpout),
            ]
        )
        tmpout.replace(out)
    expected = sum(x["duration_s"] for x in records)
    info = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=codec_name,codec_type,nb_frames:format=duration,size",
                "-of",
                "json",
                str(out),
            ]
        )
    )
    duration = float(info["format"]["duration"])
    assert 60 < duration < 180 and abs(duration - expected) < 0.13
    ff(["-i", str(out), "-f", "null", "-"])
    write_json(
        ROOT / "two-takes-demo.json",
        {
            "private_edit": "Local FFmpeg presentation rehearsal. Event-day AdaL export pending.",
            "sources": sources,
            "bruin_receipt_sha256": hashlib.sha256(receipt_file.read_bytes()).hexdigest(),
            "components": records,
            "master_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
            "full_decode": True,
            "probe": info,
        },
    )
    print(out, round(duration, 2), "seconds")


if __name__ == "__main__":
    build()
