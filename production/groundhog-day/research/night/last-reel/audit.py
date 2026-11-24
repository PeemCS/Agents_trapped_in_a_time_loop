"""Reconstruct witnessed outcomes and intervene on individual physical choices."""
from collections import Counter
from itertools import product
import json
from pathlib import Path
import re

import scene

HERE=Path(__file__).resolve().parent
PATS={"film_or_performer":r"\b(?:groundhog day|bill murray|1993 (?:film|movie|comedy)|the movie|the film)\b",
      "recurrence":r"\b(?:time loop|repeating|reliving|same day|stuck|trapped|no escape)\b",
      "withdrawal_language":r"\b(?:give up|given up|giving up|what(?:'s| is) the point|no point|can(?:not|'t) (?:get out|escape)|tired of)\b"}
REST={"stay_in_bed","go_to_bed","sit_at_depot","sleep_at_terminal","wait_for_morning"}

def excerpts(turn):
    fields={"spoken":turn["decision"]["words"],"intention":turn["decision"]["intention"],
            "thinking":turn["attempts"][-1]["public_thinking"]}
    found=[]
    for channel,txt in fields.items():
        for label,pattern in PATS.items():
            for match in list(re.finditer(pattern,txt,re.I))[:3]:
                found.append({"channel":channel,"candidate":label,"match":match.group(),
                              "context":" ".join(txt[max(0,match.start()-90):match.end()+125].split()),"offset":match.start()})
    return found

def decs(turns):return {k:v["decision"] for k,v in turns.items()}

def changes(day):
    ms=decs(day["afternoon"]);ns=decs(day["evening"]);obs=day["ending"]
    targets=("delivered","dance","both_at_party","closed_clock","story_complete_clock")
    influences={k:[] for k in targets};tried=0;illegal=0
    for phase,role in product(("afternoon","evening"),scene.ROLES):
        src=ms if phase=="afternoon" else ns
        acts=scene.options(role,phase,day["afternoon_state"])
        for choice in acts:
            if choice==src[role]["action"]:continue
            m=ms.copy();n=ns.copy()
            (m if phase=="afternoon" else n)[role]={**src[role],"action":choice}
            before=scene.afternoon(m)
            if any(n[r]["action"] not in scene.options(r,"evening",before) for r in scene.ROLES):
                illegal+=1;continue
            result=scene.evening(n,before);tried+=1
            for key in targets:
                if result[key]!=obs[key]:
                    influences[key].append({"phase":phase,"role":role,"replace":choice,"outcome":result[key]})
    return {"legal_single_changes":tried,"incompatible_followup_skipped":illegal,"changes":influences}

def audit(filename):
    r=json.loads(filename.read_bytes());rid=filename.parent.name
    results=[];turns=[];first_release=None;history=[]
    for d in r["days"]:
        n=d["day"];a=decs(d["afternoon"]);b=decs(d["evening"]);state=scene.afternoon(a);end=scene.evening(b,state)
        if end!=d["ending"] or state!=d["afternoon_state"]:raise ValueError("Physical replay drift in "+rid)
        if end["delivered"] and first_release is None:first_release=n
        for t,phase in enumerate(("afternoon","evening")):
            tr=d[phase]["reporter"];sid=f"last-reel-{rid}-d{n:02d}-t{t:02d}-reporter"
            turns.append({"id":sid,"day":n,"phase":phase,"action":tr["decision"]["action"],"words":tr["decision"]["words"],
                          "intention":tr["decision"]["intention"],"hits":excerpts(tr)})
        result={"day":n,"reporter":[a["reporter"]["action"],b["reporter"]["action"]],"producer":[a["producer"]["action"],b["producer"]["action"]],
                "camera":[a["camera"]["action"],b["camera"]["action"]],"outcomes":end,"outside_receipt_already_existed":bool(history),
                "actual_rest":any(v["reporter"]["action"] in REST for v in (a,b)),"counterfactual":changes(d)}
        results.append(result)
        if end["delivered"]:history.append(n)
    if r.get("last_alarm"):
        tr=r["last_alarm"];turns.append({"id":f"last-reel-{rid}-d04-t02-reporter","day":4,"phase":"alarm","action":tr["decision"]["action"],
                     "words":tr["decision"]["words"],"intention":tr["decision"]["intention"],"hits":excerpts(tr)})
    return {"run":rid,"condition":r["condition"],"source_event_ids":r["source"]["events"],"status":r["status"],
            "first_sister_rule_wednesday_after_day":first_release,"days":results,"reporter_turns":turns}

def main():
    results=[audit(p) for p in sorted((HERE/"runs").glob("*/take.json"))]
    out={"method":"Replay both physical rules. For each lever, substitute one legal move with everyone else's actual choice held fixed. Skip an afternoon change if it makes the retained evening move illegal. Text hits are candidates for human or editorial review.","takes":results}
    (HERE/"outcomes.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    for r in results:print(r["run"],r["status"],len(r["days"]),r["first_sister_rule_wednesday_after_day"])

if __name__=="__main__":main()
