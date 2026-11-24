#!/usr/bin/env python3
"""Verify a cut against its source and extract actual encoded frames for visual review."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import wave
from PIL import Image, ImageDraw
from edit import verify, write_json
from render_cut import srt_time


def output(command):
    proc = subprocess.run(command, capture_output=True, check=True)
    return proc.stdout


def inspect(trace, edl_path, folder):
    video = folder / "film.mp4"
    edl = json.loads(edl_path.read_text())
    valid = verify(trace, edl)
    recorded = json.loads((folder / "timing.json").read_text())
    result = json.loads(
        output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=codec_name,codec_type,width,height,nb_frames,sample_rate:format=duration,size",
                "-of",
                "json",
                str(video),
            ]
        )
    )
    streams = {s["codec_type"]: s for s in result["streams"]}
    assert streams["video"]["codec_name"] == "h264" and streams["audio"]["codec_name"] == "aac"
    assert int(streams["video"]["nb_frames"]) == recorded["frames"]
    assert [streams["video"][field] for field in ("width", "height")] == recorded["size"]
    assert abs(float(result["format"]["duration"]) - recorded["seconds"]) <= 1 / recorded["fps"]
    assert valid["source_sha256"] == recorded["source_sha256"]
    assert len(edl["shots"]) == len(recorded["shots"])
    track_quality = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-v",
            "info",
            "-i",
            str(video),
            "-af",
            "ebur128=peak=true",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        check=True,
    ).stderr.decode()
    summary = track_quality.rsplit("Summary:", 1)[-1]
    integrated = float(re.search(r"I:\s*([-\d.]+) LUFS", summary).group(1))
    peak = float(re.search(r"Peak:\s*([-\d.]+) dBFS", summary).group(1))
    assert -35 < integrated < -7 and peak < 0
    total = 0
    expected = []
    for a, b in zip(edl["shots"], recorded["shots"]):
        assert [a[k] for k in ("event_index", "view", "focus")] == [
            b[k] for k in ("event_index", "view", "focus")
        ]
        assert b["first_frame"] == total
        assert [(x["actor"], x["text"]) for x in a["speech"]] == [
            (x["actor"], x["text"]) for x in b["speech"]
        ]
        total += b["frames"]
        for line in b["speech"]:
            assert (
                b["first_frame"] / recorded["fps"]
                <= line["start_s"]
                < line["end_s"]
                <= total / recorded["fps"]
            )
            expected.append(
                f"{len(expected) + 1}\n{srt_time(line['start_s'])} --> {srt_time(line['end_s'])}\n{line['actor']}: {line['text']}"
            )
    assert total == recorded["frames"]
    assert (folder / "captions.srt").read_text().strip() == "\n\n".join(expected)
    for stem in ("dialogue", "places", "mix"):
        with wave.open(str(folder / (stem + ".wav"))) as w:
            assert abs(w.getnframes() / w.getframerate() - recorded["seconds"]) < 0.001
    # Include a frame from every shot, so the submitted video can be checked visually without the renderer.
    shots = recorded["shots"]
    col = 4
    width = 300
    row_h = 186
    sheet = Image.new("RGB", (col * width, ((len(shots) + col - 1) // col) * row_h), "#112027")
    ink = ImageDraw.Draw(sheet)
    for j, shot in enumerate(shots):
        pos = (shot["first_frame"] + (shot["frames"] - 1) * 0.65) / recorded["fps"]
        data = output(
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-ss",
                f"{pos:.4f}",
                "-i",
                str(video),
                "-frames:v",
                "1",
                "-f",
                "image2pipe",
                "-c:v",
                "mjpeg",
                "-",
            ]
        )
        frame = Image.open(io.BytesIO(data)).convert("RGB")
        frame.thumbnail((width - 3, 167))
        x = j % col * width
        y = j // col * row_h
        sheet.paste(frame, (x, y))
        ink.text((x + 3, y + 168), f"{pos:05.1f}s   {shot['focus']}    {shot['event_id']}", fill="#fff1cb")
    sheet.save(folder / "contact-sheet.jpg", quality=90)
    report = {
        "source_sha256": valid["source_sha256"],
        "mp4_sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
        "edl_sha256": hashlib.sha256(edl_path.read_bytes()).hexdigest(),
        "probe": result,
        "shots": len(shots),
        "caption_cues": len(expected),
        "frames": total,
        "three_stems_match": True,
        "source_and_captions_verified": True,
        "full_decode": True,
        "integrated_lufs": integrated,
        "true_peak_dbfs": peak,
        "voices": recorded["voices"],
    }
    write_json(folder / "qa.json", report)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("trace", "edl", "folder"):
        p.add_argument(arg, type=Path)
    a = p.parse_args()
    print(json.dumps(inspect(a.trace, a.edl, a.folder), indent=2))
