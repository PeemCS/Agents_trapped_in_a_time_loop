"""Compare matched whole takes and borrowed-checkpoint reaction probes."""
from collections import Counter,defaultdict
import json
from pathlib import Path
import re
from statistics import median

HERE=Path(__file__).resolve().parent
NIGHT=HERE.parent
CULTURE=re.compile(r"\b(?:groundhog day|bill murray|andi[e]? macdowell|1993 (?:movie|film)|the movie|the film|motion picture)\b",re.I)
LOOP=re.compile(r"\b(?:(?:time|in a|this) loop|same (?:Tuesday|day) again|(?:back|here) again|reliv(?:e|ing)|trapped)\b",re.I)

def hit(line,expr):
    return [{"text":m.group(),"around":" ".join(line[max(0,m.start()-64):m.end()+82].split())} for m in expr.finditer(line)]

def take(file):
    r=json.loads(file.read_bytes());events=r["events"]
    if r["status"]!="complete":return None
    rides=[i for i,e in enumerate(events) if e["decision"]["action"]=="take_coach_to_Pittsburgh"]
    returns=[events[i+2]["id"] for i in rides if i+2<len(events) and events[i+1]["place"]=="Pittsburgh" and events[i+2]["origin"]=="inn" and events[i+2]["clock"]=="6:00 am"]
    receipts=Counter();lex=[]
    for e in events:
        q=json.loads(e["inference"]["messages"][1]["content"])
        rows=q.get("remembered_overnight_observations",[])
        if rows:receipts["lead_turns_with_retrieved_observation"]+=1
        if any("Pittsburgh" in x["last_evening"] and "inn" in x["next_thing_you_saw"] for x in rows):receipts["lead_turns_with_city_to_inn"]+=1
        for a in [e,*e["cast"]]:
            d=a["decision"]
            for channel in ("words","intention"):
                matches=hit(d[channel],CULTURE)+hit(d[channel],LOOP)
                if matches:lex.append({"event":a["id"],"role":a["role"],"channel":channel,"text":d[channel],"matches":matches})
    return {"seed":r["seed"],"cast":r["cast_condition"],"physical_trips":len(rides),"verified_payoffs":len(returns),"payoff_ids":returns,
            "sister_calls":sum(e["decision"]["action"]=="call_sister" for e in events),"places":sorted({e["place"] for e in events}),
            "final_channel":events[-1]["world_after"]["bulletin"]["channel"],"retrieval":dict(receipts),"candidates":lex}

def probes():
    rows=[]
    for file in sorted((HERE/"deliberation").glob("7??-96?-*.json")):
        x=json.loads(file.read_bytes())
        d=x["decision"] or {};t=x["public_thinking"]
        rows.append({"file":file.name,"world":x["world"],"seed":x["decoding_seed"],"on":x["think"],"valid":x["decision"] is not None,
                     "stop":x["end"],"action":d.get("action"),"words":d.get("words"),"seconds":x["wall_s"],"tokens":x["tokens"],
                     "emitted_character_count":len(t),"thinking_candidates":hit(t,CULTURE)+hit(t,LOOP),
                     "spoken_candidates":hit(d.get("words",""),CULTURE)+hit(d.get("words",""),LOOP)})
    return rows

def main():
    cohorts={}
    for key,folder in [("neutral_badges","badges/neutral"),("film_badges","badges/film"),("film_badges_with_retrieval","surprise/film")]:
        results=[v for f in sorted((NIGHT/"takes"/folder).glob("seed-*.json")) if (v:=take(f))]
        cohorts[key]={"runs":len(results),"rides":sum(x["physical_trips"] for x in results),"payoffs":sum(x["verified_payoffs"] for x in results),"by_seed":results}
    notes=[]
    for f in sorted(HERE.glob("memo-*.jsonl")):
        for line in f.read_text().splitlines():
            r=json.loads(line);t=r["memo"]
            notes.append({"model":r["model"],"cast":r["cast"],"mem":r["has_memory"],"seed":r["seed"],"stop":r["stop"],
                             "marks":hit(t,CULTURE)+hit(t,LOOP),"literal_silence":not t.strip().strip('"').strip(),"memo":t})
    samples=probes();stats={}
    for on in (False,True):
        a=[r for r in samples if r["on"]==on]
        stats["on" if on else "off"]={"n":len(a),"valid":sum(r["valid"] for r in a),"stops":dict(Counter(r["stop"] for r in a)),
                      "median_seconds":median(r["seconds"] for r in a) if a else None,"median_tokens":median(r["tokens"] for r in a) if a else None}
    quizfile=HERE/"deliberation/capability-quiz.json"
    out={"unit":"Three paired whole-world roots for credential and retrieval treatments. Reaction draws reuse four eligible independent root groups with repeated sampling. Keyword matches are only review candidates.",
         "cohorts":cohorts,"probes":samples,"probe_summary":stats,"memos":notes,
         "quiz":[{"model":r["model"],"seed":r["seed"],"answer":r["answer"]} for r in json.loads(quizfile.read_bytes())] if quizfile.exists() else []}
    (HERE/"results.json").write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
    for k,v in cohorts.items():print(k,v["runs"],v["rides"],v["payoffs"])
    print("reaction draws",len(samples),"memos",len(notes),"quiz",len(out["quiz"]))

if __name__=="__main__":main()
