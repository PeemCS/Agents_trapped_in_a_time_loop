#!/usr/bin/env python3
"""Compare the first held-out feature and earliest different final channel, after all four roots finish."""

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from PIL import Image, ImageDraw
from build_demo import card, font, ff
from bulletin import before_cut
from edit import write_json
from render_cut import srt_time

ED = Path(__file__).resolve().parent
ROOTS = ED.parent / "takes" / "heldout" / "v2"
DISPLAY = {
    "producer_live": "Rita’s microphone",
    "live_report": "Phil’s live return",
    "camera_take": "Larry’s recorded take",
    "filed_forecast": "The filed forecast",
    "station_ident": "The station ident",
    "empty_selected_return": "An empty return",
    "silent_producer_mic": "A silent microphone",
    "silent_live_reporter_line": "A silent live line",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare():
    stages = {}
    for seed in (711, 712, 713, 714):
        _, _, _, _, r = before_cut(ROOTS / f"seed-{seed}.json")
        stages[seed] = r
    source = stages[711]
    ch = source["bulletin"]["channel"]
    other = next((seed for seed in (712, 713, 714) if stages[seed]["bulletin"]["channel"] != ch), None)
    if other is None:
        raise ValueError("All four final bulletins are equal; keep 711 alone per frozen rule.")
    alt = stages[other]
    feature = ED / "seven-oclock"
    board = ED / f"bulletin-{other}-final"
    a = json.loads((feature / "feature.json").read_text())
    b = json.loads((board / "receipt.json").read_text())
    assert a["source_sha256"] == source["source_sha256"] and b["source_sha256"] == alt["source_sha256"]
    assert (
        digest(feature / "film.mp4") == a["mp4_sha256"] and digest(board / "film.mp4") == b["video_sha256"]
    )
    bruin = json.loads((ED / "heldout-v2-bruin.json").read_text())
    assert set(bruin["input_hashes"]) == {r["source_sha256"] for r in stages.values()}
    assert "4 succeeded" in bruin["run_log"] and "7 succeeded" in bruin["run_log"]
    out = ED / "four-bulletins"
    out.mkdir(exist_ok=True)
    video = out / "film.mp4"
    t1 = float(a["probe"]["format"]["duration"])
    t2 = b["duration_s"]
    duration = 3 + t1 + 3.5 + t2 + 8.5
    assert 60 < duration < 180
    with tempfile.TemporaryDirectory(prefix="paired-airtime-") as tmpname:
        tmp = Path(tmpname)
        card(
            tmp / "a.png",
            "The seven o’clock bulletin",
            "One coach ticket, one camera take, one channel on air.",
            "A private rehearsal with three independently deciding agents.",
        )
        card(
            tmp / "b.png",
            "The other broadcast",
            "Same cast, same six mornings, same station.",
            "A new sampling seed. Watch what the producer sends to air.",
        )
        im = Image.new("RGB", (1280, 720), "#14282c")
        d = ImageDraw.Draw(im)
        d.text((62, 39), "What reached the audience?", font=font("Georgia.ttf", 56), fill="#fff5da")
        d.text(
            (66, 128),
            "EVERY FINAL EVENING FROM THE FOUR HELD-OUT RUNS",
            font=font("Arial Bold.ttf", 20),
            fill="#e6b46d",
        )
        for i, (seed, r) in enumerate(stages.items()):
            y = 210 + i * 69
            channel = r["bulletin"]["channel"]
            d.text((66, y), f"Take {seed}", font=font("Arial.ttf", 28), fill="#bccabc")
            d.text((285, y), DISPLAY[channel], font=font("Georgia.ttf", 32), fill="#fff5da")
            active = r["bulletin"]["source_ids"]
            d.text(
                (756, y + 6),
                f"{len(active)} verified source event" + ("s" if len(active) > 1 else ""),
                font=font("Arial.ttf", 22),
                fill="#d2dfd2",
            )
        d.line((65, 535, 1213, 535), fill="#60716a")
        d.text(
            (65, 565),
            f"Bruin linked {bruin['verified_air_source_count']} source decisions to 24 actual evening programs.",
            font=font("Arial.ttf", 26),
            fill="#fff5da",
        )
        d.text(
            (66, 618),
            "Four pipeline assets and seven quality checks passed.",
            font=font("Arial.ttf", 20),
            fill="#b1c3b7",
        )
        im.save(tmp / "c.png")
        parts = [
            ("opener", tmp / "a.png", 3),
            ("711", feature / "film.mp4", t1),
            ("fork", tmp / "b.png", 3.5),
            (str(other), board / "film.mp4", t2),
            ("evidence", tmp / "c.png", 8.5),
        ]
        inputs = []
        filters = []
        labels = []
        next_input = 0
        for n, (label, p, length) in enumerate(parts):
            if p.suffix == ".png":
                inputs += [
                    "-loop",
                    "1",
                    "-framerate",
                    "24",
                    "-t",
                    str(length),
                    "-i",
                    str(p),
                    "-f",
                    "lavfi",
                    "-t",
                    str(length),
                    "-i",
                    "anullsrc=r=48000:cl=mono",
                ]
                v = next_input
                au = next_input + 1
                next_input += 2
            else:
                inputs += ["-i", str(p)]
                v = au = next_input
                next_input += 1
            filters += [
                f"[{v}:v]fps=24,format=yuv420p,setsar=1,trim=duration={length},setpts=PTS-STARTPTS[v{n}]",
                f"[{au}:a]aresample=48000,atrim=duration={length},asetpts=PTS-STARTPTS[a{n}]",
            ]
            labels.extend((f"[v{n}]", f"[a{n}]"))
        filters.append("".join(labels) + f"concat=n={len(parts)}:v=1:a=1[v][a]")
        target = tmp / "video.mp4"
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
                "144k",
                "-t",
                str(duration),
                "-movflags",
                "+faststart",
                str(target),
            ]
        )
        target.replace(video)
        (tmp / "c.png").replace(out / "outcomes.png")
    cues = [
        {**c, "seed": 711, "start_s": 3 + c["start_s"], "end_s": 3 + c["end_s"]}
        for c in json.loads((feature / "spoken-cues.json").read_text())["spoken_cues"]
    ]
    shift = 3 + t1 + 3.5
    if b["spoken_cue"]:
        c = b["spoken_cue"]
        cues.append(
            {
                **c,
                "seed": other,
                "track": "alternate on-air program",
                "start_s": shift + c["start_s"],
                "end_s": shift + c["end_s"],
            }
        )
    (out / "captions.srt").write_text(
        "\n\n".join(
            f"{n}\n{srt_time(c['start_s'])} --> {srt_time(c['end_s'])}\n{c['actor']}: {c['text']}"
            for n, c in enumerate(cues, 1)
        )
        + "\n"
    )
    write_json(out / "spoken-cues.json", cues)
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
    assert abs(float(probe["format"]["duration"]) - duration) < 0.13
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(video), "-f", "null", "-"], check=True)
    write_json(
        out / "comparison.json",
        {
            "main_seed": 711,
            "contrast_seed": other,
            "criterion": "First numeric eligible comparison seed with a different final bulletin channel. Every completed root counted.",
            "all_final_bulletins": {seed: r["bulletin"] for seed, r in stages.items()},
            "sources_sha256": {seed: r["source_sha256"] for seed, r in stages.items()},
            "bruin_sha256": digest(ED / "heldout-v2-bruin.json"),
            "main_film_sha256": a["mp4_sha256"],
            "comparison_board_sha256": b["video_sha256"],
            "full_decode": True,
            "probe": probe,
            "mp4_sha256": digest(video),
            "cues": len(cues),
        },
    )
    print(duration, video)


if __name__ == "__main__":
    compare()
