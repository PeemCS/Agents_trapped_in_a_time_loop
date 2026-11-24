#!/usr/bin/env python3
"""Source-locked festival edit for the separate Rialto trajectories."""

import argparse, hashlib, json, math, re, subprocess, sys, tempfile
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image, ImageDraw
from render_cut import synth_line, wav, RATE, VOICES, wrap, srt_time
from rialto_stage import set_stage, font

ROOT = Path(__file__).resolve().parent.parent / "last-reel"
sys.path.insert(0, str(ROOT))
from scene import afternoon, evening, ALARM

FPS = 24
PLACES = {
    "pocket_fare_envelope": "coat_check",
    "take_coach": "town",
    "sleep_at_terminal": "terminal",
    "call_sister": "terminal",
    "wait_for_morning": "terminal",
    "rehearse_piano": "ballroom",
    "play_piano": "ballroom",
    "go_to_party": "ballroom",
    "ask_Rita_to_dance": "ballroom",
    "go_dancing": "ballroom",
    "visit_party": "ballroom",
    "go_to_party_for_work": "ballroom",
    "sit_at_depot": "depot",
    "deliver_reel": "patch",
    "transmit_interview": "patch",
    "interview_Alma": "Rialto",
    "film_Alma": "Rialto",
    "record_Alma": "Rialto",
    "wait_at_Rialto": "Rialto",
    "help_driver": "roadside",
    "get_up": "hotel",
    "listen_again": "hotel",
    "stay_in_bed": "hotel",
    "go_to_bed": "hotel",
}
LABELS = {
    "coat_check": "Hotel coat check",
    "town": "Coach to Pittsburgh",
    "terminal": "Pittsburgh terminal",
    "ballroom": "Festival ballroom",
    "Rialto": "Rialto projection booth",
    "patch": "Regional station line",
    "depot": "Town coach depot",
    "hotel": "Hearthside Hotel",
    "roadside": "Roadside",
    "archive": "The regional reply",
}
VOICEMAP = dict(zip(("Phil", "Rita", "Larry"), VOICES))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(p, obj):
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def speech_policy(words, mode="silent", quote=None):
    """A human selects a line. We check that selection conservatively; the full field always survives."""
    if mode == "silent":
        if quote:
            raise ValueError("silence cannot carry a line")
        return {"mode": mode, "text": "", "source_start": None, "source_end": None}
    if not words:
        raise ValueError("empty dialogue field")
    if mode == "quoted":
        if not quote or words.count(quote) != 1:
            raise ValueError("quote must be unique and contiguous")
        start = words.index(quote)
        end = start + len(quote)
        if (
            start == 0
            or end == len(words)
            or (words[start - 1], words[end])
            not in {('"', '"'), ("“", "”"), ("'", "'"), ("‘", "’")}
        ):
            raise ValueError("dialogue excerpt must span an explicit pair of quotes")
        if "*" in quote or "\n" in quote:
            raise ValueError("marked or multiline quote needs review")
        return {"mode": mode, "text": quote, "source_start": start, "source_end": end}
    if mode == "whole":
        if (
            quote
            or not re.search(r"[a-z0-9]", words, re.I)
            or re.search(
                r"^\s*(?:none|nothing|no words|silent|silence|i (?:do not|don[’']t) (?:say|speak)|i am putting on my socks)\b",
                words,
                re.I,
            )
            or re.search(
                r'[*"“”\[\]\n]|\b(?:i (?:say nothing|do not say|say to|turn to|nod|walk|push the door)|i do not speak|you (?:do not|nod|walk)|silence|over my shoulder|says?[: ])\b',
                words,
                re.I,
            )
        ):
            raise ValueError(
                "whole-field speech has a direction, quotation or unclear boundary"
            )
        return {
            "mode": mode,
            "text": words,
            "source_start": 0,
            "source_end": len(words),
        }
    raise ValueError("unknown dialogue policy")


