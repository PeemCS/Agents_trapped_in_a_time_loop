"""Resolve invalid wakes by the source protocol, retaining original attempts as primary."""
import json
import os
import time
from types import SimpleNamespace
from run import OUT, DEADLINE, LIMIT, URL, MODEL, SEEDS, MATCHED, save, sha
from run import ObservableOllama, validate, afternoon, afternoon_decisions

def main():
    os.umask(0o077)
    # Run after all evening actors have finished. Reserve at most remaining call slots.
    for seed in SEEDS:
        for condition in ("none","full","control"):
            folder = OUT/f"{seed}-{condition}-wake"
            primary = json.loads((folder/"decision.json").read_bytes())
            if primary["status"] == "valid" or (folder/"supplemental-repair.json").exists():
                continue
            count = len(list(OUT.glob("*/reservation-*.json")))
            if count >= LIMIT or time.time() >= DEADLINE - 45:
                return
            response = json.loads((folder/"response-0.json").read_bytes())
            body = response["body"]
            messages = body["messages"] + [{"role":"assistant","content":response["raw_final"]},
                        {"role":"user","content":"Choose the physical act and return the four required JSON strings."}]
            choices = list(json.loads(body["messages"][-1]["content"])["physical_choices"])
            reserve = folder/"reservation-1.json"
            if reserve.exists():
                raise RuntimeError("Incomplete repair already reserved")
            save(reserve,{"call_number":count+1,"seed":seed+1,"role":"reporter","phase":"afternoon","supplemental":True})
            backend = ObservableOllama(SimpleNamespace(model=MODEL,base_url=URL,temperature=.8,num_ctx=8192,
                        max_tokens=3072,timeout=min(420,max(1,int(DEADLINE-time.time())))),folder)
            raw, meta = backend.respond("reporter",(2,0),messages,choices,seed+1)
            archive = folder/meta["stream_path"]
            head = json.loads(archive.read_text().splitlines()[0])
            save(folder/"response-1.json",{"meta":meta,"raw_final":raw,"body":head["body"]})
            result = {"status":"invalid","source":"supplemental canonical format repair","primary_status":"invalid",
                      "request_sha256":head["request_sha256"],"stream_sha256":sha(archive.read_bytes())}
            try:
                if meta["finish_reason"] != "stop":
                    raise ValueError("incomplete decision")
                result["decision"] = validate(raw,choices)
                result["status"] = "valid"
            except (TypeError,ValueError) as exc:
                result["error"]=str(exc)
            save(folder/"supplemental-repair.json",result)
            if result["status"]=="valid":
                save(folder/"supplemental-resolved.json",afternoon(afternoon_decisions(result)))
            print(folder.name,result["status"],result.get("decision",{}).get("action"),flush=True)

if __name__=="__main__":
    main()
