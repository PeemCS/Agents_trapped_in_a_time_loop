"""Audit every complete V1 take, aggregate by the experimental unit and keep a quote ledger."""
import argparse
import hashlib
import itertools
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"story"))
from audit import inspect

TRAVEL = re.compile(r"\b(coach|depot|bus|pittsburgh)\b", re.I)
CULTURE = re.compile(r"\b(movies?|films?|cinema|murray|macdowell|connors|ryerson|ramis|ground\s*hog\s+day|punxsutawney|deja vu|déjà vu)\b",re.I)


def make_row(p):
    row=json.loads(p.read_bytes())
    audit=inspect(p)
    if audit["replay_errors"]:raise ValueError(str((p,audit["replay_errors"])))
    m=audit["metrics"];rt=audit["runtime"];ev=row["events"]
    culture=[{"id":e["id"],"speaker":e["actor"],"role":e["role"],"words":e["decision"]["words"]} for root in ev for e in [root,*root["cast"]]
             if CULTURE.search(e["decision"]["words"])]
    actions=Counter(e["decision"]["action"] for e in ev);moves=sum(e["origin"]!=e["place"] for e in ev)
    data={"family":p.parents[1].name,"cast":row["cast_condition"],"memory":row["memory"],"seed":row["seed"],
          "path":str(p.relative_to(HERE.parent)),"sha256":audit["sha256"],"model":row["model"],
          "slots":len(ev),"actors":m["cast_decisions"],"calls":rt["committed_generation_attempts"],"repairs":rt["committed_repairs"],
          "cache_reuses":rt["reused_slots"],"prompt_tokens":rt["recorded_prompt_tokens"],"output_tokens":rt["recorded_completion_tokens"],
          "trips":m["physical_coach_trips"],"returns":m["confirmed_next_wakes_after_pittsburgh"],
          "moves":moves,"locations":len(m["reporter_places"]),"stationary_travel_talk":sum(e["origin"]==e["place"] and
                    bool(TRAVEL.search(e["decision"]["words"])) for e in ev),
          "talk_actions":sum(n for a,n in actions.items() if a.startswith("talk_to_")),
          "sister_calls":actions["call_sister"],"marked_sill":actions["leave_pencil_mark"],
          "culture_candidates":culture,"failed_audit_checks":len(audit["replay_errors"])}
    return data


def aggregate(rows):
    fields=["slots","actors","calls","repairs","cache_reuses","prompt_tokens","output_tokens","trips","returns","moves",
            "stationary_travel_talk","talk_actions","sister_calls","marked_sill","failed_audit_checks"]
    out={k:sum(r[k] for r in rows) for k in fields}
    out.update({"takes":len(rows),"distinct_start_seeds":len({r["seed"] for r in rows}),
                "takes_with_trip":sum(r["trips"]>0 for r in rows),"takes_with_payoff":sum(r["returns"]>0 for r in rows),
                "takes_with_sill_mark":sum(r["marked_sill"]>0 for r in rows),
                "median_unique_reporter_locations":statistics.median(r["locations"] for r in rows)})
    return out


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("families",nargs="+",type=Path);ap.add_argument("--out",type=Path,required=True);a=ap.parse_args()
    rows=[];paused=[]
    for family in a.families:
        for p in sorted(family.glob("*/seed-*.json")):
            if json.loads(p.read_bytes())["status"]!="complete":paused.append(str(p));continue
            rows.append(make_row(p.resolve()))
    groups=defaultdict(list)
    for r in rows:groups[(r["family"],r["cast"],r["memory"])].append(r)
    counts={"/".join(k):aggregate(rs) for k,rs in groups.items()}
    pairs={}
    for fam in sorted({r["family"] for r in rows}):
        sub=[r for r in rows if r["family"]==fam]
        for other in sorted({r["memory"] for r in sub}):
            d={r["seed"]:{v:next((z for z in sub if z["seed"]==r["seed"] and z["memory"]==other and z["cast"]==v),None) for v in ("film","neutral")} for r in sub}
            pairs[fam+"/"+other]={str(s):{k:pair["film"][k]-pair["neutral"][k] for k in ("returns","trips","moves","talk_actions")}
                                    for s,pair in d.items() if all(pair.values())}
    output={"partial_excluded":paused,"totals":aggregate(rows),"cells":counts,"paired_film_minus_neutral_by_seed":pairs,
            "takes":rows,"notes":"Each arm is a take from one of four shared base seeds. Slots, three agents and decoding replicates are nested. Culture candidates are unclassified high-recall keywords, not recognition. Stationary travel talk includes plans for a future trip, and need not be a contradiction."}
    a.out.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"complete":len(rows),"cells":{k:(v["takes"],v["takes_with_payoff"]) for k,v in counts.items()},
                      "repairs":output["totals"]["repairs"],"checked":output["totals"]["actors"]}))


if __name__=="__main__":
    main()
