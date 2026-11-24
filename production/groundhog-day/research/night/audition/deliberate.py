"""Paired provider thinking-mode probes at previously observed real hotel wakes."""
import concurrent.futures
import hashlib
import itertools
import json
import random
import sys
import time
from pathlib import Path

HERE=Path(__file__).resolve().parent
NIGHT=HERE.parent
sys.path.insert(0,str(NIGHT/"story"))
from inference import object_schema, validate
from town import atomic_json
from memo import request
MODEL="qwen3.8:27b"
OUT=HERE/"deliberation"


def checkpoint(seed):
    for arm in ("film-transcript","film-receipts","neutral-transcript","neutral-receipts"):
        path=NIGHT/"takes/q27"/arm/f"seed-{seed}.json";raw=path.read_bytes();r=json.loads(raw)
        for i,e in enumerate(r["events"][2:],start=2):
            ride,night=r["events"][i-2:i]
            if (ride["decision"]["action"]=="take_coach_to_Pittsburgh" and night["place"]=="Pittsburgh"
                 and night["clock"]=="7:00 pm" and e["clock"]=="6:00 am" and e["origin"]=="inn" and e["day"]==night["day"]+1):
                return {"world":seed,"arm":arm,"sha256":hashlib.sha256(raw).hexdigest(),"sources":[ride["id"],night["id"],e["id"]],
                        "model_revision":r["configuration"]["model_revision"],"receipt":night["effect"],
                        "messages":e["inference"]["messages"],"legal":e["inference"]["legal_actions"]}
    return None


def probe(row,seed,think):
    path=OUT/f'{row["world"]}-{seed}-{"on" if think else "off"}.json'
    if path.is_file():return
    payload={"model":MODEL,"stream":False,"think":think,"messages":row["messages"],"format":object_schema(row["legal"]),
             "options":{"temperature":.8,"seed":seed,"num_ctx":8192,"num_predict":1536}}
    start=time.monotonic();rep=request("/api/chat",payload,timeout=360);elapsed=time.monotonic()-start
    raw=rep["message"]["content"];parsed=None;error=None
    try:
        if rep["done_reason"]=="length":raise ValueError("token limit")
        parsed=validate(raw,row["legal"])
    except (ValueError,TypeError) as exc:error=str(exc)
    result={**row,"decoding_seed":seed,"think":think,"request":payload,"decision":parsed,"raw_visible":raw,"error":error,
            "tokens":rep["eval_count"],"prompt_tokens":rep["prompt_eval_count"],"end":rep["done_reason"],
            "wall_s":round(elapsed,3),"public_thinking":rep["message"].get("thinking",""),"thinking_channel_present":bool(rep["message"].get("thinking"))}
    atomic_json(path,result)


def quiz(model,digest,seed):
    payload={"model":model,"messages":[{"role":"user","content":"Which 1993 American comedy follows a TV weatherman who relives one day in Pennsylvania? Give only the film title and the actor who plays the weatherman."}],
             "stream":False,"think":False,"options":{"seed":seed,"temperature":.8,"num_ctx":8192,"num_predict":80}}
    rep=request("/api/chat",payload,timeout=360)
    return {"model":model,"digest":digest,"seed":seed,"request":payload,"answer":rep["message"]["content"],"stop":rep.get("done_reason")}


def main():
    OUT.mkdir(exist_ok=True)
    rows=[r for seed in range(701,705) if (r:=checkpoint(seed))]
    tags={r["name"]:r["digest"] for r in request("/api/tags")["models"]}
    assert all(r["model_revision"]==tags[MODEL] for r in rows)
    tasks=list(itertools.product(rows,(961,962),(False,True)));random.Random(771).shuffle(tasks)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(probe,*t) for t in tasks]
        for f in futures:f.result()
    controls=[]
    for model in (MODEL,"qwen3.5:4b"):
        for seed in (971,972):controls.append(quiz(model,tags[model],seed))
    atomic_json(OUT/"capability-quiz.json",controls)
    print("Audited",len(tasks),"reaction draws and",len(controls),"quiz draws")

if __name__=="__main__":main()
