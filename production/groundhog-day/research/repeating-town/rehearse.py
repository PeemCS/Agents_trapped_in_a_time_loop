"""Private pre-event rehearsal. Python 3 standard library and a local Ollama server."""
import argparse
import hashlib
import json
import os
import random
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

API = "http://127.0.0.1:11434/api/"
TIMES = ("6:00 am", "9:30 am", "1:00 pm", "7:00 pm")
PLACES = {
    "inn": "The bedside radio plays three bright notes. A delivery van backfires twice outside.",
    "diner": "A spoon drops beside the counter. The owner chalks up the price of pie.",
    "square": "Festival bunting hangs above the bandstand. A rope keeps the crowd off the platform.",
    "studio": "A desk microphone and a piano share a cramped room. A record light is off.",
    "depot": "A coach timetable lists an afternoon departure for Pittsburgh. You have a valid ticket.",
    "Pittsburgh": "The terminal has a left-luggage desk and a working payphone. Your hometown bus pass works here."
}
CAST = {
    "Lou": ("a radio producer", "Get a usable piece for the station. You also want to record the town band."),
    "Bea": ("the diner owner", "Get the kitchen through the festival rush. You want an hour off to watch the band.")
}
ROUNDS = {"Lou": ("inn","square","studio","diner"), "Bea": ("diner","diner","square","diner")}
HERO = ("You are Ellis, a visiting radio reporter in Pennsylvania in 2016. You came to file a short "
        "winter forecast and get home to Pittsburgh. Your time is yours. You can change your plans. "
        "Choose your next physical action. In words, say something aloud or into your pocket recorder "
        "if you wish. Silence is available. Write only what you actually say.")
MORNING = ("The digital display reads Tuesday, February 2, 2016. The hotel radio announces today's "
           "groundhog forecast from the square. "+PLACES["inn"])
LOCAL = {"inn": ["leave_pencil_mark"], "diner": ["clear_tables"], "square": ["watch_ceremony"],
         "studio": ["file_forecast","play_piano"], "depot": ["check_timetable"],
         "Pittsburgh":["call_home"]}
EFFECTS = {"clear_tables":"You clear the dirty tables.","watch_ceremony":"You watch the crowd at the bandstand.",
           "file_forecast":"The station records and receives your forecast.","play_piano":"You spend the hour at the piano.",
           "check_timetable":"The Pittsburgh coach leaves at 1:00 pm.","call_home":"You leave a voicemail on your home phone."}

def available(place, tick, present):
    choices = ["look_around","spend_time_here","try_something"] + LOCAL[place]
    if place != "Pittsburgh":
        choices += ["go_to_"+p for p in PLACES if p != place and p != "Pittsburgh"]
        if tick == 2:
            choices.append("take_coach_to_Pittsburgh")
    choices += ["talk_to_"+name for name in present]
    return choices

def perform(act, place, marked):
    if act.startswith("go_to_"):
        place = act.removeprefix("go_to_")
        effect = "You arrive at the "+place+". "+PLACES[place]
    elif act == "take_coach_to_Pittsburgh":
        place = "Pittsburgh"
        effect = "You use your ticket and arrive in Pittsburgh. "+PLACES[place]
    elif act == "leave_pencil_mark":
        marked = True
        effect = "You pencil a cross on the wooden window frame."
    elif act == "look_around":
        effect = PLACES[place]
        if place == "inn":
            effect += " There is a pencil cross on the sill." if marked else " The sill has no pencil marks."
    elif act == "spend_time_here":
        effect = "You stay in place as the hours pass."
    else:
        effect = EFFECTS[act]
    return place, marked, effect

def read_api(route, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    with urlopen(Request(API+route,data=data,headers={"Content-Type":"application/json"}),timeout=120) as response:
        return json.load(response)

def decide(model, role, obs, choices, key, temp, fields=("words",)):
    properties = {"action":{"type":"string","enum":choices}}
    properties.update({f:{"type":"string"} for f in fields})
    schema = {"type":"object","properties":properties,"required":list(properties),"additionalProperties":False}
    turns = [{"role":"system","content":role},{"role":"user","content":obs+"\nAvailable actions: "+", ".join(choices)}]
    seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:4],"big") % (2**31-1)
    options = {"seed":seed,"temperature":temp,"num_ctx":4096,"num_predict":160}
    attempts=[]
    for _ in range(2):
        body={"model":model,"messages":turns.copy(),"format":schema,"options":options,"stream":False,"think":False}
        res=read_api("chat",body)
        raw=res["message"]["content"]
        attempts.append({"messages":body["messages"],"schema":schema,"options":options,"raw":raw})
        try:
            answer=json.loads(raw)
            if (res.get("done_reason")!="length" and answer["action"] in choices and
                    all(isinstance(answer[f],str) for f in fields)):
                return answer, attempts
        except (TypeError,KeyError,ValueError):
            pass
        turns=turns+[{"role":"user","content":"Choose one of the listed actions and keep all text very short."}]
    raise ValueError("invalid response after repair: "+repr(attempts))

