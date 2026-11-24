"""Run the frozen grid serially, with a per-condition checkpoint journal and a local-only server."""
import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

HERE=Path(__file__).resolve().parent
NIGHT=HERE.parent
ENDPOINT="http://127.0.0.1:18527"
SEEDS=(701,702,703,704)
ARMS=(("film","receipts"),("neutral","transcript"),("neutral","receipts"),("film","transcript"))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",default="qwen3.8:27b")
    p.add_argument("--family",default="q27")
    p.add_argument("--small-comparison",action="store_true")
    p.add_argument("--days",type=int,default=6)
    a=p.parse_args()
    out=NIGHT/"takes"/a.family
    out.mkdir(parents=True,exist_ok=True)
    deadline=time.monotonic()+900
    while True:
        try:
            tags=json.load(urlopen(ENDPOINT+"/api/tags",timeout=4))["models"]
            tag=next(r for r in tags if r["name"]==a.model)
            break
        except (OSError,StopIteration):
            if time.monotonic()>=deadline:
                raise SystemExit("Model readiness deadline exceeded")
            time.sleep(5)
    (out/"model.json").write_text(json.dumps(tag,indent=2)+"\n")
    with (out/"progress.jsonl").open("a",buffering=1) as progress:
        for i,seed in enumerate(SEEDS):
            arms=(("film","receipts"),("neutral","receipts")) if a.small_comparison else ARMS
            for cast,memory in arms[i%len(arms):]+arms[:i%len(arms)]:
                dest=out/(cast+"-"+memory)
                dest.mkdir(exist_ok=True)
                logfile=dest/f"seed-{seed}.log"
                cmd=[sys.executable,"-B",str(NIGHT/"story"/"town.py"),"run","--backend","ollama",
                     "--base-url",ENDPOINT,"--model",a.model,"--model-revision",tag["digest"],
                     "--thinking","off","--num-ctx","8192","--max-tokens","256","--workers","3","--days",str(a.days),
                     "--seeds",str(seed),"--cast",cast,"--memory",memory,"--out",str(dest)]
                start=time.monotonic()
                with logfile.open("a") as log:
                    status=subprocess.run(cmd,stdout=log,stderr=log).returncode
                entry={"utc":dt.datetime.now(dt.timezone.utc).isoformat(),"seed":seed,"cast":cast,"memory":memory,
                       "exit":status,"wall_s":round(time.monotonic()-start,2)}
                print(json.dumps(entry),file=progress)
                print(entry,flush=True)
                # Surface runtime issues promptly. A caller may rerun after repairing infrastructure.
                if status:raise SystemExit(status)
if __name__=="__main__":main()
