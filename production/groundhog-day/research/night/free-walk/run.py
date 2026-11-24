"""Run paired, sequential local model calls with independently observed waypoints."""
from __future__ import annotations
import hashlib,json,math,os,subprocess,time,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
MODEL="qwen3:0.6b"
HOST="http://127.0.0.1:11434"
ROLES={"reporter":"Phil","producer":"Rita","camera":"Larry"}
STARTS={"reporter":{"x":6.75,"y":8.25},"producer":{"x":8.22,"y":8.40},"camera":{"x":11.0,"y":7.3}}
JOBS={"reporter":"You are Phil, a television weather reporter between live reports in a small town.","producer":"You are Rita, a television producer in town for a festival broadcast.","camera":"You are Larry, a camera operator carrying your camera around a festival town."}
TRIALS=[(c,s,3,tuple(ROLES)) for s in (913,927,941,953) for c in ("free","doors")]
TRIALS.extend([("unmarked",s,3,tuple(ROLES)) for s in (913,927,941,953)])
TRIALS.extend([("obstruction",967,2,("reporter",))])
SCHEMA={"type":"object","properties":{"x":{"type":"number"},"y":{"type":"number"},"say":{"type":"string"}},"required":["x","y","say"],"additionalProperties":False}
def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n");os.replace(tmp,path)
def post(body):
    req=urllib.request.Request(HOST+"/api/chat",data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=80) as result:return json.load(result)
def ask_route(pipe,req):
    pipe.stdin.write(json.dumps(req)+"\n");pipe.stdin.flush()
    r=json.loads(pipe.stdout.readline())
    if "error" in r:raise ValueError(r["error"])
    return r
def observation(role,places,history,world):
    p=places[role]
    fellows={ROLES[r]:pos for r,pos in places.items() if r!=role and math.dist(tuple(p.values()),tuple(pos.values()))<=4}
    # Each actor carries the same static public street map. Other actors outside the
    # observation radius and their plans/outcomes are unavailable.
    return {"you_are_at":p,"nearby_people":fellows,"map_limits":world["bounds"],
            "public_map_door_xy":{k:[v["x"],v["y"]] for k,v in world["doors"].items()},
            "public_map_blocked_rectangles_x_y_width_depth":[[b["id"],b["x"],b["y"],b["w"],b["d"]] for b in world["blocks"]],
            "your_own_previous_walks":history[-2:]}
