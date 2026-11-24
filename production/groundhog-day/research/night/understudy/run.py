"""A small local cast plays fresh reactions using the Rialto world and action validator."""
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.request

HERE = Path(__file__).resolve().parent
NIGHT = HERE.parent
sys.path[:0] = [str(NIGHT / "last-reel"), str(NIGHT / "story")]
from inference import FIELDS, validate
from scene import ALARM, ROLES, afternoon, evening, input_for
from town import atomic_json

HOST = "http://127.0.0.1:11434"
MODEL = "qwen3:0.6b"


def query(messages, choices, seed):
    schema = {"type":"object", "properties":{f:{"type":"string"} for f in FIELDS},
              "required":list(FIELDS), "additionalProperties":False}
    schema["properties"]["action"]["enum"] = choices
    req = {"model": MODEL, "messages": messages, "think":False, "stream":True,
           "format":schema, "keep_alive":"90s",
           "options":{"num_ctx":4096,"num_predict":240,"temperature":0.8,"seed":seed}}
    post = urllib.request.Request(HOST + "/api/chat", data=json.dumps(req).encode(),
                                  headers={"Content-Type":"application/json"})
    started = time.monotonic()
    with urllib.request.urlopen(post, timeout=90) as answer:
        chunks = [json.loads(line) for line in answer if line.strip()]
    return {"request":req, "chunks":chunks, "wall_s":time.monotonic()-started}


def pick(role, day, phase, root, prior, history, state, external, folder):
    msgs, choices = input_for(role, phase, "uncued", prior, history, state, external, day)
    msgs[0] = {**msgs[0], "content":msgs[0]["content"] +
               " Return action, words, intention and detail. Choose an exact listed action. Keep each other field to one short sentence."}
    seed = 800000 + root*37 + (day if role == "reporter" else 0)*13 + ("afternoon","evening","alarm").index(phase)*3 + ROLES.index(role)
    attempts = []
    for attempt in range(2):
        sample = query(msgs, choices, seed + attempt)
        action_text = "".join(x["message"]["content"] for x in sample["chunks"])
        filename = f"d{day}-{phase}-{role}-{attempt+1}.json"
        atomic_json(folder / filename, sample)
        attempts.append(filename)
        try:
            if sample["chunks"][-1].get("done_reason") != "stop":
                raise ValueError("Generation did not stop normally")
            return {"decision":validate(action_text, choices), "attempts":attempts}
        except ValueError as error:
            msgs = msgs + [{"role":"assistant","content":action_text},
                           {"role":"user","content":"Return one exact physical choice with brief, complete JSON fields."}]
            if attempt == 1:
                raise ValueError(f"{filename}: {error}") from error


def run(root, tag):
    source_path = NIGHT / "last-reel/runs" / f"{root}-uncued/take.json"
    source_data = source_path.read_bytes()
    prior = json.loads(source_data)["source"]["memory"]
    folder = HERE / f"seed-{root}"
    folder.mkdir(exist_ok=True)
    result = folder / "take.json"
    if result.exists():
        return
    record = {"root":root,"model":tag["name"],"revision":tag["digest"],
              "source":str(source_path.relative_to(NIGHT)),"source_sha256":hashlib.sha256(source_data).hexdigest(),"days":[]}
    started = time.monotonic()
    history = []
    external = False
    try:
        for day in (1, 2):
            before = {"afternoon_memory":{}}
            cast = {role:pick(role,day,"afternoon",root,prior,history,before,external,folder) for role in ROLES}
            state = afternoon({r:v["decision"] for r,v in cast.items()})
            local = state["afternoon_memory"]["reporter"] + state["seen"]["reporter"]
            night = {role:pick(role,day,"evening",root,prior,history+local,state,external,folder) for role in ROLES}
            ending = evening({r:v["decision"] for r,v in night.items()},state)
            history.append({"afternoon":state["effects"]["reporter"],"evening":ending["effects"]["reporter"],
                            "what_you_said":night["reporter"]["decision"]["words"],
                            "your_last_intention":night["reporter"]["decision"]["intention"],"next_wake":ALARM})
            if ending["both_at_party"]:
                history[-1]["also_seen"] = "You saw Rita at the ballroom."
            external = external or ending["delivered"]
            record["days"].append({"afternoon":cast,"evening":night,"afternoon_state":state,"ending":ending})
        record["alarm"] = pick("reporter",3,"alarm",root,prior,history,{"afternoon_memory":{}},external,folder)
        record["status"] = "complete"
    except (ValueError, OSError) as error:
        record.update(status="incomplete", reason=str(error))
    record["wall_s"] = time.monotonic()-started
    atomic_json(result, record)
    print(root, record["status"], len(record["days"]), round(record["wall_s"],2), flush=True)


if __name__ == "__main__":
    with urllib.request.urlopen(HOST + "/api/tags", timeout=5) as reply:
        tag = next(m for m in json.load(reply)["models"] if m["name"] == MODEL)
    assert tag["size"] < 650_000_000
    for root in (721, 731):
        run(root,tag)
