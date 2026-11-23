"""Prepare event-keyed macOS speech clips for a personal LOOPDAY rehearsal."""

from __future__ import annotations

from argparse import ArgumentParser
from array import array
from collections import Counter
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
import wave

from .film import build_film
from .film_audio import RATE
from .render_film import _ffmpeg


SAY = Path("/usr/bin/say")
MAX_RATE = 245
MAX_TEMPO = 1.17
PRONUNCIATIONS = {
    "Punxsutawney": "Punk-suh-TAW-nee",
    "Ryerson": "RYE-er-son",
}


@dataclass(frozen=True)
class VoiceDirection:
    candidates: tuple[str, ...]
    words_per_minute: int


DIRECTIONS = {
    "phil": VoiceDirection(("Reed (English (US))", "Alex", "Daniel"), 156),
    "rita": VoiceDirection(("Samantha (English (US))", "Samantha", "Flo (English (US))"), 168),
    "larry": VoiceDirection(("Eddy (English (US))", "Fred", "Daniel"), 150),
    "ned": VoiceDirection(("Rocko (English (US))", "Ralph", "Albert"), 188),
}


class VoiceError(ValueError):
    """Speech synthesis returned an unusable result."""


def spoken_text(text: str) -> str:
    text = re.sub(r"\[\[[^\]]*\]\]", "", text)
    text = " ".join(text.replace("[", " ").replace("]", " ").split())
    for original, pronunciation in PRONUNCIATIONS.items():
        text = re.sub(rf"\b{original}\b", pronunciation, text, flags=re.IGNORECASE)
    return text


def local_voices() -> set[str]:
    try:
        result = subprocess.run([str(SAY), "-v", "?"], capture_output=True, text=True, check=True, timeout=8)
    except (OSError, subprocess.SubprocessError):
        return set()
    return {match[1].strip() for line in result.stdout.splitlines()
            if (match := re.match(r"(.+?)\s+en[_-][A-Za-z]+\s+\s*#", line))}


