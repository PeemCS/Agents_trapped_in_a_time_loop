"""Serially shoot the paired held-out worlds and declared follow-up scenes on the existing tunnel."""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

NIGHT=Path(__file__).resolve().parent.parent
STATE=Path.home()/"Projects/finishers/nights/2026-11-23-groundhog-rehearsal"
OUT=NIGHT/"takes/heldout"
MODEL="qwen3.8:27b"
URL="http://127.0.0.1:18527"


def run(cmd,label):
    print(datetime.now(timezone.utc).isoformat(),label,flush=True)
    with (STATE/("heldout-"+label+".log")).open("a") as log:
        subprocess.run([sys.executable,"-B",*map(str,cmd)],stdout=log,stderr=log,check=True)


def main():
    wait_pid=int((STATE/"after-grid.pid").read_text())
    deadline=time.monotonic()+80*60
    while not (STATE/"followup-grid-complete").exists():
        try:os.kill(wait_pid,0)
        except ProcessLookupError:raise SystemExit("Prior auditions exited before completion")
        if time.monotonic()>deadline:raise SystemExit("Prior auditions exceeded wait window")
        time.sleep(8)
    tag=json.loads((NIGHT/"takes/q27/model.json").read_text())
    OUT.mkdir(exist_ok=True)
    common=["run","--backend","ollama","--base-url",URL,"--model",MODEL,"--model-revision",tag["digest"],"--cast","film",
            "--thinking","off","--num-ctx","8192","--max-tokens","256","--workers","3","--days","6"]
    for seed in range(711,715):
        arms=("v2","v1") if seed%2 else ("v1","v2")
        for arm in arms:
            if arm=="v1":
                file="town.py";flags=["--memory","receipts"]
            else:
                file="v2.py";flags=["--memory","wakes","--physical","move","--ending","bulletin"]
            t=time.monotonic()
            run([NIGHT/"story"/file,*common,*flags,"--seeds",str(seed),"--out",OUT/arm],f"{arm}-{seed}")
            with (OUT/"progress.jsonl").open("a") as log:
                print(json.dumps({"seed":seed,"arm":arm,"wall_s":round(time.monotonic()-t,2),"utc":datetime.now(timezone.utc).isoformat()}),file=log)
    run([NIGHT/"branches/shoot_branch.py"],"coach-fork")
    run([NIGHT/"learning/social_scene.py","--model",MODEL],"social-history")
    (STATE/"heldout-complete").touch()

if __name__=="__main__":main()
