"""Rebuild an overnight town take, audit its witnesses and emit a compact presentation copy."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
from statistics import median

from inference import fingerprint, validate
from town import atomic_json, metrics
import world_v2
from world import ACTORS, CAST_NAMES, CLOCKS, cue, initial_state, memory_slot, pack, resolve, stable_seed

TITLE=re.compile(r"\bgroundhog\s+day\b",re.I)
SPECIFIC=re.compile(r"\b(?:bill\s+murray|phil\s+connors|punxsutawney\s+phil|andie\s+macdowell|harold\s+ramis|ned\s+ryerson)\b",re.I)
CINEMA=re.compile(r"\b(?:this|that|a|the) (?:movie|film)\b|\b(?:movie|film) (?:where|about|called|I (?:saw|watched))\b",re.I)
REPEAT=re.compile(r"\b(?:time\s*loop|reliv(?:e|ing)|same (?:day|morning|Tuesday)|yesterday (?:was|is) Tuesday|repeating (?:again|itself|day)|keeps? repeating|woke (?:up )?(?:here )?again)\b",re.I)

def source_bytes(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def cues(text):
    return [tag for tag,pat in (("holiday_or_title",TITLE),("specific_name",SPECIFIC),
                                ("cinema_wording",CINEMA),("recurrence_wording",REPEAT)) if pat.search(text)]

def events_at(lead):
    return [lead,*lead["cast"]]

def final_evening_signature(row):
    """Independent editorial classification of the last fully observed evening, including mundane outcomes."""
    if row["status"]!="complete" or not row["events"] or row["events"][-1]["clock"]!=CLOCKS[-1]:
        return {"status":"unresolved_recording"}
    e=row["events"][-1];s=e["world_after"]
    sig={"status":"complete_evening","reporter_location":s["positions"]["reporter"],
            "forecast":"aired" if s["aired"] else "filed" if s["weather_tape"] else "unfiled",
            "camera_footage":s["camera_footage"] or "unused",
            "sister_called":s["called_sister"],"heard_band_roles":sorted(s["heard_band"]),
            "ending_event_ids":[a["id"] for a in events_at(e)]}
    if s.get("bulletin") is not None:sig["bulletin"]=s["bulletin"]
    return sig

def inspect(path):
    r=json.loads(path.read_text())
    use_v2=r.get("version")==2
    init=world_v2.initial if use_v2 else initial_state
    seed=r["seed"];names=CAST_NAMES[r["cast_condition"]];history=[];state=init()
    cfg=r["configuration"]
    seen_ids=set();repairs=0;tokens=Counter();calls=cache=0;lats=[];flags=[];candidates=[];cache_index={}
    def check(test, message):
        if not test: flags.append(message)
    check(r["cast_names"]==names, "cast mapping differs from declared condition")
    check(r["protagonist"]==names["reporter"],"reported protagonist differs from cast mapping")
    check(len(r["events"])<=r["configuration"]["days"]*4,"more slots than declared shooting horizon")
    for index,root in enumerate(r["events"]):
        day=index//4+1;tick=index%4
        if tick==0:state=init()
        ev=events_at(root);roles=[e["role"] for e in ev]
        if roles!=list(ACTORS):
            flags.append(f"slot {index} cast role order {roles}");break
        check(root["world_before"]==state,f"{root['id']} world before")
        decisions={e["role"]:e["decision"] for e in ev}
        try:
            after,resolved=(world_v2.resolve(seed,day,tick,state,decisions,names,r["physical"],r["ending"])
                            if use_v2 else resolve(seed,day,tick,state,decisions,names))
        except (KeyError,ValueError) as ex:
            flags.append(f"slot {index} could not resolve: {ex}");break
        check(after==root["world_after"],f"{root['id']} world after")
        for e in ev:
            role=e["role"];ident=e["id"];inf=e["inference"]
            check(ident not in seen_ids,f"duplicate event {ident}");seen_ids.add(ident)
            for field in ("id","day","actor","role","clock","origin","place","effect","observed","observation_sources"):
                check(e[field]==resolved[role][field],f"{ident} mismatch in {field}")
            if use_v2:
                for field in ("radio_heard","signal_status","bulletin_result"):
                    check(e.get(field)==resolved[role].get(field),f"{ident} invalid {field}")
                if cfg["protocol"]=="town-surprise-1":
                    from surprise_memory import cue as prompt_builder
                elif cfg["protocol"]=="town-monitored-1":
                    import persona_cue
                    prompt_builder=persona_cue.builder(cfg["persona"])
                elif cfg["protocol"]=="town-credentials-1":
                    from badge_cues import cue as prompt_builder
                else:
                    prompt_builder=world_v2.cue
                turns,actions=prompt_builder(role,state,tick,history,r["memory"],seed,names,r["physical"],r["ending"])
            else:turns,actions=cue(role,state,tick,history,r["memory"],seed,names)
            check(turns==inf["messages"],f"{ident} actor-visible memory or role diverges from replay")
            check(actions==inf["legal_actions"],f"{ident} displayed menu diverges")
            expected_seed=stable_seed(seed,role,day if role=="reporter" else 0,tick)
            check(expected_seed==inf["sampling_seed"],f"{ident} unexpected decoding seed")
            key=fingerprint([r["model"],cfg["model_revision"],turns,actions,expected_seed,cfg["temperature"],
                             cfg["max_tokens"],cfg["thinking"],cfg["response_format"],cfg["omit_seed"]])
            check(key==inf["request_id"],f"{ident} request fingerprint mismatch")
            if inf["cache_hit"]:
                cache+=1;prior=cache_index.get(inf["request_id"])
                check(prior is not None and prior==e["decision"],f"{ident} cache source missing or changed")
            else:
                attempts=inf["attempts"]
                calls+=len(attempts);repairs+=max(0,len(attempts)-1)
                for a in attempts:
                    usage=a.get("usage") or {}
                    for k in ("prompt_tokens","completion_tokens"): 
                        if isinstance(usage.get(k),int): tokens[k]+=usage[k]
                    if isinstance(a.get("latency_s"),(int,float)):lats.append(a["latency_s"])
                check(bool(attempts),f"{ident} fresh slot without provider attempts")
                if attempts:
                    check(attempts[0]["messages"]==turns,f"{ident} executed prompt differs from recorded request")
                    try: raw_decision=validate(attempts[-1]["response"],actions)
                    except ValueError: raw_decision=None
                    check(raw_decision==e["decision"],f"{ident} committed choice differs from provider response")
            cache_index.setdefault(inf["request_id"],e["decision"])
            for field in ("words","intention","detail"):
                quote=e["decision"][field];matches=cues(quote)
                if matches:
                    # Private self-directed intentions are retained for audit but are not film dialogue.
                    visible=[]
                    for m in inf["messages"]:
                        for line in m["content"].splitlines():
                            hit=cues(line)
                            if hit:
                                visible.append({"role":m["role"],"cues":hit,"line":line.strip()})
                    candidates.append({"id":ident,"actor":e["actor"],"field":field,"cues":matches,
                                       "utterance":quote,"actor_visible_candidates_before_decision":visible})
        history.append(memory_slot(root));state=after
    m=metrics(r);stats={"committed_generation_attempts":calls,"committed_repairs":repairs,"reused_slots":cache,
                       "recorded_prompt_tokens":tokens["prompt_tokens"],"recorded_completion_tokens":tokens["completion_tokens"]}
    if lats:
        lats.sort();stats.update({"request_median_s":median(lats),"request_p95_s":lats[math.ceil(.95*len(lats))-1],
                                  "sum_request_seconds":round(sum(lats),3)})
    journal=path.parent/f".requests-{seed}"
    stats["disk_attempt_records"]=sum(1 for _ in journal.glob("*.json")) if journal.exists() else None
    return {"path":path.name,"sha256":source_bytes(path),"status":r["status"],"source":r["source"],"seed":seed,
            "cast_condition":r["cast_condition"],"memory":r["memory"],"model":r["model"],"metrics":m,
            "runtime":stats,"final_evening":final_evening_signature(r),"replay_errors":flags,"candidate_quote_count":len(candidates),"candidate_quotes":candidates}

def compact_event(root):
    """Project one committed lead/cast slot. This function performs no I/O and does not mutate its input."""
    cast=[]
    for e in events_at(root):
        d=e["decision"]
        entry={k:e[k] for k in ("id","day","clock","role","actor","origin","place","effect")}
        entry["decision"]={"action":d["action"],"words":d["words"]}
        if d["action"]=="try_something": entry["decision"]["detail"]=d["detail"]
        receipt=e["receipt"]
        entry["receipt"]={"from":receipt["from"],"to":receipt["to"],"observation_ids":list(receipt["observation_ids"])}
        cast.append(entry)
    lead=cast[0];lead["cast"]=cast[1:]
    visible_props=("marked","weather_tape","aired","band_recorded","called_sister","dishes","camera_battery","camera_footage")
    for source,destination in (("world_before","visible_before"),("world_after","visible_after")):
        if source in root:
            lead[destination]={k:root[source][k] for k in visible_props if k in root[source]}
    bulletin=root.get("world_after",{}).get("bulletin")
    if bulletin is not None:lead["bulletin"]=dict(bulletin)
    return lead

def pack_run(row, source_sha256=None):
    """Project a partial or complete run. A caller can attach the immutable source file hash once sealed."""
    data={"version":1,"format":"town-replay","source":row["source"],"seed":row["seed"],
          "protagonist":row["protagonist"],"cast_names":dict(row["cast_names"]),"cast_condition":row["cast_condition"],
          "memory":row["memory"],"model":row["model"],"status":row["status"],
          "events":[compact_event(e) for e in row["events"]]}
    if row.get("version")==2:
        data["simulation_version"]=2;data["physical"]=row["physical"];data["ending"]=row["ending"]
    if row.get("municipality"):
        data["municipality"]=row["municipality"]
    if source_sha256 is not None: data["source_sha256"]=source_sha256
    return data

def compact(path):
    return pack_run(json.loads(path.read_text()),source_bytes(path))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("take",type=Path);p.add_argument("--report",type=Path);p.add_argument("--public-replay",type=Path)
    args=p.parse_args()
    paths=[x.resolve() for x in (args.take,args.report,args.public_replay) if x is not None]
    if len(set(paths))!=len(paths):p.error("Input, report and presentation output must be distinct files.")
    report=inspect(args.take)
    if args.report:atomic_json(args.report,report)
    if report["replay_errors"]:
        print(json.dumps(report["replay_errors"],indent=2));raise SystemExit(1)
    if args.public_replay:atomic_json(args.public_replay,compact(args.take))
    print(json.dumps({k:v for k,v in report.items() if k!="candidate_quotes"},ensure_ascii=False,indent=2))

if __name__=="__main__": main()
