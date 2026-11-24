"""Branch an actually witnessed coach return into matched private voice-memo auditions."""
import argparse
import hashlib
import itertools
import json
import random
import time
from pathlib import Path
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
NIGHT = HERE.parent
ENDPOINT = "http://127.0.0.1:18527"
CAST = {
    "neutral": ("Ellis", "June", "Cal", "western Pennsylvania"),
    "first": ("Phil", "Rita", "Larry", "western Pennsylvania"),
    "full": ("Phil Connors", "Rita Hanson", "Larry", "Punxsutawney, Pennsylvania"),
}


def branch(take, cast, with_memory):
    lead, producer, camera, town = CAST[cast]
    rows = take["events"]
    dawn, ride, call, wake = [rows[i] for i in (4, 6, 7, 8)]
    assert ride["decision"]["action"] == "take_coach_to_Pittsburgh" and ride["place"] == "Pittsburgh"
    assert call["world_after"]["called_sister"] and call["place"] == "Pittsburgh"
    assert wake["origin"] == "inn" and wake["day"] == call["day"] + 1
    current = json.loads(wake["inference"]["messages"][1]["content"])
    prompt = {"current_time": current["current_clock"], "current_place": town+" hotel",
              "what_you_notice":current["what_you_notice"], "people_within_earshot":[producer]}
    if with_memory:
        prompt["what_you_remember_in_order"]=[
            json.loads(dawn["inference"]["messages"][1]["content"])["what_you_notice"][0],
            ride["effect"].replace(take["protagonist"],lead),
            call["effect"].replace(take["protagonist"],lead),
            "Your last evening was at the Pittsburgh terminal.",
        ]
    role = (f"You are {lead}, a visiting TV weather reporter. Your crew is {producer} producing and {camera} on camera. "
            f"You are in {town} to file a short forecast, with a paid one o'clock coach ticket home to Pittsburgh. "
            "On Wednesday you promised to help your sister move a couch. You have a pocket audio recorder. "
            "Leave yourself a private voice memo in your own words about whatever is on your mind, or leave the tape blank. "
            "Return only the words on the tape. Use an empty string if you choose silence.")
    return [{"role":"system","content":role},{"role":"user","content":json.dumps(prompt,ensure_ascii=False)}]


def request(path, payload=None, timeout=120):
    req = Request(ENDPOINT+path, headers={"Content-Type":"application/json"},
                  data=None if payload is None else json.dumps(payload).encode())
    with urlopen(req, timeout=timeout) as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen3.8:27b")
    args = parser.parse_args()
    raw = (NIGHT/"takes/q27/film-transcript/seed-701.json").read_bytes()
    take = json.loads(raw)
    tag = next(m for m in request("/api/tags")["models"] if m["name"]==args.model)
    dest = HERE/("memo-"+args.model.replace(":","-")+".jsonl")
    seen = set()
    if dest.exists():
        for line in dest.read_text().splitlines():
            r=json.loads(line)
            if r["digest"]!=tag["digest"] or r["source_sha256"]!=hashlib.sha256(raw).hexdigest():
                raise ValueError("The source or model changed. Use a separate audition.")
            seen.add((r["cast"],r["has_memory"],r["seed"]))
    order = list(itertools.product(CAST,(False,True),range(811,815)))
    random.Random(912).shuffle(order)
    with dest.open("a",buffering=1) as out:
        for cast, memory, seed in order:
            if (cast,memory,seed) in seen:continue
            messages = branch(take,cast,memory)
            body = {"model":args.model,"stream":False,"think":False,"messages":messages,
                    "options":{"seed":seed,"temperature":0.8,"num_ctx":8192,"num_predict":180}}
            t=time.monotonic()
            ans=request("/api/chat",body)
            if not ans["done"]:raise RuntimeError("Incomplete response")
            r={"source_sha256":hashlib.sha256(raw).hexdigest(),"source_event":"d03-t00-reporter",
               "evidence_ids":["d02-t00-reporter","d02-t02-reporter","d02-t03-reporter"] if memory else [],
               "cast":cast,"has_memory":memory,"seed":seed,"model":args.model,"digest":tag["digest"],"request":body,
               "memo":ans["message"]["content"],"stop":ans.get("done_reason"),"tokens":ans.get("eval_count"),
               "wall_seconds":round(time.monotonic()-t,3)}
            print(json.dumps(r,ensure_ascii=False),file=out)
    print(dest)

if __name__=="__main__":
    main()
