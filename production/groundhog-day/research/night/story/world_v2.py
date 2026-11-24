"""Wake-grouped evidence, simultaneous speech and a signed-off bulletin for the second protocol."""
import copy
import json
import random
from collections import defaultdict

import world as v1

FEEDS={"call_live_report":"Dial the station and deliver your live report from your current location.",
       "send_camera_take":"Use the camera uplink to send the take you actually filmed today.",
       "patch_reporter_line":"Select the reporter's live return on the portable broadcast switcher. A silent line stays silent.",
       "patch_camera_line":"Select the cameraman's live return. If he sends no footage, the channel has no pictures.",
       "play_filed_forecast":"Play the forecast reel already filed at the station.",
       "host_bulletin":"Take the station microphone and host the bulletin yourself."}
DEFAULT_ACTION_HINTS={"look_around":"Inspect your present surroundings.","spend_time_here":"Stay where you are for the period.",
                      "take_coach_to_Pittsburgh":"Use your ticket, make it to the coach, and arrive in Pittsburgh this period.",
                      "go_to_depot":"Walk to the local depot and stay in town.","file_forecast":"Record an actual forecast reel in the studio.",
                      "call_sister":"Telephone your sister in Pittsburgh about tomorrow's move.",
                      "film_festival":"Use the last camera charge to film the festival.",
                      "film_cornet_player":"Use the last camera charge to film the cornet player."}

def initial():
    s=v1.initial_state()
    s.update({"assignments":{},"bulletin":None,"weather_reel_event":None,"camera_take_event":None})
    return s

def actions(role,s,tick,names,physical,ending):
    allowed=[a for a in v1.menu(role,s,tick,names)
             if a!="try_something" and not (physical=="move" and a.startswith("talk_to_"))]
    if ending=="bulletin" and tick==3:
        allowed=[a for a in allowed if a!="air_forecast"]
        if role=="reporter": allowed.append("call_live_report")
        elif role=="camera" and s["camera_footage"]: allowed.append("send_camera_take")
        elif role=="producer":
            allowed+=["patch_reporter_line","patch_camera_line","host_bulletin"]
            if s["weather_tape"]: allowed.append("play_filed_forecast")
    return allowed

def signal_menu(role,s,tick,ending):
    allowed=[""]
    if ending!="bulletin":return allowed
    if role=="producer" and tick<3:
        for target in ("reporter","camera"):
            if target not in s["assignments"]:allowed.append("invite_"+target)
    elif role!="producer" and s["assignments"].get(role,{}).get("status")=="invited":
        allowed+=["accept_assignment","decline_assignment"]
    return allowed

def cue(role,s,tick,history,mode,seed,names,physical,ending):
    allowed=actions(role,s,tick,names,physical,ending)
    random.Random(v1.stable_seed(seed,role,tick)).shuffle(allowed)
    signals=signal_menu(role,s,tick,ending)
    visible=history if role=="reporter" else history[-tick:] if tick else []
    records=[h["events_by_actor"][role] for h in visible]
    mem=memory(records,role,mode)
    place=s["positions"][role]
    facts=v1.scene_facts(role,s,tick)
    duties={names[target]:d["status"] for target,d in s["assignments"].items() if role in ("producer",target)}
    if ending=="bulletin":
        facts.append("Today the station has one seven o'clock bulletin. The producer can run the portable switcher from anywhere. The reporter has a phone return; the cameraman has a return for footage he has captured. The station plays its ident if nobody takes the switcher.")
        if duties:facts.append("Your crew radio assignments for this date: "+json.dumps(duties))
    descriptions={}
    for a in allowed:
        descriptions[a]=FEEDS.get(a) or DEFAULT_ACTION_HINTS.get(a) or (
            "Move to "+a.removeprefix("go_to_")+" and arrive this period." if a.startswith("go_to_") else a.replace("_"," ")+".")
    signal_help={"":"No assignment signal.","invite_reporter":"Ask the reporter to deliver tonight's live report.",
                 "invite_camera":"Ask the cameraman to send his actual footage tonight.",
                 "accept_assignment":"Accept the producer's offered contribution for tonight.",
                 "decline_assignment":"Decline the producer's offered contribution for tonight."}
    obs={"where":place,"clock":v1.CLOCKS[tick],"evidence_now":facts,
         "people_in_earshot":[names[r] for r in v1.ACTORS if r!=role and s["positions"][r]==place],
         "remembered_experiences":mem,"available_actions":descriptions,
         "optional_assignment_signals":{k:signal_help[k] for k in signals if k}}
    rule=(" Choose one physical action for this period. You may speak while carrying out any action, or stay silent. "
          "Return a JSON object with action, words, intention and detail. action must be one available action. "
          "words is a brief line you actually say. intention is an optional practical next plan. "
          "detail is empty unless you send one exact available assignment signal. Only physical actions change position or produce work.")
    if ending=="bulletin" and role=="producer":rule+=" The portable switcher is yours. The two contributors make their own decisions."
    return [{"role":"system","content":(v1.ROLES[role]+v1.CREW).format(**names)+rule},
            {"role":"user","content":json.dumps(obs,ensure_ascii=False,indent=1)}],allowed

