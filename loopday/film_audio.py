"""Generate the original LOOPDAY score and synchronized sound effects."""

from __future__ import annotations

from array import array
from math import exp, pi, sin
from pathlib import Path
import random
import re
import sys
import wave


RATE = 22_050
TAU = pi * 2
MOTIF = (523.25, 392, 349.23, 440, 293.66)


def _tone(
    samples: array, onset: float, seconds: float, frequency: float, volume: float, *, resonant: bool = False
) -> None:
    start = round(RATE * onset)
    count = min(round(RATE * seconds), len(samples) - start)
    for index in range(count):
        age = index / RATE
        envelope = min(1., age / .012) * exp(-3.5 * age / seconds)
        if resonant:
            envelope *= min(1., (seconds - age) / .10)
        cycle = TAU * frequency * age
        tone = sin(cycle) + .22 * sin(cycle * 2.003) + .075 * sin(cycle * 3.011)
        samples[start + index] += tone * volume * envelope


def _noise(
    samples: array, onset: float, seconds: float, volume: float, seed: int, *, roughness: float
) -> None:
    start = round(RATE * onset)
    count = min(round(RATE * seconds), len(samples) - start)
    rng = random.Random(seed)
    previous = 0.
    for index in range(count):
        age = index / RATE
        fade = min(1., age * 80) * exp(-3.6 * age / seconds)
        sample = previous * (1 - roughness) + (2. * rng.random() - 1.) * roughness
        samples[start + index] += sample * fade * volume
        previous = sample


def _voice(samples: array, start: float, hold: float, path: Path) -> None:
    with wave.open(str(path), "rb") as source:
        rate, channels = source.getframerate(), source.getnchannels()
        if source.getsampwidth() != 2 or channels not in {1, 2} or not 8_000 <= rate <= 96_000:
            raise ValueError(f"Voice asset {path.name} must be 16-bit mono or stereo PCM WAV (8–96 kHz).")
        limit = min(source.getnframes(), round(rate * hold) + 1)
        pcm = array("h")
        pcm.frombytes(source.readframes(limit))
    limit = len(pcm) // channels
    if sys.byteorder != "little":
        pcm.byteswap()
    onset = round((start + .07) * RATE)
    count = min(round(hold * RATE), round(limit * RATE / rate), len(samples) - onset)
    for index in range(count):
        phase = index * rate / RATE
        a = int(phase)
        b = min(limit - 1, a + 1)
        blend = phase - a
        dry = sum(pcm[a * channels + c] * (1 - blend) + pcm[b * channels + c] * blend for c in range(channels))
        envelope = min(1., index / (.008 * RATE), (count - index) / (.071 * RATE))
        samples[onset + index] = samples[onset + index] * .38 + .72 * envelope * dry / (channels * 32_768)


def render_audio(plan: dict, path: Path, *, start_seconds: float = 0, seconds: float | None = None,
                 voice_dir: Path | None = None) -> None:
    """Write a mono 16-bit WAV with timing tied to the full edit decision list."""
    total = plan["duration_ms"] / 1_000
    samples = array("f", [0.]) * round(total * RATE)
    for index, shot in enumerate(plan["shots"]):
        cue = shot["sound"]
        start = shot["start_ms"] / 1_000
        hold = shot["duration_ms"] / 1_000
        if cue in {"radio", "tomorrow"}:
            _noise(samples, start + hold * .21, .5, .19, index, roughness=.67)
            for offset, frequency in enumerate(MOTIF):
                opened = frequency * (1.25 if cue == "tomorrow" else 1.)
                _tone(samples, start + hold * .24 + offset * .16, .56, opened, .12, resonant=True)
        elif cue == "snap":
            _noise(samples, start + hold * .27, .19, .23, index, roughness=.95)
        elif cue == "splash":
            _noise(samples, start + hold * .37, .64, .21, index, roughness=.35)
            _tone(samples, start + hold * .39, .16, 179, .09)
        elif cue == "wind":
            _noise(samples, start, hold, .33, index, roughness=.047)
        elif cue == "bell":
            _tone(samples, start + hold * .14, 1.8, 293.66, .14, resonant=True)
        elif cue in {"piano", "practice"}:
            frequencies = MOTIF[2:] if cue == "practice" else MOTIF + (349.23, 493.88, 587.33, 392)
            spacing = .18 if cue == "practice" else .073
            for offset, frequency in enumerate(frequencies):
                _tone(samples, start + hold * (.15 + spacing * offset), .73, frequency, .12, resonant=True)
        elif cue == "steps":
            for offset in (.18, .39, .60, .83):
                _noise(samples, start + hold * offset, .12, .085, index, roughness=.27)

        # A recurring bed gives each loop a recognizable motif and yields to dialogue.
        frequency = (130.81, 146.83, 110., 130.81)[shot["loop"] % 4]
        _tone(samples, start, min(hold + .28, 4.4), frequency, .018, resonant=True)
        _tone(samples, start + .035, min(hold, 4.1), frequency * 1.5, .014, resonant=True)
    if voice_dir is not None:
        for shot in plan["shots"]:
            event_id = shot["event_id"]
            if shot["speaker"] and isinstance(event_id, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,72}", event_id):
                asset = voice_dir / (event_id + ".wav")
                if asset.is_file():
                    _voice(samples, shot["start_ms"] / 1_000, max(.1, shot["duration_ms"] / 1_000 - .16), asset)
    start_frame = round(start_seconds * RATE)
    end_frame = len(samples) if seconds is None else start_frame + round(seconds * RATE)
    peak = max((abs(sample) for sample in samples), default=0.)
    master = min(2.20, .73 / max(.01, peak))
    pcm = array("h", (round(sample * master * 32_767) for sample in samples[start_frame:end_frame]))
    if sys.byteorder != "little":
        pcm.byteswap()
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(RATE)
        output.writeframes(pcm.tobytes())
