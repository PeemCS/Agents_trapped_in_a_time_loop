#!/usr/bin/env python3
"""Assemble a single real held-out world into a chronological town opening and its final TV return."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from bulletin import before_cut
from edit import coach_clusters, make_edl, verify, write_json
from render_cut import srt_time


def choose_opening(path, output):
    trace, last_day, end, rows, broadcast = before_cut(path)
    events = trace["events"]
    limit = last_day[0][0]
    eligible = events[:limit]
    if not eligible:
        raise ValueError("need at least two recorded days for a film opening")
    clusters = [c for c in coach_clusters(events) if c["wake"] <= limit]
    cluster = clusters[0] if clusters else None
    # A keyed take contains at most one view of a simultaneous slot, except the distinct dawn pre-action shot.
    choices = {}

    def add(i, role, voice=True, seconds=4, view="action", framing="close"):
        key = (i, 0 if view == "morning" else 1)
        if key in choices:
            return
        e = events[i]
        actor = next(r for r in [e, *e["cast"]] if r["role"] == role)
        words = actor["decision"]["words"].strip()
        # Long practical monologues stay in the complete take. Preserve whole utterances on this short cut.
        audible = voice and words and len(words.split()) <= 32
        choices[key] = {
            "event_index": i,
            "event_id": e["id"],
            "view": view,
            "focus": actor["actor"],
            "framing": framing,
            "start": 0.22 if view == "morning" else 0.25 if i and events[i - 1]["day"] != e["day"] else 0,
            "end": 0.22 if view == "morning" else 1,
            "seconds": seconds,
            "speech": [{"actor": actor["actor"], "text": words}] if audible else [],
        }

    # First reserve the images required to make a bus claim true.
    if cluster:
        add(cluster["arrival"], "reporter", True, 5.8, framing="street")
        add(cluster["hold"], "reporter", True, 5.5)
        add(cluster["wake"], "reporter", False, 3.5, "morning")
    add(0, "reporter", True, 5.0)
    # Give the two other people coverage of a choice with an actual contact, location change, or finite resource.
    for role in ("producer", "camera"):
        options = []
        for i, e in enumerate(eligible):
            if (i, 1) in choices:
                continue
            actor = next(r for r in [e, *e["cast"]] if r["role"] == role)
            a = actor["decision"]["action"]
            spoken = actor["decision"]["words"].strip()
            score = 0
            if a.startswith("film_") or a in ("host_bulletin", "patch_camera_line", "patch_reporter_line"):
                score += 4
            if a.startswith("go_to_") or a == "file_forecast":
                score += 2
            if actor.get("signal_status") == "sent":
                score += 2
            if spoken and len(spoken.split()) <= 25:
                score += 2
            if i <= 7:
                score += 1
            options.append((-score, i))
        if options:
            add(min(options)[1], role, True, 5.0)
    categories = [
        ("call_sister",),
        ("leave_pencil_mark", "clear_tables", "file_forecast"),
        ("take_coach_to_Pittsburgh", "go_to_depot", "go_to_diner", "go_to_studio"),
    ]
    for actions in categories:
        i = next(
            (
                n
                for n, e in enumerate(eligible)
                if (n, 1) not in choices and e["decision"]["action"] in actions
            ),
            None,
        )
        if i is not None:
            add(i, "reporter", True, 5.0)
    # Five day's coverage must remain understandable even when an actor repeats the same action throughout.
    need = 8 - len(choices)
    if need > 0:
        previously = {events[k[0]]["decision"]["action"] for k in choices}
        ranked = sorted(
            (e["decision"]["action"] not in previously, bool(e["decision"]["words"].strip()), i)
            for i, e in enumerate(eligible)
            if (i, 1) not in choices
        )
        for _, _, i in reversed(ranked[-need:]):
            add(i, "reporter", True, 4.8)
    edl = make_edl(path, "chronicle")
    edl.update(
        selection="predeclared-bulletin",
        title="The Seven O’clock Bulletin",
        purpose="Private held-out root, prior-day chronology followed by the last day in three synchronized monitors.",
        cluster=cluster,
        shots=[choices[k] for k in sorted(choices)],
    )
    verify(path, edl)
    write_json(output, edl)
    return edl


def assemble(path, edl_path, opening, board, out):
    edl = json.loads(edl_path.read_text())
    verify(path, edl)
    verified = json.loads((opening / "qa.json").read_text())
    tv = json.loads((board / "receipt.json").read_text())
    assert verified["source_sha256"] == tv["source_sha256"] == edl["source_sha256"]
    assert verified["mp4_sha256"] == hashlib.sha256((opening / "film.mp4").read_bytes()).hexdigest()
    assert tv["video_sha256"] == hashlib.sha256((board / "film.mp4").read_bytes()).hexdigest()
    timing = json.loads((opening / "timing.json").read_text())
    expected = timing["seconds"] + tv["duration_s"]
    assert 60 <= expected <= 180, f"{expected:.1f} seconds"
    out.mkdir(parents=True, exist_ok=True)
    movie = out / "film.mp4"
    tmp = out / "render.tmp.mp4"
    filt = "[0:v]fps=24,setsar=1,setpts=PTS-STARTPTS[v0];[1:v]fps=24,setsar=1,setpts=PTS-STARTPTS[v1];[0:a]aresample=48000,asetpts=PTS-STARTPTS[a0];[1:a]aresample=48000,asetpts=PTS-STARTPTS[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][audio];[audio]loudnorm=I=-17:TP=-1.5:LRA=9[a]"
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-i",
            str(opening / "film.mp4"),
            "-i",
            str(board / "film.mp4"),
            "-filter_complex",
            filt,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-b:a",
            "144k",
            "-t",
            str(expected),
            "-movflags",
            "+faststart",
            str(tmp),
        ],
        check=True,
    )
    tmp.replace(movie)
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
                str(movie),
            ]
        )
    )
    assert abs(float(info["format"]["duration"]) - expected) < 0.12
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(movie), "-f", "null", "-"], check=True)
    cues = []
    raw = json.loads(path.read_text())
    for shot in timing["shots"]:
        time_slot = raw["events"][shot["event_index"]]
        actors = {r["actor"]: r for r in [time_slot, *time_slot["cast"]]}
        for line in shot["speech"]:
            cues.append(
                {
                    "actor": line["actor"],
                    "text": line["text"],
                    "start_s": line["start_s"],
                    "end_s": line["end_s"],
                    "event_id": actors[line["actor"]]["id"],
                    "track": "local dialogue",
                }
            )
    if tv["spoken_cue"]:
        cue = tv["spoken_cue"]
        cues.append(
            {
                **cue,
                "start_s": cue["start_s"] + timing["seconds"],
                "end_s": cue["end_s"] + timing["seconds"],
                "track": "on-air program",
            }
        )
    subtitle = out / "captions.srt"
    subtitle.write_text(
        "\n\n".join(
            f"{i}\n{srt_time(c['start_s'])} --> {srt_time(c['end_s'])}\n{c['actor']}: {c['text']}"
            for i, c in enumerate(cues, 1)
        )
        + "\n"
    )
    write_json(out / "spoken-cues.json", {"source_sha256": tv["source_sha256"], "spoken_cues": cues})
    write_json(
        out / "feature.json",
        {
            "source_sha256": tv["source_sha256"],
            "seed": json.loads(path.read_text())["seed"],
            "opening_edl": str(edl_path),
            "opening_video_sha256": verified["mp4_sha256"],
            "board_sha256": tv["video_sha256"],
            "crew_monitor_start_s": timing["seconds"],
            "on_air_at_s": timing["seconds"] + tv["on_air_from_s"],
            "actual_final_bulletin": tv["bulletin"],
            "observed_return_s": tv["duration_s"] - tv["on_air_from_s"],
            "probe": info,
            "mp4_sha256": hashlib.sha256(movie.read_bytes()).hexdigest(),
            "full_decode": True,
        },
    )
    print(expected, movie)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    c = p.add_subparsers(dest="command", required=True)
    a = c.add_parser("opening")
    a.add_argument("trace", type=Path)
    a.add_argument("edl", type=Path)
    a = c.add_parser("assemble")
    for x in ("trace", "edl", "opening", "board", "out"):
        a.add_argument(x, type=Path)
    a = p.parse_args()
    if a.command == "opening":
        choose_opening(a.trace, a.edl)
    else:
        assemble(a.trace, a.edl, a.opening, a.board, a.out)