def verify_orig(actor):
    a = actor["attempts"][-1]
    origin = ROOT / a["stream"]
    raw = origin.read_bytes()
    assert sha(raw) == a["stream_sha256"]
    rows = [json.loads(l) for l in raw.splitlines()]
    chunks = [r for r in rows if r["kind"] == "chunk"]
    msgs = [r["provider"]["message"] for r in chunks if "message" in r["provider"]]
    final = json.loads("".join(m.get("content", "") for m in msgs))
    thought = "".join(m.get("thinking", "") for m in msgs)
    assert (
        final == actor["decision"]
        and thought == a["public_thinking"]
        and rows[0]["role"] == actor["role"]
        and chunks[-1]["provider"]["done"]
    )
    return thought, {
        "stream": a["stream"],
        "sha256": a["stream_sha256"],
        "original_emission_take": actor["source_run"],
        "original_emission_day": actor["source_day"],
        "original_emission_phase": actor["source_phase"],
        "cache_hit": actor["cache_hit"],
        "model": a["response_model"],
    }


def prepare(source, plan):
    take = json.loads(source.read_text())
    assert take["status"] == "complete"
    # Replay the entire closed-world ledger independently, never count the alternative clock as observed.
    for d in take["days"]:
        st = afternoon({k: v["decision"] for k, v in d["afternoon"].items()})
        assert st == d["afternoon_state"]
        en = evening({k: v["decision"] for k, v in d["evening"].items()}, st)
        assert en == d["ending"] and en["closed_clock"] == "Tuesday"
    assert (
        sha((ROOT.parent / take["source"]["source"]).read_bytes())
        == take["source"]["sha256"]
    )
    shots = []
    last = (0, 0)
    for s in plan["shots"]:
        day, phase, role = s["day"], s["phase"], s["role"]
        order = (day, {"afternoon": 0, "evening": 1, "alarm": 2}[phase])
        assert order >= last
        last = order
        if phase == "alarm":
            assert day == len(take["days"]) + 1
            who = take["last_alarm"]
            assert who["role"] == role
            d = take["days"][-1]
            effect = {
                "get_up": "Phil gets up.",
                "stay_in_bed": "Phil stays in bed.",
                "listen_again": "Phil listens for the second backfire.",
            }[who["decision"]["action"]]
            obs = json.loads(who["messages"][-1]["content"])["what_you_observe"]
            assert ALARM in obs
        else:
            d = take["days"][day - 1]
            who = d[phase][role]
            effect = d["afternoon_state" if phase == "afternoon" else "ending"][
                "effects"
            ][role]
        event = f"d{day:02d}-{phase}-{role}"
        kind = s.get("kind", "action")
        note, proof = verify_orig(who)
        dec = who["decision"]
        act = dec["action"]
        row = {
            "event_id": event,
            "day": day,
            "phase": phase,
            "kind": kind,
            "role": role,
            "actor": who["speaker"],
            "action": act,
            "source_effect": effect,
            "full_words_field": dec["words"],
            "stream": proof,
            "scene": (
                "archive"
                if kind == "receipt"
                else "hotel"
                if kind == "wake"
                else PLACES[act]
            ),
            "seconds": s["seconds"],
            "delivery_by_end_of_this_source_day": d["ending"]["delivered"],
            "reporter_receipt_visible_in_actor_input": any(
                "daughter sent a receipt" in o
                for o in json.loads(who["messages"][-1]["content"])["what_you_observe"]
            ),
            "dance": d["ending"]["dance"],
        }
        if kind == "note":
            q = s["quote"]
            assert 0 < len(q.split()) <= 44 and note.count(q) == 1
            row.update(
                text=q,
                offset=note.index(q),
                label="Unspoken model note",
                sound="silence",
                scene=s.get("scene", row["scene"]),
            )
        elif kind == "wake":
            obs = json.loads(who["messages"][-1]["content"])["what_you_observe"]
            assert ALARM in obs
            row.update(
                text="Tuesday, February 2. Six am in the Hearthside Hotel.",
                label="World clock",
                scene="hotel",
                sound="alarm",
            )
        elif kind == "witnesses":
            from fare_evidence import audit

            facts = audit(source)
            assert (
                day == 1
                and phase == "afternoon"
                and role == "producer"
                and facts["observers"]["producer"]["where"]
                == facts["observers"]["camera"]["where"]
                == "Rialto"
            )
            row.update(
                text="Rita and Larry heard him in the lobby. Both went to the Rialto. Neither saw him empty the envelope.",
                label="What Rita and Larry witnessed",
                sound="room",
                scene="Rialto",
            )
        elif kind == "receipt":
            obs = json.loads(who["messages"][-1]["content"])["what_you_observe"]
            line = next(x for x in obs if "daughter sent a receipt" in x)
            q = s["quote"]
            assert line.count(q) == 1
            row.update(
                text=q,
                visible_receipt=line,
                label="Letter from Pittsburgh",
                scene="archive",
                sound="room",
            )
        elif kind == "action":
            v = speech_policy(dec["words"], s.get("speech", "silent"), s.get("quote"))
            row.update(
                speech=v,
                label=who["speaker"] + " · " + ("Spoken" if v["text"] else "Action"),
                text=v["text"] or effect,
                sound="perform",
                voice_choice_reason=s["reason"],
            )
        else:
            raise ValueError("unknown shot")
        if (
            plan.get("format") == "short"
            and act == "go_to_bed"
            and role == "reporter"
            and d["afternoon_state"]["fare_cash"]
        ):
            available = json.loads(who["messages"][-1]["content"])["physical_choices"]
            assert (
                "wire_deposit" in available
                and d["ending"]["effects"][role]
                == "Phil lets the evening go by in bed alone."
            )
            row["verified_extra_caption"] = (
                "He could wire the money for his sister’s van. No payment was issued."
            )
        if plan.get("format") == "short" and kind == "wake":
            now = json.loads(who["messages"][-1]["content"])["what_you_observe"]
            assert any(
                "envelope holds the TV crew’s return fares" in item for item in now
            )
            row["verified_extra_caption"] = (
                "The coat-check envelope holds the crew’s return fares again."
            )
        if plan.get("format") == "short" and act == "take_coach" and kind == "action":
            assert d["afternoon_state"]["positions"]["reporter"] == "Pittsburgh"
            row["show_terminal_arrival"] = True
        shots.append(row)
    for i, s in enumerate(shots):
        if s["kind"] == "note":
            assert (
                shots[i + 1]["event_id"] == s["event_id"]
                and shots[i + 1]["kind"] == "action"
            )
    return {
        "title": plan["title"],
        "format": plan.get("format", "festival"),
        "take": source.parent.name,
        "exact_path": str(source),
        "source_sha256": sha(source.read_bytes()),
        "source_carry_in": take["source"],
        "condition": take["condition"],
        "clock": "Closed Tuesday. An outside receipt may survive. Wednesday is only an alternative reducer rule and is never filmed in this cut.",
        "shots": shots,
        "speech_gate_counts": dict(
            Counter(s["speech"]["mode"] for s in shots if s["kind"] == "action")
        ),
        "stage": "New illustrated reconstruction; nonverbal staging and foley are editorial. All committed actions, actual receiver, and the closed clock replayed from the source.",
    }


