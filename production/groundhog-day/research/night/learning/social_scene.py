"""Two coworkers choose whether to make six small recordings. The actor never sees the learned side state."""
import argparse
import hashlib
import itertools
import json
import math
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"audition"))
from memo import request

JOBS = [
    ("bandstand", "Get a clean level on a cornet warm-up; someone can hold the second mic.", "morning coffee", True),
    ("platform", "Record the station clock over the terminal crowd; someone can hold the boom.", "the quiet waiting room", True),
    ("diner", "Record a pie plate spinning on the counter; a second person can catch it.", "a hot breakfast", True),
    ("reel", "Record a family story on an old reel; a second person can ride the levels.", "an early lunch", False),
    ("keys", "Record one last chord on a piano; a second person can hold the loose stand.", "a call home", True),
    ("bridge", "Record the river under the bridge; a second person can shield the wind.", "the next local bus", True),
]
PEOPLE = {"Rita":"You are Rita, a local news producer planning a radio segment about the band.",
          "Larry":"You are Larry, a local news cameraman putting together an audio portrait of the town."}
SEEDS = (831,832,833)


def infer(model, seed, messages, options):
    rng=random.Random(seed)
    actions=list(options);rng.shuffle(actions)
    schema={"type":"object","properties":{"choice":{"type":"string","enum":actions},"words":{"type":"string"}},
            "required":["choice","words"],"additionalProperties":False}
    payload={"model":model,"messages":messages,"format":schema,"think":False,"stream":False,
             "options":{"temperature":0.8,"seed":seed,"num_ctx":8192,"num_predict":160}}
    start=time.monotonic()
    reply=request("/api/chat",payload)
    answer=json.loads(reply["message"]["content"])
    if answer["choice"] not in actions or not isinstance(answer["words"], str) or reply.get("done_reason")=="length":
        raise ValueError("Unusable generation")
    return {"request":payload,"choice":answer["choice"],"words":answer["words"],
            "wall_seconds":round(time.monotonic()-start,3),"tokens":reply.get("eval_count")}


def exchange(model,seed,name,job,memories):
    key, setup, cost, functional = JOBS[job]
    record={"seed":seed,"person":name,"job":key,"model":model}
    offer = [{"role":"system","content":PEOPLE[name]+" Decide how to spend the current session. You have your own work to do. Return your choice and at most one short line spoken aloud; silence is fine."},
             {"role":"user","content":json.dumps({"setup":setup,"who_is_here":"Phil, the weather reporter",
             "your_choices":["invite_him","work_independently","shelve_the_take"],
             "recent_shared_receipts":memories[-2:]})}]
    record["owner"]=infer(model,seed*93+job*2,offer,["invite_him","work_independently","shelve_the_take"])
    if record["owner"]["choice"]=="invite_him":
        take=[{"role":"system","content":"You are Phil. You cover the weather. You have personal appointments and can choose how to spend the current session. Return your choice and at most one short line spoken aloud; silence is fine."},
              {"role":"user","content":json.dumps({"setup":setup,"offer_from":name,"their_words":record["owner"]["words"],
                "the_schedule":"Joining costs you "+cost+".","choices":["join_the_take","keep_appointment"],
                "recent_shared_receipts":memories[-2:]})}]
        record["reporter"]=infer(model,seed*93+job*2+1,take,["join_the_take","keep_appointment"])
    joined=record.get("reporter",{}).get("choice")=="join_the_take"
    record["mutually_joined"]=joined
    record["shared_success"]=functional if joined else None
    if joined:
        receipt=f"{name} and Phil made the {key} take together. "+("The recording played back." if functional else "The playback was blank.")
    else:
        receipt=f"{name} and Phil did not make the {key} take together."
    record["receipt"]=receipt
    return record


def histories(model,seed,name,digest,folder):
    path=folder/(str(seed)+"-"+name+".jsonl")
    previous=[]
    if path.exists():
        previous=[json.loads(line) for line in path.read_text().splitlines()]
        if any(x.get("digest")!=digest for x in previous):raise ValueError("Model digest changed")
    order=list(range(len(JOBS)));random.Random(seed).shuffle(order)
    if [x["job"] for x in previous]!=[JOBS[i][0] for i in order[:len(previous)]]:raise ValueError("Broken scene prefix")
    receipts=[x["receipt"] for x in previous]
    with path.open("a",buffering=1) as out:
        for job in order[len(previous):]:
            data=exchange(model,seed,name,job,receipts)
            receipts.append(data["receipt"])
            data["digest"]=digest
            print(json.dumps(data,ensure_ascii=False),file=out)


def probability(par,z,cost,requested):
    # Two-action softmax. Own appointment has utility zero. Repeated pressure has no progress and incurs unwanted contact.
    w=par["fitted_weights"]
    utility=(w[0]+par["relation_weight"]*z if requested else w[2])+w[4]*cost
    return 1/(1+math.exp(-utility/par["policy_temperature"]))


def projections(raws,par):
    per=[]
    for seed in SEEDS:
        records={}
        for name in PEOPLE:
            rows=[r for r in raws if r["person"]==name and r["seed"]==seed]
            assert len({r["job"] for r in rows})==len(JOBS)
            joined=[r for r in rows if r["mutually_joined"]];s=sum(r["shared_success"] for r in joined)
            z=max(0,2*(2+s)/(4+len(joined))-1)
            records[name]={"invited":sum(r["owner"]["choice"]=="invite_him" for r in rows),"joined":len(joined),
                           "successful":s,"z":z,"jobs":len(rows)}
        for name,other in [("Rita","Larry"),("Larry","Rita")]:
            obj=records[name]
            obj["one_appointment_cost"]={}
            for diary,keep in itertools.product(["erased","retained"],repeat=2):
                obj["one_appointment_cost"][diary+"_diary_"+keep+"_record"]=probability(par,obj["z"] if keep=="retained" else 0,1,True)
            obj["same_state_swapped_partner_record"]=probability(par,records[other]["z"],1,True)
            obj["same_state_new_display_name"]=probability(par,obj["z"],1,True)
            obj["press_after_refusal_with_retained_record"]=probability(par,obj["z"],1,False)
            obj["press_after_refusal_with_erased_record"]=probability(par,0,1,False)
            obj["cost_sweep"]={str(c):probability(par,obj["z"],c,True) for c in (0,.25,.5,1,1.5,2)}
        per.append({"root":seed,"people":records})
    return per


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--model",default="qwen3.8:27b");args=p.parse_args()
    tag=next(m for m in request("/api/tags")["models"] if m["name"]==args.model)
    folder=HERE/("social-"+args.model.replace(":","-"));folder.mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        fs=[pool.submit(histories,args.model,s,n,tag["digest"],folder) for s in SEEDS for n in PEOPLE]
        for f in fs:f.result()
    rows=[json.loads(line) for path in sorted(folder.glob("*.jsonl")) for line in path.read_text().splitlines()]
    old=HERE.parents[1]/"social-learning-results.json";par=json.loads(old.read_text())
    output={"model":args.model,"digest":tag["digest"],"generic_head_source_sha256":hashlib.sha256(old.read_bytes()).hexdigest(),
            "sidecar_is_visible_to_actors":False,"roots":projections(rows,par)}
    (folder/"results.json").write_text(json.dumps(output,indent=2)+"\n")
    print(folder/"results.json")

if __name__=="__main__":
    main()
