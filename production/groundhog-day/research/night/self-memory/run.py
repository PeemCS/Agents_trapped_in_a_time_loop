"""Private counterfactual on a sealed Rialto take. All writes stay beside this file."""
from datetime import datetime
import copy
import hashlib
import json
import os
import re
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
NIGHT = ROOT.parent
REEL = NIGHT / "last-reel"
ORIG = REEL / "runs/721-uncued"
sys.dont_write_bytecode = True
sys.path[:0] = [str(REEL), str(NIGHT / "thinking"), str(NIGHT / "story")]
from scene import ROLES, input_for, afternoon, evening
from ensemble import ObservableOllama
from inference import canonical, object_schema, validate

URL = "http://127.0.0.1:18527"
MODEL = "qwen3.8:27b"
DEADLINE = datetime.fromisoformat("2026-11-23T06:04:45-08:00").timestamp()
LIMIT = 10
OUT = ROOT / "results"
LOCK = threading.Lock()
TAKE = json.loads((ORIG / "take.json").read_bytes())
PREVIOUS, MATCHED = TAKE["days"][:2]
SEED = MATCHED["afternoon"]["reporter"]["seed"]
SEEDS = (SEED, SEED + 1009)
ERASE = " from Groundhog Day"

def sha(b):
    return hashlib.sha256(b).hexdigest()

def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".partial")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)

def stream(turn):
    attempt = turn["attempts"][-1]
    path = REEL / attempt["stream"]
    assert sha(path.read_bytes()) == attempt["stream_sha256"]
    return path

def request(turn):
    with stream(turn).open() as f:
        head = json.loads(next(f))
    assert sha(canonical(head["body"])) == head["request_sha256"]
    return head["body"]

def native(turn):
    rows = [json.loads(l) for l in stream(turn).read_text().splitlines()]
    text = "".join(r["provider"]["message"].get("thinking","") for r in rows[1:])
    assert text == turn["attempts"][-1]["public_thinking"]
    return text

source = PREVIOUS["evening"]["reporter"]
NOTE = native(source)
assert NOTE.count(ERASE) == 1 and not re.search("groundhog day|movie|film", NOTE.replace(ERASE,""), re.I)
CONTROL = NOTE.replace(ERASE,"")
KEY = "your_private_note_from_last_evening"

def treatment(messages, condition):
    msgs = copy.deepcopy(messages)
    if condition == "none":
        return msgs
    data = json.loads(msgs[-1]["content"])
    entries = data["your_own_memories"]
    entries.append({KEY: NOTE if condition == "full" else CONTROL})
    msgs[-1]["content"] = json.dumps(data, ensure_ascii=False, indent=1)
    check = json.loads(msgs[-1]["content"])
    check["your_own_memories"].pop()
    assert check == json.loads(messages[-1]["content"])
    return msgs

def preserve(name, turn):
    folder = OUT / name
    folder.mkdir(parents=True, exist_ok=True)
    path = stream(turn)
    shutil.copyfile(path, folder / "canonical-stream.ndjson")
    data = {"status":"valid","source":"canonical replay, no new inference","decision":turn["decision"],
            "request":request(turn),"source_request_key":turn["key"],"source_stream":str(path.relative_to(NIGHT)),
            "stream_sha256":sha(path.read_bytes())}
    save(folder / "decision.json",data)
    return data

def call(name, role, phase, messages, actions, seed):
    folder = OUT / name
    result = folder / "decision.json"
    if result.exists():
        return json.loads(result.read_bytes())
    folder.mkdir(parents=True, exist_ok=True)
    if role != "reporter":
        assert KEY not in str(messages) and NOTE not in str(messages) and CONTROL not in str(messages)
    request_hashes = []
    # Repairs are secondary and retained separately. They never change the primary wake statistic.
    attempt_msgs = messages
    for attempt in range(2):
        if attempt == 1 and name.endswith("wake"):
            break
        with LOCK:
            starts = list(OUT.glob("*/reservation-*.json"))
            if len(starts) >= LIMIT or time.time() >= DEADLINE - 45:
                break
            reservation = folder / f"reservation-{attempt}.json"
            if reservation.exists():
                raise RuntimeError(f"An interrupted reservation exists: {reservation}")
            save(reservation,{"call_number":len(starts)+1,"seed":seed+attempt,"role":role,"phase":phase})
        latest = SimpleNamespace(model=MODEL,base_url=URL,temperature=.8,num_ctx=8192,max_tokens=3072,
                                 timeout=min(420,max(1, int(DEADLINE-time.time()))))
        backend = ObservableOllama(latest,folder)
        raw,meta = backend.respond(role,(2,0 if phase=="afternoon" else 1),attempt_msgs,actions,seed+attempt)
        archive = folder / meta["stream_path"]
        with archive.open() as f:
            h = json.loads(next(f))
        request_hashes.append(h["request_sha256"])
        save(folder / f"response-{attempt}.json",{"meta":meta,"raw_final":raw,"body":h["body"]})
        try:
            if meta["finish_reason"] != "stop":
                raise ValueError("response capped")
            decision = validate(raw,actions)
        except (ValueError,TypeError) as e:
            error = str(e)
            attempt_msgs = messages + [{"role":"assistant","content":raw},{"role":"user","content":"Choose the physical act and return the four required JSON strings."}]
            continue
        data = {"status":"valid","decision":decision,"request_hashes":request_hashes,"attempt":attempt,"source":"new draw"}
        save(result,data)
        return data
    data = {"status":"invalid","error":locals().get("error","call/time limit"),"request_hashes":request_hashes}
    save(result,data)
    return data