def tone(sec, freq, dur=0.45, level=0.1):
    t = np.arange(round(dur * RATE)) / RATE
    return (
        level
        * (np.sin(2 * math.pi * freq * t) + 0.21 * np.sin(4 * math.pi * freq * t))
        * np.minimum(1, t / 0.012)
        * np.exp(-4 * t)
        * np.minimum(1, (dur - t) / 0.09)
    ).astype("float32")


def score(s, n):
    dur = n / RATE
    data = np.zeros(n, dtype="float32")

    def put(tm, ss):
        off = round(tm * RATE)
        if off < n:
            data[off : min(n, off + len(ss))] += ss[: max(0, min(n - off, len(ss)))]

    if s["sound"] == "silence":
        return data
    if s["kind"] == "wake":
        for t, f in ((0.14, 465), (0.44, 604), (0.78, 506)):
            put(t, tone(t, f, 0.45, 0.12))
        for t, f in ((1.4, 65), (1.83, 51)):
            put(t, tone(t, f, 0.14, 0.11))
    elif s["action"] in ("rehearse_piano", "play_piano") and s["kind"] == "action":
        for i, f in enumerate([220, 329.63, 293.66, 246.94, 329.63, 392, 293.66, 220]):
            put(0.24 + i * (dur - 0.8) / 8, tone(0, f, 0.68, 0.12))
    elif s["scene"] == "town":
        t = np.arange(n) / RATE
        data += (
            0.043
            * np.sin(2 * math.pi * (38 * t + 0.9 * t * t))
            * np.minimum(1, t / 0.4)
            * np.minimum(1, (dur - t) / 0.45)
        )
    elif s["scene"] == "patch":
        put(0.18, tone(0, 480, 0.17, 0.085))
        put(0.42, tone(0, 640, 0.17, 0.07))
    elif s["scene"] == "Rialto":
        for k in np.arange(0.18, dur - 0.1, 0.24):
            put(k, tone(0, 142, 0.03, 0.03))
    else:
        t = np.arange(n) / RATE
        data += (
            0.007
            * np.sin(2 * math.pi * 92 * t)
            * np.minimum(1, t / 0.35)
            * np.minimum(1, (dur - t) / 0.5)
        )
    return data


