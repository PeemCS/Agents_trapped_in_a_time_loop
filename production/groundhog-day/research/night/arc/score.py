"""Read-only audit of the six Rialto paths using the local source and frozen review judgments."""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json
import os
import re
import sys

HERE = Path(__file__).resolve().parent
NIGHT = HERE.parent
REEL = NIGHT / "last-reel"
sys.path.insert(0, str(NIGHT/"story"))
sys.path.insert(0, str(REEL))
import scene
from inference import canonical, validate

RUBRIC_SHA = "efe6b7b3456a3b34018172712e63ca9eb46358a61e18b48a6ee7f11b37a8416c"
PHASE = {"afternoon":"A","evening":"E","alarm":"Z"}
ENGAGE = {"help_driver", "record_Alma", "play_piano", "go_to_party", "ask_Rita_to_dance", "call_sister"}
BED = {"stay_in_bed", "go_to_bed"}
LITERAL_SOLITUDE = BED | {"sit_at_depot", "sleep_at_terminal", "wait_for_morning", "wait_at_Rialto"}
CINEMA = re.compile(r"\b(?:Groundhog Day|Bill Murray|in the (?:original )?(?:film|movie)|(?:way|ending) it (?:works|breaks) in the film)\b", re.I)
def digest(path): return sha256(path.read_bytes()).hexdigest()
def rel(path): return os.path.relpath(path, HERE)
def yes_order(a,b,c=None):
    if c is None: return any(x<y for x in a for y in b)
    return any(x<y<z for x in a for y in b for z in c)

def decoded(turn, expected):
    assert turn["messages"]==expected
    attempts=turn["attempts"]
    final=None;used_msgs=None
    for attempt in attempts:
        path=REEL/attempt["stream"]
        assert digest(path)==attempt["stream_sha256"]
        with path.open() as f:
            header=json.loads(next(f))
            body=header["body"]
            assert header["kind"]=="request" and header["request_sha256"]==sha256(canonical(body)).hexdigest()
            assert body["messages"][:2]==expected and body["think"] is True
            blocks=[z["provider"] for line in f if (z:=json.loads(line)).get("kind")=="chunk"]
        why="".join(z["message"].get("thinking","") for z in blocks if "message" in z)
        answer="".join(z["message"].get("content","") for z in blocks if "message" in z)
        assert why==attempt["public_thinking"]
        if attempt is attempts[-1]:
            assert blocks[-1]["done"] and blocks[-1]["done_reason"]=="stop"
            assert validate(answer,body["format"]["properties"]["action"]["enum"])==turn["decision"]
            final=(path,why)
            used_msgs=body["messages"]
    return final,used_msgs

def one_turn(n,phase,turn,expected,effect,judgment,additional=None):
    (path,why),actual_messages=decoded(turn,expected)
    opts=json.loads(expected[1]["content"])["physical_choices"]
    decision=turn["decision"];action=decision["action"];slot=str(n)+PHASE[phase]
    assert action in opts
    streams={**decision,"reasoning":why}
    coded=judgment.get("solitude",{}).get(slot)
    if coded:
        assert action in LITERAL_SOLITUDE|{"spend_time_here"}
        assert coded[1] in decision["intention"] or coded[1] in decision["words"]
    if action in LITERAL_SOLITUDE:assert coded
    recognition=judgment["recognition"] if judgment["recognition"]["slot"]==slot else None
    structured=judgment.get("structured_recognition")
    if structured and structured["slot"]!=slot:structured=None
    for tag in (recognition,structured):
        if tag:assert tag["excerpt"] in streams[tag["channel"]]
    tags={}
    for field in ("words","intention","detail","reasoning"):
        tags[field]=list(dict.fromkeys(m.group() for m in CINEMA.finditer(streams[field])))
    # All raw spoken fields were also read for unnamed cinematic allusions when writing judgments.json.
    assert not tags["words"], f"Review public recognition in {slot}"
    return {"slot":slot,"phase":phase,"action":action,"effect":effect,"menu":list(opts),"words":decision["words"],
            "intention":decision["intention"],"physical_solitude":action in LITERAL_SOLITUDE,
            "withdrawal":bool(coded and coded[0]=="withdrawal"),"solitude_judgment":coded,
            "engagement":action in ENGAGE,"bed_available":bool(BED&set(opts)),"outward_option":bool(ENGAGE&set(opts)),
            "coach_was_available":"take_coach" in opts,"file":rel(path),"stream_sha256":digest(path),
            "provider_attempts":len(turn["attempts"]),"recognition":recognition,"structured_recognition":structured,
            "film_terms_in_base_input":list(dict.fromkeys(CINEMA.findall(" ".join(m["content"] for m in expected)))),
            "film_terms_in_repair_context":list(dict.fromkeys(CINEMA.findall(" ".join(m["content"] for m in actual_messages[2:])))),
            "film_terms_by_output_channel":tags,**(additional or {})}

