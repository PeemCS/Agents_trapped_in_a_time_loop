"""Join alternate rehearsal and interview performances to the native stream journal."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
NIGHT=HERE.parent
NAMES={"reporter":"Phil","producer":"Rita","camera":"Larry"}
PHASES=("afternoon","evening","alarm")
LABELS=("Afternoon","Seven o’clock","Six o’clock alarm")

def identity(group,run,stream):
    return group+"-"+run+"/"+Path(stream).stem

def collect(group,slots,refs,read_object,read_lines):
    base=NIGHT/group/"runs"
    if not base.exists():return
    for folder in sorted(p for p in base.iterdir() if p.is_dir()):
        run=folder.name
        tag=("Rialto · " if group=="last-reel" else "Rita interview · ")+run
        doc=folder/("take.json" if group=="last-reel" else "scene.json")
        obj=read_object(doc) if doc.exists() else {}
        pending={};meta={}
        for row in read_lines(folder/"request-index.ndjson"):
            short=row["stream"]
            rid=identity(group,run,short)
            file="../"+str((folder/short).relative_to(NIGHT))
            refs[rid]={"kind":"stream","file":file,"url":"/sources/"+rid+".ndjson","stage":row["stage"],"chars":row.get("thinking_chars",0)}
            k=(row["day"],row["tick"],row["role"])
            if rid not in pending.setdefault(k,[]):pending[k].append(rid)
            meta[k]=row["stage"]
        def slot(k,decision=None,effect="",attempts=None,origin=None,cache=False):
            day,tick,role=k
            event=f"d{day:02d}-t{tick:02d}-{role}"
            key=group+"-"+run+"-"+event
            route=pending.pop(k,[]) if k in pending else []
            for a in attempts or []:
                src=Path(a["stream"]) if "stream" in a else Path("runs")/run/a["stream_path"]
                original=src.parts[1]
                rid=identity(group,original,src.name)
                file="../"+group+"/"+str(src)
                refs.setdefault(rid,{"kind":"stream","file":file,"url":"/sources/"+rid+".ndjson","stage":"returned","chars":len(a.get("public_thinking",""))})
                if rid not in route:route.append(rid)
            when=(f"Tuesday {day} · {LABELS[tick]}" if group=="last-reel" else ("At the booth · "+("The request" if tick==0 else "The apology")))
            slots.append({"id":key,"persona":tag,"day":day,"tick":tick,"when":when,"short":when,"role":role,"actor":NAMES[role],
                          "stage":("exact cached decision" if cache else "committed") if decision else ("generating" if meta[k]=="started" else meta[k]),
                          "action":decision,"consequence":effect,"requests":route,"original_slot":origin,"event_id":event})
        if group=="last-reel":
            for day in obj.get("days",[]):
                for tick,phase in enumerate(PHASES[:2]):
                    fx=day["afternoon_state" if tick==0 else "ending"]["effects"]
                    for r,val in day[phase].items():
                        origin=None
                        if val["cache_hit"]:
                            origin=(group+"-"+val["source_run"]+f'-d{val["source_day"]:02d}-t{PHASES.index(val["source_phase"]):02d}-'+r)
                        slot((day["day"],tick,r),val["decision"],fx[r],val["attempts"],origin,val["cache_hit"])
            if obj.get("last_alarm"):
                v=obj["last_alarm"];what={"get_up":"Phil gets out of bed.","stay_in_bed":"Phil turns over.","listen_again":"The second backfire sounds."}[v["decision"]["action"]]
                slot((4,2,"reporter"),v["decision"],what,v["attempts"],None,v["cache_hit"])
        else:
            for beat in obj.get("beats",[]):
                fx=beat["owner_after"]+" holds the original interview reel."
                if beat["disclosure"]:fx+=" "+beat["disclosure"]
                slot((1,beat["beat"],"producer"),beat["decision"],fx,beat["attempts"])
        for k in list(pending):slot(k)

def blocking(slots,refs,read_object):
    for file in sorted((NIGHT/"blocking/draws").glob("*/performance.json")):
        row=read_object(file);resp=row["response"];think=row["request"]["think"]
        rid="blocking-"+file.parent.name;tag="Unscripted gesture · "+("on" if think else "off")
        slotfile="../"+str(file.relative_to(NIGHT))
        refs[rid]={"kind":"performance","file":slotfile,"url":"/sources/"+rid+".json","stage":"returned","chars":len(resp["message"].get("thinking",""))}
        move=None;effect="";resolution=file.with_name("resolution.json")
        if resp.get("done_reason")=="stop":
            try:
                d=json.loads(resp["message"]["content"])
                move={"action":d["gesture"],"words":d["words"]}
            except (ValueError,KeyError):pass
        if resolution.exists():
            x=read_object(resolution)
            effect=("Engine act · "+x["mapped_action"]["action"] if x["simulated"] else "The engine did not execute this proposal.")
        actor="Phil" if row["arm"].startswith("film-") else "Ellis"
        slots.append({"id":rid,"persona":tag,"day":int(row["sources"][-1][1:3]),"tick":0,"role":"reporter","actor":actor,
                      "short":"Wake "+file.parent.name,"when":"Morning back at the inn","stage":"returned proposal" if move else "invalid draw",
                      "action":move,"consequence":effect,"requests":[rid],"original_slot":None,"event_id":row["sources"][-1]})

def two_channels(slots,refs,read_object):
    for file in sorted((NIGHT/"blocking/two-channels").glob("*.json")):
        row=read_object(file);rid="two-fields-"+file.stem
        response=row["response"]
        refs[rid]={"kind":"performance","file":"../"+str(file.relative_to(NIGHT)),"url":"/sources/"+rid+".json","stage":"returned",
                   "chars":len(response["message"].get("thinking",""))}
        act=row["decision"];p=row["physical"]
        slots.append({"id":rid,"persona":"Gesture with physical act","day":int(row["sources"][-1][1:3]),"tick":0,"role":"reporter",
                      "actor":"Phil" if row["arm"].startswith("film-") else "Ellis","short":"Wake "+file.stem,"when":"Morning back at the inn",
                      "stage":"returned branch" if p else "invalid draw","action":act,"consequence":p["effect"] if p else row["error"],
                      "requests":[rid],"original_slot":None,"event_id":row["sources"][-1]})

def epilogues(slots,refs,read_object,read_lines):
    for folder in sorted((NIGHT/"last-reel/epilogues").glob("*")):
        if not folder.is_dir():continue
        routes={};last={}
        for req in read_lines(folder/"request-index.ndjson"):
            rid="epilogue-"+folder.name+"/"+req["id"];role=req["role"]
            f=folder/req["stream"]
            refs[rid]={"kind":"stream","file":"../"+str(f.relative_to(NIGHT)),"url":"/sources/"+rid+".ndjson","stage":req["stage"],"chars":req.get("thinking_chars",0)}
            if rid not in routes.setdefault(role,[]):routes[role].append(rid)
            last[role]=req
        for role,rids in routes.items():
            file=folder/(role+".json");row=read_object(file) if file.is_file() else {}
            slot="epilogue-"+folder.name+"-"+role
            tag="The morning after · "+folder.name.title()
            slots.append({"id":slot,"persona":tag,"day":last[role]["day"],"tick":0,"role":role,"actor":NAMES[role],"short":folder.name.title()+" morning",
                         "when":folder.name.title()+" · Six o’clock","stage":"committed" if row else ("generating" if last[role]["stage"]=="started" else last[role]["stage"]),
                         "action":row.get("decision"),"consequence":row.get("effect",""),"requests":rids,"original_slot":None,"event_id":slot})
