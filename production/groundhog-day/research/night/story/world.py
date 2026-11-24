"""Physical state, actor observations and deterministic resolution for the dress rehearsal."""
import hashlib
import json
import random

ACTORS = ("reporter", "producer", "camera")
CAST_NAMES = {"film":{"reporter":"Phil","producer":"Rita","camera":"Larry"},
              "neutral":{"reporter":"Ellis","producer":"June","camera":"Cal"}}
CLOCKS = ("6:00 am", "9:30 am", "1:00 pm", "7:00 pm")
START = {"reporter":"inn","producer":"inn","camera":"square"}
PLACES = {
    "inn": "A hotel lobby, a windowsill, a payphone and your coat by the door.",
    "diner": "A pie counter, a bell and a rack of breakfast dishes. The window overlooks the square.",
    "square": "A bandstand beside the winter festival tent. The town band will play in the afternoon.",
    "studio": "A tape deck, a live microphone and a narrow upright piano.",
    "depot": "The timetable lists the afternoon coach to Pittsburgh.",
    "Pittsburgh": "You are in Pittsburgh. At the bus terminal there is a payphone and a bench."
}
DAWN = "Tuesday, February 2, 2016. The local radio plays three bright notes and announces a groundhog forecast in the town square. A delivery van backfires twice."
ROLES = {
    "reporter": ("You are {reporter}, a visiting TV weather reporter in western Pennsylvania in 2016. You came to file "
                 "a short forecast and get home to Pittsburgh. On Wednesday you promised your sister to help move a couch. "
                 "The van is booked for then. You have a paid ticket on the one o'clock coach. You choose your own plans."),
    "producer": ("You are {producer}, the producer of a visiting TV crew in western Pennsylvania in 2016. "
                 "The station booked a weather segment. You also want to put the town band on air this afternoon. "
                 "You have final say over the station's rundown and your own time."),
    "camera": ("You are {camera}, the cameraman for a visiting TV crew in western Pennsylvania in 2016. "
               "You have one charged camera battery. The newsroom wants festival footage, and you want to make a portrait "
               "of the cornet player after the ceremony. Decide what to film and how to spend your day.")
}
CREW = " Your crew are {reporter} on weather, {producer} producing, and {camera} on camera."
DECISION_INSTRUCTION = (
    "Choose your own action from the available physical actions. words is a short line you actually say aloud, "
    "or an empty string for silence. When anyone is present they can hear you before anyone leaves. "
    "intention is an optional short practical plan you would remember. "
    "detail is only for a small personal activity during try_something. A line about an act does not perform it."
)

def stable_seed(*parts):
    return int.from_bytes(hashlib.sha256(json.dumps(parts, ensure_ascii=False, separators=(",", ":")).encode()).digest()[:4], "big") & 0x7fffffff

def initial_state():
    return {"positions":dict(START), "marked":False, "weather_tape":False, "aired":False, "dishes":2,
            "band_recorded":False, "heard_band":[], "called_sister":False,"camera_battery":1,"camera_footage":None}

def scene_facts(actor, state, tick):
    place=state["positions"][actor]
    facts=[DAWN if tick==0 else f"Tuesday, February 2, 2016, {CLOCKS[tick]}.", PLACES[place]]
    if tick==0:
        facts.append("You wake in your bed at the hotel and come down to the lobby." if actor=="reporter"
                     else ("You have just arrived at the hotel lobby." if actor=="producer" else "You have just reached the festival bandstand with your camera."))
    if place=="inn":
        facts.append("The sill has a pencil cross." if state["marked"] else "The windowsill is unmarked.")
    elif place=="diner":
        facts.append(f"Racks of dishes to clear: {state['dishes']}.")
    elif place=="studio":
        facts.append("A recorded forecast is on the deck." if state["weather_tape"] else "The forecast reel is blank.")
        facts.append("The forecast has aired." if state["aired"] else "The forecast has yet to air.")
    elif place=="square":
        facts.append("The band is playing." if tick>=2 else "The band is setting up.")
    if actor=="camera": facts.append(f"Your camera battery has {state['camera_battery']} take(s) left.")
    return facts

