"""An append-only, checksum-verified interchange for a live or recorded presentation."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"story"))
from audit import pack_run


def wire(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()


def encode(kind,body,previous):
    digest=hashlib.sha256(bytes.fromhex(previous)+wire([kind,body])).hexdigest()
    return wire({"kind":kind,"data":body,"previous":previous,"checksum":digest})+b"\n",digest


def records(trace):
    t=pack_run(trace)
    events=t.pop("events");status=t.pop("status")
    previous="00"*32
    line,previous=encode("begin",t,previous);yield line
    for offset,event in enumerate(events):
        line,previous=encode("slot",{"offset":offset,"event":event},previous);yield line
    if status=="complete":
        line,_=encode("end",{"slots":len(events)},previous);yield line


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("take",type=Path);ap.add_argument("output",type=Path)
    args=ap.parse_args()
    raw=json.loads(args.take.read_bytes())
    with args.output.open("xb") as f:
        for line in records(raw):f.write(line)
    print(args.output)

if __name__=="__main__":main()