def memory(records,role,mode):
    if not records:return []
    if mode=="flat":
        out=[]
        for e in records:
            items=e["observed"][:]
            if e["decision"]["words"]:items.append("You said: "+e["decision"]["words"])
            if e["decision"]["intention"]:items.append("Your next plan was: "+e["decision"]["intention"])
            if role=="reporter" and e["clock"]==v1.CLOCKS[-1]:items.append("You fell asleep in "+e["place"]+".")
            out.append(f"Tuesday {e['clock']}, {e['origin']}. "+" ".join(items))
        return out
    groups=defaultdict(list)
    for e in records:groups[e["day"]].append(e)
    # Keep one actual early journey, the most recent wake groups, and durable commitments from older groups.
    day_order=list(groups)
    retained=day_order[-3:]
    bus_day=next((e["day"] for e in records if e["decision"]["action"]=="take_coach_to_Pittsburgh"),None)
    if bus_day and bus_day not in retained:retained=[bus_day,*retained]
    old_anchors={}
    for e in records:
        if e["day"] in retained:continue
        if e["decision"]["action"]=="call_sister":old_anchors["family call"]=e["effect"]
        for x in e.get("radio_heard",[]):
            old_anchors[x["target_role"]+" assignment"]=x["text"]
    out=[]
    if old_anchors:out.append({"earlier_witnessed_commitments":list(old_anchors.values())})
    for d in retained:
        group=groups[d]
        episode={"morning_observation":group[0]["observed"][0],"episodes_in_order":[]}
        for e in group:
            observed=[x for x in e["observed"] if x!=v1.DAWN]
            episode["episodes_in_order"].append(f"{e['clock']} in {e['origin']}: "+" ".join(observed))
        if role=="reporter" and group[-1]["clock"]==v1.CLOCKS[-1]:
            episode["end_of_that_evening"]="You fell asleep in "+group[-1]["place"]+"."
        out.append(episode)
    last=records[-1]["decision"]["intention"]
    if last:out.append({"most_recent_own_plan":last})
    return out

def new_effect(role,act,place,names):
    who=names[role]
    return {"call_live_report":f"{who} phones the station's live return from {place}.",
            "send_camera_take":f"{who} switches on the camera uplink.",
            "patch_reporter_line":f"{who} takes the reporter's return on the portable switcher.",
            "patch_camera_line":f"{who} takes the camera return on the portable switcher.",
            "play_filed_forecast":f"{who} starts the filed weather reel.",
            "host_bulletin":f"{who} opens the station microphone."}[act]

