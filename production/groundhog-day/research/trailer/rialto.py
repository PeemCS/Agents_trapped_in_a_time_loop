"""Shoot six new three-day takes on RunPod from the archived 721 movie-theory premise.

Usage: python3 rialto.py OUTPUT_DIRECTORY
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

import os
import subprocess
from urllib.request import Request, urlopen


def ollama(method, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request("http://127.0.0.1:11434/api/" + method, data=data,
                      headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=240) as response:
        return json.load(response)


NIGHT = Path(__file__).resolve().parents[1] / "night"
sys.path[:0] = [str(NIGHT / "last-reel"), str(NIGHT / "story")]
from inference import fingerprint, object_schema, validate
from scene import NAMES, ROLES, input_for
from town import atomic_json

spec = importlib.util.spec_from_file_location("archived_shoot", NIGHT / "last-reel/shoot.py")
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)
MODEL = "qwen3.8:27b"


class Recast(original.Shoot):
    def __init__(self, seed, out, digest):
        self.seed = seed
        self.condition = "hypothesis" if seed < 845 else "uncued"
        self.source = original.initial(721)
        self.folder = out / f"rialto-{seed}"
        self.folder.mkdir(exist_ok=True)
        self.digest = digest

    def act(self, role, day, phase, history, state, external):
        messages, actions = input_for(role, phase, self.condition, self.source["memory"], history,
                                      state, external, day)
        slot = ("afternoon", "evening", "alarm").index(phase)
        draw = self.seed * 37 + (day if role == "reporter" else 0) * 13 + slot * 3 + ROLES.index(role)
        payload = {"model": MODEL, "messages": messages, "stream": False, "think": False,
                   "format": object_schema(actions),
                   "options": {"num_ctx": 8192, "num_predict": 720, "temperature": .8, "seed": draw}}
        reply = ollama("chat", payload)
        sample = f"day-{day}-{phase}-{role}.json"
        atomic_json(self.folder / sample, {"request": payload, "response": reply, "revision": self.digest})
        if reply.get("done_reason") != "stop":
            raise ValueError(f"Incomplete response in {self.folder.name}/{sample}")
        return {"key": fingerprint(payload), "role": role, "speaker": NAMES[role], "seed": draw,
                "decision": validate(reply["message"]["content"], actions), "messages": messages,
                "attempts": [sample]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    pod = os.environ["RUNPOD_POD_ID"]
    gpu = subprocess.check_output(["nvidia-smi", "--query-gpu=name,uuid", "--format=csv,noheader"], text=True).strip()
    digest = next(m["digest"] for m in ollama("tags")["models"] if m["name"] == MODEL)
    for seed in range(841, 847):
        shoot = Recast(seed, args.out, digest)
        shoot.run()
        path = shoot.folder / "take.json"
        record = json.loads(path.read_text())
        record["performance"] = {"model": MODEL, "digest": digest, "source_root": 721, "pod": pod, "gpu": gpu,
                                 "driver_sha256": original.sha(Path(__file__).read_bytes())}
        atomic_json(path, record)


if __name__ == "__main__":
    main()
