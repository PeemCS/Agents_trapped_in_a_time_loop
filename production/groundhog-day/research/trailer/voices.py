"""Synthesize the edit's dialogue on the RunPod, aligned to the shot lengths."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

RATE = 24000
VOICES = {"Phil": "am_michael", "Rita": "af_heart", "Larry": "am_fenrir", "Narrator": "bf_emma"}


def phrases(text):
    pieces = re.split(r'(?<=[.!?])\s+|(?<=,)\s+(?=before\b)', text)
    return [piece.strip() for piece in pieces if piece.strip()]


def main():
    if not os.environ.get("RUNPOD_POD_ID"):
        raise SystemExit("Run this audio export on the production pod.")
    k = Kokoro("kokoro-v1.0.int8.onnx", "voices-v1.0.bin")
    cache = Path("voice-cache")
    cache.mkdir(exist_ok=True)
    edit = json.loads(Path("cut.json").read_text())
    start = 0
    cues = []
    output = np.zeros(RATE*sum(s["seconds"] for s in edit), dtype=np.float32)
    for number, shot in enumerate(edit):
        at = start
        start += shot["seconds"]
        voice = shot["voice"]
        if not voice:
            continue
        lines, waves = phrases(shot["text"]), []
        for line in lines:
            key = hashlib.sha256((VOICES[voice]+line).encode()).hexdigest()
            file = cache / (key + ".wav")
            if not file.exists():
                spoken = line.replace("8 AM", "eight A.M.").replace("forty-two", "forty two")
                wave, rate = k.create(spoken, voice=VOICES[voice], speed=1.02,
                                      lang="en-gb" if voice=="Narrator" else "en-us")
                assert rate == RATE
                active = np.flatnonzero(abs(wave)>.002)
                if not len(active):
                    raise ValueError(f"No speech for {line}")
                wave = wave[max(0,active[0]-500):active[-1]+900]
                sf.write(file,wave,RATE)
            waves.append(sf.read(file,dtype="float32")[0])
        room = shot["seconds"] - .58 - .10 * (len(lines)-1)
        ratio = sum(len(w) for w in waves)/(room*RATE)
        start_line = at+.28
        for line,w in zip(lines,waves):
            if ratio>1:
                # FFmpeg changes tempo while preserving pitch.
                w=np.frombuffer(subprocess.check_output([
                    "ffmpeg","-loglevel","error","-f","f32le","-ar",str(RATE),"-ac","1","-i","-",
                    "-af",f"atempo={ratio:.6f}","-f","f32le","-"],input=w.tobytes()),dtype="<f4")
            i=round(start_line*RATE)
            output[i:i+len(w)] += w*.85
            end=start_line+len(w)/RATE
            assert end<=start+.03,(number,end,start)
            cues.append({"shot":number,"start":start_line,"end":end,"voice":voice,"line":line})
            start_line=end+.10
    sf.write("dialogue.wav",output,RATE)
    Path("timing.json").write_text(json.dumps(cues,indent=2,ensure_ascii=False))
    print(f"{len(cues)} cues · {start}s",flush=True)


if __name__ == "__main__":
    main()
