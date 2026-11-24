"""Count independent seeds and decisions, and identify the exact files delivered for playback."""
import hashlib
import json
from pathlib import Path
import subprocess

NIGHT=Path(__file__).resolve().parents[1]
DIRS={"larger_casting":"takes/q27/*/seed-*.json","smaller_casting":"takes/q4/*/seed-*.json","world_comparison":"takes/heldout/*/seed-*.json",
      "credentials":"takes/badges/*/seed-*.json","surprise_memory":"takes/surprise/*/seed-*.json","thinking_ensemble":"thinking/runs/*/seed-*.json"}
FILMS=("editor/rialto-cut/film.mp4","editor/thinking-cut/film.mp4","editor/five-trips/film.mp4","editor/four-bulletins/film.mp4",
       "editor/wednesday-couch/film.mp4","editor/afternoon-coach/film.mp4","editor/seven-oclock/film.mp4",
       "editor/fare-envelope/film.mp4","stage3d/viewer/evidence/motion-proof.mp4","stage3d/viewer/rialto/evidence/eight-bars-3d.mp4","free-walk/evidence/movement-proof.mp4")

def sha(path):
    with path.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()

def runfile(f):
    r=json.loads(f.read_bytes());events=r["events"];decisions=[a for e in events for a in [e,*e["cast"]]]
    assert r["status"]=="complete" and len(decisions)==3*len(events)
    assert all(set(a["role"] for a in [e,*e["cast"]])=={"reporter","producer","camera"} for e in events)
    return {"file":str(f.relative_to(NIGHT)),"source_sha256":sha(f),"seed":r["seed"],"model":r["model"],"days":max(e["day"] for e in events),
            "ticks":len(events),"decisions":len(decisions),"cached_slots":sum(bool(a["inference"]["cache_hit"]) for a in decisions)}

def film(f):
    r=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_entries","stream=codec_type,codec_name,width,height,nb_frames:format=duration","-of","json",str(f)]))
    return {"path":str(f.relative_to(NIGHT)),"sha256":sha(f),"bytes":f.stat().st_size,"duration_s":float(r["format"]["duration"]),"streams":r["streams"]}

def main():
    groups={d:[runfile(f) for f in sorted(NIGHT.glob(pattern))] for d,pattern in DIRS.items()}
    allfiles=[r for g in groups.values() for r in g]
    assert len(allfiles)==43
    manifest={"scope":"Complete six-day main worlds and four-day monitored ensembles. An absolute seed repeated across matched treatments is one underlying root. The separate Rialto worlds branch off prior completed histories.",
              "totals":{"complete_main_worlds":len(allfiles),"distinct_seed_values":len({x["seed"] for x in allfiles}),
                        "lead_ticks":sum(x["ticks"] for x in allfiles),"cast_decisions":sum(x["decisions"] for x in allfiles),"exact_cache_reuses":sum(x["cached_slots"] for x in allfiles)},
              "cohorts":groups,"media":[film(NIGHT/r) for r in FILMS]}
    p=NIGHT/"ops/delivery-manifest.json";p.write_text(json.dumps(manifest,indent=2)+"\n");print(manifest["totals"])
if __name__=="__main__":main()
