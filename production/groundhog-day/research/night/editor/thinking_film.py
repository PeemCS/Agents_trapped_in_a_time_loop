#!/usr/bin/env python3
"""Project one external model's emitted note, followed by its exact committed speech and physical action."""

import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright
from edit import read_trace, make_edl, verify, write_json
from render_cut import srt_time, FONT_DIR, wrap

ED = Path(__file__).resolve().parent
W, H, FPS = 1280, 720, 24


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def locate(trace_dir, slot, actor, quote):
    rows = {r["actor"]: r for r in [slot, *slot["cast"]]}
    row = rows[actor]
    inference = row["inference"]
    accepted = [
        a
        for a in inference["attempts"]
        if a["error"] is None and a.get("public_thinking")
    ]
    if not accepted:
        raise ValueError("no accepted emitted note on this decision")
    if inference["cache_hit"]:
        raise ValueError("selected note is a reused generation")
    a = accepted[-1]
    raw = (trace_dir / a["stream_path"]).resolve()
    raw.relative_to(trace_dir.resolve())
    actual = checksum(raw)
    assert actual == a["stream_sha256"]
    lines = [json.loads(line) for line in raw.read_text().splitlines()]
    request = lines[0]
    assert (
        request["role"] == row["role"]
        and request["day"] == row["day"]
        and request["tick"] == int(row["id"].split("-")[1][1:])
    )
    chunks = [line for line in lines if line["kind"] == "chunk"]
    pieces = [c["provider"].get("message", {}) for c in chunks]
    thinking = "".join(m.get("thinking", "") for m in pieces)
    response = "".join(m.get("content", "") for m in pieces)
    assert (
        thinking == a["public_thinking"]
        and response == a["response"]
        and json.loads(response) == row["decision"]
    )
    assert chunks[-1]["provider"]["done"] is True
    if thinking.count(quote) != 1 or "\n" in quote or len(quote.split()) > 45:
        raise ValueError(
            "select one unambiguous contiguous provider excerpt of at most 45 words"
        )
    offset = thinking.index(quote)
    last = offset + len(quote)
    p = 0
    covered = []
    for chunk, m in zip(chunks, pieces):
        text = m.get("thinking", "")
        stop = p + len(text)
        if max(p, offset) < min(stop, last):
            covered.append(chunk["seq"])
        p = stop
    first_content = next(c["seq"] for c, m in zip(chunks, pieces) if m.get("content"))
    assert covered and covered[-1] <= first_content
    return {
        "actor": actor,
        "role": row["role"],
        "event_id": row["id"],
        "quote": quote,
        "channel": "Ollama message.thinking, external model output; unspoken",
        "codepoint_start": offset,
        "codepoint_end": last,
        "stream_path": a["stream_path"],
        "stream_sha256": actual,
        "request_id": inference["request_id"],
        "provider_chunk_first": covered[0],
        "provider_chunk_last": covered[-1],
        "provider_first_final_chunk": first_content,
        "provider_receipt_elapsed_s": {
            "excerpt_start": next(
                c["elapsed_s"] for c in chunks if c["seq"] == covered[0]
            ),
            "excerpt_end": next(
                c["elapsed_s"] for c in chunks if c["seq"] == covered[-1]
            ),
            "first_final": next(
                c["elapsed_s"] for c in chunks if c["seq"] == first_content
            ),
        },
        "formatted_retry": bool(request.get("repair")),
        "recorded_attempt_count": len(inference["attempts"]),
        "provider_usage": a.get("usage", {}),
        "provider_done_reason": chunks[-1]["provider"].get("done_reason"),
        "full_thinking_chars": len(thinking),
        "selected_attempt_is_cache_hit": False,
        "validated_entire_thinking_and_final_object": True,
    }


