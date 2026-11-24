"""Run two retained monitored casts on the existing bounded endpoint."""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE=Path(__file__).resolve().parent
STATE=Path.home()/"Projects/finishers/nights/2026-11-23-groundhog-rehearsal"


def main():
    tag=json.loads((HERE.parent/"takes/q27/model.json").read_text())
    for persona in ("standard","guarded"):
        folder=HERE/"runs"/persona;folder.mkdir(exist_ok=True,parents=True)
        cmd=[sys.executable,"-B",str(HERE/"ensemble.py"),"--backend","ollama","--base-url","http://127.0.0.1:18527",
             "--model",tag["name"],"--model-revision",tag["digest"],"--cast","film","--memory","wakes","--physical","move",
             "--ending","bulletin","--thinking","on","--persona",persona,"--num-ctx","8192","--max-tokens","4096","--timeout","320",
             "--workers","3","--days","4","--seeds","731","--out",str(folder)]
        print("Shooting",persona,flush=True)
        with (STATE/("thinking-"+persona+".log")).open("a") as log:
            subprocess.run(cmd,stdout=log,stderr=log,check=True)
        row=json.loads((folder/"seed-731.json").read_bytes())
        assert row["status"]=="complete" and len(row["events"])==16
    (STATE/"monitored-ensemble-complete").touch()
    print("Both monitored ensembles complete",flush=True)
if __name__=="__main__":main()
