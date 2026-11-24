"""Prepare blinded human-readable matched-pair screenings, keeping the codebook outside the screening room."""
import argparse
import hashlib
import json
import random
import secrets
from pathlib import Path

NIGHT=Path(__file__).resolve().parent.parent
STATE=Path.home()/"Projects/finishers/nights/2026-11-23-groundhog-rehearsal"
ROOM=Path("/private/tmp/groundhog-screening-room")


def render(data):
    pages=[]
    for idx,e in enumerate(data["events"],start=1):
        pages.append(f"\nE{idx:02d} | day {e['day']} | {e['clock']}")
        for person in [e,*e["cast"]]:
            d=person["decision"];pages.append(f"  {person['actor']} | {person['origin']} → {person['place']} | {d['action']} | {person['effect']}")
            if d["words"]:pages.append("    “"+d["words"]+"”")
        bulletin=e["world_after"].get("bulletin")
        if bulletin:pages.append("  Broadcast record | "+json.dumps({k:v for k,v in bulletin.items() if k not in ('source_ids','ending_event_ids')},ensure_ascii=False))
    return "\n".join(pages)+"\n"


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("mode",choices=["model","architecture"]);a=p.parse_args()
    private_key=STATE/(a.mode+"-screen-key.json")
    if private_key.is_file():raise SystemExit("A codebook already exists; preserve this screening.")
    pairs=[]
    if a.mode=="model":
        for seed in range(701,705):
            for cast in ("film","neutral"):
                pairs.append([NIGHT/"takes"/fam/(cast+"-receipts")/f"seed-{seed}.json" for fam in ("q27","q4")])
    else:
        for seed in range(711,715):
            pairs.append([NIGHT/"takes"/"heldout"/arm/f"seed-{seed}.json" for arm in ("v1","v2")])
    rng=random.Random(secrets.randbits(128));rng.shuffle(pairs)
    groupdir=ROOM/a.mode;groupdir.mkdir(parents=True,exist_ok=True)
    key={};contents={}
    for i,pair in enumerate(pairs,start=1):
        rng.shuffle(pair)
        for side,path in zip(("L","R"),pair):
            raw=path.read_bytes();data=json.loads(raw)
            if data["status"]!="complete":raise SystemExit("Screening materials still in progress")
            label=f"{i:02d}-{side}";contents[label]=render(data)
            key[label]={"sha256":hashlib.sha256(raw).hexdigest(),"file":str(path.relative_to(NIGHT))}
    for name,s in contents.items():(groupdir/(name+".txt")).write_text(s)
    private_key.write_text(json.dumps(key,indent=2)+"\n");private_key.chmod(0o600)
    (groupdir/"rubric.md").write_bytes((NIGHT/"editor/screening-rubric.md").read_bytes())
    (groupdir/"READY").write_text("All matched performances are present.\n")
    print("Sealed",len(pairs),"pairs in",groupdir)


if __name__=="__main__":
    main()
