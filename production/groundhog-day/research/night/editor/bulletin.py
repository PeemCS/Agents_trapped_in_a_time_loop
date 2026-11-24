#!/usr/bin/env python3
"""Replay the final evening as a three-monitor control room, then the station's physical return."""

import argparse
import base64
import hashlib
import io
import math
from pathlib import Path
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright
from edit import read_trace, write_json
from render_cut import RATE, VOICES, synth_line, wav

FPS = 12
W, H = 1280, 720
ROLE = ("reporter", "producer", "camera")
FONTS = Path("/System/Library/Fonts/Supplemental")
FONT = {
    key: ImageFont.truetype(str(FONTS / file), size)
    for key, file, size in [
        ("title", "Georgia.ttf", 49),
        ("h", "Arial Bold.ttf", 25),
        ("body", "Arial.ttf", 26),
        ("small", "Arial.ttf", 20),
        ("micro", "Courier New.ttf", 16),
    ]
}
BG = "#15262a"
CREAM = "#f8f2dc"
AMBER = "#e6b16d"
GREEN = "#b5ceba"


def before_cut(path):
    trace, digest = read_trace(path)
    ev = trace["events"]
    last = ev[-1]
    picked = last["world_after"].get("bulletin")
    if not picked or last["clock"] != "7:00 pm":
        raise ValueError("no resolved final evening bulletin")
    rows = {r["id"]: (i, r) for i, e in enumerate(ev) for r in [e, *e["cast"]]}
    end = {r["role"]: r for r in [last, *last["cast"]]}
    by_role = lambda role: end[role]["decision"]["action"]
    ch = picked["channel"]
    role = picked["source_role"]
    source_ids = picked["source_ids"]
    if not source_ids or any(x not in rows or rows[x][1]["day"] != last["day"] for x in source_ids):
        raise ValueError("missing source from this date")
    if source_ids[0] != end["producer"]["id"]:
        raise ValueError("missing final producer choice")
    if ch in ("live_report", "silent_live_reporter_line"):
        assert (
            by_role("producer") == "patch_reporter_line"
            and by_role("reporter") == "call_live_report"
            and role == "reporter"
            and end["reporter"]["id"] in source_ids
        )
    elif ch in ("producer_live", "silent_producer_mic"):
        assert by_role("producer") == "host_bulletin" and role == "producer"
    elif ch == "camera_take":
        assert (
            by_role("producer") == "patch_camera_line"
            and by_role("camera") == "send_camera_take"
            and end["camera"]["id"] in source_ids
        )
        assert any(
            rows[r][0] < len(ev) - 1 and rows[r][1]["decision"]["action"].startswith("film_")
            for r in source_ids
        )
    elif ch == "filed_forecast":
        assert by_role("producer") == "play_filed_forecast" and any(
            rows[r][0] < len(ev) - 1 and rows[r][1]["decision"]["action"] == "file_forecast"
            for r in source_ids
        )
    elif ch == "empty_selected_return":
        assert by_role("producer") in ("patch_reporter_line", "patch_camera_line") and role is None
    elif ch == "station_ident":
        assert (
            by_role("producer")
            not in ("patch_reporter_line", "patch_camera_line", "play_filed_forecast", "host_bulletin")
            and role is None
        )
    else:
        raise ValueError("unknown bulletin channel")
    if ch in ("live_report", "producer_live", "silent_live_reporter_line", "silent_producer_mic"):
        assert (
            picked["spoken"] == end[role]["decision"]["words"]
            and picked["source_place"] == end[role]["place"]
        )
    else:
        assert not picked["spoken"]
    final = [(i, e) for i, e in enumerate(ev) if e["day"] == last["day"]]
    assert len(final) == 4
    credit = {
        "source_sha256": digest,
        "source_type": trace.get("source", trace.get("source_type")),
        "source_path": str(path),
        "final_day": last["day"],
        "event_ids": [e["id"] for _, e in final],
        "bulletin": picked,
        "source_rows": [
            {
                "event_id": r,
                "slot": rows[r][0],
                "actor": rows[r][1]["actor"],
                "action": rows[r][1]["decision"]["action"],
                "place": rows[r][1]["place"],
            }
            for r in source_ids
        ],
    }
    return trace, final, end, rows, credit


def wrap(draw, s, font, width):
    lines = []
    for word in s.split():
        if lines and draw.textlength(lines[-1] + " " + word, font=font) <= width:
            lines[-1] += " " + word
        else:
            lines.append(word)
    return lines


def capture(page, index, progress):
    content = page.evaluate(
        '([i,p])=>{TuesdayTown.seek(i,p);return document.querySelector("#town").toDataURL("image/jpeg",.92).split(",")[1]}',
        [index, progress],
    )
    return Image.open(io.BytesIO(base64.b64decode(content))).convert("RGB")


