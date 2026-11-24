#!/usr/bin/env python3
"""Print a verified single-lineage town cut as an MP4, SRT, audio stems and timing EDL."""

import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

from edit import read_trace, verify, write_json

RATE = 24000
FONT_DIR = Path("/System/Library/Fonts/Supplemental")
VOICES = ("Eddy (English (US))", "Samantha", "Daniel (English (UK))")


def wav(path, samples):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes())


def synth_line(actor, text, voices, tmp):
    voice = voices[actor]
    cache = hashlib.sha256((voice + "\n" + text).encode()).hexdigest()[:20]
    path = tmp / (cache + ".aiff")
    if not path.exists():
        # Untrusted dialogue is sent through stdin as text, never shell-interpolated.
        subprocess.run(
            ["say", "-v", voice, "-r", "162", "-o", str(path)],
            input=text.encode(),
            check=True,
            timeout=30,
        )
    proc = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-i",
            str(path),
            "-f",
            "f32le",
            "-ac",
            "1",
            "-ar",
            str(RATE),
            "pipe:1",
        ],
        capture_output=True,
        check=True,
        timeout=30,
    )
    out = np.frombuffer(proc.stdout, dtype="<f4").copy()
    if not len(out) or np.max(np.abs(out)) < 0.002:
        raise RuntimeError(f"empty speech for {actor}")
    return out


def origin_note(line, event):
    rows = {r["actor"]: r for r in [event, *event.get("cast", [])]}
    speaker = rows.get(line["actor"])
    if speaker is None:
        return ""
    for listener, row in rows.items():
        direct = rf"^(?:(?:hey|morning|good morning|listen|sorry)[, ]+)?{re.escape(listener)}(?:[,.!?]|\s*—)"
        if row["origin"] != speaker["origin"] and re.match(direct, line["text"], re.I):
            place = row["origin"]
            where = "in Pittsburgh" if place == "Pittsburgh" else "at the " + place
            return f"{listener} is {where}"
    return ""


def audio_schedule(shots, events, fps, tmp, voiced):
    cast = list(dict.fromkeys(line["actor"] for s in shots for line in s["speech"]))
    role_voices = {"reporter": VOICES[0], "producer": VOICES[1], "camera": VOICES[2]}
    roles = {r["actor"]: r.get("role") for e in events for r in [e, *e.get("cast", [])]}
    voices = {
        name: role_voices.get(roles.get(name), VOICES[i % len(VOICES)])
        for i, name in enumerate(cast)
    }
    timing = []
    sentence_data = []
    frames = 0
    for shot in shots:
        start = frames / fps
        cursor = 0.42
        lines = []
        for line in shot["speech"]:
            samples = (
                synth_line(line["actor"], line["text"], voices, tmp) if voiced else None
            )
            length = (
                len(samples) / RATE
                if voiced
                else max(1.15, len(line["text"].split()) / 2.65)
            )
            lines.append(
                {
                    **line,
                    "origin_note": origin_note(line, events[shot["event_index"]]),
                    "start_s": round(start + cursor, 4),
                    "end_s": round(start + cursor + length, 4),
                }
            )
            if voiced:
                sentence_data.append((round((start + cursor) * RATE), samples))
            cursor += length + 0.24
        n = max(1, math.ceil(max(shot["seconds"], cursor + 0.38) * fps))
        timing.append({**shot, "speech": lines, "first_frame": frames, "frames": n})
        frames += n
    n = math.ceil(frames / fps * RATE)
    speech = np.zeros(n, dtype=np.float32)
    for start, samples in sentence_data:
        speech[start : start + len(samples)] += samples * 0.79
    return timing, speech, frames, voices