def run_trial(condition,seed,turns,roles,world,pipe,revision):
    folder=HERE/("prospective" if condition=="coordinated" else "runs")/f"{condition}-{seed}";out=folder/"take.json"
    if out.exists():return json.loads(out.read_text())
    places={r:STARTS[r].copy() for r in roles};history={r:[] for r in roles};ticks=[]
    for tick in range(turns):
        events=[]
        for role in roles:
            visible=observation(role,places,history[role],world)
            if condition=="unmarked":visible.pop("public_map_door_xy")
            rule=("You can choose any x,y anywhere on the map, including staying where you are." if condition!="doors" else
                  "For this walking shift, choose one of the five posted door coordinates from your map.")
            if condition=="obstruction" and tick==0:rule="Calibration assignment: ask to stand at precisely x=5.2, y=6.0, the blocked survey pin inside the hotel. The resolver will report what happened."
            elif condition=="obstruction":rule="Your survey pin was inside a building. Read your own previous result. Choose your next reachable roadside spot yourself."
            system=JOBS[role]+" Your shift has a few unscheduled walks. Decide your next destination in world coordinates. "+rule+" Use the public map. Buildings cannot be crossed. Choose numbers x,y, and optionally a short remark spoken out loud in say. Return JSON."
            messages=[{"role":"system","content":system},{"role":"user","content":json.dumps(visible,ensure_ascii=False,separators=(",",":"))}]
            callseed=seed*100+tick*7+list(ROLES).index(role)
            request={"model":MODEL,"messages":messages,"think":False,"stream":False,"format":SCHEMA,"keep_alive":"3m",
                     "options":{"num_ctx":4096,"num_predict":96,"temperature":.78,"seed":callseed}}
            eid=f"{condition}-{seed}-t{tick:02}-{role}";rawfile=folder/"calls"/(eid+".json")
            if rawfile.exists():
                saved=json.loads(rawfile.read_text())
                if saved["request"]!=request:raise ValueError("Cached raw request differs")
            else:
                before=time.monotonic();response=post(request)
                saved={"request":request,"response":response,"wall_s":time.monotonic()-before};write(rawfile,saved)
            response=saved["response"];choice=json.loads(response["message"]["content"])
            if response.get("done_reason")!="stop" or any(type(choice.get(k)) not in (int,float) or not math.isfinite(choice[k]) for k in ("x","y")):raise ValueError(f"Invalid model content in {eid}")
            movement=ask_route(pipe,{"start":places[role],"requested":{k:choice[k] for k in ("x","y")}})
            events.append({"id":eid,"role":role,"actor":ROLES[role],"say":choice.get("say",""),"raw":str(rawfile.relative_to(HERE)),
                "raw_sha256":hashlib.sha256(rawfile.read_bytes()).hexdigest(),"seed":callseed,**movement})
        if condition=="coordinated":
            settled=json.loads(subprocess.check_output(["node",str(HERE/"reservations.cjs"),"--solve"],text=True,
                input=json.dumps({"events":events,"tick":tick,"seed":seed,"positions":places})))
            for e,move in zip(events,settled["rows"]):
                canonical=e["resolved"];e["canonicalEndpoint"]=canonical;e["canonicalPath"]=e["path"];e.update(move)
                if math.dist(tuple(canonical.values()),tuple(e["resolved"].values()))>1e-7:
                    e["status"]="reserved-nearby";e["reason"]="The crew reservation placed you at a nearby clear point."
                elif e["length"]<1e-6:
                    e["reason"]="You stayed at the requested position."
                near=min(world["doors"],key=lambda k:math.dist(tuple(e["resolved"].values()),(world["doors"][k]["x"],world["doors"][k]["y"])))
                e["nearDoor"]=near;e["resolvedDoorDistance"]=math.dist(tuple(e["resolved"].values()),(world["doors"][near]["x"],world["doors"][near]["y"]))
                e["resolvedOffDoor"]=e["resolvedDoorDistance"]>1
                e["adjustment"]=math.dist(tuple(e["quantized"].values()),tuple(e["resolved"].values()))
                e["yUp"]=[[p["x"],0,p["y"]] for p in e["path"]];e["slotMinimumGap"]=settled["minimumGap"]
        # Barrier: actors never see another actor's freshly chosen move in the same slot.
        for event in events:
            r=event["role"];places[r]=event["resolved"];history[r].append({k:event[k] for k in ("requested","resolved","status","reason")})
        ticks.append(events)
    take={"condition":condition,"seed":seed,"model":MODEL,"revision":revision,"initial":{r:STARTS[r] for r in roles},"ticks":ticks}
    write(out,take);return take
def main():
    with urllib.request.urlopen(HOST+"/api/tags",timeout=4) as reply:tag=next(t for t in json.load(reply)["models"] if t["name"]==MODEL)
    assert tag["size"]<650000000
    pipe=subprocess.Popen(["node",str(HERE/"resolve.cjs")],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
    try:
        world=ask_route(pipe,{"world":True});write(HERE/"map.json",world)
        runs=[];start=time.monotonic()
        for args in TRIALS:
            runs.append(run_trial(*args,world,pipe,tag["digest"]));print(args[:2],"complete",round(time.monotonic()-start,1),flush=True)
        payload={"model":MODEL,"revision":tag["digest"],"geometry_sha256":hashlib.sha256((HERE.parent/"visual/world.js").read_bytes()).hexdigest(),"runs":runs}
        (HERE/"takes.js").write_text("window.FreeWalkTakes = "+json.dumps(payload,ensure_ascii=False,separators=(",",":"))+";\n")
    finally:pipe.stdin.close();pipe.wait()
if __name__=="__main__":main()