def painted(s, t, take):
    who = s["actor"]
    act = s["action"]
    kind = s["kind"]
    stage = set_stage(
        "archive" if kind == "note" else s["scene"],
        t,
        who,
        "wake" if kind == "wake" else act,
        kind == "witnesses" or (s["dance"] and act == "ask_Rita_to_dance"),
    )
    arrived = s.get("show_terminal_arrival") and t >= 0.73
    if arrived:
        stage = set_stage("terminal", (t - 0.73) / 0.27, who, "arrive_terminal", False)
    if kind == "action" and s["scene"] not in ("town", "archive"):
        centre = {
            "ballroom": 438 if "piano" in act else 741,
            "depot": 584,
            "Rialto": 791,
            "patch": 716,
            "terminal": 639,
            "hotel": 849,
            "roadside": 760,
        }.get(s["scene"], 640)
        zoom = 1.03 + 0.075 * (0.5 - 0.5 * math.cos(math.pi * t))
        ww, hh = 1280 / zoom, 570 / zoom
        left = (1280 - ww) * centre / 1280
        top = (570 - hh) * 0.61
        stage = stage.resize(
            (1280, 570), Image.Resampling.BICUBIC, box=(left, top, left + ww, top + hh)
        )
    out = Image.new("RGB", (1280, 720), "#11252b")
    out.paste(stage, (0, 0))
    d = ImageDraw.Draw(out)
    # The note remains a graphic card; physical action appears only in its following shot.
    if kind == "note":
        mask = Image.new("RGBA", (1280, 570), (15, 31, 37, 217))
        out.paste(mask, (0, 0), mask)
        d = ImageDraw.Draw(out)
        d.line((76, 164, 197, 164), fill="#e5ad69", width=5)
        d.text(
            (76, 191),
            who.upper() + "    /    UNSPOKEN MODEL NOTE",
            font=font(23, True),
            fill="#edc38b",
        )
        lines = wrap(d, s["text"], font(41, serif=True), 1072)
        for i, line in enumerate(lines):
            d.text((76, 245 + i * 56), line, font=font(41, serif=True), fill="#fff0cf")
    if (kind == "action" and s.get("speech", {}).get("text")) or s.get(
        "verified_extra_caption"
    ):
        fact = s.get("verified_extra_caption", s["source_effect"])
        f = font(19, True)
        lines = wrap(d, fact, f, 1110)
        height = 23 * len(lines) + 14
        d.rounded_rectangle(
            (42, 541 - height, 72 + max(d.textlength(l, font=f) for l in lines), 545),
            radius=6,
            fill="#183138",
        )
        for i, line in enumerate(lines):
            d.text((55, 548 - height + 23 * i), line, font=f, fill="#e6d9b4")
    if kind == "receipt":
        d.polygon(
            [(312, 312), (814, 298), (856, 470), (343, 482)],
            fill="#eddfba",
            outline="#b5a77e",
        )
        d.text(
            (365, 333),
            "REGIONAL LINE    /    PITTSBURGH",
            font=font(16, True),
            fill="#746344",
        )
        for i, line in enumerate(wrap(d, s["text"], font(30, serif=True), 412)):
            d.text((365, 377 + 40 * i), line, font=font(30, serif=True), fill="#343e37")
    d.rectangle((0, 0, 1280, 62), fill="#142a30")
    d.text(
        (42, 19),
        (
            "TUESDAY "
            + str(s["day"]).zfill(2)
            + "     /     "
            + ("6:00 AM" if kind in ("wake", "receipt") else s["phase"].upper())
        ),
        font=font(17, True),
        fill="#e2c49b",
    )
    lbl = "BEFORE THE ACTION" if kind == "note" else LABELS[s["scene"]].upper()
    if arrived:
        lbl = LABELS["terminal"].upper()
    d.text(
        (1236 - d.textlength(lbl, font=font(17, True)), 19),
        lbl,
        font=font(17, True),
        fill="#c4d4c6",
    )
    d.line((43, 570, 1237, 570), fill="#637b73", width=2)
    if kind == "note":
        label = (
            "PHIL’S PRIVATE STARTING THEORY"
            if take.endswith("hypothesis") and s["day"] == 1
            else "PROVIDER OUTPUT · SILENT"
        )
        text = (
            "Phil was given the theory that copying Groundhog Day’s ending might release him."
            if label.startswith("PHIL’S")
            else "This excerpt comes from the actor’s own recorded model output."
        )
        if take.endswith("library"):
            label = "THE LIBRARY CASE"
            text = "A library case described a 1993 comedy about a weatherman reliving February 2."
    else:
        label = s["label"].upper()
        text = s["text"]
        if s.get("speech", {}).get("text") and s["phase"] == "afternoon":
            label += " IN THE HOTEL LOBBY"
    d.text((49, 586), label, font=font(19, True), fill="#edbf7c")
    lines = wrap(d, text, font(26, serif=True), 1160)
    if len(lines) > 3:
        raise ValueError("projection sentence exceeds space: " + text)
    for i, line in enumerate(lines):
        d.text((49, 619 + i * 29), line, font=font(26, serif=True), fill="#f8edd5")
    sid = take + "  /  " + s["event_id"]
    d.text(
        (1230 - d.textlength(sid, font=font(12)), 699),
        sid,
        font=font(12),
        fill="#a4b7af",
    )
    return out