def read_case(path,judgment):
    row=json.loads(path.read_bytes());rid=path.parent.name
    assert row["status"]=="complete" and len(row["days"])==3
    src=row["source"];parent=NIGHT/src["source"]
    assert src["sha256"]==digest(parent)
    orig=json.loads(parent.read_bytes());ids={e["id"]:e for e in orig["events"]}
    ride,city,wake=[ids[i] for i in src["events"]]
    assert ride["decision"]["action"]=="take_coach_to_Pittsburgh" and city["place"]=="Pittsburgh"
    assert city["decision"]["action"]=="call_sister" and wake["origin"]=="inn" and wake["clock"]=="6:00 am"
    trapped={"source":rel(parent),"sha256":src["sha256"],"ids":src["events"],"ride":ride["effect"],
             "evening":city["effect"],"next_place":wake["origin"],"reset":src["memory"][-1]["witnessed"]}
    history=[];external=False;records=[]
    for day in row["days"]:
        n=day["day"]
        a={x:t["decision"] for x,t in day["afternoon"].items()}
        e={x:t["decision"] for x,t in day["evening"].items()}
        state=scene.afternoon(a);end=scene.evening(e,state)
        assert state==day["afternoon_state"] and end==day["ending"] and end["closed_clock"]=="Tuesday"
        prior=src["memory"]
        first=scene.input_for("reporter","afternoon",row["condition"],prior,history,{"afternoon_memory":{}},external,n)[0]
        records.append(one_turn(n,"afternoon",day["afternoon"]["reporter"],first,state["effects"]["reporter"],judgment))
        daily=state["afternoon_memory"]["reporter"]+state["seen"]["reporter"]
        second,opts=scene.input_for("reporter","evening",row["condition"],prior,history+daily,state,external,n)
        # A one-choice intervention: all three morning choices and both independent evening partners remain fixed.
        can_offer="ask_Rita_to_dance" in opts
        would_dance=False
        if can_offer:
            alt={**e,"reporter":{**e["reporter"],"action":"ask_Rita_to_dance"}}
            would_dance=scene.evening(alt,state)["dance"]
        extra={"in_city":state["city"],"co_present_at_party":end["both_at_party"],"dance":end["dance"],
               "could_offer_dance":can_offer,"dance_if_offered_with_cast_fixed":would_dance,
               "rita_action":e["producer"]["action"],"larry_action":e["camera"]["action"],
               "interview_delivered":end["delivered"],"next_closed_clock":end["closed_clock"]}
        if a["reporter"]["action"]=="record_Alma":
            ordinary={**a,"reporter":{**a["reporter"],"action":"spend_time_here"}}
            alternate_state=scene.afternoon(ordinary)
            assert all(e[role]["action"] in scene.options(role,"evening",alternate_state) for role in scene.ROLES)
            extra["delivery_if_phil_stayed_in_lobby_instead_of_recording"]=scene.evening(e,alternate_state)["delivered"]
        records.append(one_turn(n,"evening",day["evening"]["reporter"],second,end["effects"]["reporter"],judgment,extra))
        history.append({"afternoon":state["effects"]["reporter"],"evening":end["effects"]["reporter"],
                        "what_you_said":e["reporter"]["words"],"your_last_intention":e["reporter"]["intention"],"next_wake":scene.ALARM})
        if end["both_at_party"]:history[-1]["also_seen"]="You saw Rita at the ballroom."
        external=external or end["delivered"]
    assert history==row["reporter_memory"] and external==row["external_receipt"]
    alarm=scene.input_for("reporter","alarm",row["condition"],src["memory"],history,{"afternoon_memory":{}},external,4)[0]
    choice=row["last_alarm"]["decision"]["action"]
    records.append(one_turn(4,"alarm",row["last_alarm"],alarm,"Committed final alarm choice: "+choice,judgment))
    ident=[i for i,r in enumerate(records) if r["recognition"]]
    w=[i for i,r in enumerate(records) if r["withdrawal"]]
    outward=[i for i,r in enumerate(records) if r["engagement"]]
    solitude=[i for i,r in enumerate(records) if r["physical_solitude"]]
    assert len(ident)==1 and {r["slot"] for r in records if r["solitude_judgment"]}==set(judgment["solitude"])
    return {"name":rid,"condition":row["condition"],"seed":row["seed"],"take":rel(path),"take_sha256":digest(path),
            "trap":trapped,"turns":records,
            "scores":{"trap":True,"film_backend":True,"film_spoken":False,"withdrawal":bool(w),"engagement":bool(outward),
                      "withdraw_then_engage":yes_order(w,outward),"film_then_withdraw_then_engage":yes_order(ident,w,outward),
                      "spoken_film_then_withdraw_then_engage":False,
                      "film_then_bare_solitude_then_engage":yes_order(ident,solitude,outward)}}

def summarize(cases):
    scores=Counter();events=Counter()
    for case in cases:
        scores.update({k:int(v) for k,v in case["scores"].items()})
        for t in case["turns"]:
            events["decisions"]+=1
            for k in ("physical_solitude","withdrawal","engagement","outward_option","bed_available",
                      "coach_was_available","could_offer_dance","dance_if_offered_with_cast_fixed",
                      "co_present_at_party","dance","interview_delivered"):
                events[k]+=int(t.get(k,False))
            events["take_coach"]+=int(t["action"]=="take_coach")
            events["explicit_bed"]+=int(t["action"] in BED)
            events["get_up"]+=int(t["phase"]=="alarm" and t["action"]=="get_up")
            events["attempts_audited"]+=t["provider_attempts"]
    return {"score_path_counts":dict(scores),"turn_counts":dict(events)}

if __name__=="__main__":
    assert digest(HERE/"rubric.md")==RUBRIC_SHA
    judgments=json.loads((HERE/"judgments.json").read_bytes())
    sources=sorted((REEL/"runs").glob("*/take.json"))
    assert len(sources)==6 and set(judgments)=={p.parent.name for p in sources}
    cases=[read_case(p,judgments[p.parent.name]) for p in sources]
    data={"rubric_sha256":RUBRIC_SHA,"reviewer":"Independent Codex agent applying the frozen qualitative rubric","judgments_sha256":digest(HERE/"judgments.json"),**summarize(cases),"cases":cases}
    (HERE/"scores.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:v for k,v in data.items() if k!="cases"},indent=2))
