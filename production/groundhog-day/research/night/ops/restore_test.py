"""Recover an interrupted real-model trajectory using archived provider bytes; no paid requests are made."""
import argparse
import collections
import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
STORY=HERE.parent/"story"
sys.path.insert(0,str(STORY))
import town
from audit import inspect


class ReplayedServer:
    def __init__(self,source):
        self.source=source
        self.calls=collections.Counter()

    def respond(self,actor,slot,messages,actions,seed):
        day,tick=slot
        lead=self.source["events"][(day-1)*4+tick]
        e=next(e for e in [lead,*lead["cast"]] if e["role"]==actor)
        inf=e["inference"]
        assert seed==inf["sampling_seed"] and inf["legal_actions"]==actions
        attempt=next(x for x in inf["attempts"] if x["messages"]==messages)
        self.calls[(actor,day,tick,repr(messages))]+=1
        return attempt["response"],{k:v for k,v in attempt.items() if k not in ("response","messages","error")}


def main():
    src=HERE.parent/"takes/q27/film-transcript/seed-701.json";r=json.loads(src.read_bytes())
    p=argparse.ArgumentParser();town.run_args(p);backend=ReplayedServer(r);commits=town.atomic_json
    with tempfile.TemporaryDirectory() as d:
        dest=Path(d)
        args=p.parse_args(["--backend","ollama","--model",r["model"],"--model-revision",r["configuration"]["model_revision"],
                        "--memory",r["memory"],"--cast",r["cast_condition"],"--days","6","--seeds",str(r["seed"]),
                        "--thinking","off","--num-ctx","8192","--max-tokens","256","--workers","3","--out",d])
        path=dest/"seed-701.json";interruption={}
        def disk_write(target,value):
            if target==path and len(value.get("events",[]))==7:
                interruption["accepted_responses_at_crash"]=sum(backend.calls.values())
                raise OSError("Injected loss between accepted replies and atomic slot commit.")
            return commits(target,value)
        with contextlib.redirect_stdout(io.StringIO()),patch.object(town,"atomic_json",disk_write):
            try:town.sample(args,701,backend)
            except OSError as exc:assert str(exc).startswith("Injected loss")
            else:raise AssertionError("Write interruption was not exercised")
        saved=json.loads(path.read_bytes())
        assert len(saved["events"])==6 and saved["status"]=="partial"
        with town.exclusive(dest/".seed-701.lock"):
            try:town.sample(args,701,backend)
            except RuntimeError as exc:assert "Another sampler" in str(exc)
            else:raise AssertionError("Concurrent writer entered an owned take")
        with contextlib.redirect_stdout(io.StringIO()):
            fixed=town.sample(args,701,backend)
        assert fixed["status"]=="complete"
        for source,replay in zip(r["events"],fixed["events"],strict=True):
            for key in ["world_before","world_after","id","effect","observed","decision"]:
                assert source[key]==replay[key]
            assert [(a["decision"],a["effect"],a["observed"]) for a in source["cast"]]==[(a["decision"],a["effect"],a["observed"]) for a in replay["cast"]]
        audit=inspect(path);assert audit["replay_errors"]==[]
        assert max(backend.calls.values())==1
        recoveries=[e["id"] for lead in fixed["events"] for e in [lead,*lead["cast"]] if e["inference"].get("recovered_from_disk")]
        assert recoveries
        summary={**interruption,"injected_after_accepting_slot":7,"committed_slots_at_crash":6,
          "recovered_ids":recoveries,"recovered_slots":len(fixed["events"]),"actor_decisions_verified":24*3,
          "max_calls_per_distinct_archived_request":max(backend.calls.values()),"all_requests":sum(backend.calls.values()),
          "resulting_trajectory_equals_original":True,"concurrent_writer_blocked":True,
          "scope":"Provider responses came from the retained 27B take. A local injected write failure and a competing lock acquisition were real. No live provider calls were made."}
        (HERE/"restore-evidence.json").write_text(json.dumps(summary,indent=2)+"\n");print(json.dumps(summary))

if __name__=="__main__":main()
