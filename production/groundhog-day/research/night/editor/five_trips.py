#!/usr/bin/env python3
"""Select five completed transfers from one life, then walk a real terminal call backward."""

import argparse
import copy
from pathlib import Path
import sys

from edit import coach_clusters, make_edl, read_trace, verify, write_json

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "story"))
from world_v2 import actions, initial, resolve


def prepare(source, out):
    world, digest = read_trace(source)
    es = world["events"]
    trips = list(coach_clusters(es))[:5]
    if len(trips) != 5:
        raise ValueError("a single take with five witnessed returns is required")
    edl = make_edl(source, "chronicle")
    edl.update(
        selection="five-trips",
        purpose="Five consecutive departures and observed hotel returns from one life.",
        cluster=None,
        shots=[],
    )
    # Speak selected entire lines only. All other shots carry stage foley and recorded physical facts.
    voiced = {
        (1, "arrival"): "reporter",
        (3, "arrival"): "reporter",
        (4, "arrival"): "camera",
        (5, "hold"): "reporter",
    }
    lengths = [
        (3, 1.7, 1.75),
        (3, 2, 1.65),
        (3.15, 1.8, 1.55),
        (2.85, 1.85, 1.5),
        (2.65, 1.8, 2.65),
    ]
    proof = []
    for n, trip in enumerate(trips, 1):
        ids = {}
        for step, part, seconds in zip(
            ("arrival", "hold", "wake"),
            ("outbound", "in Pittsburgh", "back at the hotel"),
            lengths[n - 1],
        ):
            i = trip[step]
            e = es[i]
            who = voiced.get((n, step))
            rows = {r["role"]: r for r in [e, *e["cast"]]}
            speech = []
            if who:
                r = rows[who]
                if r["origin"] != e["origin"]:
                    raise ValueError(
                        "speaker must actually be present at the start of this shot"
                    )
                speech.append({"actor": r["actor"], "text": r["decision"]["words"]})
            waking = step == "wake"
            if waking:
                assert e["clock"] == "6:00 am" and e["world_before"] == initial()
                assert any("Tuesday, February 2, 2016." in x for x in e["observed"])
            else:
                assert e["world_after"]["positions"]["reporter"] == "Pittsburgh"
            ids[step] = {
                "id": e["id"],
                "day": e["day"],
                "clock": e["clock"],
                "source_index": i,
                "from": e["origin"],
                "to_after_action": e["place"],
                "action": e["decision"]["action"],
                "effect": e["effect"],
            }
            edl["shots"].append(
                {
                    "event_index": i,
                    "event_id": e["id"],
                    "focus": e["actor"],
                    "view": "morning" if waking else "action",
                    "framing": "close",
                    "start": 0.22 if waking else 0,
                    "end": 0.22 if waking else 1,
                    "seconds": seconds,
                    "speech": speech,
                    "montage_index": n,
                    "montage_part": part,
                }
            )
        proof.append(ids)
    verify(source, edl)
    # Select the first confirmed van call among the five. Enumerate every legal reporter move at the
    # previous lunch, keeping actual speech, the other participants and the incoming world fixed.
    trip = next(
        t for t in trips if es[t["hold"]]["decision"]["action"] == "call_sister"
    )
    depart, call, wake = [es[trip[k]] for k in ("arrival", "hold", "wake")]
    assert (
        call["world_before"] == depart["world_after"]
        and call["world_after"]["called_sister"]
    )
    assert (
        not call["world_before"]["called_sister"]
        and not wake["world_before"]["called_sister"]
    )

    def simulate(e, override=None):
        choices = {r["role"]: copy.deepcopy(r["decision"]) for r in [e, *e["cast"]]}
        if override is not None:
            choices["reporter"]["action"] = override
        tick = int(e["id"].split("-")[1][1:])
        state, _ = resolve(
            world["seed"],
            e["day"],
            tick,
            copy.deepcopy(e["world_before"]),
            choices,
            world["cast_names"],
            world["physical"],
            world["ending"],
        )
        return state

    assert (
        simulate(depart) == depart["world_after"]
        and simulate(call) == call["world_after"]
    )
    possibilities = {}
    for act in depart["inference"]["legal_actions"]:
        s = simulate(depart, act)
        can_call = "call_sister" in actions(
            "reporter", s, 3, world["cast_names"], world["physical"], world["ending"]
        )
        possibilities[act] = {
            "evening_location": s["positions"]["reporter"],
            "call_sister_available": can_call,
        }
    assert [k for k, v in possibilities.items() if v["call_sister_available"]] == [
        "take_coach_to_Pittsburgh"
    ]
    final = {
        act: simulate(call, act)["called_sister"]
        for act in call["inference"]["legal_actions"]
    }
    assert [k for k, v in final.items() if v] == ["call_sister"]
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "edit.json", edl)
    write_json(
        out / "backward-search.json",
        {
            "source": str(source),
            "sha256": digest,
            "model": world["model"],
            "seed": world["seed"],
            "trips": proof,
            "root": "The sister actually confirms the moving van on the second evening.",
            "backward_chain": [
                {
                    "event": call["id"],
                    "fact": call["effect"].split(" The pre-recorded")[0],
                    "state_edge": "called_sister false → true",
                },
                {
                    "event": depart["id"],
                    "fact": depart["effect"],
                    "state_edge": "reporter in diner → Pittsburgh",
                },
                {
                    "fact": "At 1 pm the role has a paid ticket and legal coach action. The reducer permits the call only from Pittsburgh."
                },
            ],
            "next_wake": {
                "event": wake["id"],
                "world_before_equals_daily_initial": wake["world_before"] == initial(),
                "clock_and_radio": wake["observed"][0],
            },
            "at_lunch_legal_alternatives": possibilities,
            "at_terminal_legal_alternatives_and_confirmed_call": final,
            "causal_scope": "Same pre-action state and peer decisions; only the reporter's physical verb is replaced in the local world reducer. Alternatives were never enacted. The check tests specific mechanics, not why Phil decided to board. The unconditional daily reset causes the hotel wake.",
        },
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("out", type=Path)
    args = p.parse_args()
    prepare(args.source, args.out)