def foley(timing, events, fps, total):
    sound = np.zeros(total, dtype=np.float32)
    rng = np.random.default_rng(1701)

    def add(sec, part):
        start = round(sec * RATE)
        end = min(start + len(part), len(sound))
        if end > start:
            sound[start:end] += part[: end - start]

    def note(sec, freq, duration, amplitude):
        t = np.arange(round(duration * RATE)) / RATE
        env = (
            np.minimum(t / 0.009, 1)
            * np.exp(-t * 7.5)
            * np.minimum((duration - t) / 0.05, 1)
        )
        add(
            sec,
            amplitude
            * (np.sin(2 * np.pi * freq * t) + 0.18 * np.sin(4 * np.pi * freq * t))
            * env,
        )

    def pulse(sec, amplitude, duration, freq):
        t = np.arange(round(duration * RATE)) / RATE
        add(
            sec,
            (np.sin(2 * np.pi * freq * t) + 0.22 * rng.normal(size=len(t)))
            * amplitude
            * np.exp(-t / duration * 6),
        )

    for n, shot in enumerate(timing):
        slot = events[shot["event_index"]]
        e = next(
            (
                row
                for row in [slot, *slot.get("cast", [])]
                if row["actor"] == shot["focus"]
            ),
            slot,
        )
        sec = shot["first_frame"] / fps
        dur = shot["frames"] / fps
        morning = shot["view"] == "morning" or (
            e["clock"] == "6:00 am"
            and (not n or timing[n - 1]["event_index"] != shot["event_index"])
        )
        if morning:
            for delay, freq in ((0.09, 465), (0.31, 604), (0.53, 506)):
                note(sec + delay, freq, 0.38, 0.115)
            pulse(sec + 0.96, 0.085, 0.17, 53)
            pulse(sec + 1.20, 0.065, 0.15, 57)
        if (
            shot["view"] == "action"
            and e["decision"]["action"] == "take_coach_to_Pittsburgh"
        ):
            t = np.arange(round(dur * RATE)) / RATE
            env = np.minimum(1, t / 0.4) * np.minimum(1, (dur - t) / 0.5)
            phase = 2 * np.pi * (43 * t + 1.8 * t * t)
            add(sec, 0.052 * (np.sin(phase) + 0.4 * np.sin(phase * 2)) * env)
            note(sec + 0.60 * dur, 380, 0.18, 0.06)
        physical = e["decision"]["action"] if shot["view"] == "action" else ""
        if physical == "film_festival":
            pulse(sec + 0.16, 0.11, 0.028, 900)
            note(sec + 0.21, 858, 0.12, 0.055)
        if physical == "call_sister":
            for delay, lo, hi in (
                (0.05, 697, 1209),
                (0.17, 770, 1336),
                (0.29, 852, 1477),
            ):
                note(sec + delay, lo, 0.085, 0.048)
                note(sec + delay, hi, 0.085, 0.039)
        if physical == "leave_pencil_mark":
            for delay in (0.29, 0.47):
                grain = rng.normal(size=round(0.135 * RATE))
                grain = np.diff(grain, prepend=grain[0]) * np.hanning(len(grain))
                add(sec + delay, 0.014 * grain)
        if physical == "clear_tables":
            for delay, freq in ((0.20, 1140), (0.28, 1530), (0.39, 1190)):
                note(sec + delay, freq, 0.16, 0.058)
        if e["place"] == "diner" and physical == "look_around":
            note(sec + 0.55, 1378, 0.3, 0.055)
    return sound


