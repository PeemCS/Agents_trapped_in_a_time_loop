"""Run the two predeclared auditions once the larger-model grid has completed."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

NIGHT = Path(__file__).resolve().parent.parent
STATE = Path.home()/"Projects/finishers/nights/2026-11-23-groundhog-rehearsal"
GRID = NIGHT/"takes/q27"


def done():
    completed = set()
    for path in GRID.glob("*/seed-*.json"):
        row = json.loads(path.read_bytes())
        if row["status"] == "complete":
            completed.add((row["seed"],row["cast_condition"],row["memory"]))
    expected = {(s,c,m) for s in range(701,705) for c in ("film","neutral") for m in ("receipts","transcript")}
    return completed == expected


def run(command):
    print("Starting", command, flush=True)
    subprocess.run([sys.executable,"-B",*map(str,command)],check=True)
    print("Completed", command, flush=True)


def main():
    if (STATE/"followup-grid-complete").exists():return
    deadline = time.monotonic()+45*60
    grid_pid = int((STATE/"q27-shoot.pid").read_text())
    while not done():
        try:
            os.kill(grid_pid,0)
        except ProcessLookupError:
            raise SystemExit("Main grid exited early. Inspect its journals before resuming.")
        if time.monotonic()>=deadline:raise SystemExit("Main grid exceeded queue window.")
        time.sleep(12)
    run([NIGHT/"audition/memo.py","--model","qwen3.8:27b"])
    run([NIGHT/"casting/shoot.py","--small-comparison","--model","qwen3.5:4b","--family","q4"])
    run([NIGHT/"audition/memo.py","--model","qwen3.5:4b"])
    (STATE/"followup-grid-complete").touch()


if __name__=="__main__":
    main()
