"""Test a destination/physical act plus independent optional performance gesture."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from itertools import product
from pathlib import Path
import random
from perform import HERE,NIGHT,native,checkpoint,MODEL,atomic_json,resolve
from inference import object_schema,validate

def shoot(source,seed):
    folder=HERE/"two-channels";folder.mkdir(exist_ok=True)
    path=folder/(str(source["world"])+"-"+str(seed)+".json")
    if path.exists():return
    old=source["messages"][0]["content"]
    clause="detail is only for a small personal activity during try_something."
    assert clause in old
    system=old.replace(clause,"detail is optional, a small visible gesture with your own body or an observed prop while you carry out the selected action. It cannot move you to a second destination or give you an extra act.")
    messages=[{"role":"system","content":system},source["messages"][1]]
    body={"model":MODEL,"think":True,"stream":False,"messages":messages,"format":object_schema(source["legal"]),
          "options":{"seed":seed,"temperature":.8,"num_ctx":8192,"num_predict":1536}}
    row=native(body);response=row["response"];decision=None;error=None;effect=None
    try:
        if response.get("done_reason")!="stop":raise ValueError("incomplete answer")
        decision=validate(response["message"]["content"],source["legal"])
        orig=(NIGHT/"takes/q27"/source["arm"]/("seed-"+str(source["world"])+".json")).read_bytes()
        assert hashlib.sha256(orig).hexdigest()==source["sha256"]
        take=json.loads(orig);e=next(v for v in take["events"] if v["id"]==source["sources"][-1])
        choices={c["role"]:c["decision"] for c in e["cast"]};choices["reporter"]=decision
        after,events=resolve(source["world"],e["day"],0,e["world_before"],choices,take["cast_names"])
        effect={"physical_action":decision["action"],"effect":events["reporter"]["effect"],"position":after["positions"]["reporter"],
                "suggested_performance_detail":decision["detail"]}
    except (ValueError,TypeError) as exc:error=str(exc)
    atomic_json(path,{**row,"world":source["world"],"arm":source["arm"],"source_sha256":source["sha256"],"sources":source["sources"],
                      "model_revision":source["model_revision"],"decision":decision,"physical":effect,"error":error})

def main():
    items=list(product([checkpoint(i) for i in range(701,705)],(961,962)))
    random.Random(9735).shuffle(items)
    with ThreadPoolExecutor(max_workers=1) as pool:
        futures=[pool.submit(shoot,*i) for i in items]
        for f in futures:f.result()
    print("Eight paired gesture and physical-choice draws returned.")

if __name__=="__main__":main()
