"""Strict read-only micro-fork of one specific archived hotel checkpoint."""
import copy
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
NIGHT=HERE.parent
sys.path.insert(0,str(NIGHT/"story"))
import world
import world_v2
from inference import canonical, validate

ROOT=NIGHT/"thinking/runs/guarded/seed-731.json"
ROOT_SHA="c68f58f7f57563cfa3c3c29a476ab4d1abf9a8724e146673b4c018e54e511e10"
STREAM_SHA="5feb773f409418f18bef3c8209297b221dbed8a19fdc3be14af19ec202ea4bfe"
SEEDS=(1306712661,1306712662)
VARIANTS=("original","local","routed")
LENS={"local":"LOCAL CALLS ONLY","routed":"LOCAL AND LONG-DISTANCE CALLS"}

def checksum(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def source():
    if checksum(ROOT)!=ROOT_SHA:raise ValueError("Archive changed")
    row=json.loads(ROOT.read_bytes());e=row["events"][8];inf=e["inference"]
    assert e["id"]=="d03-t00-reporter" and e["origin"]=="inn" and e["day"]==3
    assert inf["sampling_seed"]==SEEDS[0]
    stream=ROOT.parent/inf["attempts"][0]["stream_path"]
    if checksum(stream)!=STREAM_SHA:raise ValueError("Original model stream changed")
    with stream.open() as f:header=json.loads(next(f))
    body=header["body"]
    assert body["messages"]==inf["messages"] and hashlib.sha256(canonical(body)).hexdigest()==header["request_sha256"]
    return row,e,stream,body

def make_body(variant,seed):
    if variant not in VARIANTS or seed not in SEEDS:raise ValueError("Unknown preregistered case")
    _,_,_,body=source()
    body["options"]["seed"]=seed
    if variant=="original":return body
    obs=json.loads(body["messages"][1]["content"])
    ix=next(i for i,s in enumerate(obs["evidence_now"]) if "a payphone" in s)
    obs["evidence_now"][ix]+=" A plate on the payphone reads “"+LENS[variant]+"”."
    if variant=="routed":
        obs["available_actions"]["call_sister"]="Use the lobby payphone to call your sister in Pittsburgh."
        body["format"]["properties"]["action"]["enum"].append("call_sister")
    body["messages"][1]["content"]=json.dumps(obs,indent=1,ensure_ascii=False)
    return body

def resolve(variant,decision,source_request,source_response):
    row,archived,_,_=source()
    menu=make_body(variant,SEEDS[0])["format"]["properties"]["action"]["enum"]
    if decision["action"] not in menu:raise ValueError("Action unavailable on this instrument")
    decisions={e["role"]:copy.deepcopy(e["decision"]) for e in archived["cast"]}
    decisions["reporter"]=copy.deepcopy(decision)
    placed=decision["action"]=="call_sister"
    # The standard resolver applies the frozen simultaneous neighbors, signals, witnesses and movement.
    # A new lobby call occupies the whole period at the inn, with a separately admitted instrument receipt.
    if placed:decisions["reporter"]["action"]="spend_time_here"
    pre=archived["world_before"];names=row["cast_names"]
    after,events=world_v2.resolve(row["seed"],3,0,pre,decisions,names,"move","bulletin")
    if not placed:return after,events,[]
    lead=events["reporter"];old=lead["effect"]
    dest,effect=world.physical("reporter",decision,pre,after,0,names)
    assert dest==pre["positions"]["reporter"]=="inn" and after["called_sister"]
    lead.update(decision=copy.deepcopy(decision),effect=effect)
    for role,event in events.items():
        heard=effect if role=="reporter" else f"{names['reporter']} makes a phone call from the lobby payphone."
        event["observed"]=[heard if line==old else line for line in event["observed"]]
    receipt={"event_id":"d03-t00-reporter/payphone","source_event_id":lead["id"],"actor":names["reporter"],"from":"inn",
             "instrument":"hotel lobby payphone","exchange":"Pittsburgh","connected_to":"reporter's sister",
             "confirmed":"Moving van booked for Wednesday","source_request_sha256":source_request,"source_response_sha256":source_response}
    return after,events,[receipt]
