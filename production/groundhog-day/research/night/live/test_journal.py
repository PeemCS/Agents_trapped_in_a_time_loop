"""Measure bounded incremental ingestion, interruption handling and prefix integrity using real frame shapes."""
import argparse
import json
import math
import os
import statistics
import tempfile
import time
from pathlib import Path

from journal import encode,records
from journal_source import JournalSource


def percentile(values,p):
    return sorted(values)[math.ceil(len(values)*p)-1]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("take",type=Path);ap.add_argument("--out",type=Path,required=True);ap.add_argument("--slots",type=int,default=20000)
    a=ap.parse_args();raw=json.loads(a.take.read_bytes());lines=list(records(raw))
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/"town.journal";source=JournalSource(path,0)
        with path.open("wb") as f:
            f.write(lines[0]);f.write(lines[1]);f.write(lines[2][:53]);f.flush()
            s=source.slice(-1,0);assert len(s["events"])==1 and "rest" in s["notice"]
            f.write(lines[2][53:]);f.flush();s=source.slice(s["epoch"],1);assert s["next"]==2
            split=s["epoch"]
            corrupt=json.loads(lines[3]);corrupt["data"]["event"]["decision"]["words"]="Damaged record"
            f.write(json.dumps(corrupt).encode()+b"\n");f.flush()
            s=source.slice(split,2);assert s["next"]==2 and "Holding" in s["notice"]
        fixed=path.with_suffix(".new");fixed.write_bytes(b"".join(lines));os.replace(fixed,path)
        s=source.slice(split,2);assert s["epoch"]==split+1 and s["complete"] and s["from"]==0
        assert source.slice(s["epoch"],len(lines)-2)["events"]==[]
        # Stream a synthetic load in batches of 24, the number of lead slots in a normal six-day shoot.
        loadfile=Path(d)/"load.journal";load=JournalSource(loadfile,0)
        hdr=json.loads(lines[0])["data"];hdr["source"]="synthetic_load_test"
        example=[json.loads(l)["data"]["event"] for l in lines[1:-1]]
        l,prev=encode("begin",hdr,"00"*32);durations=[];wm=0;actor_events=0
        with loadfile.open("wb") as f:
            f.write(l)
            for offset in range(a.slots):
                template=example[offset%len(example)]
                eid=f"synthetic-{offset}"
                event={**template,"day":offset//4+1,"id":eid,
                       "cast":[{**e,"day":offset//4+1,"id":eid+"-"+e["role"]} for e in template["cast"]]}
                l,prev=encode("slot",{"offset":offset,"event":event},prev);f.write(l);actor_events+=len(event["cast"])+1
                if offset%24==23 or offset+1==a.slots:
                    f.flush();t=time.perf_counter();msg=load.slice(load.epoch,wm);durations.append((time.perf_counter()-t)*1000)
                    assert msg["next"]==offset+1;wm=msg["next"]
            l,prev=encode("end",{"slots":a.slots},prev);f.write(l);f.flush();sealed=load.slice(load.epoch,wm)
            assert sealed["complete"] and len(load.frames)==a.slots
        assert load.read_bytes==loadfile.stat().st_size
        packet=load.slice(load.epoch,0)
        assert packet["next"]==min(128,a.slots)
        result={"fixture":"Synthetic load stream with copied real presentation-frame shape. Unique IDs; no new model calls.",
                "slots":a.slots,"actor_records":actor_events,"journal_bytes":loadfile.stat().st_size,"bytes_accepted_by_reader":load.read_bytes,
                "ingest_batch_slots":24,"batches":len(durations),"median_batch_parse_ms":round(statistics.median(durations),3),
                "p95_batch_parse_ms":round(percentile(durations,.95),3),"incomplete_line_held":True,
                "modified_text_rejected":True,"atomic_replacement_recovered":True,"sealed":True,"max_response_events":packet["next"],
                "scope":"Local CPython, one reader, buffered file writes, hash verification and event decoding. Excludes generator serialization, browser painting, GPU inference and broadcast fan-out."}
        a.out.write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result))

if __name__=="__main__":main()