def resolve(seed,day,tick,state,decisions,names,physical,ending):
    # Use the validated v1 reducer for ordinary physical verbs, then resolve independent broadcast
    # contributions and assignment messages against the sealed start state. Nobody sees a peer's turn before acting.
    standin=copy.deepcopy(decisions)
    for r,d in decisions.items():
        if d["action"] not in actions(r,state,tick,names,physical,ending):raise ValueError(f"Illegal {r} action {d['action']}")
        if d["action"] in FEEDS:standin[r]["action"]="spend_time_here"
    after,rows=v1.resolve(seed,day,tick,state,standin,names)
    for r,e in rows.items():
        d=decisions[r];e["decision"]=dict(d);e["radio_heard"]=[]
        if d["action"]=="file_forecast":after["weather_reel_event"]=e["id"]
        if d["action"] in ("film_festival","film_cornet_player"):after["camera_take_event"]=e["id"]
        if d["action"] in FEEDS:e["effect"]=new_effect(r,d["action"],e["place"],names)
    # Retain the actual public movement/witnesses. Replace v1's temporary local effect in each witness's view.
    for r,e in rows.items():
        for who,other in rows.items():
            if decisions[who]["action"] not in FEEDS:continue
            original=f"{names[who]} spends the period at the {other['origin']}."
            e["observed"]=[other["effect"] if x==original else x for x in e["observed"]]
    for r in v1.ACTORS:
        e=rows[r];d=decisions[r];signal=d["detail"].strip()
        e["signal_status"]="none"
        if not signal or signal.lower() in ("none","n/a"):continue
        if signal not in signal_menu(r,state,tick,ending):
            e["signal_status"]="unavailable";continue
        target=signal[len("invite_"):] if signal.startswith("invite_") else r
        status={"accept_assignment":"accepted","decline_assignment":"declined"}.get(signal,"invited")
        phrase=(f"{names['producer']} invites {names[target]} on the crew radio to contribute to the evening slot."
                if status=="invited" else f"{names[target]} radios {names['producer']} and {status} the evening assignment.")
        record={"target_role":target,"status":status,"event_id":e["id"],"invite_id":e["id"] if status=="invited" else state["assignments"][target]["invite_id"],"text":phrase}
        after["assignments"][target]=record;e["signal_status"]="sent"
        for witness in ("producer",target):
            rows[witness]["observed"].append(phrase)
            rows[witness]["radio_heard"].append(record)
            if e["id"] not in rows[witness]["observation_sources"]:rows[witness]["observation_sources"].append(e["id"])
    if ending=="bulletin" and tick==3:
        pick=decisions["producer"]["action"]
        if pick=="patch_reporter_line" and decisions["reporter"]["action"]=="call_live_report":
            channel="live_report" if decisions["reporter"]["words"].strip() else "silent_live_reporter_line";source="reporter"
        elif pick=="patch_camera_line" and decisions["camera"]["action"]=="send_camera_take" and state["camera_footage"]:
            channel="camera_take";source="camera"
        elif pick=="host_bulletin":channel="producer_live" if decisions["producer"]["words"].strip() else "silent_producer_mic";source="producer"
        elif pick=="play_filed_forecast":channel="filed_forecast";source="filed_reel";after["aired"]=True
        elif pick in ("patch_camera_line","patch_reporter_line"):channel="empty_selected_return";source=None
        else:channel="station_ident";source=None
        origin=rows[source]["place"] if source in v1.ACTORS else None
        sources=[rows["producer"]["id"]]
        if pick=="patch_reporter_line":sources.append(rows["reporter"]["id"])
        if pick=="patch_camera_line":sources.append(rows["camera"]["id"])
        if channel=="camera_take":sources.append(state["camera_take_event"])
        if channel=="filed_forecast":sources.append(state["weather_reel_event"])
        broadcast={"channel":channel,"source_role":source,"source_place":origin,"selected_by":names["producer"],
            "source_ids":[event_id for event_id in sources if event_id],"delivered_assignments":[],
            "spoken":decisions[source]["words"] if source in ("reporter","producer") else "",
            "footage":state["camera_footage"] if channel=="camera_take" else None}
        for target,x in after["assignments"].items():
            if x["status"]=="accepted" and decisions[target]["action"]==("call_live_report" if target=="reporter" else "send_camera_take"):
                broadcast["delivered_assignments"].append(target)
        after["bulletin"]=broadcast
        line={"live_report":f"The seven o'clock broadcast carries {names['reporter']}'s live report from {origin}.",
              "silent_live_reporter_line":"The selected live reporter line carries silence.",
              "camera_take":f"The seven o'clock broadcast carries the cameraman's recorded pictures of {state['camera_footage']}.",
              "producer_live":f"{names['producer']} hosts the seven o'clock bulletin live.",
              "silent_producer_mic":"The producer's open microphone carries silence.",
              "filed_forecast":"The seven o'clock broadcast plays the filed weather reel.",
              "empty_selected_return":"The selected contributor line is empty at seven.",
              "station_ident":"The pre-recorded station ident runs in the unattended seven o'clock slot."}[channel]
        for r,e in rows.items():
            e["observed"].append(line);e["bulletin_result"]=line
            if r=="reporter":e["effect"]+=" "+line
            if broadcast["spoken"] and r!=source:
                e["observed"].append("On the return monitor you hear: "+broadcast["spoken"])
            # Broadcast outcome and its public evidence are heard via each crew member's confidence monitor.
            # Private acceptance by a different worker does not become visible to outside observers.
            for ref in broadcast["source_ids"]:
                if ref not in e["observation_sources"]:e["observation_sources"].append(ref)
    return after,rows
