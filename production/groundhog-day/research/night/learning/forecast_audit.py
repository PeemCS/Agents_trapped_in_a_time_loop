"""Measure how the online calendar/location predictor changes on observed mornings, without giving it private state."""
import argparse
import datetime
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"story"))
from world import memory_slot
from surprise_memory import Forecaster, Overnight, witnessed


def summarize(m):
    if not m:return {"observations":0}
    return {"observations":len(m),"learned_mean_bits":round(mean(t[1] for t in m),4),
            "ordinary_fixed_mean_bits":round(mean(t[2] for t in m),4)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("families",nargs="+",type=Path);p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    families={};checks=[]
    for family in a.families:
        allrows=[];first=[];last=[];slices=defaultdict(list)
        for path in sorted(family.glob("*/seed-*.json")):
            data=json.loads(path.read_bytes())
            if data["status"]!="complete":continue
            events=data["events"];rows=witnessed([memory_slot(e) for e in events])
            assert len(rows)==len(events)//4-1,(path,len(rows))
            allrows.extend(rows);first.extend(rows[:1]);last.extend(rows[-1:])
            for q in rows:slices[q[0].evening_place+" → "+q[0].morning_place].append(q)
        families[family.name]={"all":summarize(allrows),"first_night":summarize(first),"final_observed_night":summarize(last),
                               "route":{k:summarize(v) for k,v in sorted(slices.items())}}
    d=datetime.date(2016,2,2)
    for label,repeat,switch in [("ordinary seven-day stay",False,False),("repeating calendar, same location",True,False),("repeating calendar, city to hotel",True,True)]:
        model=Forecaster();rows=[]
        for i in range(6):
            new=d if repeat else d+datetime.timedelta(days=1);here="Pittsburgh" if switch else "inn"
            n=Overnight(str(i),str(i+1),here,"inn",d,new)
            l,f=model.observe(n);rows.append({"learned_bits":round(l,4),"fixed_bits":round(f,4)});d=new
        checks.append({"fixture":label,"nights":rows})
    a.out.write_text(json.dumps({"scope":"Prequential paired date/place log loss in bits, computed before seeing each wake with a fresh predictor per run. Each observed location and original-source dawn date comes from the reporter's observations. The real engine always resets to Tuesday. Synthetic controls exercise what would happen in ordinary calendar conditions. This measures world learning, not an actor's emotional state.","families":families,"technical_controls":checks},indent=2)+"\n")
    print(json.dumps({k:x["all"] for k,x in families.items()}))

if __name__=="__main__":main()
