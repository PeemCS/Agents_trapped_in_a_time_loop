"""Build an offline shot ledger for the two mixed films, using recovered source IDs."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
NIGHT=HERE.parent
SETS=[("wednesday-couch","Wednesday’s couch","film-transcript",701),
      ("afternoon-coach","The afternoon coach","film-transcript",702)]


def catalog(name,title,cast,seed,family="q27",timing_name=None):
    import hashlib
    raw=(NIGHT/"takes"/family/cast/f"seed-{seed}.json").read_bytes()
    trace=json.loads(raw);timing=json.loads((NIGHT/"editor"/(timing_name or name)/"timing.json").read_bytes())
    assert hashlib.sha256(raw).hexdigest()==timing["source_sha256"]
    header={"id":name,"title":title,"film":"../editor/"+name+"/film.mp4","poster":name+".jpg","model":trace["model"],
            "seed":seed,"hash":timing["source_sha256"],"shots":[]}
    for shot in timing["shots"]:
        row=trace["events"][shot["event_index"]]
        assert row["id"]==shot["event_id"]
        person=next((a for a in [row,*row["cast"]] if a["actor"]==shot.get("focus")),row)
        header["shots"].append({"at":round(shot["first_frame"]/timing["fps"],3),"day":row["day"],"clock":row["clock"],
                     "id":person["id"],"focus":person["actor"],"action":person["decision"]["action"],
                     "origin":person["origin"],"place":person["place"],"effect":person["effect"],"view":shot["view"],
                     "speech":[{"actor":s["actor"],"text":s["text"]} for s in shot["speech"]],
                     "others":[{"actor":a["actor"],"action":a["decision"]["action"],"place":a["place"]} for a in [row,*row["cast"]] if a["role"]!=person["role"]]})
    return header


def bulletin_catalog():
    header=catalog("seven-oclock","The seven o’clock bulletin","v2",711,"heldout","bulletin-711-opening")
    ed=NIGHT/"editor";feature=json.loads((ed/"seven-oclock/feature.json").read_bytes())
    board=json.loads((ed/"bulletin-711-final/receipt.json").read_bytes())
    run=json.loads((NIGHT/"takes/heldout/v2/seed-711.json").read_bytes())
    assert board["source_sha256"]==feature["source_sha256"]==header["hash"]
    assert board["on_air_from_s"]==19 and board["final_day"]==6
    for start,root in zip((0,4,8,14),run["events"][-4:]):
        people=[root,*root["cast"]]
        header["shots"].append({"at":feature["crew_monitor_start_s"]+start,"day":root["day"],"clock":root["clock"],
            "id":" / ".join(e["id"] for e in people),"focus":"The three crew monitors","action":"monitor",
            "origin":root["origin"],"place":root["place"],"effect":"Each member of the crew chooses during the same period.",
            "view":"monitors","speech":[],"others":[{"actor":e["actor"],"action":e["decision"]["action"],"place":e["place"]} for e in people]})
    bulletin=feature["actual_final_bulletin"];end=run["events"][-1]
    header["shots"].append({"at":feature["on_air_at_s"],"day":end["day"],"clock":end["clock"],
        "id":", ".join(bulletin["source_ids"]),"focus":bulletin["selected_by"],"action":bulletin["channel"],
        "origin":bulletin["source_place"],"place":bulletin["source_place"],"effect":"Rita opens her own microphone. The two incoming contributions remain off air.",
        "view":"carrier","speech":[{"actor":"Rita","text":bulletin["spoken"]}],"others":[]})
    assert bulletin["channel"]=="producer_live" and sorted(bulletin["delivered_assignments"])==["camera","reporter"]
    return header


def thinking_catalog():
    import hashlib
    folder=NIGHT/"editor/thinking-cut"
    receipt=json.loads((folder/"verification.json").read_bytes())
    path=NIGHT/"thinking/runs"/receipt["take"]/"seed-731.json"
    raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==receipt["source_sha256"]
    source=json.loads(raw)
    events={a["id"]:(row,a) for row in source["events"] for a in [row,*row["cast"]]}
    cues=json.loads((folder/"cues.json").read_bytes())
    shots=[]
    for segment in receipt["segments"]:
        start=segment["absolute_start_s"];end=start+segment["duration"]
        row,a=events[segment["event_id"]]
        is_note=segment["kind"]=="unspoken model note"
        speech=[{"actor":c["actor"],"text":c["text"]} for c in cues if c["type"]=="spoken" and start-.001<=c["start_s"]<end-.001]
        shots.append({"at":round(start,3),"day":a["day"],"clock":a["clock"],"id":a["id"],"focus":a["actor"],
                      "action":a["decision"]["action"],"origin":a["origin"],"place":a["place"],"effect":a["effect"],
                      "view":"unspoken" if is_note else segment.get("view","action"),"speech":speech,
                      "note":segment.get("quote") if is_note else None,"thinkingSlot":receipt["take"]+"-"+a["id"],
                      "others":[{"actor":b["actor"],"action":b["decision"]["action"],"place":b["place"]}
                                for b in [row,*row["cast"]] if b["id"]!=a["id"]]})
    return {"id":"thinking-cut","title":"Inside Phil’s take","film":"../editor/thinking-cut/film.mp4","poster":"thinking-cut.jpg",
            "model":source["model"],"seed":731,"hash":receipt["source_sha256"],"shots":shots}


def rialto_catalog():
    import hashlib
    folder=NIGHT/"editor/rialto-cut"
    receipt=json.loads((folder/"shot-evidence.json").read_bytes())
    runfile=NIGHT/"last-reel/runs"/receipt["take"]/"take.json"
    raw=runfile.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==receipt["source_sha256"]
    source=json.loads(raw);cues=json.loads((folder/"cues.json").read_bytes())
    labels={"archive":"Pittsburgh return line","ballroom":"Festival ballroom","local_depot":"Town depot","terminal":"Pittsburgh terminal",
            "hotel":"Hearthside Hotel","rialto":"Rialto booth","station":"Radio station"}
    shots=[]
    for shot in receipt["shots"]:
        d=shot["day"];phase=shot["phase"];role=shot["role"]
        t=0 if phase=="afternoon" else 1;event=source["days"][d-1][phase]
        assert event[role]["decision"]["action"]==shot["action"]
        start=shot["start_s"];end=shot["end_s"]
        speech=[{"actor":c["actor"],"text":c["text"]} for c in cues if c["type"]=="spoken" and start-.001<=c["start"]<end-.001]
        scene=labels.get(shot["scene"],shot["scene"].replace("_"," ").title())
        moment="Afternoon" if t==0 else "7:00 pm"
        note=shot["text"] if shot["kind"]=="note" else None
        fact=shot["text"] if shot["kind"] in ("receipt","reset") else shot["source_effect"]
        shots.append({"at":round(start,3),"day":d,"clock":moment,"id":shot["event_id"],"focus":shot["actor"],"action":shot["action"],
                      "origin":scene,"place":scene,"effect":fact,"view":"unspoken" if note else shot["kind"],"speech":speech,"note":note,
                      "thinkingSlot":f"last-reel-{receipt['take']}-d{d:02d}-t{t:02d}-{role}",
                      "others":[{"actor":q["speaker"],"action":q["decision"]["action"],"place":""} for who,q in event.items() if who!=role]})
    return {"id":"rialto-cut","title":"Eight Bars","film":"../editor/rialto-cut/film.mp4","poster":"rialto-cut.jpg",
            "model":"Qwen 27B","seed":source["seed"],"hash":receipt["source_sha256"],"shots":shots,
            "companion":"../editor/rialto-cut/index.html","companionLabel":"Trace the reel back to Alma ↗"}


if __name__=="__main__":
    data=[rialto_catalog(),thinking_catalog(),*[catalog(*s) for s in SETS],bulletin_catalog()]
    (HERE/"catalog.js").write_text("window.SCREENINGS="+json.dumps(data,ensure_ascii=False).replace("<","\\u003c")+";\n")
