"""One documented higher-cap extension of a length-limited primary checkpoint."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from threading import Lock
import time
from urllib import request
from scene import Booth, ROOTS, WINDOWS, seeded
from shoot import BASE, CUTOFF, DIGEST, HERE, MODEL, RUN, exact, saved, sha

OUT = HERE/"q27-cassette-continuations-20261123"
LOCK = Lock()

def reference(path, base): return os.path.relpath(path, base)
def new_body(role, phase, seed, menu, messages):
    return {"model":MODEL,"messages":messages,"format":{"type":"object","additionalProperties":False,"required":["action","note"],
            "properties":{"action":{"type":"string","enum":list(menu)},"note":{"type":"string","description":"One short private sentence."}}},
            "think":True,"stream":False,"options":{"seed":seeded(seed,phase,role),"temperature":0.75,"num_ctx":8192,"num_predict":3072}}

def sample(case):
    seed,window=case
    base=RUN/f"{seed}-{window}"
    folder=OUT/f"{seed}-{window}"
    if (base/"take.json").exists(): return
    folder.mkdir(parents=True,exist_ok=True)
    if (folder/"take.json").exists():return
    room=Booth(seed,window);steps=[];primary_fail=None
    while room.phase!="closed":
        role,menu,evidence,messages=room.request()
        phase=room.phase
        name=f"{len(steps)+1:02d}-{phase}-{role.lower()}"
        src=base if primary_fail is None else folder
        inp=src/(name+".request.json");raw=src/(name+".response.json")
        body=new_body(role,phase,seed,menu,messages)
        if primary_fail is None:
            current=json.loads(raw.read_bytes())
            original=json.loads(inp.read_bytes())
            matched={**body,"options":{**body["options"],"num_predict":1000}}
            if original!=matched:raise ValueError("Could not reconstruct exact original request")
            if current["done_reason"]=="length":
                primary_fail={"phase":phase,"response":reference(raw,folder),"sha256":sha(raw),
                              "request":reference(inp,folder),"generated_tokens":current["eval_count"]}
                src=folder
                inp=src/(name+".request.json");raw=src/(name+".response.json")
            elif current["done_reason"]!="stop":raise ValueError("Original stop is outside the length continuation protocol")
        if primary_fail is not None and src==folder:
            exact(inp,json.dumps(body,ensure_ascii=False,separators=(",",":")).encode())
            start=src/(name+".started.json")
            if not raw.exists():
                with LOCK:
                    calls=sum(1 for parent in (RUN,OUT) for _ in parent.glob("*/*.started.json"))
                    if calls>=20 or CUTOFF-time.time()<135:raise RuntimeError("Maximum call allowance or wall clock limit reached.")
                    if start.exists():raise ValueError("Refusing to repeat unconfirmed provider request")
                    saved(start,{"source":"native_ollama","started_utc":datetime.now(timezone.utc).isoformat(),"path":"/api/chat",
                                 "model_digest":DIGEST,"input_sha256":sha(inp),"evidence_ids":evidence})
                q=request.Request(BASE+"/api/chat",data=inp.read_bytes(),headers={"Content-Type":"application/json"})
                try:
                    with request.urlopen(q,timeout=125) as res: exact(raw,res.read())
                except Exception as ex:
                    saved(src/(name+".error.json"),{"type":type(ex).__name__,"message":str(ex)})
                    raise
            current=json.loads(raw.read_bytes())
        if not current["done"] or current["done_reason"]!="stop":
            saved(folder/"incomplete.json",{"phase":phase,"receipts":steps,"primary_fail":primary_fail,"stop":current["done_reason"]})
            return
        dec=json.loads(current["message"]["content"])
        if set(dec)!={"action","note"} or not isinstance(dec["note"],str):raise ValueError("Bad action output")
        room.act(dec["action"])
        steps.append({"phase":phase,"role":role,"evidence_ids":evidence,"input":reference(inp,folder),"input_sha256":sha(inp),
                      "response":reference(raw,folder),"response_sha256":sha(raw),"decision":dec,"stop":current["done_reason"],
                      "thinking_chars":len(current["message"].get("thinking","")),"prompt_tokens":current["prompt_eval_count"],
                      "generated_tokens":current["eval_count"]})
    saved(folder/"take.json",{**room.record(),"source":"live_ollama_continuation","primary_fail":primary_fail,"calls":steps})
    print(f"completed {seed} {window}",flush=True)

if __name__=="__main__":
    inputs=[(seed,window) for seed in ROOTS for window in WINDOWS]
    for seed,window in inputs:
        base=RUN/f"{seed}-{window}"
        if (base/"take.json").exists():continue
        closed=any(json.loads(p.read_bytes())["done_reason"]=="length" for p in base.glob("*.response.json"))
        if not closed:raise SystemExit(f"Primary seed {seed}, {window} not ready")
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(sample,inputs))
