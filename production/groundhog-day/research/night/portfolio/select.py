"""Choose four distinct, source-backed scenes from the 24 actual bulletin evenings."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import re

HERE=Path(__file__).resolve().parent
NIGHT=HERE.parent
STOCK=re.compile(r"\b(?:i hear you|that(?:’s|'s| is) valid|your feelings are valid|thank you for sharing)\b",re.I)
WEIGHTS={"channel":4,"city":1,"reporter":2,"had_camera_reel":1,"after_wake":2,"earlier_work":2,"delivered":1}

def enumerate_scenes():
    causal=json.loads((NIGHT/"editor/heldout-v2-causality.json").read_bytes())
    scenes=[]
    for world in causal["per_world"]:
        path=NIGHT/"takes/heldout/v2"/("seed-"+str(world["seed"])+".json")
        raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==world["source_sha256"]
        trace=json.loads(raw)
        for rec in world["evenings"]:
            idx=4*rec["day"]-1;row=trace["events"][idx];b=row["world_after"]["bulletin"]
            assert row["id"]==rec["event"] and b["source_ids"]==rec["actual_sources"]
            others=[row,*row["cast"]];people={a["role"]:a for a in others}
            next_wake=(idx+1<len(trace["events"]) and row["place"]=="Pittsburgh" and trace["events"][idx+1]["origin"]=="inn")
            power={role:alternatives["changes_feed"] for role,alternatives in rec["one_actor_at_a_time"].items()}
            stock=[match.group() for a in others for match in STOCK.finditer(a["decision"]["words"])]
            fs={"channel":b["channel"],"city":row["place"]=="Pittsburgh","reporter":row["decision"]["action"],
                "had_camera_reel":bool(row["world_before"]["camera_footage"]),"after_wake":bool(next_wake),
                "earlier_work":rec["selected_earlier_recorded_work"],"delivered":tuple(sorted(b["delivered_assignments"]))}
            competing=bool(b["delivered_assignments"]) and b["channel"] in ("producer_live","empty_selected_return","station_ident")
            parts={"earlier_work":2*int(fs["earlier_work"]),"physical_return":2*int(next_wake),
                   "competing_contribution":2*int(competing),"second_actor_with_leverage":int(power["reporter"] or power["camera"]),
                   "spoken_cliche":-min(1,len(stock))}
            scenes.append({"id":f'{world["seed"]}-d{rec["day"]:02d}',"seed":world["seed"],"day":rec["day"],"source_sha256":world["source_sha256"],
                           "event":row["id"],"source_ids":b["source_ids"],"features":fs,"power":power,"score_parts":parts,
                           "score":sum(parts.values()),"stock_matches":stock,"line":b["spoken"]})
    return scenes

def similarity(a,b):
    return sum(w for k,w in WEIGHTS.items() if a["features"][k]==b["features"][k])/sum(WEIGHTS.values())

def pick(rows,n,strength):
    picked=[];history=[]
    while len(picked)<n:
        scored=[]
        for row in rows:
            if row in picked:continue
            repeat=max((similarity(row,prev) for prev in picked),default=0)
            quality=row["score"]/7
            scored.append((quality-strength*repeat,quality,row["id"],row,repeat))
        _,_,_,best,repeated=sorted(scored,key=lambda s:(-s[0],-s[1],s[2]))[0]
        picked.append(best);history.append({"scene":best["id"],"score":best["score"],"nearest_previous_similarity":round(repeated,4),"channel":best["features"]["channel"]})
    return history

def main():
    rows=enumerate_scenes();assert len(rows)==24
    out={"posthoc":True,"selection_unit":"one evening, with same-world setup and next morning if applicable",
         "axes":WEIGHTS,"scores":"Earlier physical source on air +2; next city-to-hotel reset +2; submitted contribution bypassed by switcher +2; another crew member could change broadcast +1; explicit stock acknowledgement −1 (max). Scores describe edit opportunities.",
         "quality_only":pick(rows,4,0),"variety_plus_quality":pick(rows,4,.75),"stock_phrase_hits":sum(len(r["stock_matches"]) for r in rows),
         "scenes":rows}
    (HERE/"selection.json").write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
    for k in ("quality_only","variety_plus_quality"):
        print(k,[(r["scene"],r["channel"]) for r in out[k]])

if __name__=="__main__":main()
