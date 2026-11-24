"""Complete the final predeclared reaction probes, then release precisely the ephemeral rehearsal GPU."""
import json
import os
import sys
import time
from heldout_queue import NIGHT,STATE,MODEL,URL,run
from runpod_shift import terminate


def main():
    done=STATE/"badges-complete";deadline=time.monotonic()+110*60
    pid=int((STATE/"badge-queue.pid").read_text())
    while not done.exists():
        try:os.kill(pid,0)
        except ProcessLookupError:raise SystemExit("Badge shoot ended before completion")
        if time.monotonic()>deadline:raise SystemExit("Badge wait window exceeded")
        time.sleep(8)
    digest=json.loads((NIGHT/"takes/q27/model.json").read_text())["digest"]
    run([NIGHT/"audition/surprise.py","--backend","ollama","--base-url",URL,"--model",MODEL,"--model-revision",digest,
         "--cast","film","--memory","wakes","--physical","move","--ending","bulletin","--thinking","off","--num-ctx","8192",
         "--max-tokens","256","--workers","3","--days","6","--seeds","721","722","723","--out",NIGHT/"takes/surprise/film"],"surprise")
    for seed in (721,722,723):
        if json.loads((NIGHT/"takes/surprise/film"/f"seed-{seed}.json").read_bytes())["status"]!="complete":
            raise RuntimeError("Missing retrieval-assisted credential take")
    run([NIGHT/"audition/deliberate.py"],"deliberation")
    folder=NIGHT/"audition/deliberation"
    if len(list(folder.glob("7??-96?-*.json")))!=16 or len(json.loads((folder/"capability-quiz.json").read_text()))!=4:
        raise RuntimeError("Incomplete final reaction/quiz ledger")
    # Two later user-requested jobs share this single existing allocation.
    # The server's separate 180-minute guard remains authoritative if the Mac disappears.
    from datetime import datetime
    born=datetime.fromisoformat(json.loads((STATE/"created-pod.json").read_text())["createdAt"].replace("Z","+00:00")).timestamp()
    while not all((STATE/name).is_file() for name in ("monitored-ensemble-complete","persona-artifacts-on-mac","last-reel-complete","interview-scenes-complete")):
        if time.time()-born>174*60:
            print("Releasing before the hard cutoff with a supplemental job still open.",flush=True)
            terminate()
            return
        time.sleep(10)
    (STATE/"all-paid-experiments-on-disk").touch()
    terminate()
    print("Final calls complete. Requested termination of the owned ephemeral resource.",flush=True)

if __name__=="__main__":main()
