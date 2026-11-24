#!/usr/bin/env python3
"""Time the offline browser-to-H.264 pipeline at two projector sizes on one fixed physical life."""

import argparse
import collections
import json
from pathlib import Path
import platform
import random
import statistics
import subprocess
import tempfile
import time

from PIL import ImageFont
from playwright.sync_api import sync_playwright
from edit import read_trace, write_json
from render_cut import FONT_DIR, frame_of


def measure(trace, stage, out, chrome):
    take, digest = read_trace(trace)
    edl = json.loads(Path(__file__).with_name("wednesday-couch-edl.json").read_text())
    assert digest == edl["source_sha256"]
    cues = [s for s in edl["shots"] if s["event_index"] in (1, 6, 7, 21)]
    assert len(cues) == 4
    measurements = collections.defaultdict(list)
    per_type = collections.defaultdict(list)
    rng = random.Random(9711)
    with tempfile.TemporaryDirectory(prefix="film-profiling-") as temp, sync_playwright() as api:
        browser = api.chromium.launch(
            headless=True, executable_path=chrome, args=["--disable-background-networking"]
        )
        for width, height in ((1280, 720), (1920, 1080), (1920, 1080), (1280, 720)):
            key = f"{width}x{height}"
            page = browser.new_page(
                viewport={"width": width, "height": round(height * 0.79)}, device_scale_factor=1
            )
            page.goto(stage.resolve().as_uri())
            page.evaluate("t=>TuesdayTown.loadTrace(t)", take)
            page.evaluate("TuesdayTown.setCinematic(true,{captions:false})")
            fonts = [
                ImageFont.truetype(str(FONT_DIR / n), round(height * f))
                for n, f in [("Arial Bold.ttf", 0.022), ("Georgia.ttf", 0.038), ("Courier New.ttf", 0.016)]
            ]
            dest = Path(temp) / "sample.mp4"
            encoder = subprocess.Popen(
                [
                    "ffmpeg",
                    "-nostdin",
                    "-v",
                    "error",
                    "-f",
                    "rawvideo",
                    "-pix_fmt",
                    "rgb24",
                    "-s",
                    f"{width}x{height}",
                    "-r",
                    "24",
                    "-i",
                    "pipe:0",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "19",
                    "-pix_fmt",
                    "yuv420p",
                    "-y",
                    str(dest),
                ],
                stdin=subprocess.PIPE,
            )
            try:
                rng.shuffle(cues)
                for cue in cues:
                    e = take["events"][cue["event_index"]]
                    actor = next(r for r in [e, *e["cast"]] if r["actor"] == cue["focus"])
                    page.evaluate(
                        "x=>TuesdayTown.setCamera(x)",
                        {"actor": actor["role"], "framing": cue.get("framing", "street")},
                    )
                    shot = {**cue, "speech": []}
                    for j in range(11):
                        started = time.perf_counter()
                        frame = frame_of(page, shot, actor, j / 10, 0, (width, height), fonts)
                        encoder.stdin.write(frame.tobytes())
                        elapsed = time.perf_counter() - started
                        if j:
                            measurements[key].append(elapsed)
                            per_type[(key, actor["decision"]["action"])].append(elapsed)
            finally:
                encoder.stdin.close()
                rc = encoder.wait()
                page.close()
            assert rc == 0
        browser.close()
    rows = {}
    for key, t in measurements.items():
        q = statistics.quantiles(t, n=100, method="inclusive")
        mean = statistics.mean(t)
        rows[key] = {
            "timed_frames": len(t),
            "median_ms": round(statistics.median(t) * 1000, 2),
            "p95_ms": round(q[94] * 1000, 2),
            "mean_ms": round(mean * 1000, 2),
            "implied_seconds_for_90s_at_24fps": round(mean * 2160, 1),
            "mean_by_action_ms": {
                act: round(statistics.mean(vals) * 1000, 2)
                for (k, act), vals in per_type.items()
                if k == key
            },
        }
    try:
        model = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
    except Exception:
        model = platform.machine()
    write_json(
        out,
        {
            "source_sha256": digest,
            "hardware": model,
            "os": platform.platform(),
            "method": "Headless Chrome seek, JPEG snapshot, Pillow caption, RGB conversion and local x264 pipe. Four actual scenes, 10 timed frames per scene, two rounds per resolution in ABBA order. First frame per scene, TTS, startup, final encoder flush and disk transfer excluded. Other rehearsal jobs may be active. Extrapolations apply only to this mix.",
            "results": rows,
        },
    )
    print(rows)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace", type=Path)
    p.add_argument("stage", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--chrome", default="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    measure(**vars(p.parse_args()))
