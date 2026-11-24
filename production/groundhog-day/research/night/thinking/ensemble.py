"""Sample the full canonical ensemble while saving each externally emitted thinking/content chunk for the user."""
import argparse
import datetime
import hashlib
import json
import os
import sys
import threading
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request,urlopen

HERE=Path(__file__).resolve().parent
AUDITION=HERE.parent/"audition"
sys.path.insert(0,str(AUDITION))
import badges
import persona_cue
from inference import canonical, object_schema
from town import atomic_json, fingerprint

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
log_lock=threading.Lock()


def record(path,row):
    # Concurrent actors write their index entries as a single locked local append.
    with log_lock,path.open("a",encoding="utf-8") as f:
        f.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n")


class ObservableOllama:
    def __init__(self,args,folder):
        self.args=args;self.folder=folder;self.streams=folder/"streams";self.streams.mkdir(parents=True,exist_ok=True)

    def respond(self,role,slot,messages,actions,seed):
        day,tick=slot;run_id=f"d{day:02d}-t{tick:02d}-{role}-{uuid.uuid4().hex[:12]}"
        path=self.streams/(run_id+".ndjson")
        repair=len(messages)>2
        limit=max(6144,self.args.max_tokens) if repair else self.args.max_tokens
        payload={"model":self.args.model,"stream":True,"think":True,"messages":messages,"format":object_schema(actions),
                 "options":{"temperature":self.args.temperature,"num_ctx":self.args.num_ctx,"num_predict":limit,"seed":seed}}
        signature=hashlib.sha256(canonical(payload)).hexdigest()
        header={"id":run_id,"utc":utc(),"role":role,"day":day,"tick":tick,"stream":str(path.relative_to(self.folder)),
                "request_sha256":signature,"repair":repair,"sampling_seed":seed}
        record(self.folder/"request-index.ndjson",{**header,"stage":"started"})
        record(path,{"kind":"request",**header,"body":payload})
        req=Request(self.args.base_url.rstrip("/")+"/api/chat",data=canonical(payload),headers={"Content-Type":"application/json"})
        start=time.monotonic();parts=[];contents=[];status=None;chunk_count=0
        try:
            with urlopen(req,timeout=self.args.timeout) as response,path.open("a",encoding="utf8",buffering=1) as output:
                for line in response:
                    chunk=json.loads(line)
                    if "error" in chunk:raise RuntimeError(chunk["error"])
                    # Keep every provider NDJSON object, including empty content and terminal timing statistics.
                    output.write(json.dumps({"kind":"chunk","seq":chunk_count,"elapsed_s":round(time.monotonic()-start,5),
                                             "provider":chunk},ensure_ascii=False,separators=(",",":"))+"\n")
                    chunk_count+=1;msg=chunk.get("message",{})
                    if msg.get("thinking"):parts.append(msg["thinking"])
                    if msg.get("content"):contents.append(msg["content"])
                    if chunk.get("done"):status=chunk
            if status is None:raise ValueError("Provider stream ended without its final record")
        except Exception as exc:
            record(path,{"kind":"error","type":type(exc).__name__,"message":str(exc),"utc":utc()})
            record(self.folder/"request-index.ndjson",{**header,"stage":"failed","error":type(exc).__name__})
            raise
        raw="".join(contents);thinking="".join(parts)
        latency=round(time.monotonic()-start,4)
        record(self.folder/"request-index.ndjson",{**header,"stage":"returned","elapsed_s":latency,
               "stop":status.get("done_reason"),"thinking_chars":len(thinking),"chunks":chunk_count})
        return raw,{"latency_s":latency,"finish_reason":status.get("done_reason"),"response_model":status.get("model"),
             "usage":{"prompt_tokens":status.get("prompt_eval_count"),"completion_tokens":status.get("eval_count")},
             "server_duration_ns":status.get("total_duration"),"public_thinking":thinking,"stream_path":header["stream"],
             "stream_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"provider_chunk_count":chunk_count}


def public_config(args,seed):
    c=badges.card_config(args,seed)
    c["protocol"]="town-monitored-1";c["parent_badge_code"]=c["code"]
    c["persona"]=args.persona
    c["code"]=fingerprint([c["parent_badge_code"],Path(__file__).read_text(),Path(persona_cue.__file__).read_text()])
    return c


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    badges.sampler.run_args(ap)
    ap.add_argument("--persona",choices=("standard","guarded"),default="standard")
    a=ap.parse_args()
    if a.thinking!="on":ap.error("This rehearsal captures a thinking-enabled model; use --thinking on.")
    if len(a.seeds)!=1:ap.error("Use a separate folder for each monitored seed.")
    badges.sampler.config=public_config;badges.sampler.cue=persona_cue.builder(a.persona)
    row=badges.sampler.sample(a,a.seeds[0],ObservableOllama(a,a.out))
    row["municipality"]=badges.badge_cues.TOWN.split(",")[0];row["credential_names"]=badges.badge_cues.FULL[row["protagonist"]]
    atomic_json(a.out/f"seed-{a.seeds[0]}.json",row)
    print(json.dumps(row["metrics"]),flush=True)

if __name__=="__main__":main()
