"""Run four matched immutable cassette-booth takes and keep the exact Ollama wire evidence."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib import request
from zoneinfo import ZoneInfo

from scene import Booth, ROOTS, WINDOWS, seeded

BASE = "http://127.0.0.1:18527"
MODEL = "qwen3.8:27b"
DIGEST = "aaee06c39dcf2437cde036998d960e1fc1494b8191be7cc9657d01e509097813"
CUTOFF = datetime(2026, 11, 23, 5, 55, tzinfo=ZoneInfo("America/Los_Angeles")).timestamp()
HERE = Path(__file__).resolve().parent
RUN = HERE / "q27-cassette-20261123"
SCRIPT = {"first_offer": "share_origin", "second_offer": "lend_latch",
          "fresh_handoff": "patch_drawer", "producer_response": "hold_drawer_key"}

def exact(path, body):
    """Do not replace an earlier wire record on a resume or a second invocation."""
    if path.exists():
        if path.read_bytes() != body: raise ValueError(f"Immutable file differs: {path}")
        return
    with path.open("xb") as f: f.write(body)

def saved(path, data):
    exact(path, (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def transact(seed, window, folder, live):
    room = Booth(seed, window)
    files = []
    folder.mkdir(parents=True, exist_ok=True)
    while room.phase != "closed":
        role, menu, evidence, messages = room.request()
        phase = room.phase
        base = folder / f"{len(files)+1:02d}-{phase}-{role.lower()}"
        schema = {"type": "object", "additionalProperties": False, "required": ["action", "note"],
                  "properties": {"action": {"type": "string", "enum": list(menu)},
                                 "note": {"type": "string", "description": "One short private sentence."}}}
        body = {"model": MODEL, "messages": messages, "format": schema, "think": True, "stream": False,
                "options": {"seed": seeded(seed, phase, role), "temperature": 0.75, "num_ctx": 8192, "num_predict": 1000}}
        inp = base.with_suffix(".request.json")
        raw = base.with_suffix(".response.json")
        meta = base.with_suffix(".started.json")
        exact(inp, json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode())
        if live:
            if not raw.exists():
                if meta.exists(): raise RuntimeError(f"Prior attempt lacks completed server response: {meta}")
                remaining = CUTOFF - time.time()
                if remaining < 135: raise RuntimeError("Paid request launch window has closed.")
                saved(meta, {"source": "native_ollama", "started_utc": datetime.now(timezone.utc).isoformat(),
                             "path": "/api/chat", "model_digest": DIGEST, "input_sha256": sha(inp), "evidence_ids": evidence})
                req = request.Request(BASE + "/api/chat", data=inp.read_bytes(), headers={"Content-Type":"application/json"})
                try:
                    with request.urlopen(req, timeout=125) as res:
                        raw_bytes = res.read()
                    exact(raw, raw_bytes)
                except Exception as error:
                    saved(base.with_suffix(".error.json"), {"type": type(error).__name__, "message": str(error)})
                    raise
            result = json.loads(raw.read_bytes())
            if not result.get("done") or result.get("done_reason") != "stop":
                raise RuntimeError(f"Model did not stop cleanly: {raw}")
            decision = json.loads(result["message"]["content"])
            if decision.keys() != {"action", "note"} or not isinstance(decision["note"], str):
                raise ValueError(f"Bad structured decision in {raw}")
        else:
            choice = SCRIPT[phase] if SCRIPT[phase] in menu else next(iter(menu))
            decision = {"action": choice, "note": "Injected mechanism probe."}
            saved(raw, {"fixture": True, "decision": decision})
        room.act(decision["action"])
        step = {"phase": phase, "role": role, "evidence_ids": evidence, "input": inp.name, "input_sha256": sha(inp),
                "response": raw.name, "response_sha256": sha(raw), "decision": decision}
        if live:
            step.update(stop=result.get("done_reason"), thinking_chars=len(result["message"].get("thinking", "")),
                        prompt_tokens=result.get("prompt_eval_count"), generated_tokens=result.get("eval_count"))
        files.append(step)
    take = {**room.record(), "source": "live_ollama" if live else "injected_fixture", "calls": files}
    saved(folder/"take.json", take)
    return take

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--live", action="store_true")
    p.add_argument("--fixture-out", type=Path, default=HERE/"fixtures")
    args = p.parse_args()
    root = RUN if args.live else args.fixture_out
    root.mkdir(parents=True, exist_ok=True)
    if args.live:
        with request.urlopen(BASE + "/api/tags", timeout=5) as res:
            tags = json.load(res)
        if not any(m["name"] == MODEL and m["digest"] == DIGEST for m in tags["models"]):
            raise SystemExit("Wrong model digest")
    cases = [(seed, window) for seed in ROOTS for window in WINDOWS]
    def case(config):
        seed, window = config
        take = transact(seed, window, root/f"{seed}-{window}", args.live)
        print(f"{seed} {window} {take['meter']}", flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(case, cases))

if __name__ == "__main__": main()
