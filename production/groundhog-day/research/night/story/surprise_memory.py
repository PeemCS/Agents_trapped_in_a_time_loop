"""Recurrence memory selected by causal prequential surprise, using the lead's own scene observations."""
import datetime
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass

import badge_cues
from world import CLOCKS, PLACES

DATE=re.compile(r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), ([A-Z][a-z]+ \d{1,2}, \d{4})")
STAMP="%B %d, %Y"


def heard_date(lines):
    for line in lines:
        match=DATE.search(line)
        if match:return datetime.datetime.strptime(match.group(1),STAMP).date()
    return None


@dataclass(frozen=True)
class Overnight:
    evening_id:str
    wake_id:str
    evening_place:str
    morning_place:str
    evening_date:datetime.date
    morning_date:datetime.date


class Forecaster:
    def __init__(self):
        self.calendar=Counter()
        self.locations=defaultdict(Counter)

    def observe(self,night):
        changed=night.morning_date!=night.evening_date
        p0_calendar=.92 if changed else .08
        p0_place=.82 if night.morning_place==night.evening_place else .18/(len(PLACES)-1)
        local=self.locations[night.evening_place]
        p_calendar=(2*p0_calendar+self.calendar[changed])/(2+self.calendar.total())
        p_place=(2*p0_place+local[night.morning_place])/(2+local.total())
        self.calendar[changed]+=1;local[night.morning_place]+=1
        return -math.log2(p_calendar*p_place),-math.log2(p0_calendar*p0_place)


def witnessed(history,current=None):
    # Dates come from the announcement the reporter actually heard. Origins/places are own physical receipts.
    prior_evening=None;date=None;rows=[];model=Forecaster()
    events=[h["events_by_actor"]["reporter"] for h in history]
    if current:events.append(current)
    for e in events:
        if e["clock"]==CLOCKS[0]:
            today=heard_date(e["observed"])
            if prior_evening and date and today:
                night=Overnight(prior_evening["id"],e["id"],prior_evening["place"],e["origin"],date,today)
                bits,ordinary=model.observe(night);rows.append((night,bits,ordinary))
            date=today;prior_evening=None
        elif e["clock"]==CLOCKS[-1]:prior_evening=e
    return rows


def cue(role,state,tick,history,mode,seed,names,physical,ending):
    turns,actions=badge_cues.cue(role,state,tick,history,mode,seed,names,physical,ending)
    if role!="reporter" or not history:return turns,actions
    obs=json.loads(turns[1]["content"]);current=None
    if tick==0:
        day=history[-1]["events_by_actor"]["reporter"]["day"]+1
        current={"id":f"d{day:02d}-t00-reporter","clock":CLOCKS[0],"origin":state["positions"]["reporter"],
                 "observed":obs["evidence_now"]}
    ranked=sorted(witnessed(history,current),key=lambda x:x[1],reverse=True)
    selected=[];routes=set()
    for night,_,_ in ranked:
        pair=(night.evening_place,night.morning_place)
        if pair in routes:continue
        routes.add(pair)
        selected.append((night.evening_id,{"last_evening":f'{night.evening_date.strftime("%A, %B %-d")}, 7 pm, {night.evening_place}.',
                     "next_thing_you_saw":f'{night.morning_date.strftime("%A, %B %-d")}, 6 am, {night.morning_place}.'}))
        if len(selected)==2:break
    if selected:
        obs["remembered_overnight_observations"]=[r for _,r in sorted(selected)]
        turns=[turns[0],{"role":"user","content":json.dumps(obs,ensure_ascii=False,indent=1)}]
    return turns,actions
