#!/usr/bin/env python3
"""Transcribe the finished audio without a reference prompt; compare exact cue windows afterward."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
import numpy as np
from faster_whisper import WhisperModel


def seconds(s):
    h, m, sec = s.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(sec)


def listen(folder, model_path, subs):
    media = folder / "film.mp4"
    raw = subprocess.check_output(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-i",
            str(media),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "f32le",
            "-",
        ]
    )
    audio = np.frombuffer(raw, dtype="<f4").copy()
    asr = WhisperModel(
        str(model_path),
        device="cpu",
        compute_type="int8",
        cpu_threads=4,
        local_files_only=True,
    )

    def transcribe(samples):
        segs, _ = asr.transcribe(
            samples,
            language="en",
            beam_size=5,
            temperature=0,
            vad_filter=False,
            condition_on_previous_text=False,
        )
        return " ".join(s.text.strip() for s in segs)

    all_text = transcribe(audio)
    rows = []
    for s in subs.read_text().strip().split("\n\n"):
        _, time, *lines = s.splitlines()
        a, b = map(seconds, time.split(" --> "))
        text = " ".join(lines).split(": ", 1)[-1]
        pred = transcribe(
            audio[max(0, round((a - 0.16) * 16000)) : round((b + 0.16) * 16000)]
        )
        norm = lambda x: re.findall("[a-z0-9]+", x.lower().replace("’", "'"))
        rows.append(
            {
                "start_s": a,
                "end_s": b,
                "caption": text,
                "asr": pred,
                "exact_lexical_after_punctuation_case": norm(pred) == norm(text),
            }
        )
    return {
        "mp4_sha256": hashlib.sha256(media.read_bytes()).hexdigest(),
        "model_bin_sha256": hashlib.sha256(
            (model_path / "model.bin").read_bytes()
        ).hexdigest(),
        "method": "Local faster-whisper base.en, CPU int8. First blind continuous pass, then isolated spoken cue time windows with 160ms padding. No text prompts, vocabulary hints, VAD or prior-text conditioning. Exact lexical check normalizes punctuation and capitalization only.",
        "continuous_asr": all_text,
        "cues": rows,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder", type=Path)
    p.add_argument("model_path", type=Path)
    p.add_argument("subs", type=Path)
    a = p.parse_args()
    r = listen(a.folder, a.model_path, a.subs)
    (a.folder / "audio-readback.json").write_text(
        json.dumps(r, ensure_ascii=False, indent=2) + "\n"
    )
    print("Verified", len(r["cues"]), "timestamped speech windows.", flush=True)
