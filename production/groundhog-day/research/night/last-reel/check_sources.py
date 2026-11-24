"""Verify every filmed action and exact observable input against the source and stream journals."""
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from scene import ROLES, ALARM, input_for, afternoon, evening, CLUE, BELIEF

HERE=Path(__file__).resolve().parent
NIGHT=HERE.parent
def digest(b):return hashlib.sha256(b).hexdigest()

@lru_cache(maxsize=None)
def stream(path):
    raw=path.read_bytes();rows=[json.loads(s) for s in raw.splitlines()]
    chunks=[r["provider"] for r in rows if r["kind"]=="chunk"]
    assert rows[0]["kind"]=="request" and chunks and chunks[-1].get("done") is True
    return {"sha":digest(raw),"body":rows[0]["body"],
            "thinking":"".join(c.get("message",{}).get("thinking","") for c in chunks),
            "content":"".join(c.get("message",{}).get("content","") for c in chunks),"end":chunks[-1]["done_reason"]}

def validate_actor(rec,messages,folder):
    assert rec["messages"]==messages
    infos=rec["attempts"]
    for a in infos:
        p=HERE/a["stream"] if "stream" in a else folder/a["stream_path"]
        t=stream(p)
        assert t["sha"]==a["stream_sha256"] and t["thinking"]==a["public_thinking"] and t["end"]==a["finish_reason"]
    assert stream(HERE/infos[0]["stream"] if "stream" in infos[0] else folder/infos[0]["stream_path"])["body"]["messages"]==messages
    assert t["end"]=="stop" and json.loads(t["content"])==rec["decision"]
    return len(infos)

def audit(p):
    r=json.loads(p.read_bytes());history=[];external=False;slots=attempts=cached=0
    source=r["source"];assert digest((NIGHT/source["source"]).read_bytes())==source["sha256"]
    for d in r["days"]:
        day=d["day"];before={"afternoon_memory":{}};daily=[]
        for ph in ("afternoon","evening"):
            for role in ROLES:
                rec=d[ph][role]
                msgs,_=input_for(role,ph,r["condition"],source["memory"],history+(daily if ph=="evening" else []),before,external,day)
                attempts+=validate_actor(rec,msgs,p.parent);slots+=1;cached+=rec["cache_hit"]
                if role!="reporter":
                    alt,_=input_for(role,ph,"hypothesis",["PRIVATE-PHIL-CANARY"],["PRIVATE-HISTORY-CANARY"],before,external,day)
                    assert msgs==alt
                body=json.loads(msgs[1]["content"])
                assert any("An envelope has arrived" in s for s in body["what_you_observe"])==(external and ph=="afternoon")
                assert (CLUE in body["what_you_observe"])==(role=="reporter" and day==1 and ph=="afternoon" and r["condition"]=="library")
                assert (BELIEF in msgs[0]["content"])==(role=="reporter" and day==1 and ph=="afternoon" and r["condition"]=="hypothesis")
            if ph=="afternoon":
                before=afternoon({k:v["decision"] for k,v in d[ph].items()});assert before==d["afternoon_state"]
                daily=before["afternoon_memory"]["reporter"]+list(before["seen"]["reporter"])
        ns={k:v["decision"] for k,v in d["evening"].items()}
        end=evening(ns,before);assert end==d["ending"]
        history.append({"afternoon":before["effects"]["reporter"],"evening":end["effects"]["reporter"],"what_you_said":ns["reporter"]["words"],"your_last_intention":ns["reporter"]["intention"],"next_wake":ALARM})
        if end["both_at_party"]:history[-1]["also_seen"]="You saw Rita at the ballroom."
        external=external or end["delivered"]
    assert r["reporter_memory"]==history and r["external_receipt"]==external
    if r.get("last_alarm"):
        m,_=input_for("reporter","alarm",r["condition"],source["memory"],history,{"afternoon_memory":{}},external,4)
        attempts+=validate_actor(r["last_alarm"],m,p.parent);slots+=1;cached+=r["last_alarm"]["cache_hit"]
    return {"run":p.parent.name,"status":r["status"],"decision_slots":slots,"attempt_references_including_reuses":attempts,
            "exact_cache_reuses":cached,"worlds_replayed":len(r["days"]),"raw_source_sha256":digest(p.read_bytes())}

def main():
    worlds=[audit(p) for p in sorted((HERE/"runs").glob("*/take.json"))]
    ep=[]
    for p in sorted((HERE/"epilogues").glob("*/*.json")):
        row=json.loads(p.read_bytes());assert digest((HERE/"runs"/row["source_run"]/"take.json").read_bytes())==row["source_sha256"]
        validate_actor(row,row["messages"],p.parent)
        ep.append({"rule":row["rule"],"role":row["role"],"chosen":row["decision"]["action"],"effect":row["effect"]})
    out={"evidence":"Exact role-visible input reconstructed from witnessed state and identity, raw NDJSON and decoded action identity, every recorded reducer transition, persistent external receipt timing, and role-card and history isolation canaries.","worlds":worlds,"epilogues":ep,
         "unique_native_streams_checked":stream.cache_info().currsize}
    (HERE/"source-audit.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    print("Audited",sum(w["decision_slots"] for w in worlds),"recorded slots and",len(ep),"epilogue roles")
if __name__=="__main__":main()