def menu(actor, state, tick, names):
    place=state["positions"][actor]
    present=[a for a in ACTORS if a!=actor and state["positions"][a]==place]
    actions=["look_around", "spend_time_here", "try_something"]+["talk_to_"+names[a] for a in present]
    if place!="Pittsburgh":
        actions.extend("go_to_"+p for p in PLACES if p not in {place,"Pittsburgh"})
    if actor=="reporter" and tick==2 and place!="Pittsburgh":
        actions.append("take_coach_to_Pittsburgh")
    if place=="inn": actions.append("leave_pencil_mark")
    if place=="diner" and state["dishes"]>0: actions.append("clear_tables")
    if place=="square":
        actions.append("watch_ceremony")
        if actor=="camera" and state["camera_battery"]:
            actions.append("film_festival")
            if tick>=2: actions.append("film_cornet_player")
        if tick>=2:
            actions.append("listen_to_band")
            if actor in ("producer","reporter"): actions.append("record_band")
    if place=="studio":
        actions.append("play_piano")
        if actor in ("reporter","producer"): actions.append("file_forecast")
        if actor=="producer" and state["weather_tape"]: actions.append("air_forecast")
    if place=="depot": actions.append("check_timetable")
    if actor=="reporter" and place=="Pittsburgh": actions.append("call_sister")
    return actions

def cue(actor, state, tick, events, memory, seed, names):
    place=state["positions"][actor]
    here=[names[a] for a,p in state["positions"].items() if a!=actor and p==place]
    history=events if actor=="reporter" else events[-tick:] if tick else []
    # Both branches have the same receipts and remember sleep. The bounded branch protects key travel
    # and a voluntary ongoing plan from being pushed out by repeated speech.
    chosen=list(range(len(history)))
    if memory=="receipts" or actor!="reporter":
        if len(chosen)>9:
            older=[i for i in chosen[:-6] if history[i]["events_by_actor"][actor]["decision"]["action"]=="take_coach_to_Pittsburgh"]
            chosen=sorted(set([chosen[0]]+older[-2:]+chosen[-6:]))
    recollections=[]
    for i in chosen:
        slot=history[i]
        e=slot["events_by_actor"][actor]
        observed=list(e["observed"])
        if actor=="reporter" and memory=="transcript":
            if e["decision"]["words"]: observed.append("You said: "+e["decision"]["words"])
            if e["decision"]["intention"]: observed.append("Your plan then: "+e["decision"]["intention"])
        if actor=="reporter" and e["clock"]==CLOCKS[-1]: observed.append("You later fell asleep in "+e["place"]+".")
        recollections.append(f"Tuesday {e['clock']}, {e['origin']}. "+" ".join(observed))
    if (memory=="receipts" or actor!="reporter") and history:
        last=history[-1]["events_by_actor"][actor]["decision"]["intention"]
        if last: recollections.append("Your most recent stated intention: "+last)
    actions=menu(actor,state,tick,names)
    random.Random(stable_seed(seed,actor,tick)).shuffle(actions)
    obs={"current_place":place,"current_clock":CLOCKS[tick],"what_you_notice":scene_facts(actor,state,tick),
         "people_within_earshot":here,"your_memories_in_order":recollections,"available_actions":actions}
    return [{"role":"system","content":(ROLES[actor]+CREW).format(**names)+" "+DECISION_INSTRUCTION},
            {"role":"user","content":json.dumps(obs,ensure_ascii=False,indent=1)}], actions

