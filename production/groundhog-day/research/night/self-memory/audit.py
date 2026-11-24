"""Verify source identity, private message isolation, exact treatment and physical receipts offline."""
import copy
import json
import re
from pathlib import Path
from run import (ROOT, OUT, TAKE, MATCHED, PREVIOUS, SEED, SEEDS, MODEL, NOTE, CONTROL, KEY,
                 ROLES, treatment, request, sha, canonical, afternoon, evening, input_for, validate,
                 afternoon_decisions, save)

def read(p):
    return json.loads(p.read_bytes())

def records(path):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert rows[0]["request_sha256"] == sha(canonical(rows[0]["body"]))
    chunks = [r["provider"] for r in rows[1:]]
    assert chunks and chunks[-1]["done"] and sum(bool(r.get("done")) for r in chunks)==1
    return (rows[0], "".join(r["message"].get("thinking","") for r in chunks),
            "".join(r["message"].get("content","") for r in chunks),chunks[-1])

def original(folder):
    return folder/"canonical-stream.ndjson"

def first(folder):
    if original(folder).exists():
        return original(folder)
    for path in (folder/"streams").glob("*.ndjson"):
        with path.open() as f:
            header=json.loads(next(f))
        if not header["repair"]:
            return path
    raise ValueError(folder)

def compare():
    source=request(MATCHED["afternoon"]["reporter"])
    check=[]
    for seed in SEEDS:
        for condition in ("none","full","control"):
            folder=OUT/f"{seed}-{condition}-wake"
            result=read(folder/"decision.json")
            head, thinking, raw, end=records(first(folder))
            body=copy.deepcopy(source)
            body["messages"]=treatment(source["messages"],condition)
            body["options"]["seed"]=seed
            assert body == head["body"]
            fields=json.loads(raw)
            exceeds={k:len(v) for k,v in fields.items() if isinstance(v,str) and len(v)>1200}
            if result["status"]=="valid":
                assert validate(raw,list(json.loads(body["messages"][-1]["content"])["physical_choices"])) == result["decision"]
                assert read(folder/"resolved.json")==afternoon(afternoon_decisions(result))
            item={"seed":seed,"condition":condition,"request_sha256":head["request_sha256"],
                  "first_stream_sha256":sha(first(folder).read_bytes()),"status":result["status"],
                  "first_candidate":fields.get("action"),"enacted_first":result.get("decision",{}).get("action"),
                  "public_words":fields.get("words") if result["status"]=="valid" else None,"overlong_fields":exceeds,
                  "native_chars":len(thinking),"native_mentions_film_title":bool(re.search("Groundhog Day",thinking,re.I)),
                  "native_mentions_piano":bool(re.search(r"\bpiano\b",thinking,re.I)),
                  "spoken_mentions_film_title":bool(re.search("Groundhog Day",fields["words"],re.I)),
                  "completion_tokens":end.get("eval_count"),"finish_reason":end["done_reason"]}
            repair=folder/"supplemental-repair.json"
            if repair.exists():
                resolved=read(repair)
                path=next(p for p in (folder/"streams").glob("*.ndjson") if p!=first(folder))
                hdr,th,rr,last=records(path)
                expected=copy.deepcopy(body)
                expected["messages"] += [{"role":"assistant","content":raw},{"role":"user","content":"Choose the physical act and return the four required JSON strings."}]
                expected["options"].update(seed=seed+1,num_predict=6144)
                assert expected==hdr["body"]
                if resolved["status"]=="valid":
                    assert validate(rr,list(json.loads(body["messages"][-1]["content"])["physical_choices"])) == resolved["decision"]
                    assert read(folder/"supplemental-resolved.json")==afternoon(afternoon_decisions(resolved))
                item["repair"]={"status":resolved["status"],"enacted":resolved.get("decision",{}).get("action"),
                                "finish_reason":last["done_reason"],"native_chars":len(th),"hash":hdr["request_sha256"]}
            check.append(item)
    cont=read(OUT/"continued-evening.json")
    full=read(OUT/f"{SEED}-full-wake/decision.json")
    state=afternoon(afternoon_decisions(full))
    assert state==cont["afternoon"]
    privacy={}
    for role in ROLES:
        folder=OUT/f"{SEED}-full-evening-{role}"
        head,_,raw,_=records(first(folder))
        msgs,actions=input_for(role,"evening","uncued",TAKE["source"]["memory"],
                        [TAKE["reporter_memory"][0]]+state["afternoon_memory"]["reporter"]+state["seen"]["reporter"],
                        state, PREVIOUS["ending"]["delivered"],2)
        if role=="reporter":
            msgs=treatment(msgs,"full")
        else:
            assert KEY not in str(msgs) and NOTE not in str(msgs) and CONTROL not in str(msgs)
        assert head["body"]["messages"]==msgs and list(head["body"]["format"]["properties"]["action"]["enum"])==actions
        assert head["body"]["options"]["seed"] == MATCHED["evening"][role]["seed"]
        assert validate(raw,actions)==cont["cast"][role]["decision"]
        orig=MATCHED["evening"][role]
        privacy[role]={"original_request_sha256":sha(canonical(request(orig))),
                       "current_request_sha256":head["request_sha256"],"private_note_supplied":role=="reporter",
                       "old_action":orig["decision"]["action"],"new_action":cont["cast"][role]["decision"]["action"]}
    assert evening({r:v["decision"] for r,v in cont["cast"].items()},state)==cont["ending"]
    calls=len(list(OUT.glob("*/reservation-*.json")))
    streams=len(list(OUT.glob("*/streams/*.ndjson")))
    assert calls==streams<=10
    return {"verified_new_provider_calls":calls,"seeds":SEEDS,"wakes":check,"evening":privacy,
            "physical_ending":cont["ending"],"source_physical_ending":MATCHED["ending"]}
if __name__=="__main__":
    save(OUT/"audit.json",compare())
