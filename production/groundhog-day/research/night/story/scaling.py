"""CPU-only matched fixture to measure memory volume and renderer payload scaling."""
import argparse
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile

from audit import inspect, compact
from town import run_args, sample, atomic_json

def one(root,days,memory):
    p=argparse.ArgumentParser()
    run_args(p)
    args=p.parse_args(["--backend","fixture","--days",str(days),"--memory",memory,"--out",str(root)])
    with redirect_stdout(io.StringIO()): row=sample(args,701)
    path=root/"seed-701.json";check=inspect(path)
    if check["replay_errors"]: raise RuntimeError(check["replay_errors"])
    out=compact(path)
    packed_size=len((json.dumps(out,ensure_ascii=False,separators=(",",":"))+"\n").encode())
    dawn=row["events"][-4]
    remembered=json.loads(dawn["inference"]["messages"][1]["content"])["your_memories_in_order"]
    return {"days":days,"memory":memory,"source":"injected_fixture","roots":1,"ticks":len(row["events"]),
            "decisions":row["metrics"]["cast_decisions"],"fresh_fixture_responses":check["runtime"]["committed_generation_attempts"],
            "cached_decisions":row["metrics"]["response_reuses"],
            "last_morning_reporter_full_request_utf8_bytes":sum(len(x["content"].encode()) for x in dawn["inference"]["messages"]),
            "last_morning_retained_memory_lines":len(remembered),
            "retains_earliest_coach_arrival":any("rides the coach all the way to Pittsburgh" in line for line in remembered),
            "retains_sister_confirmation":any("She confirms the moving van" in line for line in remembered),
            "raw_trace_bytes":path.stat().st_size,"presentation_bytes":packed_size}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--out",type=Path,required=True);args=p.parse_args()
    with tempfile.TemporaryDirectory() as work:
        root=Path(work)
        rows=[one(root/f"d{days}-{m}",days,m) for days in (4,12,20) for m in ("receipts","transcript")]
    body={"scope":"Identical scripted decisions on six CPU-only instrument checks. Counts are bytes, not tokens or GPU speed.",
          "samples":rows}
    atomic_json(args.out,body);print(json.dumps(body,indent=2))
if __name__=="__main__":main()
