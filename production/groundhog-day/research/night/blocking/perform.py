"""Pair free blocking with retained menu draws at four actual hotel wakes."""
import concurrent.futures
import hashlib
import itertools
import json
from pathlib import Path
import random
import sys
import time
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
NIGHT = HERE.parent
sys.path[:0] = [str(NIGHT / "audition"), str(NIGHT / "story")]
from deliberate import checkpoint, MODEL
from town import atomic_json
from world import resolve

ENDPOINT = "http://127.0.0.1:18527"
FOLDER = HERE / "draws"

def schema(fields):
    properties = {key: {"type": "string"} for key in fields}
    return {"type": "object", "properties": properties, "required": list(fields), "additionalProperties": False}

def native(body):
    started = time.monotonic()
    req = Request(ENDPOINT + "/api/chat", data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
    with urlopen(req, timeout=300) as f:
        response = json.load(f)
    return {"request": body, "response": response, "wall_s": round(time.monotonic()-started,3)}

def parsed(row, required):
    response = row["response"]
    if response.get("done_reason") != "stop":
        return None
    try:
        act = json.loads(response["message"]["content"])
    except (ValueError, TypeError):
        return None
    if not isinstance(act,dict) or set(act)!=set(required) or any(not isinstance(v,str) for v in act.values()):
        return None
    return act

def perform(row,seed,think):
    folder=FOLDER / (str(row["world"])+"-"+str(seed)+"-"+("on" if think else "off"))
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/"performance.json"
    control=row["messages"]
    system=control[0]["content"].partition(" Choose your own action from the available physical actions.")
    if not system[1]:
        raise ValueError("Unexpected role card")
    card=(system[0]+" Give one immediate visible action of your own in plain language, optional words spoken aloud, "
         "and an optional short practical intention. A gesture may be small. You control only your character.")
    setup=json.loads(control[1]["content"])
    menu=setup.pop("available_actions")
    body={"model":MODEL,"stream":False,"think":think,"messages":[{"role":"system","content":card},
          {"role":"user","content":json.dumps(setup,ensure_ascii=False,indent=2)}],
          "format":schema(("gesture","words","intention")),
          "options":{"seed":seed,"temperature":.8,"num_ctx":8192,"num_predict":1536}}
    if not path.is_file():
        atomic_json(path,{**native(body),"world":row["world"],"arm":row["arm"],"sources":row["sources"],
                          "source_sha256":row["sha256"],"digest":row["model_revision"]})
    result=json.loads(path.read_bytes());assert result["request"]==body
    decision=parsed(result,("gesture","words","intention"))
    if decision is None or (folder/"resolution.json").is_file():
        return
    actions=row["legal"]+["unsupported"]
    shape=schema(("action","detail","evidence"));shape["properties"]["action"]["enum"]=actions
    instruction=("Map the performer's visible gesture to one available engine action if its physical requirements are met. "
                 "Use unsupported for a new destination, an unavailable prop, a claimed world-state change, or another character's act. "
                 "An ordinary bodily gesture can map to try_something with a short literal gesture as detail. "
                 "Multiple acts are resolved by the first currently executable one. Spoken dialogue never moves the actor. "
                 "Return the selected action, detail, and one short quoted fragment of the proposed gesture as evidence.")
    public={k:setup[k] for k in ("current_place","current_clock","what_you_notice","people_within_earshot")}
    payload={"model":MODEL,"stream":False,"think":False,
             "messages":[{"role":"system","content":instruction},{"role":"user","content":json.dumps(
                 {"visible":public,"available_actions":menu,"gesture":decision["gesture"]},ensure_ascii=False)}],
             "format":shape,"options":{"temperature":0,"seed":seed,"num_ctx":8192,"num_predict":192}}
    mapped=native(payload);chosen=parsed(mapped,("action","detail","evidence"))
    event=None;accepted=False
    if chosen and chosen["action"] in row["legal"] and chosen["evidence"].strip().casefold() in decision["gesture"].casefold() and chosen["evidence"].strip():
        source=NIGHT/"takes/q27"/row["arm"]/("seed-"+str(row["world"])+".json")
        raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()==row["sha256"]
        take=json.loads(raw);e=next(x for x in take["events"] if x["id"]==row["sources"][-1])
        decs={c["role"]:c["decision"] for c in e["cast"]}
        decs["reporter"]={"action":chosen["action"],"detail":chosen["detail"] if chosen["action"]=="try_something" else "",
                          "words":decision["words"],"intention":decision["intention"]}
        after,events=resolve(row["world"],e["day"],0,e["world_before"],decs,take["cast_names"])
        event={"world_before":e["world_before"],"world_after":after,"events":events}
        accepted=True
    atomic_json(folder/"resolution.json",{"mapping":mapped,"mapped_action":chosen,
               "simulated":accepted,"transition":event})

def main():
    with urlopen(ENDPOINT+"/api/tags",timeout=10) as f:
        digest=next(m["digest"] for m in json.load(f)["models"] if m["name"]==MODEL)
    rows=[checkpoint(i) for i in range(701,705)]
    assert len(rows)==4 and all(r and r["model_revision"]==digest for r in rows)
    jobs=list(itertools.product(rows,(961,962),(False,True)));random.Random(472).shuffle(jobs)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(perform,*job) for job in jobs]
        for f in futures:f.result()
    print("Retained",len(list(FOLDER.glob("*/performance.json"))),"original free performances",flush=True)

if __name__=="__main__":main()
