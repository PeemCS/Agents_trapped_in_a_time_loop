"""Audit and compare matched independent roots from the two preregistered shooting protocols."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re

from audit import inspect
from town import atomic_json

FROZEN_V1 = "b56465788fca071f0c877e7ba36cb1c2ce516eb0f4c92d78e1ec324acc5cbd38"
FROZEN_V2 = "6c102f72ff164156bbebd800285ecad995cf372a59c44a66df0e5a39b1cf70e3"

COACH_WORDS=re.compile(r"\b(?:I(?:'m| am) (?:boarding|taking|catching|getting on)|I(?:'ve| have) (?:boarded|caught)) (?:the |my |this |that |one o'clock |afternoon |Pittsburgh )*(?:bus|coach)\b",re.I)

def root_measure(path):
    row=json.loads(path.read_text());a=inspect(path)
    if a["replay_errors"]:raise ValueError(f"Unverified source {path}: {a['replay_errors'][:2]}")
    if row["status"]!="complete":raise ValueError(f"Partial source {path}")
    events=row["events"]; opp=Counter();channels=Counter();bids=Counter()
    claims=[];returned=[]
    for i,e in enumerate(events):
        decision=e["decision"];words=decision["words"].replace("’","'")
        if COACH_WORDS.search(words):
            claims.append({"id":e["id"],"words":decision["words"],"committed":decision["action"]})
        if i and e["clock"]==events[0]["clock"] and events[i-1]["place"]=="Pittsburgh":
            obs=e["inference"]["messages"][1]["content"]
            returned.append({"id":e["id"],"earned_sleep_place_in_context":bool(re.search(r"fell asleep in Pittsburgh",obs,re.I)),
                             "next_action":decision["action"],"next_words":decision["words"]})
        if e["clock"]!="7:00 pm" or "bulletin" not in e["world_after"]:continue
        state=e["world_after"];bulletin=state["bulletin"]
        if not bulletin:continue
        channels[bulletin["channel"]]+=1
        cast={x["role"]:x for x in (e,*e["cast"])}
        for target,contribution in [("reporter","call_live_report"),("camera","send_camera_take")]:
            opp[target+"_day_opportunities"]+=1
            task=state["assignments"].get(target)
            offered=bool(task);accepted=bool(task and task["status"]=="accepted")
            sent=cast[target]["decision"]["action"]==contribution
            aired=bulletin["source_role"]==target and bulletin["channel"] in ("live_report","camera_take")
            for kind,condition in [("offered",offered),("accepted",accepted),("declined",bool(task and task["status"]=="declined")),
                                   ("sent",sent),("accepted_and_sent",accepted and sent),("actually_aired",aired),
                                   ("accepted_sent_and_aired",accepted and sent and aired)]:
                bids[target+"_"+kind]+=int(condition)
    return row,{"sha256":a["sha256"],"seed":row["seed"],"version":row["version"],"model":row["model"],
                "runtime":a["runtime"],"physical":a["metrics"],"last_evening":a["final_evening"],
                "all_evening_channels":dict(channels),"handoffs":{**dict(opp), **dict(bids)},
                "morning_after_pittsburgh":returned,
                "immediate_sounding_coach_lines_for_review":claims,
                "candidate_references":[{k:x[k] for k in ("id","actor","field","cues","utterance","actor_visible_candidates_before_decision")} for x in a["candidate_quotes"]]}

def compare(base_dir,new_dir,seeds,horizon,strict_sources=True):
    pairs=[];endings=Counter()
    for seed in seeds:
        base,ma=root_measure(base_dir/f"seed-{seed}.json")
        new,mb=root_measure(new_dir/f"seed-{seed}.json")
        cfg=base["configuration"];cfg2=new["configuration"]
        if cfg["code"] != FROZEN_V1 or cfg2["code"] != FROZEN_V2:
            raise ValueError(f"Unexpected sampler revision on seed {seed}")
        if len(base["events"]) != horizon*4 or len(new["events"]) != horizon*4:
            raise ValueError(f"Incomplete shooting horizon on seed {seed}")
        if cfg["cast"] != "film":
            raise ValueError(f"Wrong cast condition on seed {seed}")
        for k in ("seed","days","cast","backend","model","model_revision","temperature","max_tokens","response_format","thinking","omit_seed","num_ctx"):
            if cfg.get(k)!=cfg2.get(k):raise ValueError(f"Unmatched {k} on seed {seed}")
        if seed!=base["seed"] or seed!=new["seed"] or cfg["days"]!=horizon:raise ValueError(f"Root/horizon mismatch {seed}")
        if strict_sources and (base["source"]!="live_model" or new["source"]!="live_model"):raise ValueError(f"Non-live source {seed}")
        if base["version"]!=1 or base["memory"]!="receipts" or new["version"]!=2 or new["memory"]!="wakes" or new["ending"]!="bulletin" or new["physical"]!="move":
            raise ValueError(f"Wrong preregistered arms on seed {seed}")
        m1=ma["physical"];m2=mb["physical"]
        diffs={k:m2[k]-m1[k] for k in ("physical_coach_trips","confirmed_next_wakes_after_pittsburgh","reporter_spoken",
                                        "reporter_distinct_lines","response_reuses")}
        diffs["distinct_reporter_locations"]=len(m2["reporter_places"])-len(m1["reporter_places"])
        settlement=mb["last_evening"]["bulletin"]
        endings[settlement["channel"]]+=1
        pairs.append({"seed":seed,"baseline":ma,"variant":mb,"variant_minus_baseline":diffs})
    n=len(pairs)
    entropy=-sum((count/n)*math.log2(count/n) for count in endings.values()) if n else None
    return {"study":"heldout-v2","roots":seeds,"days":horizon,"source_class":"live_model" if strict_sources else "fixture-comparison-test",
            "final_evening_channel_counts":dict(endings),"empirical_final_channel_entropy_bits":entropy,
            "warning":"Seed-level descriptive paired comparison of a bundled change. The film-recognition and travel-claim hits are candidates for human review, not positive labels.",
            "pairs":pairs}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline",type=Path,required=True);p.add_argument("--variant",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True);p.add_argument("--days",type=int,default=6)
    p.add_argument("--seeds",nargs="+",type=int,default=[711,712,713,714])
    args=p.parse_args()
    if len(args.seeds)!=len(set(args.seeds)):p.error("Specify unique root seeds.")
    inputs={ (source/f"seed-{seed}.json").resolve() for source in (args.baseline,args.variant) for seed in args.seeds }
    if args.out.resolve() in inputs:p.error("The summary must use a separate output file.")
    data=compare(args.baseline,args.variant,args.seeds,args.days)
    atomic_json(args.out,data)
    print(json.dumps({"roots":data["roots"],"final_evening_channel_counts":data["final_evening_channel_counts"],
                      "empirical_final_channel_entropy_bits":data["empirical_final_channel_entropy_bits"],
                      "per_root_differences":[[pa["seed"],pa["variant_minus_baseline"]] for pa in data["pairs"]]},indent=2))

if __name__=="__main__":main()