def stage3(views, i, e, progress):
    image = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(image)
    slot = {r["role"]: r for r in [e, *e["cast"]]}
    d.text((53, 38), "The seven o’clock bulletin", font=FONT["title"], fill=CREAM)
    d.text(
        (56, 115),
        f"TUESDAY {e['day']}    /    {e['clock'].upper()}    /    THREE SIMULTANEOUS CHOICES",
        font=FONT["small"],
        fill=AMBER,
    )
    for j, role in enumerate(ROLE):
        x = 52 + j * 397
        r = slot[role]
        pic = capture(views[role], i, progress)
        pic = pic.resize((375, 251), Image.Resampling.LANCZOS)
        image.paste(pic, (x, 178))
        d.text((x, 455), f"{r['actor']}  /  {role}", font=FONT["h"], fill=CREAM)
        action = r["decision"]["action"].replace("_", " ")
        tokens = wrap(d, action, FONT["body"], 375)
        for n, l in enumerate(tokens):
            d.text((x, 504 + n * 34), l, font=FONT["body"], fill=GREEN)
        place = r["place"] if r["origin"] == r["place"] else r["origin"] + " → " + r["place"]
        signal = r["decision"].get("detail", "")
        if r.get("signal_status") == "sent":
            labels = {
                "invite_camera": "Invited " + slot["camera"]["actor"],
                "invite_reporter": "Invited " + slot["reporter"]["actor"],
                "accept_assignment": "Accepted assignment",
                "decline_assignment": "Declined assignment",
            }
            if signal in labels:
                d.text((x, 559), labels[signal], font=FONT["small"], fill=CREAM)
        d.text((x, 607), place, font=FONT["small"], fill=AMBER)
        d.text((x, 647), r["id"], font=FONT["micro"], fill="#9bb3ab")
    return image


def source_view(views, ev, receipt, rows, role_rows, sec, duration):
    chosen = receipt["bulletin"]
    channel = chosen["channel"]
    mode = chosen["source_role"]
    ref = receipt["source_rows"]
    last_i = len(ev) - 1
    view_role = None
    words = chosen["spoken"]
    if mode in ("producer", "reporter"):
        view_role = mode
        i = last_i
    elif channel in ("camera_take", "filed_forecast"):
        i, op = next((rows[x] for x in chosen["source_ids"] if rows[x][0] < last_i))
        view_role = op["role"]
    image = Image.new("RGB", (W, H), "#0f2024")
    d = ImageDraw.Draw(image)
    banner = {
        "live_report": "Live reporter return",
        "producer_live": "Producer microphone",
        "silent_live_reporter_line": "Silent reporter return",
        "silent_producer_mic": "Silent producer microphone",
        "empty_selected_return": "Empty return",
        "station_ident": "Station identification",
        "camera_take": "Camera tape",
        "filed_forecast": "Filed weather reel",
    }[channel]
    d.text((56, 37), "On air", font=FONT["title"], fill=CREAM)
    d.text((56, 111), f"7:00 PM     /     {banner.upper()}", font=FONT["small"], fill=AMBER)
    if view_role:
        pic = capture(views[view_role], i, min(1, sec / max(duration * 0.55, 0.1)))
        pic = pic.resize((612, 410), Image.Resampling.LANCZOS)
        image.paste(pic, (55, 183))
        x = 708
    else:
        # The trace contains no live words or pictures on this channel. A black return stays black.
        d.rectangle((55, 183, 667, 593), fill="#0a1316", outline="#46575b")
        x = 708
    if words:
        # Captions follow the unaltered aired string. Hold shorter segments on the projector.
        lines = wrap(d, words, FONT["body"], 510)
        groups = [lines[i : i + 3] for i in range(0, len(lines), 3)]
        idx = min(len(groups) - 1, int(max(0, sec - 0.4) / max(duration - 0.8, 0.1) * len(groups)))
        label = role_rows[mode]["actor"].upper()
        d.text((x, 218), label, font=FONT["h"], fill=AMBER)
        for j, line in enumerate(groups[idx]):
            d.text((x, 281 + j * 41), line, font=FONT["body"], fill=CREAM)
    else:
        explanation = {
            "silent_live_reporter_line": "The live line carries silence.",
            "silent_producer_mic": "The open microphone carries silence.",
            "empty_selected_return": "No contribution arrives on the selected line.",
            "station_ident": "The unattended slot runs the station ident.",
            "camera_take": f"The station plays the recorded pictures of {chosen['footage']}.",
            "filed_forecast": "The station plays the filed forecast reel.",
        }[channel]
        for j, line in enumerate(wrap(d, explanation, FONT["body"], 503)):
            d.text((x, 263 + j * 41), line, font=FONT["body"], fill=CREAM)
        if channel in ("camera_take", "filed_forecast"):
            d.text((x, 473), "Image shows the traced capture event.", font=FONT["small"], fill=GREEN)
    delivered = [role_rows[role]["actor"] for role in chosen["delivered_assignments"]]
    if delivered:
        d.text(
            (56, 599),
            "Assignments delivered by " + " and ".join(delivered) + ".",
            font=FONT["small"],
            fill=AMBER,
        )
    d.text(
        (56, 650), "SOURCE   " + "  ·  ".join(r["event_id"] for r in ref), font=FONT["micro"], fill=GREEN
    )
    return image


