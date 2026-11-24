"""Launch the explicitly primed local film/neutral credential cohort after the paired holdouts."""
import json
import os
import time
from heldout_queue import STATE, NIGHT, MODEL, URL, run


def main():
    done=STATE/"heldout-complete"
    deadline=time.monotonic()+100*60
    pid=int((STATE/"heldout-queue.pid").read_text())
    while not done.exists():
        try:os.kill(pid,0)
        except ProcessLookupError:raise SystemExit("Previous experiments exited early")
        if time.monotonic()>deadline:raise SystemExit("Previous experiments exceeded this queue's wait window")
        time.sleep(8)
    tag=json.loads((NIGHT/"takes/q27/model.json").read_text())
    for seed in (721,722,723):
        for cast in (("film","neutral") if seed%2 else ("neutral","film")):
            run([NIGHT/"audition/badges.py","--backend","ollama","--base-url",URL,"--model",MODEL,"--model-revision",tag["digest"],
                 "--cast",cast,"--memory","wakes","--physical","move","--ending","bulletin","--thinking","off","--num-ctx","8192",
                 "--max-tokens","256","--workers","3","--days","6","--seeds",str(seed),"--out",NIGHT/"takes/badges"/cast],f"badge-{cast}-{seed}")
    (STATE/"badges-complete").touch()
if __name__=="__main__":
    main()