def prepare(trace, plan, out):
    world, digest = read_trace(trace)
    events = world["events"]
    edl = make_edl(trace, "chronicle")
    edl.update(
        selection="observed-model-notes",
        purpose="One complete thinking-enabled model performance. All separately displayed notes come from the accepted provider stream.",
        cluster=plan.get("cluster"),
        title=plan["title"],
    )
    shots = []
    notes = []
    for n, p in enumerate(plan["shots"]):
        i = p["index"]
        e = events[i]
        actor = p.get("actor", e["actor"])
        r = next(r for r in [e, *e["cast"]] if r["actor"] == actor)
        morning = p.get("view") == "morning"
        spoken = r["decision"]["words"] if p.get("speak", True) and not morning else ""
        bulletin = e["world_after"].get("bulletin") or {}
        aired = bool(
            spoken
            and e["clock"] == "7:00 pm"
            and bulletin.get("source_role") == r["role"]
            and bulletin.get("spoken") == spoken
        )
        quote = p.get("quote")
        if quote:
            assert not morning
            wake = next(x for x in events if x["day"] == e["day"])
            calendar = next(
                w for w in wake["observed"] if "Tuesday, February 2, 2016." in w
            )
            notes.append(
                {
                    "before_shot": n,
                    "slot_index": i,
                    "witnessed_calendar": calendar,
                    "wake_id": wake["id"],
                    **locate(trace.parent, e, actor, quote),
                }
            )
        start = (
            0.22 if morning else 0.25 if i and events[i - 1]["day"] != e["day"] else 0
        )
        shots.append(
            {
                "event_index": i,
                "event_id": e["id"],
                "focus": actor,
                "view": "morning" if morning else "action",
                "framing": p.get("framing", "close"),
                "start": start,
                "end": 0.22 if morning else 1,
                "seconds": p.get("seconds", 4),
                "show_action_with_speech": True,
                **({"verified_air_sources": bulletin["source_ids"]} if aired else {}),
                "speech": [{"actor": actor, "text": spoken}] if spoken else [],
            }
        )
    edl["shots"] = shots
    verify(trace, edl)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "edit.json", edl)
    write_json(
        out / "notes.json",
        {
            "source_sha256": digest,
            "source_path": str(trace),
            "take": trace.parent.name,
            "notes": notes,
            "title": plan["title"],
        },
    )
    return edl, notes


def overlay(path, pic, note, slot, title, first):
    # A still of the actual pre-action location accompanies the unvoiced trace text.
    bg = Image.new("RGB", (W, H), "#112529")
    d = ImageDraw.Draw(bg)
    pre = pic.convert("RGB")
    pre.thumbnail((560, 480), Image.Resampling.LANCZOS)
    xx = 724
    yy = (H - pre.height) // 2
    bg.paste(pre, (xx, yy))
    d = ImageDraw.Draw(bg)

    def f(name, size):
        return ImageFont.truetype(str(FONT_DIR / name), size)

    d.rectangle((56, 55, 140, 60), fill="#e3ba78")
    d.text(
        (56, 87),
        note["actor"].upper() + "  /  UNSPOKEN MODEL NOTE",
        font=f("Arial Bold.ttf", 24),
        fill="#e9bd77",
    )
    body = f("Georgia.ttf", 39)
    lines = wrap(d, note["quote"], body, 630)
    if len(lines) > 7:
        body = f("Georgia.ttf", 34)
        lines = wrap(d, note["quote"], body, 630)
    y = max(169, 345 - len(lines) * 26)
    for j, s in enumerate(lines):
        d.text((56, y + j * (body.size + 12)), s, font=body, fill="#fff2d5")
    d.text(
        (56, 590),
        f"WORLD CLOCK    ·    TUE, FEB 2    ·    {slot['clock'].upper()}",
        font=f("Arial Bold.ttf", 19),
        fill="#a7bcad",
    )
    d.text(
        (56, 641),
        "Ollama thinking  /  " + note["event_id"],
        font=f("Courier New.ttf", 16),
        fill="#b8c9c0",
    )
    d.text(
        (xx, yy + pre.height + 18),
        "Before the action",
        font=f("Arial.ttf", 18),
        fill="#b8c9c0",
    )
    bg.save(path)


def source_note_frame(page, which, slot, role):
    p = 0.22 if which and slot["clock"] == "6:00 am" else 0
    page.evaluate('r=>TuesdayTown.setCamera({actor:r,framing:"close"})', role)
    page.evaluate("([i,p])=>TuesdayTown.seek(i,p)", [which, p])
    return Image.open(io.BytesIO(page.screenshot(type="jpeg", quality=94))).convert(
        "RGB"
    )