def physical(actor, choice, pre, next_state, tick, names):
    name=names[actor]
    act=choice["action"]
    place=pre["positions"][actor]
    dest=place
    if act.startswith("go_to_"):
        dest=act[6:]; detail=f"{name} reaches the {dest}."
    elif act=="take_coach_to_Pittsburgh":
        dest="Pittsburgh"; detail=f"{name} uses the paid ticket and rides the coach all the way to Pittsburgh."
    elif act.startswith("talk_to_"):
        detail=f"{name} addresses {act[8:]}." if choice["words"] else f"{name} turns toward {act[8:]} without speaking."
    elif act=="leave_pencil_mark":
        next_state["marked"]=True; detail=f"{name} pencils a cross on the hotel windowsill."
    elif act=="clear_tables":
        n=next_state["dishes"]
        if n:
            next_state["dishes"]-=1; detail=f"{name} clears one rack. {next_state['dishes']} rack(s) remain."
        else: detail=f"{name} reaches for the dishes. The other workers have already cleared them."
    elif act=="file_forecast":
        next_state["weather_tape"]=True; detail=f"{name} records and files a forecast reel at the station."
    elif act=="air_forecast":
        next_state["aired"]=True; detail=f"{name} puts the recorded forecast on air."
    elif act=="record_band":
        next_state["band_recorded"]=True; detail=f"{name} records the town band on its afternoon stand."
    elif act=="listen_to_band":
        if actor not in next_state["heard_band"]: next_state["heard_band"].append(actor)
        detail=f"{name} stays for the band's cornet solo."
    elif act in ("film_festival", "film_cornet_player"):
        next_state["camera_battery"]=0
        subject="the festival" if act=="film_festival" else "the cornet player"
        next_state["camera_footage"]=subject
        detail=f"{name} uses the camera's last charged take to film {subject}."
    elif act=="play_piano": detail=f"{name} spends the period playing the studio piano."
    elif act=="watch_ceremony": detail=f"{name} watches the winter festival at the bandstand."
    elif act=="check_timetable": detail=f"{name} reads the timetable. The Pittsburgh coach departs at one."
    elif act=="call_sister":
        next_state["called_sister"]=True; detail=f"{name} phones his sister. She confirms the moving van is booked for Wednesday."
    elif act=="look_around":
        detail=f"{name} inspects the {place}. "+scene_facts(actor,pre,tick)[-1]
    elif act=="try_something":
        detail=f"{name} spends this period on a personal attempt at the {place}. Its proposed result is unverified."
    elif act=="spend_time_here": detail=f"{name} spends the period at the {place}."
    else: raise ValueError(f"Unsupported action {act}")
    next_state["positions"][actor]=dest
    return dest,detail

def resolve(seed, day, tick, state, decisions, names):
    import copy
    next_state=copy.deepcopy(state)
    order=list(ACTORS)
    random.Random(stable_seed(seed, day, tick, "resolution")).shuffle(order)
    data={}
    for actor in order:
        d=decisions[actor]
        if d["action"] not in menu(actor,state,tick,names): raise ValueError(f"Illegal action for {actor}: {d['action']}")
        dest,effect=physical(actor,d,state,next_state,tick,names)
        data[actor]={"id":f"d{day:02}-t{tick:02}-{actor.lower()}","actor":names[actor],"role":actor,"day":day,"clock":CLOCKS[tick],
                     "origin":state["positions"][actor],"place":dest,"decision":d,"effect":effect}
    for actor,e in data.items():
        seen=([DAWN] if tick==0 else [])+[e["effect"]];sources=[e["id"]]
        for who in ACTORS:
            if who==actor: continue
            oth=data[who]; same_start=e["origin"]==oth["origin"]; same_end=e["place"]==oth["place"]
            if same_start and oth["decision"]["words"]: seen.append(f"{names[who]} says: "+oth["decision"]["words"])
            if oth["origin"]==oth["place"]:
                if same_start:
                    if oth["decision"]["action"]=="look_around":
                        seen.append(f"{names[who]} looks around.")
                    elif oth["decision"]["action"]=="call_sister":
                        seen.append(f"{names[who]} makes a phone call.")
                    else: seen.append(oth["effect"])
            elif same_start: seen.append(f"{names[who]} leaves the {e['origin']}.")
            if same_end and (not same_start or e["origin"]!=e["place"] or oth["origin"]!=oth["place"]):
                seen.append(f"You see {names[who]} at the {e['place']}.")
            if same_start or same_end: sources.append(oth["id"])
        e["observed"]=seen;e["observation_sources"]=sources
    return next_state, data

def pack(day,tick,data,state,after,diagnostics):
    inner={}
    for actor in ACTORS:
        e=dict(data[actor])
        e["receipt"]={"from":e["origin"],"to":e["place"],"observation_ids":e["observation_sources"]}
        e["inference"]=diagnostics[actor]
        inner[actor]=e
    root=inner["reporter"]
    root["cast"]=[inner["producer"],inner["camera"]]
    return {"day":day,"tick":tick,"world_before":state,"world_after":after,"root":root}

def memory_slot(root):
    return {"events_by_actor":{a["role"]:a for a in [root,*root["cast"]]}}
