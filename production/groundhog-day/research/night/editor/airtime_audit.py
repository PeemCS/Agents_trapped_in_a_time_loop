#!/usr/bin/env python3
"""Which single actor's legal last-minute choices could change what actually went on air?"""

import argparse
import collections
import copy
from pathlib import Path
import sys
from edit import read_trace, write_json

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "story"))
from world_v2 import resolve


def signature(bulletin):
    return (bulletin["channel"], bulletin["source_role"], bulletin["source_place"], bulletin["footage"])


def audit(path):
    trace, digest = read_trace(path)
    if trace.get("ending") != "bulletin":
        raise ValueError("a resolved bulletin protocol is required")
    moments = []
    for e in trace["events"]:
        if e["clock"] != "7:00 pm":
            continue
        rows = {r["role"]: r for r in [e, *e["cast"]]}
        choices = {r: row["decision"] for r, row in rows.items()}
        before = e["world_before"]
        truth = e["world_after"]["bulletin"]
        base = signature(truth)

        def render(choices):
            return resolve(
                trace["seed"],
                e["day"],
                3,
                copy.deepcopy(before),
                choices,
                trace["cast_names"],
                trace["physical"],
                trace["ending"],
            )[0]["bulletin"]

        if truth != render(choices):
            raise ValueError(f"actual bulletin differs from replay, {e['id']}")
        interventions = {}
        for role, row in rows.items():
            alternatives = {}
            for physical in row["inference"]["legal_actions"]:
                decisions = copy.deepcopy(choices)
                decisions[role]["action"] = physical
                alternative = render(decisions)
                s = signature(alternative)
                if s != base:
                    alternatives[physical] = list(s)
            outcomes = {tuple(s) for s in alternatives.values()}
            interventions[role] = {
                "actual": choices[role]["action"],
                "alternate_channel_count": len(outcomes),
                "changes_feed": bool(outcomes),
                "other_reachable_channels": sorted({s[0] for s in outcomes}),
                "edits": alternatives,
            }
        moments.append(
            {
                "day": e["day"],
                "event": e["id"],
                "actual": list(base),
                "actual_sources": truth["source_ids"],
                "selected_earlier_recorded_work": any(
                    x.split("-")[1] != "t03" for x in truth["source_ids"]
                ),
                "one_actor_at_a_time": interventions,
            }
        )
    return {
        "source_sha256": digest,
        "seed": trace["seed"],
        "source_type": trace.get("source"),
        "evenings": moments,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("traces", nargs="+", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    results = [audit(x) for x in a.traces]
    rows = [m for w in results for m in w["evenings"]]
    roles = ("producer", "reporter", "camera")
    report = {
        "method": "Replay the original last slot and verify the full stored bulletin. Replace one actor’s physical action at a time with every action legal in that exact state. Freeze the other actors, words, prior footage and actual world. Alternative feed signatures are counterfactual mechanics, not samples of model behavior.",
        "worlds": len(results),
        "evenings": len(rows),
        "actual_channels": collections.Counter(m["actual"][0] for m in rows),
        "evenings_with_single_actor_power": {
            role: sum(m["one_actor_at_a_time"][role]["changes_feed"] for m in rows) for role in roles
        },
        "realized_earlier_work_reaching_air": sum(m["selected_earlier_recorded_work"] for m in rows),
        "per_world": results,
    }
    write_json(a.out, report)
    print(report["actual_channels"], report["evenings_with_single_actor_power"])
