"""Measure when model-emitted thinking and final usable text actually became available."""
import json
import statistics
from collections import Counter,defaultdict
from datetime import datetime,timedelta
from pathlib import Path

HERE=Path(__file__).resolve().parent

def spread(values):
    vals=sorted(values)
    if not vals:return None
    def quantile(p):
        slider=p*(len(vals)-1);left=int(slider)
        return round(vals[left]+(vals[min(left+1,len(vals)-1)]-vals[left])*(slider-left),3)
    return {"count":len(vals),"p50":quantile(.5),"p95":quantile(.95),"max":round(vals[-1],3)}

def read_stream(file):
    first_thought=first_final=None;last=None;chars=0;actual=0
    for line in file.open():
        row=json.loads(line)
        if row["kind"]=="request":meta=row;continue
        if row["kind"]!="chunk":continue
        p=row["provider"];msg=p.get("message",{});t=row["elapsed_s"]
        thought=msg.get("thinking") or "";final=msg.get("content") or ""
        if thought and first_thought is None:first_thought=t
        if final and first_final is None:first_final=t
        chars+=len(thought);actual+=len(final)
        if p.get("done"):last=(t,p)
    if not last:return {"role":meta["role"],"error":"no terminal chunk"}
    t,p=last
    return {"role":meta["role"],"day":meta["day"],"period":meta["tick"],"repair":meta["repair"],"utc":meta["utc"],
            "first_thought_s":first_thought,"first_final_s":first_final,"complete_s":t,"reason":p.get("done_reason"),
            "thinking_chars":chars,"final_chars":actual,"tokens":p["eval_count"],"prompt_tokens":p["prompt_eval_count"],
            "backend_output_tokens_per_s":round(p["eval_count"]*1e9/p["eval_duration"],2) if p.get("eval_duration") else None}

def summarize(folder):
    run=json.loads((folder/"seed-731.json").read_bytes());assert run["status"]=="complete"
    all_events=[a for e in run["events"] for a in [e,*e["cast"]]]
    rawfiles=sorted((folder/"streams").glob("*.ndjson"));rows=[read_stream(f) for f in rawfiles]
    start=min(datetime.fromisoformat(r["utc"]) for r in rows if "utc" in r)
    finish=max(datetime.fromisoformat(r["utc"])+timedelta(seconds=r["complete_s"]) for r in rows if "utc" in r)
    modes=Counter(r.get("reason","error") for r in rows)
    valid=[r for r in rows if r.get("reason")=="stop"]
    return {"status":run["status"],"physical_slots":len(run["events"]),"actor_decisions":len(all_events),"native_attempts":len(rows),
        "cached_decisions":sum(bool(a["inference"]["cache_hit"]) for a in all_events),"repairs":sum(bool(r.get("repair")) for r in rows),
        "stop_reasons":dict(modes),"window_wall_s":round((finish-start).total_seconds(),1),"thinking_chars":sum(r.get("thinking_chars",0) for r in rows),
        "final_chars":sum(r.get("final_chars",0) for r in rows),"telemetry":{k:spread([r[k] for r in rows if r.get(k) is not None]) for k in ("first_thought_s","first_final_s","complete_s","tokens","prompt_tokens","backend_output_tokens_per_s")},
        "cap_coverage_on_successful_attempts":{str(n):sum(r["tokens"]<=n for r in valid) for n in (512,1024,1536,2048,3072,4096)},
        "by_role":{k:{"unique":sum(r["role"]==k for r in rows),"latency_s":spread([r["complete_s"] for r in rows if r["role"]==k and "complete_s" in r])} for k in ("reporter","producer","camera")},
        "raw":rows}

if __name__=="__main__":
    out={"environment":"The same private 80 GB H100 and Ollama endpoint. Simultaneous casts, other rehearsal jobs and the small-adapter study contended for it. Wall windows include contention. The count of completed outputs fitting under a token cap is a retrospective coverage statistic.",
         "takes":{f.name:summarize(f) for f in sorted((HERE/"runs").iterdir()) if (f/"seed-731.json").exists()}}
    (HERE/"serving.json").write_text(json.dumps(out,indent=2)+"\n")
    for name,r in out["takes"].items():print(name,r["actor_decisions"],r["native_attempts"],r["cached_decisions"],r["stop_reasons"],r["window_wall_s"],r["telemetry"]["first_final_s"],r["cap_coverage_on_successful_attempts"])