def render(path, out, stage, chrome):
    trace, final, end, rows, receipt = before_cut(path)
    chosen = receipt["bulletin"]
    out.mkdir(parents=True, exist_ok=True)
    shot_frames = [4 * FPS, 4 * FPS, 6 * FPS, 5 * FPS]
    start = sum(shot_frames) / FPS
    with tempfile.TemporaryDirectory(prefix="broadcast-edit-") as tmpname:
        tmp = Path(tmpname)
        spoken = chosen["spoken"]
        voice = np.empty(0, dtype=np.float32)
        if spoken.strip():
            r = chosen["source_role"]
            name = end[r]["actor"]
            voice = synth_line(name, spoken, {name: dict(zip(ROLE, VOICES))[r]}, tmp)
        air_frames = math.ceil(max(7, 0.8 + len(voice) / RATE) * FPS)
        total = sum(shot_frames) + air_frames
        audio = np.zeros(round(total / FPS * RATE), dtype=np.float32)
        if len(voice):
            pos = round((start + 0.4) * RATE)
            audio[pos : pos + len(voice)] = voice * 0.78
        # The control-room monitor sequence precedes a genuinely silent return when that is what aired.
        for elapsed in (0, 4, 8, 14):
            t = np.arange(round(0.07 * RATE)) / RATE
            n = round(elapsed * RATE)
            audio[n : n + len(t)] += 0.045 * np.sin(2 * np.pi * 530 * t) * np.hanning(len(t))
        if chosen["channel"] == "station_ident":
            for j, hz in enumerate((327, 436, 545)):
                t = np.arange(round(0.42 * RATE)) / RATE
                n = round((start + 0.26 + j * 0.37) * RATE)
                audio[n : n + len(t)] += 0.075 * np.sin(2 * np.pi * hz * t) * np.hanning(len(t))
        wav(tmp / "mix.wav", audio)
        video = tmp / "board.mp4"
        ff = [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{W}x{H}",
            "-r",
            str(FPS),
            "-i",
            "pipe:0",
            "-i",
            str(tmp / "mix.wav"),
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-b:a",
            "128k",
            "-t",
            str(total / FPS),
            "-movflags",
            "+faststart",
            "-y",
            str(video),
        ]
        with sync_playwright() as pw:
            b = pw.chromium.launch(
                headless=True, executable_path=chrome, args=["--disable-background-networking"]
            )
            views = {}
            for r in ROLE:
                q = b.new_page(viewport={"width": 612, "height": 410}, device_scale_factor=1)
                q.goto(stage.resolve().as_uri())
                q.evaluate("r=>TuesdayTown.loadTrace(r)", trace)
                q.evaluate("TuesdayTown.setCinematic(true,{captions:false})")
                q.evaluate('a=>TuesdayTown.setCamera({actor:a,framing:"close"})', r)
                views[r] = q
            enc = subprocess.Popen(ff, stdin=subprocess.PIPE)
            try:
                for j, (idx, e) in enumerate(final):
                    for fi in range(shot_frames[j]):
                        enc.stdin.write(
                            stage3(views, idx, e, min(1, fi / max(1, shot_frames[j] * 0.65))).tobytes()
                        )
                for fi in range(air_frames):
                    enc.stdin.write(
                        source_view(
                            views, trace["events"], receipt, rows, end, fi / FPS, air_frames / FPS
                        ).tobytes()
                    )
            finally:
                enc.stdin.close()
                code = enc.wait()
                b.close()
            if code:
                raise RuntimeError("film encoding failed")
        dest = out / "film.mp4"
        video.replace(dest)
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(dest), "-f", "null", "-"], check=True)
    receipt.update(
        {
            "duration_s": total / FPS,
            "frames": total,
            "fps": FPS,
            "on_air_from_s": start,
            "spoken_cue": {
                "actor": end[chosen["source_role"]]["actor"],
                "event_id": end[chosen["source_role"]]["id"],
                "text": spoken,
                "start_s": start + 0.4,
                "end_s": start + 0.4 + len(voice) / RATE,
            }
            if len(voice)
            else None,
            "control_room": "Three simultaneous camera views. Monitors and return images are staged renderings of recorded event geometry.",
            "video_sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
            "full_decode": True,
        }
    )
    write_json(out / "receipt.json", receipt)
    return receipt


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--stage", type=Path, default=Path("research/night/visual/index.html"))
    p.add_argument("--chrome", default="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    a = p.parse_args()
    r = render(a.trace, a.out, a.stage, a.chrome)
    print(r["bulletin"]["channel"], r["duration_s"])
