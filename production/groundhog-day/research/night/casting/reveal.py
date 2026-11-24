"""Join sealed choices to source checksums after the independent screening."""
import argparse
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
NIGHT=HERE.parent
STATE=Path.home()/"Projects/finishers/nights/2026-11-23-groundhog-rehearsal"
ROOM=Path("/private/tmp/groundhog-screening-room")


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("mode",choices=("model","architecture"));a=p.parse_args()
    key=json.loads((STATE/(a.mode+"-screen-key.json")).read_text());file=ROOM/(a.mode+"-ratings.json");raw=file.read_bytes()
    ratings=json.loads(raw)
    seen=set();counts=Counter();out=[]
    for r in ratings:
        i=f'{int(r["pair"]):02d}';pick=r["choice"].upper()
        assert i not in seen and pick in ("L","R","TIE");seen.add(i)
        sides={}
        for side in ("L","R"):
            info=key[i+"-"+side];path=NIGHT/info["file"]
            assert hashlib.sha256(path.read_bytes()).hexdigest()==info["sha256"]
            label=path.parents[1].name if a.mode=="model" else path.parent.name
            sides[side]={**info,"condition":label}
        counts["tie" if pick=="TIE" else sides[pick]["condition"]]+=1
        out.append({**r,"sides":sides})
    assert len(seen)*2==len(key)
    output={"evaluator":"Independent Codex agent; visible names and any resemblance to earlier cold-screened film could reveal some content. Model/seed label and condition codebook were unavailable until sealed.",
            "rating_sha256":hashlib.sha256(raw).hexdigest(),"counts":dict(counts),"pairs":out}
    target=HERE/(a.mode+"-screen-results.json");target.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n")
    shutil.copyfile(ROOM/(a.mode+"-editorial.md"),HERE/(a.mode+"-screen-notes.md"))
    print(dict(counts))

if __name__=="__main__":main()