def afternoon_decisions(d):
    return {r:(d["decision"] if r=="reporter" else MATCHED["afternoon"][r]["decision"]) for r in ROLES}

def wake(condition,seed):
    label = f"{seed}-{condition}-wake"
    orig = MATCHED["afternoon"]["reporter"]
    body = request(orig)
    messages = treatment(body["messages"],condition)
    actions = list(json.loads(body["messages"][-1]["content"])["physical_choices"])
    assert body == {"model":MODEL,"stream":True,"think":True,"messages":orig["messages"],"format":object_schema(actions),
                    "options":{"temperature":.8,"num_ctx":8192,"num_predict":3072,"seed":SEED}}
    if condition=="none" and seed==SEED:
        result = preserve(label,orig)
    else:
        result = call(label,"reporter","afternoon",messages,actions,seed)
    if result["status"]=="valid":
        state = afternoon(afternoon_decisions(result))
        save(OUT / label / "resolved.json",state)
    return result

def extend(d):
    state = afternoon(afternoon_decisions(d))
    prior = TAKE["source"]["memory"]
    history = [TAKE["reporter_memory"][0]]
    external = PREVIOUS["ending"]["delivered"]
    original = MATCHED["afternoon_state"]
    def build(role, state):
        own = history + state["afternoon_memory"]["reporter"] + state["seen"]["reporter"]
        return input_for(role,"evening","uncued",prior,own,state,external,2)
    def actor(role):
        target = MATCHED["evening"][role]
        old, _ = build(role,original)
        assert old == target["messages"]
        msgs, opts = build(role,state)
        if role=="reporter":
            msgs = treatment(msgs,"full")
        name = f"{SEED}-full-evening-{role}"
        if msgs == old:
            return role,preserve(name,target)
        return role,call(name,role,"evening",msgs,opts,target["seed"])
    with ThreadPoolExecutor(max_workers=3) as pool:
        cast = dict(pool.map(actor,ROLES))
    if all(x["status"]=="valid" for x in cast.values()):
        ending = evening({r:v["decision"] for r,v in cast.items()},state)
        save(OUT / "continued-evening.json",{"afternoon":state,"cast":cast,"ending":ending})
        print("evening",json.dumps(ending),flush=True)
    else:
        save(OUT / "evening-unresolved.json",{r:v["status"] for r,v in cast.items()})

def main():
    os.umask(0o077)
    OUT.mkdir(exist_ok=True)
    digest = TAKE["source"]["digest"]
    with urlopen(URL+"/api/tags",timeout=10) as f:
        assert any(m["name"]==MODEL and m["digest"]==digest for m in json.load(f)["models"])
    scene = (REEL/"scene.py").read_bytes()
    assert sha(scene+(REEL/"shoot.py").read_bytes()) == TAKE["code"]
    assert "groundhog day" not in json.dumps(request(source)["messages"]).lower()
    save(OUT/"provenance.json",{"film":"721-uncued","source_day":1,"source_phase":"evening","role":"reporter",
         "take_sha256":sha((ORIG/"take.json").read_bytes()),"source_stream":str(stream(source).relative_to(NIGHT)),
         "source_stream_sha256":sha(stream(source).read_bytes()),"source_request_sha256":sha(canonical(request(source))),
         "note_sha256":sha(NOTE.encode()),"control_sha256":sha(CONTROL.encode()),"note_chars":len(NOTE),
         "single_edit":{"removed":ERASE,"start_offset":NOTE.index(ERASE)},"wrapper":KEY,"seeds":SEEDS,
         "model_digest":digest,"scene_sha256":sha(scene),"budget_new_calls":LIMIT,"canonical_evening":MATCHED["ending"]})
    (OUT/"original-note.txt").write_bytes(NOTE.encode())
    (OUT/"control-note.txt").write_bytes(CONTROL.encode())
    # The original morning decisions of Rita and Larry were made before either heard this new Phil.
    for role in ("producer","camera"):
        assert input_for(role,"afternoon","uncued",TAKE["source"]["memory"],[TAKE["reporter_memory"][0]],{"afternoon_memory":{}},PREVIOUS["ending"]["delivered"],2)[0] == MATCHED["afternoon"][role]["messages"]
    assert afternoon({r:MATCHED["afternoon"][r]["decision"] for r in ROLES}) == MATCHED["afternoon_state"]
    assert evening({r:MATCHED["evening"][r]["decision"] for r in ROLES},MATCHED["afternoon_state"]) == MATCHED["ending"]
    with ThreadPoolExecutor(max_workers=3) as pool:
        primary = pool.submit(wake,"full",SEED)
        jobs = [pool.submit(wake,c,s) for s in SEEDS for c in ("none","control","full") if (s,c)!=(SEED,"full")]
        first = primary.result()
        if first["status"]=="valid":
            extend(first)
        for job in jobs:
            job.result()
    print("complete",flush=True)

if __name__ == "__main__":
    main()
