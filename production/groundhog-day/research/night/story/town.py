"""Private event-day rehearsal for a three-agent, repeatedly reset Pennsylvania town."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import datetime
import fcntl
import json
import os
from pathlib import Path
import tempfile
import time

from inference import Fixture, OpenAIChat, OllamaChat, decide, fingerprint, validate
from world import ACTORS, CAST_NAMES, CLOCKS, cue, initial_state, memory_slot, pack, resolve, stable_seed

ROOT=Path(__file__).resolve().parent
ENGINE_FILES=("town.py","world.py","inference.py")

def atomic_json(path, obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=path.parent,delete=False) as file:
        tmp=Path(file.name)
        try:
            json.dump(obj,file,ensure_ascii=False,separators=(",",":"))
            file.write("\n"); file.flush(); os.fsync(file.fileno())
        except BaseException:
            tmp.unlink(missing_ok=True); raise
    try: os.replace(tmp,path)
    finally: tmp.unlink(missing_ok=True)

@contextmanager
def exclusive(path):
    with path.open("a+") as f:
        try: fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"Another sampler owns {path}.") from exc
        try: yield
        finally: fcntl.flock(f.fileno(),fcntl.LOCK_UN)

def config(args, seed):
    return {"protocol":"town-night-1","code":fingerprint([p+":"+(ROOT/p).read_text() for p in ENGINE_FILES]),
            "seed":seed,"days":args.days,"backend":args.backend,"model":args.model if args.backend!="fixture" else "fixture",
            "model_revision":args.model_revision,"memory":args.memory,"cast":args.cast,
            "temperature":args.temperature,"max_tokens":args.max_tokens,"response_format":args.response_format,
            "thinking":args.thinking,"omit_seed":args.omit_seed,"num_ctx":args.num_ctx if args.backend=="ollama" else None}

def metrics(row):
    events=row["events"]; all_events=[e for p in events for e in [p,*p["cast"]]]
    words=[e["decision"]["words"].strip() for e in events if e["decision"]["words"].strip()]
    trips=[i for i,e in enumerate(events) if e["decision"]["action"]=="take_coach_to_Pittsburgh"]
    return {"seed":row["seed"],"source":row["source"],"model":row["model"],"memory":row["memory"],"cast":row["cast_condition"],
            "status":row["status"],"committed_slots":len(events),"cast_decisions":len(all_events),
            "reporter_places":sorted({p for e in events for p in [e["origin"],e["place"]]}),
            "reporter_actions":dict(Counter(e["decision"]["action"] for e in events)),
            "reporter_spoken":len(words),"reporter_distinct_lines":len(set(words)),
            "physical_coach_trips":len(trips),
            "confirmed_next_wakes_after_pittsburgh":sum(i+2<len(events) and events[i+1]["clock"]==CLOCKS[-1] and
              events[i+1]["place"]=="Pittsburgh" and events[i+2]["origin"]=="inn" and events[i+2]["day"]==events[i]["day"]+1 for i in trips),
            "logged_valid_generation_slots":sum(not e["inference"]["cache_hit"] for e in all_events),
            "response_reuses":sum(e["inference"]["cache_hit"] for e in all_events),
            "sampled_repairs":sum(max(0,len(e["inference"]["attempts"])-1) for e in all_events),
            "physically_grounded_social_work":sum(e["decision"]["action"] in ("clear_tables","record_band","air_forecast","film_cornet_player") for e in all_events)}

def sample(args, seed, backend=None):
    out=args.out;out.mkdir(parents=True,exist_ok=True)
    path=out/f"seed-{seed}.json"
    params=config(args,seed)
    reqdir=out/f".requests-{seed}";reqdir.mkdir(exist_ok=True)
    names=CAST_NAMES[args.cast]
    with exclusive(out/f".seed-{seed}.lock"):
        if path.exists():
            row=json.loads(path.read_text())
            if row["configuration"]!=params:
                raise ValueError(f"{path} belongs to a different configuration. Use a fresh --out.")
            if row["status"]=="complete": return row
        else:
            row={"version":1,"source":"injected_fixture" if args.backend=="fixture" else "live_model","seed":seed,
                 "protagonist":names["reporter"],"cast_names":names,"model":params["model"],"memory":args.memory,
                 "cast_condition":args.cast,"configuration":params,"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 "status":"partial","events":[],"checkpoint":None}
            atomic_json(path,row)
        cache={}
        for e in row["events"]:
            for actor_event in [e,*e["cast"]]:
                inf=actor_event["inference"]
                cache.setdefault(inf["request_id"],{"decision":actor_event["decision"],
                        "slot":[actor_event["day"],CLOCKS.index(actor_event["clock"]),actor_event["actor"]]})
        recovered={}
        for attempt_path in sorted(reqdir.glob("*.json")):
            rec=json.loads(attempt_path.read_text())
            if rec["config_id"]==fingerprint(params):
                recovered.setdefault(rec["request_id"],[]).append(rec)
        if backend is None:
            if args.backend=="fixture": backend=Fixture()
            elif args.backend=="ollama": backend=OllamaChat(args.base_url,args.model,args)
            else: backend=OpenAIChat(args.base_url,args.model,args)
        history=[memory_slot(e) for e in row["events"]]
        state=row["checkpoint"] or initial_state()
        def save_attempt(key,actor,slot,a,repair):
            name=f"{time.time_ns()}-{key[:16]}.json"
            rec={"config_id":fingerprint(params),"request_id":key,"role":actor,"slot":list(slot),"repair":repair,"attempt":a}
            atomic_json(reqdir/name,rec)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            while len(row["events"])<args.days*4:
                index=len(row["events"]);day=index//4+1;tick=index%4
                if tick==0: state=initial_state()
                calls={};results={}
                for actor in ACTORS:
                    turns,actions=cue(actor,state,tick,history,args.memory,seed,names)
                    rng=stable_seed(seed,actor,day if actor=="reporter" else 0,tick)
                    key=fingerprint([params["model"],params["model_revision"],turns,actions,rng,args.temperature,args.max_tokens,
                                     args.thinking,args.response_format,args.omit_seed])
                    # An interrupted slot may already have a paid valid decision on disk.
                    attempts=recovered.get(key,[])
                    accepted=next((r for r in attempts if r["attempt"]["error"] is None),None)
                    if accepted and key not in cache:
                        dec=validate(accepted["attempt"]["response"],actions)
                        recorded=[r["attempt"] for r in attempts if r["slot"]==accepted["slot"] and r["role"]==actor]
                        results[actor]=(dec,{"request_id":key,"messages":turns,"legal_actions":actions,"sampling_seed":rng,
                            "attempts":recorded,"cache_hit":False,"recovered_from_disk":True})
                    else:
                        calls[actor]=pool.submit(decide,backend,actor,(day,tick),turns,actions,rng,key,cache,save_attempt)
                for actor,future in calls.items(): results[actor]=future.result()
                decisions={actor:results[actor][0] for actor in ACTORS}
                diagnostics={actor:results[actor][1] for actor in ACTORS}
                after,by_actor=resolve(seed,day,tick,state,decisions,names)
                slot=pack(day,tick,by_actor,state,after,diagnostics)
                event=slot["root"]
                event["world_before"]=state;event["world_after"]=after
                row["events"].append(event)
                history.append(memory_slot(event));row["checkpoint"]=after
                row["status"]="complete" if len(row["events"])==args.days*4 else "partial"
                row["metrics"]=metrics(row)
                atomic_json(path,row)
                for actor in ACTORS:
                    inf=diagnostics[actor]
                    cache.setdefault(inf["request_id"],{"slot":[day,tick,names[actor]],"decision":decisions[actor]})
                state=after
                print(f"{path.name}  day {day}  {CLOCKS[tick]}  {decisions['reporter']['action']}  [{row['status']}]",flush=True)
        return row

def run_args(sub):
    sub.add_argument("--backend",choices=("openai","ollama","fixture"),default="openai")
    sub.add_argument("--base-url",default=os.getenv("TOWN_BASE_URL","http://127.0.0.1:8000/v1"))
    sub.add_argument("--api-key-env",default="TOWN_API_KEY")
    sub.add_argument("--model",default=os.getenv("TOWN_MODEL","local-model"))
    sub.add_argument("--model-revision",default="")
    sub.add_argument("--seeds",nargs="+",type=int,default=[701,702,703])
    sub.add_argument("--days",type=int,default=4)
    sub.add_argument("--cast",choices=tuple(CAST_NAMES),default="film")
    sub.add_argument("--memory",choices=("receipts","transcript"),default="receipts")
    sub.add_argument("--out",type=Path,required=True)
    sub.add_argument("--workers",type=int,choices=(1,2,3),default=3)
    sub.add_argument("--temperature",type=float,default=.8)
    sub.add_argument("--max-tokens",type=int,default=256)
    sub.add_argument("--num-ctx",type=int,default=8192,help="Native Ollama context limit.")
    sub.add_argument("--timeout",type=float,default=120)
    sub.add_argument("--response-format",choices=("schema","object","none"),default="schema")
    sub.add_argument("--thinking",choices=("off","on","default"),default="off")
    sub.add_argument("--omit-seed",action="store_true")
    return sub

def main():
    p=argparse.ArgumentParser(description=__doc__)
    subs=p.add_subparsers(dest="command",required=True)
    run_args(subs.add_parser("run",help="Sample or resume one or more roots."))
    rev=subs.add_parser("review",help="Summarize complete and partial imported runs without inference.")
    rev.add_argument("paths",nargs="+",type=Path)
    args=p.parse_args()
    if args.command=="review":
        for path in args.paths:
            print(json.dumps(metrics(json.loads(path.read_text())),ensure_ascii=False))
        return
    if not 1<=args.days<=20 or args.max_tokens<32 or args.timeout<=0:
        p.error("Use 1–20 days, at least 32 output tokens, and a positive timeout.")
    if args.backend!="fixture" and args.model=="local-model":
        p.error("Pass the model name advertised by the server in --model or TOWN_MODEL.")
    for seed in args.seeds:
        row=sample(args,seed)
        print(json.dumps(metrics(row),ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