def srt_time(sec):
    ms = round(sec * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def wrap(draw, text, font, width):
    lines = []
    for word in text.split():
        attempt = (lines[-1] + " " + word) if lines else word
        if lines and draw.textlength(attempt, font=font) <= width:
            lines[-1] = attempt
        else:
            lines.append(word)
    return lines


def caption_band(frame, shot, e, now, fonts):
    w, h = frame.size
    d = ImageDraw.Draw(frame)
    who, dialogue, small = fonts
    # The picture occupies the upper part; the bottom matte never hides a physical act or NPC.
    top = round(h * 0.789)
    d.rectangle((0, top, w, h), fill="#101e25")
    d.line(
        (round(w * 0.05), top + 1, round(w * 0.95), top + 1), fill="#385155", width=2
    )
    active = next((x for x in shot["speech"] if x["start_s"] <= now < x["end_s"]), None)
    x = round(w * 0.05)
    y = top + round(h * 0.026)
    if active:
        speaker = active["actor"].upper()
        if active.get("origin_note"):
            speaker += "   ·   " + active["origin_note"].upper()
        if shot.get("show_action_with_speech"):
            speaker += (
                "   ·   ON AIR" if shot.get("verified_air_sources") else "   ·   SPOKEN"
            )
            verb = "ACTION   ·   " + e["decision"]["action"].replace("_", " ").upper()
            right = w - x - d.textlength(verb, font=who)
            if right - x >= d.textlength(speaker, font=who) + 12:
                d.text((right, y), verb, font=who, fill="#a9c4b8")
        d.text((x, y), speaker, font=who, fill="#f1c06f")
        lines = wrap(d, active["text"], dialogue, w - 2 * x)
        if len(lines) > 3:
            # Narrow screens reveal the whole utterance as successive two-line captions.
            # Timing is proportional to word count. The complete verbatim cue remains in the SRT.
            groups = [lines[i : i + 2] for i in range(0, len(lines), 2)]
            weights = [sum(len(line.split()) for line in group) for group in groups]
            cursor = (
                (now - active["start_s"])
                / (active["end_s"] - active["start_s"])
                * sum(weights)
            )
            elapsed = 0
            for group, weight in zip(groups, weights):
                elapsed += weight
                if cursor < elapsed:
                    lines = group
                    break
        for j, line in enumerate(lines):
            d.text(
                (x, y + round(h * 0.042) + j * round(h * 0.046)),
                line,
                font=dialogue,
                fill="#f8f5e8",
            )
    else:
        action = e["effect"]
        if shot.get("montage_part"):
            action = action.partition(". ")[0].rstrip(".") + "."
        if len(action) > 90:
            action = e["decision"]["action"].replace("_", " ")
        context = (
            f"{e['clock']}   ·   {e['origin']}  →  {e['place']}"
            if e["origin"] != e["place"]
            else f"{e['clock']}   ·   {e['place']}"
        )
        if shot["view"] == "morning":
            context = f"{e['clock']}   ·   inn"
            action = "The reporter wakes in the hotel."
        d.text((x, y), context.upper(), font=who, fill="#94abae")
        fact_lines = wrap(d, action[:1].upper() + action[1:], dialogue, w - 2 * x)
        if len(fact_lines) > 3:
            fact_lines = wrap(
                d,
                e["decision"]["action"].replace("_", " ").capitalize(),
                dialogue,
                w - 2 * x,
            )
        for j, line in enumerate(fact_lines):
            d.text(
                (x, y + round(h * 0.045) + j * round(h * 0.042)),
                line,
                font=dialogue,
                fill="#e9ebe3",
            )
    ref = e.get("id", shot["event_id"])
    if shot.get("montage_part"):
        badge = (
            f"TRIP {shot['montage_index']} OF 5    /    {shot['montage_part'].upper()}"
        )
        d.text((x, h - round(h * 0.041)), badge, font=who, fill="#e7b674")
    length = d.textlength(ref, font=small)
    d.text((w - x - length, h - round(h * 0.033)), ref, font=small, fill="#879a99")


def frame_of(page, shot, e, progress, now, size, fonts):
    w, h = size
    page.evaluate(
        "([i,p]) => window.TuesdayTown.seek(i,p)", [shot["event_index"], progress]
    )
    # Capture the entire stage so HTML time-of-day and place overlays remain visible with the canvas.
    pic = Image.open(
        io.BytesIO(page.screenshot(type="jpeg", quality=89, animations="disabled"))
    ).convert("RGB")
    output = Image.new("RGB", (w, h), "#101e25")
    output.paste(pic, (0, 0))
    caption_band(output, shot, e, now, fonts)
    return output


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace", type=Path)
    p.add_argument("edl", type=Path)
    p.add_argument("visual", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--fps", type=int, default=16)
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--silent-voices", action="store_true")
    p.add_argument("--mute-all", action="store_true")
    p.add_argument(
        "--chrome",
        default="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    )
    args = p.parse_args()
    edl = json.loads(args.edl.read_text())
    checked = verify(args.trace, edl)
    trace, _ = read_trace(args.trace)
    events = trace["events"]
    if (
        args.width % 2
        or args.height % 2
        or args.width < 640
        or args.height < 360
        or not 4 <= args.fps <= 60
    ):
        p.error("choose an even frame size of at least 640x360, with 4–60 fps")
    args.out.mkdir(parents=True, exist_ok=True)
    voiced = not (args.silent_voices or args.mute_all)
    speechfont = max(16, round(args.height * 0.038))
    fonts = (
        ImageFont.truetype(
            str(FONT_DIR / "Arial Bold.ttf"), max(12, round(args.height * 0.022))
        ),
        ImageFont.truetype(str(FONT_DIR / "Georgia.ttf"), speechfont),
        ImageFont.truetype(
            str(FONT_DIR / "Courier New.ttf"), max(10, round(args.height * 0.016))
        ),
    )
    with tempfile.TemporaryDirectory(prefix="town-export-") as temp:
        tmp = Path(temp)
        timing, speech, count, voices = audio_schedule(
            edl["shots"], events, args.fps, tmp, voiced
        )
        bed = foley(timing, events, args.fps, len(speech))
        if args.mute_all:
            bed.fill(0)
        mix = speech + bed
        peak = np.max(np.abs(mix))
        gain = min(1.0, 0.90 / max(peak, 0.0001))
        for name, samples in (("dialogue", speech), ("places", bed), ("mix", mix)):
            wav(args.out / (name + ".wav"), samples * gain)
        with (args.out / "captions.srt").open("w") as f:
            seq = 1
            for s in timing:
                for line in s["speech"]:
                    f.write(
                        f"{seq}\n{srt_time(line['start_s'])} --> {srt_time(line['end_s'])}\n{line['actor']}: {line['text']}\n\n"
                    )
                    seq += 1
        stage_height = round(args.height * 0.79)
        dest = tmp / "cut.mp4"
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=args.chrome,
                headless=True,
                args=["--disable-background-networking"],
            )
            page = browser.new_page(
                viewport={"width": args.width, "height": stage_height},
                device_scale_factor=1,
            )
            page.route(re.compile(r"^https?://"), lambda route: route.abort())
            page.goto(args.visual.resolve().as_uri(), wait_until="load")
            page.wait_for_function(
                "window.TuesdayTown && typeof window.TuesdayTown.seek==='function'",
                timeout=12000,
            )
            page.evaluate("t=>window.TuesdayTown.loadTrace(t)", trace)
            page.evaluate("window.TuesdayTown.setCinematic(true,{captions:false})")
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
                f"{args.width}x{args.height}",
                "-r",
                str(args.fps),
                "-i",
                "pipe:0",
                "-i",
                str(args.out / "mix.wav"),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "19",
                "-pix_fmt",
                "yuv420p",
                "-af",
                "loudnorm=I=-16:TP=-1.5:LRA=9",
                "-ar",
                "48000",
                "-c:a",
                "aac",
                "-b:a",
                "144k",
                "-t",
                f"{count / args.fps:.8f}",
                "-movflags",
                "+faststart",
                "-y",
                str(dest),
            ]
            encoder = subprocess.Popen(ff, stdin=subprocess.PIPE)
            try:
                for s in timing:
                    slot = events[s["event_index"]]
                    e = next(
                        (
                            row
                            for row in [slot, *slot.get("cast", [])]
                            if row["actor"] == s["focus"]
                        ),
                        slot,
                    )
                    page.evaluate(
                        "camera=>window.TuesdayTown.setCamera?.(camera)",
                        {
                            "actor": e.get("role", e["actor"]),
                            "framing": s.get("framing", "street"),
                            "scale": s.get("scale", 1),
                        },
                    )
                    for idx in range(s["frames"]):
                        # Hold the result during speech. The transition shows the beginning, middle and end of actual travel.
                        frac = min(1.0, idx / max(1, s["frames"] * 0.68 - 1))
                        progress = s["start"] + (s["end"] - s["start"]) * frac
                        now = (s["first_frame"] + idx) / args.fps
                        im = frame_of(
                            page, s, e, progress, now, (args.width, args.height), fonts
                        )
                        encoder.stdin.write(im.tobytes())
                    print(s["event_id"], s["view"], s["frames"], flush=True)
            finally:
                encoder.stdin.close()
                rc = encoder.wait()
                browser.close()
            if rc:
                raise RuntimeError("video encoder failed")
        os.replace(dest, args.out / "film.mp4")
        write_json(
            args.out / "timing.json",
            {
                "source_sha256": checked["source_sha256"],
                "fps": args.fps,
                "frames": count,
                "seconds": count / args.fps,
                "size": [args.width, args.height],
                "voices": voices if voiced else {},
                "stem_peak": float(peak * gain),
                "master_target_lufs": -16,
                "shots": timing,
            },
        )
        print(f"{count} frames, {count / args.fps:.2f}s, {args.out / 'film.mp4'}")


if __name__ == "__main__":
    main()
