"""Versioned rehearsal with parallel speech/physical choices and a participant-owned bulletin."""
import argparse
import datetime
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import time

from inference import Fixture, OpenAIChat, OllamaChat, decide, fingerprint, validate
from town import atomic_json, exclusive, metrics, run_args as base_args
from world import ACTORS, CAST_NAMES, CLOCKS, memory_slot, pack, stable_seed
from world_v2 import initial, cue, resolve

ROOT=Path(__file__).resolve().parent
ENGINE_FILES=("v2.py","world_v2.py","town.py","world.py","inference.py")

def config(args, seed):
    return {"protocol":"town-night-2","code":fingerprint([p+":"+(ROOT/p).read_text() for p in ENGINE_FILES]),
            "seed":seed,"days":args.days,"backend":args.backend,"model":args.model if args.backend!="fixture" else "fixture",
            "model_revision":args.model_revision,"memory":args.memory,"cast":args.cast,"physical":args.physical,"ending":args.ending,
            "temperature":args.temperature,"max_tokens":args.max_tokens,"response_format":args.response_format,
            "thinking":args.thinking,"omit_seed":args.omit_seed,"num_ctx":args.num_ctx if args.backend=="ollama" else None}

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
            row={"version":2,"source":"injected_fixture" if args.backend=="fixture" else "live_model","seed":seed,
                 "protagonist":names["reporter"],"cast_names":names,"model":params["model"],"memory":args.memory,
                 "cast_condition":args.cast,"physical":args.physical,"ending":args.ending,"configuration":params,"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
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
            if args.backend=="fixture": backend=V2Fixture()
            elif args.backend=="ollama": backend=OllamaChat(args.base_url,args.model,args)
            else: backend=OpenAIChat(args.base_url,args.model,args)
        history=[memory_slot(e) for e in row["events"]]
        state=row["checkpoint"] or initial()
        def save_attempt(key,actor,slot,a,repair):
            name=f"{time.time_ns()}-{key[:16]}.json"
            rec={"config_id":fingerprint(params),"request_id":key,"role":actor,"slot":list(slot),"repair":repair,"attempt":a}
            atomic_json(reqdir/name,rec)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            while len(row["events"])<args.days*4:
                index=len(row["events"]);day=index//4+1;tick=index%4
                if tick==0: state=initial()
                calls={};results={}
                for actor in ACTORS:
                    turns,actions=cue(actor,state,tick,history,args.memory,seed,names,args.physical,args.ending)
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
                after,by_actor=resolve(seed,day,tick,state,decisions,names,args.physical,args.ending)
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

class V2Fixture:
    def respond(self,actor,slot,messages,actions,seed):
        day,tick=slot
        guide={"reporter":["leave_pencil_mark","go_to_depot","take_coach_to_Pittsburgh","call_live_report"],
               "producer":["go_to_studio","file_forecast","air_forecast","patch_reporter_line"],
               "camera":["look_around","watch_ceremony","film_cornet_player","send_camera_take"]}
        act=guide[actor][tick]
        if act not in actions:act="spend_time_here"
        obs=json.loads(messages[1]["content"])
        sig="invite_reporter" if actor=="producer" and tick==0 else "accept_assignment" if actor=="reporter" and tick==1 else ""
        if sig not in obs["optional_assignment_signals"]:sig=""
        words="The phone works from Pittsburgh." if actor=="reporter" and tick==3 else ""
        return json.dumps({"action":act,"words":words,"intention":"","detail":sig}),{"latency_s":0,"usage":{},"finish_reason":"stop","response_model":"v2-fixture"}

def run_args(p):
    # Reuse the original CLI options and keep v2 intervention names explicit.
    base_args(p)
    item=next(a for a in p._actions if a.dest=="memory")
    item.choices=("wakes","flat")
    p.set_defaults(memory="wakes")
    p.add_argument("--physical",choices=("move","talk-action"),default="move")
    p.add_argument("--ending",choices=("bulletin","ordinary"),default="bulletin")
    return p

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="command",required=True)
    run_args(sub.add_parser("run"))
    args=p.parse_args()
    if not 1<=args.days<=20 or args.max_tokens<32 or args.timeout<=0:p.error("Use 1–20 days and valid generation limits.")
    if args.backend!="fixture" and args.model=="local-model":p.error("Pass the model name advertised by the server.")
    for seed in args.seeds:
        row=sample(args,seed)
        print(json.dumps(metrics(row),ensure_ascii=False),flush=True)

if __name__=="__main__": main()
