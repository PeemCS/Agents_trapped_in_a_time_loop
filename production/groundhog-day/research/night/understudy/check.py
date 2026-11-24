"""Reconstruct every committed choice and its physical effect from the local wire records."""
import hashlib
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "story"), str(HERE.parent / "last-reel")]
from inference import validate
from scene import ROLES, afternoon, evening, options


def verify(root):
    folder = HERE / f"seed-{root}"
    take = json.loads((folder / "take.json").read_bytes())
    assert take["status"] == "complete" and len(take["days"]) == 2
    assert hashlib.sha256((HERE.parent / take["source"]).read_bytes()).hexdigest() == take["source_sha256"]
    timings, tokens, cast = [], [], []
    calls = 0

    def receipt(row, role, phase, state):
        nonlocal calls
        samples = [json.loads((folder / f).read_bytes()) for f in row["attempts"]]
        calls += len(samples)
        sample = samples[-1]
        req = sample["request"]
        permitted = list(options(role,phase,state))
        assert req["format"]["properties"]["action"]["enum"] == permitted
        assert req["model"] == take["model"] and req["think"] is False
        assert all(x["model"] == take["model"] for x in sample["chunks"])
        assert sample["chunks"][-1]["done_reason"] == "stop"
        text = "".join(x["message"]["content"] for x in sample["chunks"])
        assert validate(text,permitted) == row["decision"]
        for s in samples:
            timings.append(s["wall_s"])
            tokens.append(s["chunks"][-1]["eval_count"])
        return row["decision"]

    for day in take["days"]:
        a = {r:receipt(day["afternoon"][r],r,"afternoon",{}) for r in ROLES}
        before = afternoon(a)
        assert before == day["afternoon_state"]
        b = {r:receipt(day["evening"][r],r,"evening",before) for r in ROLES}
        end = evening(b,before)
        assert end == day["ending"]
        cast.append({"afternoon":[a[r]["action"] for r in ROLES],"evening":[b[r]["action"] for r in ROLES],
                     "delivered":end["delivered"]})
    receipt(take["alarm"],"reporter","alarm",{})
    return {"seed":root, "model":take["model"], "digest":take["revision"], "wall_s":round(take["wall_s"],2),
            "committed_decisions":13, "native_calls":calls,"generated_tokens":sum(tokens),
            "median_call_seconds":round(statistics.median(timings),3),"days":cast}


if __name__ == "__main__":
    runs = [verify(r) for r in (721,731)]
    result = {"scope":"Local fresh small-model productions following archived opening memories; two complete days and a third alarm per crew.",
              "runs":runs}
    (HERE / "results.json").write_text(json.dumps(result,indent=2)+"\n")
    print("Replayed 26 local character choices and all four evenings from native Ollama responses.")
