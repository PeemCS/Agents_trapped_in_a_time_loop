"""Shoot both verified calendar outcomes from an actual delivered reel."""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from scene import ROLES,CARDS,NAMES,ALARM,PREFACE
from shoot import HERE,STATE,NIGHT,ObservableOllama,validate,atomic_json,sha

def choose():
    folder=HERE/"runs"
    while True:
        path=folder/"721-hypothesis/take.json"
        if path.exists() and json.loads(path.read_bytes())["status"]=="complete":break
        time.sleep(8)
    for name in ("721-hypothesis","721-uncued"):
        path=folder/name/"take.json";raw=path.read_bytes();r=json.loads(raw)
        for d in r["days"]:
            if d["ending"]["delivered"]:return name,sha(raw),d
    raise ValueError("No deliverable exists in this pair")

def location(role,d):
    a=d["evening"][role]["decision"]["action"]
    if role=="reporter":
        if d["afternoon_state"]["city"]:return "Pittsburgh terminal"
        return {"play_piano":"ballroom","go_to_party":"ballroom","ask_Rita_to_dance":"ballroom","wait_at_Rialto":"Rialto booth","go_to_bed":"hotel room","sit_at_depot":"town depot","wire_deposit":"town post office"}[a]
    if role=="producer":return {"transmit_interview":"radio station","go_dancing":"ballroom","go_to_party_for_work":"ballroom","take_evening_off":"hotel room"}[a]
    return {"deliver_reel":"radio station","screen_party":"ballroom","go_home":"hotel room"}[a]

def actor(source,digest,d,branch,role):
    folder=HERE/"epilogues"/branch;folder.mkdir(parents=True,exist_ok=True);target=folder/(role+".json")
    if target.is_file():return
    wed=branch=="wednesday"
    place=location(role,d) if wed else "hotel lobby"
    memories=([d["afternoon_state"]["effects"][role],d["ending"]["effects"][role],d["evening"][role]["decision"]["intention"]]
              if wed or role=="reporter" else [])
    facts=[("Wednesday, February 3, 2016. The newsreader gives the date twice. The depot clerk tears the Tuesday sheet off his timetable." if wed else ALARM),
           "You are at the "+place+". A copy of a received telegram is at your hand: Alma's daughter in Pittsburgh has the whole interview. Her reply is 'I know that voice. Play it again.'"]
    city=place=="Pittsburgh terminal"
    menu={"phone_sister":"Use the open phone return to speak to your sister about the van.","wait_here":"Stay where you are for this first hour.","listen_to_interview":"Listen to the transmitted reel on the radio."} if role=="reporter" else {"keep_own_copy":"Label a personal copy of the transmitted reel.","go_off_duty":"Put the kit away and go off duty.","listen_to_interview":"Listen to the transmitted reel on the radio."}
    if role=="reporter" and city and wed:menu["help_sister_move"]="Walk to your sister's flat and actually help lift the couch into the van."
    elif role=="reporter" and not city:menu["walk_to_depot"]="Walk to the local depot. The first coach is at one."
    messages=[{"role":"system","content":CARDS[role]+" "+PREFACE},{"role":"user","content":json.dumps({"observed":facts,"your_retained_experiences":memories,"physical_choices":menu},ensure_ascii=False,indent=1)}]
    tag=json.loads((NIGHT/"takes/q27/model.json").read_bytes())
    model=ObservableOllama(SimpleNamespace(model=tag["name"],num_ctx=8192,max_tokens=3072,temperature=.8,timeout=420,base_url="http://127.0.0.1:18527"),folder)
    seed=11221+ROLES.index(role)
    raw,meta=model.respond(role,(d["day"]+1,0),messages,list(menu),seed);attempts=[meta]
    try:
        if meta["finish_reason"]!="stop":raise ValueError("capped")
        decision=validate(raw,list(menu))
    except (ValueError,TypeError):
        raw,meta=model.respond(role,(d["day"]+1,0),messages+[{"role":"assistant","content":raw},{"role":"user","content":"Return the committed action and the words, detail and intention fields."}],list(menu),seed+9);attempts.append(meta)
        if meta["finish_reason"]!="stop":raise ValueError("capped repair")
        decision=validate(raw,list(menu))
    effect={"help_sister_move":"Phil arrives at his sister's flat and they lift the couch into the waiting van.","wait_here":NAMES[role]+" stays for the first hour.",
            "listen_to_interview":NAMES[role]+" hears Alma's recorded voice on the regional return.","phone_sister":"Phil hears his sister answer the return line.",
            "walk_to_depot":"Phil walks to the local depot. The one o’clock coach has not yet departed.","keep_own_copy":NAMES[role]+" labels a personal copy.","go_off_duty":NAMES[role]+" clocks off."}[decision["action"]]
    atomic_json(target,{"source_run":source,"source_sha256":digest,"source_day":d["day"],"rule":branch,"role":role,"place":place,
                        "messages":messages,"decision":decision,"effect":effect,"attempts":attempts,"model":tag["name"],"model_revision":tag["digest"]})

def main():
    source,digest,d=choose()
    with ThreadPoolExecutor(max_workers=2) as p:
        fs=[p.submit(actor,source,digest,d,b,r) for b in ("tuesday","wednesday") for r in ROLES]
        for f in fs:f.result()
    (STATE/"epilogues-complete").touch();print("Two calendar branches heard from all three actors.",flush=True)

if __name__=="__main__":main()
