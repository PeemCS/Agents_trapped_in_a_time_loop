"""Five new requests, immutable original checkpoint, raw native Ollama streams."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib import request
from zoneinfo import ZoneInfo

from adapter import HERE, ROOT, ROOT_SHA, SEEDS, STREAM_SHA, VARIANTS, canonical, checksum, make_body, resolve, source, validate

BASE="http://127.0.0.1:18527"
OUT=HERE/"takes"
LIMIT=datetime(2026,11,23,6,8,tzinfo=ZoneInfo("America/Los_Angeles"))
def left(): return (LIMIT-datetime.now(timezone.utc)).total_seconds()
def write(path,obj):
    body=(json.dumps(obj,ensure_ascii=False,indent=2)+"\n").encode()
    if path.exists():
        assert path.read_bytes()==body
        return
    with path.open("xb") as f:f.write(body)
def rel(path): return os.path.relpath(path,HERE)
def case(pair):
    variant,seed=pair;d=OUT/f"{variant}-{seed}";d.mkdir(parents=True,exist_ok=True)
    end=d/"result.json"
    if end.exists():return json.loads(end.read_bytes())
    body=make_body(variant,seed);inp=d/"request.json"
    if inp.exists():assert inp.read_bytes()==canonical(body)
    else:
        with inp.open("xb") as f:f.write(canonical(body))
    _,arch,old_source,_=source()
    reused=variant=="original" and seed==SEEDS[0]
    raw=old_source if reused else d/"response.ndjson"
    error=None
    if not reused and not raw.exists():
        start=d/"started.json"
        if start.exists():raise RuntimeError("Refusing an unconfirmed duplicate call")
        if left()<150:raise RuntimeError("Insufficient time to open another stream")
        write(start,{"started_utc":datetime.now(timezone.utc).isoformat(),"endpoint":"/api/chat","request_sha256":checksum(inp)})
        msg=request.Request(BASE+"/api/chat",data=inp.read_bytes(),headers={"Content-Type":"application/json"})
        try:
            with request.urlopen(msg,timeout=100) as conn,raw.open("xb",buffering=0) as f:
                for line in conn:
                    f.write(line)
                    if left()<5:raise TimeoutError("Hard cutoff reached")
        except Exception as ex:
            error=f"{type(ex).__name__}: {ex}"
            write(d/"error.json",{"error":error})
    result={"variant":variant,"sampling_seed":seed,"source_take":rel(ROOT),"source_take_sha256":ROOT_SHA,
            "checkpoint":arch["id"],"reused":reused,"request":rel(inp),"request_sha256":checksum(inp),"response":rel(raw)}
    chunks=[]
    if raw.exists():
        result["response_sha256"]=checksum(raw)
        for line in raw.read_bytes().splitlines():
            entry=json.loads(line)
            if reused:
                if entry["kind"]!="chunk":continue
                entry=entry["provider"]
            chunks.append(entry)
    thinking="".join(ch.get("message",{}).get("thinking","") for ch in chunks)
    content="".join(ch.get("message",{}).get("content","") for ch in chunks)
    terminal=chunks[-1] if chunks else {}
    result.update(stop=terminal.get("done_reason"),provider_chunks=len(chunks),thinking_chars=len(thinking),
                  output_tokens=terminal.get("eval_count"),prompt_tokens=terminal.get("prompt_eval_count"),actual_error=error)
    write(d/"provider-text.json",{"native_thinking":thinking,"content":content,"terminal":terminal})
    result["assembled_provider_text"]=rel(d/"provider-text.json")
    if terminal.get("done") and terminal.get("done_reason")=="stop" and not error:
        try:
            decision=validate(content,body["format"]["properties"]["action"]["enum"])
            if reused:assert decision==arch["decision"]
            after,events,receipts=resolve(variant,decision,result["request_sha256"],result["response_sha256"])
            result.update(decision=decision,world_after=after,actor_events=events,exchange_log=receipts,
                          confirmed_call=after["called_sister"] and bool(receipts))
        except ValueError as ex:result["actual_error"]=str(ex)
    write(end,result)
    print(variant,seed,result["stop"],result.get("decision",{}).get("action"),flush=True)
    return result

if __name__=="__main__":
    cases=[("original",SEEDS[0]),("local",SEEDS[0]),("routed",SEEDS[0]),("original",SEEDS[1]),("local",SEEDS[1]),("routed",SEEDS[1])]
    with request.urlopen(BASE+"/api/tags",timeout=5) as conn:tags=json.load(conn)
    config=source()[0]["configuration"]
    assert any(x["name"]==config["model"] and x["digest"]==config["model_revision"] for x in tags["models"])
    with ThreadPoolExecutor(max_workers=2) as pool: rows=list(pool.map(case,cases))
    write(HERE/"comparison.json",{"cases":rows,"new_provider_calls":sum(not c["reused"] for c in rows)})