def compose(trace, out, stage, chrome):
    world, digest = read_trace(trace)
    edl = json.loads((out / "edit.json").read_text())
    verify(trace, edl)
    references = json.loads((out / "notes.json").read_text())
    assert references["source_sha256"] == digest
    verified = json.loads((out / "performance" / "qa.json").read_text())
    performance = out / "performance" / "film.mp4"
    assert (
        checksum(performance) == verified["mp4_sha256"]
        and verified["source_sha256"] == digest
    )
    timing = json.loads((out / "performance" / "timing.json").read_text())
    n_by_slot = {n["before_shot"]: n for n in references["notes"]}
    segments = []
    cues = []
    clock = 0
    with (
        tempfile.TemporaryDirectory(prefix="thinking-film-") as tmpname,
        sync_playwright() as pw,
    ):
        tmp = Path(tmpname)
        browser = pw.chromium.launch(
            headless=True,
            executable_path=chrome,
            args=["--disable-background-networking"],
        )
        page = browser.new_page(
            viewport={"width": 760, "height": 540}, device_scale_factor=1
        )
        page.goto(stage.resolve().as_uri())
        page.evaluate("x=>TuesdayTown.loadTrace(x)", world)
        page.evaluate("TuesdayTown.setCinematic(true,{captions:false})")
        for i, s in enumerate(timing["shots"]):
            slot = world["events"][s["event_index"]]
            actor = next(r for r in [slot, *slot["cast"]] if r["actor"] == s["focus"])
            n = n_by_slot.get(i)
            if n:
                assert (
                    locate(trace.parent, slot, n["actor"], n["quote"])["stream_sha256"]
                    == n["stream_sha256"]
                )
                picture = source_note_frame(page, s["event_index"], slot, actor["role"])
                img = tmp / f"note-{i}.png"
                overlay(img, picture, n, slot, references["title"], i == 0)
                dur = (
                    math.ceil(
                        max(3.8, min(10.5, 1.4 + len(n["quote"].split()) / 2.65)) * FPS
                    )
                    / FPS
                )
                segments.append(
                    {
                        "kind": "unspoken model note",
                        "input": str(img),
                        "start": 0,
                        "duration": dur,
                        "event_id": n["event_id"],
                        "quote": n["quote"],
                        "absolute_start_s": clock,
                    }
                )
                cues.append(
                    {
                        "type": "unspoken model note",
                        "actor": n["actor"],
                        "text": n["quote"],
                        "event_id": n["event_id"],
                        "start_s": clock,
                        "end_s": clock + dur,
                    }
                )
                clock += dur
            start = s["first_frame"] / timing["fps"]
            dur = s["frames"] / timing["fps"]
            waking = s["view"] == "morning"
            segments.append(
                {
                    "kind": "witnessed hotel wake" if waking else "committed action",
                    "input": str(performance),
                    "start": start,
                    "duration": dur,
                    "event_id": actor["id"],
                    "action": None if waking else actor["decision"]["action"],
                    "effect": slot["observed"][0] if waking else actor["effect"],
                    "origin": actor["origin"],
                    "place": actor["origin"] if waking else actor["place"],
                    "view": s["view"],
                    "absolute_start_s": clock,
                }
            )
            for c in s["speech"]:
                cues.append(
                    {
                        "type": "spoken",
                        "actor": c["actor"],
                        "text": c["text"],
                        "event_id": actor["id"],
                        "start_s": clock + c["start_s"] - start,
                        "end_s": clock + c["end_s"] - start,
                    }
                )
            clock += dur
        browser.close()
        assert 45 <= clock <= 100, f"cut is {clock:.2f}s"
        # Each segment is independently trimmed to the nearest 24-fps frame before concat.
        normalized = []
        for j, s in enumerate(segments):
            path = tmp / f"part-{j}.mp4"
            d = s["duration"]
            if s["kind"] == "unspoken model note":
                inputs = [
                    "-loop",
                    "1",
                    "-framerate",
                    str(FPS),
                    "-i",
                    s["input"],
                    "-f",
                    "lavfi",
                    "-i",
                    "anullsrc=r=48000:cl=mono",
                ]
                audio = "1:a:0"
            else:
                inputs = ["-ss", str(s["start"]), "-i", s["input"]]
                audio = "0:a:0"
            subprocess.run(
                [
                    "ffmpeg",
                    "-nostdin",
                    "-v",
                    "error",
                    "-y",
                    *inputs,
                    "-map",
                    "0:v:0",
                    "-map",
                    audio,
                    "-t",
                    str(d),
                    "-r",
                    str(FPS),
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
                    "-ac",
                    "1",
                    "-b:a",
                    "144k",
                    str(path),
                ],
                check=True,
            )
            normalized.append(path)
        inputs = []
        filters = []
        labels = []
        for j, (p, s) in enumerate(zip(normalized, segments)):
            dur = s["duration"]
            inputs += ["-i", str(p)]
            filters += [
                f"[{j}:v]trim=duration={dur},setpts=PTS-STARTPTS[v{j}]",
                f"[{j}:a]atrim=duration={dur},asetpts=PTS-STARTPTS[a{j}]",
            ]
            labels.extend([f"[v{j}]", f"[a{j}]"])
        filters.append("".join(labels) + f"concat=n={len(segments)}:v=1:a=1[v][a]")
        master = tmp / "film.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-y",
                *inputs,
                "-filter_complex",
                ";".join(filters),
                "-map",
                "[v]",
                "-map",
                "[a]",
                "-c:v",
                "libx264",
                "-crf",
                "18",
                "-preset",
                "veryfast",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                "-b:a",
                "144k",
                "-t",
                str(clock),
                "-movflags",
                "+faststart",
                str(master),
            ],
            check=True,
        )
        master.replace(out / "film.mp4")

    def subtitles(items):
        return (
            "\n\n".join(
                f"{j}\n{srt_time(c['start_s'])} --> {srt_time(c['end_s'])}\n{c['actor']}{' [unspoken model note]' if c['type'] != 'spoken' else ''}: {c['text']}"
                for j, c in enumerate(items, 1)
            )
            + "\n"
        )

    (out / "captions.srt").write_text(subtitles(cues))
    (out / "spoken-only.srt").write_text(
        subtitles([c for c in cues if c["type"] == "spoken"])
    )
    write_json(out / "cues.json", cues)
    for s in segments:
        s.pop("input")
    video = out / "film.mp4"
    probe = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=codec_name,codec_type,width,height,nb_frames:format=duration,size",
                "-of",
                "json",
                str(video),
            ]
        )
    )
    assert abs(float(probe["format"]["duration"]) - clock) < 0.15
    subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(video), "-f", "null", "-"],
        check=True,
    )
    decoded = np.frombuffer(
        subprocess.check_output(
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-i",
                str(video),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "48000",
                "-f",
                "f32le",
                "-",
            ]
        ),
        dtype="<f4",
    )
    sound = []
    for cue in cues:
        start = round((cue["start_s"] + 0.10) * 48000)
        stop = round((cue["end_s"] - 0.10) * 48000)
        audio = decoded[start:stop]
        peak = float(np.max(np.abs(audio)))
        rms = float(np.sqrt(np.mean(audio**2)))
        if cue["type"] == "unspoken model note":
            assert peak < 0.0002, (cue["event_id"], peak)
        else:
            assert peak > 0.002, (cue["event_id"], peak)
        sound.append(
            {
                "event_id": cue["event_id"],
                "type": cue["type"],
                "peak": round(peak, 7),
                "rms": round(rms, 7),
            }
        )
    report = {
        "decoded_audio_cue_checks": sound,
        "title": references["title"],
        "take": references["take"],
        "source_path": str(trace),
        "source_sha256": digest,
        "validation": "External notes match the accepted Ollama streamed message.thinking bytes as Unicode text. Every committed decision equals that same stream’s decoded final object. Notes use a silent track and precede their own event. Whole spoken lines belong to the actor and same slot.",
        "segments": segments,
        "note_count": len(n_by_slot),
        "spoken_count": sum(c["type"] == "spoken" for c in cues),
        "full_decode": True,
        "probe": probe,
        "edl_sha256": checksum(out / "edit.json"),
        "note_evidence_sha256": checksum(out / "notes.json"),
        "subtitle_sha256": checksum(out / "captions.srt"),
        "spoken_subtitle_sha256": checksum(out / "spoken-only.srt"),
        "base_performance_sha256": verified["mp4_sha256"],
        "mp4_sha256": checksum(video),
    }
    write_json(out / "verification.json", report)
    print(report["take"], clock, video)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    cmd = p.add_subparsers(dest="command", required=True)
    a = cmd.add_parser("prepare")
    a.add_argument("trace", type=Path)
    a.add_argument("plan", type=Path)
    a.add_argument("out", type=Path)
    a = cmd.add_parser("compose")
    a.add_argument("trace", type=Path)
    a.add_argument("out", type=Path)
    a.add_argument("--stage", type=Path, default=ED.parent / "visual" / "index.html")
    a.add_argument(
        "--chrome",
        default="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    )
    a = p.parse_args()
    if a.command == "prepare":
        prepare(a.trace, json.loads(a.plan.read_text()), a.out)
    else:
        compose(a.trace, a.out, a.stage, a.chrome)
