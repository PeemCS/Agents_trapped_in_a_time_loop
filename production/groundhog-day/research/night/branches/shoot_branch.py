"""Resample a single actor's real checkpoint, then roll one differing choice forward in the original world."""
import concurrent.futures
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
NIGHT = HERE.parent
sys.path.insert(0,str(NIGHT/"story"))
from town import atomic_json
from world import ACTORS, CLOCKS, cue, initial_state, memory_slot, pack, resolve, stable_seed
from inference import OllamaChat, decide, fingerprint
from audit import pack_run

SOURCE = NIGHT/"takes/q27/film-transcript/seed-701.json"
OUTPUT = HERE/"evidence"
SEEDS = tuple(range(941,949))


def sample(backend, config, key_cache, role, day, tick, messages, actions, seed):
    key = fingerprint([config["model"],config["model_revision"],messages,actions,seed,config["temperature"],
                       config["max_tokens"],config["thinking"],config["response_format"],config["omit_seed"]])
    path=OUTPUT/"requests"/(key+".json")
    if path.exists():
        found=json.loads(path.read_text())
        if found["key"]!=key:raise ValueError("Request journal hash mismatch")
        return found["result"]
    result=decide(backend,role,(day,tick),messages,actions,seed,key,key_cache,
                  lambda key,role,slot,attempt,repair: atomic_json(OUTPUT/"attempts"/f"{key}-{repair}.json",attempt))
    atomic_json(path,{"key":key,"result":result})
    return result


def main():
    raw=SOURCE.read_bytes();parent=json.loads(raw);config=parent["configuration"]
    seed=parent["seed"];names=parent["cast_names"]
    start=next(i for i,e in enumerate(parent["events"]) if e["decision"]["action"]=="take_coach_to_Pittsburgh")
    fork=parent["events"][start];original=fork["decision"]["action"];day=fork["day"];tick=start%4
    stop=(day*4)+2
    cache={}
    for lead in parent["events"]:
        for e in [lead,*lead["cast"]]:
            inf=e["inference"]
            cache.setdefault(inf["request_id"],{"decision":e["decision"],"slot":[e["day"],CLOCKS.index(e["clock"]),e["actor"]]})
    visible=fork["inference"]
    args=SimpleNamespace(**config,api_key_env=None,timeout=120)
    backend=OllamaChat("http://127.0.0.1:18527",config["model"],args)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        jobs=[pool.submit(sample,backend,config,cache,"reporter",day,tick,visible["messages"],visible["legal_actions"],s) for s in SEEDS]
        candidates=[j.result() for j in jobs]
        report={"parent_sha256":hashlib.sha256(raw).hexdigest(),"source_event":fork["id"],"start_index":start,
                "end_exclusive":stop,"config":config,"original_action":original,"candidate_seeds":SEEDS,
                "candidates":[{"seed":s,"decision":dec,"request_id":inf["request_id"]} for s,(dec,inf) in zip(SEEDS,candidates)]}
        index=next((i for i,(dec,_) in enumerate(candidates) if dec["action"]!=original),None)
        if index is None:
            report["selected"]=None;atomic_json(OUTPUT/"selection.json",report)
            payload={"identical":True,"source_event":fork["id"],"candidate_count":len(SEEDS),"action":original}
            (HERE/"branch-traces.js").write_text("window.CoachFork="+json.dumps(payload)+";\n")
            return
        report["selected"]=SEEDS[index]
        atomic_json(OUTPUT/"selection.json",report)
        events=parent["events"][:start]
        state=fork["world_before"]
        history=[memory_slot(e) for e in events]
        for i in range(start,stop):
            day,tick=i//4+1,i%4
            if tick==0:state=initial_state()
            if i==start:
                all_dec={"reporter":candidates[index],**{e["role"]:[e["decision"],e["inference"]] for e in fork["cast"]}}
            else:
                calls={}
                for role in ACTORS:
                    messages,actions=cue(role,state,tick,history,parent["memory"],seed,names)
                    rng=stable_seed(seed,role,day if role=="reporter" else 0,tick)
                    calls[role]=pool.submit(sample,backend,config,cache,role,day,tick,messages,actions,rng)
                all_dec={role:call.result() for role,call in calls.items()}
            choices={k:v[0] for k,v in all_dec.items()};diags={k:v[1] for k,v in all_dec.items()}
            after,resolved=resolve(seed,day,tick,state,choices,names)
            entry=pack(day,tick,resolved,state,after,diags)["root"]
            entry["world_before"]=state
            entry["world_after"]=after
            events.append(entry);history.append(memory_slot(entry));state=after
        alt={**parent,"events":events,"status":"complete","source":"live_model_alternate","lineage":report,
             "checkpoint":state,"metrics":None}
        atomic_json(OUTPUT/"alternate.json",alt)
    actual=pack_run({**parent,"events":parent["events"][:stop]})
    branch=pack_run(alt)
    actual["label"]="Original take";branch["label"]="Alternate draw"
    payload={"start":start,"end":stop,"source_event":fork["id"],"parent_sha256":report["parent_sha256"],
             "selected":report["selected"],"candidate_count":len(SEEDS),"original":actual,"alternate":branch}
    # A script companion permits local, network-free double-click playback.
    (HERE/"branch-traces.js").write_text("window.CoachFork="+json.dumps(payload,ensure_ascii=False).replace("<","\\u003c")+";\n")
    print(json.dumps({"fork":fork["id"],"selected":report["selected"],"action":candidates[index][0]["action"],"through":events[-1]["id"]}))

if __name__=="__main__":
    main()