def render(source, plan_path, out):
    report = prepare(source, json.loads(plan_path.read_text()))
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rialto-cut-") as tdir:
        tmp = Path(tdir)
        snd = []
        cursor = 0
        cues = []
        for s in report["shots"]:
            speech = s.get("speech", {}).get("text")
            v = (
                synth_line(s["actor"], speech, VOICEMAP, tmp)
                if speech
                else np.array([], dtype="float32")
            )
            dur = max(s["seconds"], (len(v) / RATE + 0.96) if len(v) else 0)
            if s["kind"] == "note":
                dur = max(dur, 1.1 + len(s["text"].split()) / 3.15)
            frames = math.ceil(dur * FPS)
            n = round(frames / FPS * RATE)
            start = cursor / FPS
            s.update(
                first_frame=cursor,
                frames=frames,
                start_s=start,
                end_s=(cursor + frames) / FPS,
            )
            bed = score(s, n)
            if len(v):
                offset = round(0.40 * RATE)
                bed[offset : offset + len(v)] += 0.76 * v
                cues.append(
                    {
                        "actor": s["actor"],
                        "type": "spoken",
                        "text": speech,
                        "start": start + 0.40,
                        "end": start + 0.40 + len(v) / RATE,
                        "event": s["event_id"],
                    }
                )
            else:
                cues.append(
                    {
                        "actor": s["actor"] if s["kind"] == "note" else "Town",
                        "type": "unspoken model note"
                        if s["kind"] == "note"
                        else "stage",
                        "text": s["text"],
                        "start": start,
                        "end": start + frames / FPS,
                        "event": s["event_id"],
                    }
                )
            snd.append(bed)
            cursor += frames
        lower, upper = (20, 45) if report["format"] == "short" else (60, 110)
        assert lower <= cursor / FPS <= upper, (
            cursor / FPS,
            "seconds outside selected cut format",
        )
        wav(tmp / "track.wav", np.concatenate(snd))
        dest = out / "film.mp4"
        ff = subprocess.Popen(
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-y",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-s",
                "1280x720",
                "-r",
                str(FPS),
                "-i",
                "pipe:0",
                "-i",
                str(tmp / "track.wav"),
                "-c:v",
                "libx264",
                "-crf",
                "18",
                "-preset",
                "veryfast",
                "-pix_fmt",
                "yuv420p",
                "-af",
                "loudnorm=I=-17:TP=-1.5:LRA=10",
                "-ar",
                "48000",
                "-c:a",
                "aac",
                "-b:a",
                "144k",
                "-movflags",
                "+faststart",
                "-t",
                str(cursor / FPS),
                str(tmp / "film.mp4"),
            ],
            stdin=subprocess.PIPE,
        )
        try:
            for s in report["shots"]:
                count = s["frames"]
                for j in range(count):
                    ff.stdin.write(
                        painted(s, j / max(1, count - 1), report["take"]).tobytes()
                    )
        finally:
            ff.stdin.close()
            if ff.wait():
                raise RuntimeError("festival encode failed")
        (tmp / "film.mp4").replace(dest)
    for name, selected in [
        ("captions.srt", cues),
        ("spoken-only.srt", [c for c in cues if c["type"] == "spoken"]),
    ]:
        (out / name).write_text(
            "\n\n".join(
                f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['actor']}{' [' + c['type'] + ']' if c['type'] != 'spoken' else ''}: {c['text']}"
                for i, c in enumerate(selected, 1)
            )
            + "\n"
        )
    write(out / "cues.json", cues)
    write(out / "shot-evidence.json", report)
    probe = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=codec_name,width,height,nb_frames,sample_rate:format=duration,size",
                "-of",
                "json",
                str(dest),
            ]
        )
    )
    assert (
        int(probe["streams"][0]["nb_frames"]) == cursor
        and abs(float(probe["format"]["duration"]) - cursor / FPS) < 1 / FPS
    )
    subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(dest), "-f", "null", "-"],
        check=True,
    )
    dec = np.frombuffer(
        subprocess.check_output(
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-i",
                str(dest),
                "-vn",
                "-ar",
                "48000",
                "-ac",
                "1",
                "-f",
                "f32le",
                "-",
            ]
        ),
        dtype="<f4",
    )
    silence = []
    for s in report["shots"]:
        if s["kind"] == "note":
            window = dec[
                round((s["start_s"] + 0.15) * 48000) : round(
                    (s["end_s"] - 0.15) * 48000
                )
            ]
            peak = float(np.abs(window).max())
            assert peak < 0.0002
            silence.append({"event": s["event_id"], "decoded_peak": peak})
    qa = {
        "mp4_sha256": sha(dest.read_bytes()),
        "take_sha256": report["source_sha256"],
        "shot_evidence_sha256": sha((out / "shot-evidence.json").read_bytes()),
        "captions_sha256": sha((out / "captions.srt").read_bytes()),
        "seconds": cursor / FPS,
        "frames": cursor,
        "full_video_audio_decode": True,
        "probe": probe,
        "silent_note_windows": silence,
        "speech_gate_counts": report["speech_gate_counts"],
    }
    write(out / "verification.json", qa)
    from check_note_frames import jpg_frame

    n = len(report["shots"])
    sheet = Image.new("RGB", (1200, math.ceil(n / 3) * 250), "#152a2d")
    d = ImageDraw.Draw(sheet)
    for i, s in enumerate(report["shots"]):
        pick = s["start_s"] + (s["end_s"] - s["start_s"]) * 0.57
        img = jpg_frame(dest, pick)
        img.thumbnail((394, 220))
        x = (i % 3) * 400
        y = (i // 3) * 250
        sheet.paste(img, (x, y))
        d.text(
            (x + 5, y + 222),
            f"{pick:04.1f}s  {s['event_id']}  /  {s['kind']}",
            font=font(14),
            fill="#e4d5b9",
        )
    sheet.save(out / "contact-sheet.jpg", quality=91)
    print(json.dumps(qa, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("trace", "plan", "out"):
        p.add_argument(arg, type=Path)
    a = p.parse_args()
    render(a.trace, a.plan, a.out)