def _speech(text: str, voice: str, rate: int, path: Path) -> None:
    try:
        subprocess.run(
            [str(SAY), "-v", voice, "-r", str(rate), "--file-format=WAVE", f"--data-format=LEI16@{RATE}",
             "-o", str(path), "-f", "-"],
            input=text, capture_output=True, text=True, check=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise VoiceError("macOS speech synthesis was unavailable.") from error


def _pcm(path: Path) -> array:
    try:
        with wave.open(str(path), "rb") as recording:
            if (recording.getnchannels(), recording.getsampwidth(), recording.getframerate()) != (1, 2, RATE):
                raise VoiceError("The voice did not return mono 16-bit PCM at the expected rate.")
            if recording.getnframes() > 45 * RATE:
                raise VoiceError("The voice returned an unexpectedly long clip.")
            samples = array("h")
            samples.frombytes(recording.readframes(recording.getnframes()))
    except (OSError, wave.Error, EOFError) as error:
        raise VoiceError("macOS speech synthesis could not be read.") from error
    if sys.byteorder == "big":
        samples.byteswap()
    peak = max(map(abs, samples), default=0)
    if peak < 150:
        raise VoiceError("The selected macOS voice produced no audible frames.")
    threshold = max(42, round(peak * .008))
    start = next(i for i, sample in enumerate(samples) if abs(sample) >= threshold)
    end = len(samples) - next(i for i, sample in enumerate(reversed(samples)) if abs(sample) >= threshold)
    pad = round(RATE * .038)
    return samples[max(0, start - pad):min(len(samples), end + pad)]


def _write_pcm(path: Path, samples: array) -> None:
    output = array("h", samples)
    if sys.byteorder == "big":
        output.byteswap()
    with wave.open(str(path), "wb") as recording:
        recording.setnchannels(1)
        recording.setsampwidth(2)
        recording.setframerate(RATE)
        recording.writeframes(output.tobytes())


def voice_for(direction: VoiceDirection, installed: set[str], used: set[str], directory: Path) -> str | None:
    for index, name in enumerate(direction.candidates):
        if name not in installed or name in used:
            continue
        try:
            sample = directory / f"check-{index}.wav"
            _speech("The morning starts at six.", name, direction.words_per_minute, sample)
            _pcm(sample)
        except VoiceError:
            continue
        return name
    return None


def fit_line(text: str, voice: str, preferred_rate: int, budget: float, directory: Path) -> tuple[array, int, float]:
    if budget <= .25:
        raise VoiceError("The line has no speaking time.")
    words = len(text.split())
    rate = min(MAX_RATE, max(preferred_rate, math.ceil(words * 60 / (budget * 1.04))))
    for attempt in range(2):
        source = directory / f"clip-{attempt}.wav"
        _speech(text, voice, rate, source)
        pcm = _pcm(source)
        seconds = len(pcm) / RATE
        if seconds <= budget:
            return pcm, rate, 1.
        latest = min(MAX_RATE, math.ceil(rate * seconds / budget * 1.05))
        if attempt == 1 or rate == latest:
            break
        rate = latest
    tempo = (seconds / budget) * 1.014
    if tempo > MAX_TEMPO:
        raise VoiceError("The recorded line exceeds its shot at a comfortable speaking rate.")
    trimmed = directory / "trimmed.wav"
    adjusted = directory / "adjusted.wav"
    _write_pcm(trimmed, pcm)
    try:
        subprocess.run([_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(trimmed), "-af",
                        f"atempo={tempo:.6f}", str(adjusted)],
                       capture_output=True, check=True, timeout=12)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        raise VoiceError("There is no local tempo adjustment for this longer line.") from error
    fitted = _pcm(adjusted)
    if len(fitted) > budget * RATE:
        raise VoiceError("The line still exceeds its shot after tempo adjustment.")
    return fitted, rate, tempo


def prepare_voices(plan: dict, out: Path) -> dict:
    """Write only valid, in-budget clips. Missing voices retain the score and captions."""
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    if any(out.iterdir()):
        raise ValueError("Use a new voice directory so current and previous clips stay paired with their event IDs.")
    selected = [shot for shot in plan["shots"] if shot["speaker"] and shot["caption"]]
    installed = local_voices()
    voices = {}
    records = []
    for shot in selected:
        event_id, actor = shot["event_id"], shot["actor"]
        if not isinstance(event_id, str) or re.fullmatch(r"[A-Za-z0-9_-]{1,72}", event_id) is None:
            raise ValueError("A speech cue has an invalid event ID.")
        budget = max(0., shot["duration_ms"] / 1_000 - .25)
        record = {"event_id": event_id, "actor": actor, "caption": shot["caption"], "budget_s": round(budget, 3)}
        direction = DIRECTIONS.get(actor)
        with TemporaryDirectory(prefix="loopday-voice-") as work:
            temporary = Path(work)
            if direction and actor not in voices:
                voices[actor] = voice_for(direction, installed, set(voices.values()), temporary)
            voice = voices.get(actor)
            if voice is None:
                record.update(status="captions", detail="No distinct installed voice generated audible speech.")
            else:
                line = spoken_text(shot["caption"])
                try:
                    clip, rate, tempo = fit_line(line, voice, direction.words_per_minute, budget, temporary)
                except VoiceError as error:
                    record.update(status="captions", detail=str(error))
                else:
                    _write_pcm(out / (event_id + ".wav"), clip)
                    record.update(status="spoken", voice=voice, rate_wpm=rate, tempo=round(tempo, 4),
                                  seconds=round(len(clip) / RATE, 3), spoken_text=line)
        records.append(record)
    counts = Counter(record["status"] for record in records)
    return {
        "use": "Personal local rehearsal using macOS system voices",
        "utterances": len(records), "spoken": counts["spoken"], "captions": counts["captions"],
        "voices": {actor: name for actor, name in voices.items() if name}, "events": records,
    }


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=94)
    args = parser.parse_args()
    try:
        run = json.loads(args.run.read_text(encoding="utf-8"))
        summary = prepare_voices(build_film(run, args.seconds), args.out)
        (args.out / "manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(f"{summary['spoken']}/{summary['utterances']} lines voiced · {summary['captions']} caption-only · {args.out}")


if __name__ == "__main__":
    main()