def play(seed, days, model, digest, memory_mode):
    events, memory, npc_cache = [], [], {}
    for day in range(1,days+1):
        place, marked = "inn", False
        npc_memory = {name:[] for name in CAST}
        for tick,clock in enumerate(TIMES):
            initial=place
            present=[name for name in CAST if ROUNDS[name][tick]==place]
            now=MORNING if tick==0 else "Tuesday, February 2. "+PLACES[place]
            if memory_mode == "events" and tick == 0:
                now = "You wake in your hotel bed. "+now
            view=(now+" It is "+clock+". You are at "+place+". People within earshot: "+(", ".join(present) or "none")+
                  ".\nEarlier moments you remember, oldest first:\n"+("\n".join(memory) or "(none)")+
                  "\nUse words for a short utterance, or leave it empty. For try_something, put the proposed physical act "
                  "in proposal. Otherwise leave proposal empty.")
            actions=available(place,tick,present)
            # Keep action ordering fixed within a seed so the morning menu cannot reveal a hidden day number.
            random.Random(seed+tick).shuffle(actions)
            answer,calls=decide(model,HERO,view,actions,f"{seed}/player/{day}/{tick}",0.8,("words","proposal"))
            act=answer["action"]
            bystander=None
            if act.startswith("talk_to_"):
                name=act.removeprefix("talk_to_")
                own_view=("Tuesday, February 2, "+clock+". You're at the "+place+". "+PLACES[place]+
                          "\nYour own encounters today: "+(" / ".join(npc_memory[name]) or "none")+
                          "\nEllis addresses you: "+(answer["words"] or "(silence)")+
                          "\nChoose how to respond. Keep your words to one sentence.")
                role="You are "+name+", "+CAST[name][0]+". "+CAST[name][1]
                cache_key=(name,own_view)
                if cache_key not in npc_cache:
                    npc_cache[cache_key]=decide(model,role,own_view,["answer","ask_a_question","get_back_to_work"],
                                                f"{seed}/npc/{name}/{own_view}",0.55)
                reply,npc_calls=npc_cache[cache_key]
                bystander={"name":name,"decision":reply,"attempts":npc_calls}
                effect=f"You address {name}. {name} chooses to {reply['action'].replace('_',' ')}."
                if reply["words"]:
                    effect += " "+name+" says: "+reply["words"]
                npc_memory[name].append((answer["words"] or "(silence)")+" / "+reply["words"])
            elif act=="try_something":
                # A proposal can add a small local event. Travel, other people's decisions and the calendar belong to the engine.
                rule=("You resolve a proposed action in an ordinary Pennsylvania town. Only affirm a modest physical "
                      "act achievable here by this person alone with the available objects. Speaking, observing, waiting "
                      "and practicing are possible. Decline if it would change the calendar, transport the actor, "
                      "control another person, create an unsupported lasting object change, or require missing equipment. "
                      "Give the immediate observable result in words. One short sentence.")
                prop=answer["proposal"]
                reply,ref_calls=decide(model,rule,PLACES[place]+"\nProposed act: "+prop,["achieved","not_achieved"],
                                      f"{seed}/ref/{place}/{prop}",0)
                bystander={"name":"world referee","decision":reply,"attempts":ref_calls}
                effect=("You attempt: "+prop+". Result: "+reply["action"].replace("_"," ")+". "+reply["words"])
            else:
                place,marked,effect=perform(act,place,marked)
            receipt=f"Feb 2, {clock}, {initial}. "+(MORNING+" " if tick==0 else "")+effect
            if answer["words"] and memory_mode=="transcript":
                receipt+=" You said: "+answer["words"]
            memory.append(receipt)
            events.append({"day":day,"clock":clock,"origin":initial,"place":place,"actor":"Ellis",
                           "decision":answer,"effect":effect,"player_calls":calls,"other_call":bystander})
        if memory_mode=="events":
            memory.append(f"You remember falling asleep in {place} at the end of that evening.")
    return {"protocol":1,"memory":memory_mode,"seed":seed,"model":model,"digest":digest,"days":days,"events":events}

def replay(row):
    print("Seed",row["seed"],"/",row["model"])
    for e in row["events"]:
        print(f"  {e['day']} · {e['clock']:>7} · {e['place']:<10} {e['decision']['action']:<25} {e['decision']['words']}")
        print(" "*29+e["effect"])

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay",type=Path)
    parser.add_argument("--seeds",nargs="+",type=int,default=[511,512,513])
    parser.add_argument("--days",type=int,default=4)
    parser.add_argument("--model",default="nemotron-4b-64k:latest")
    parser.add_argument("--memory",choices=("events","transcript"),default="events",
                        help="Use witnessed events and explicit nights, or the first rehearsal's verbatim speech feedback.")
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    if args.replay:
        replay(json.loads(args.replay.read_text()))
        return
    if not 1<=args.days<=4:
        parser.error("This four-day rehearsal keeps the full action history. Use --days 1 through 4.")
    tags=read_api("tags")["models"]
    match=next((t for t in tags if t["name"]==args.model and not t.get("remote_model")),None)
    if not match:
        parser.error("Select an already installed local model.")
    out=args.out or Path(tempfile.mkdtemp(prefix="winter-town-"))
    out.mkdir(parents=True,exist_ok=True)
    print("Recorded runs:",out,flush=True)
    for seed in args.seeds:
        path=out/f"seed-{seed}.json"
        if path.exists():
            raise SystemExit(f"Run already exists at {path}. Choose a fresh output directory.")
        row=play(seed,args.days,args.model,match["digest"],args.memory)
        with tempfile.NamedTemporaryFile(mode="w",dir=out,delete=False) as temp:
            json.dump(row,temp,ensure_ascii=False)
            temp.write("\n")
        os.replace(temp.name,path)
        print("Saved",path,flush=True)

if __name__ == "__main__":
    main()
