#!/usr/bin/env python3
"""Check the cash, legal spending, observer messages and next wake in the 731 fare scene."""

import json, hashlib, sys
from pathlib import Path
from rialto_film import verify_orig, write


def audit(source):
    take = json.loads(source.read_text())
    assert take["status"] == "complete"
    d, n = take["days"][:2]
    state = d["afternoon_state"]
    reporter = d["afternoon"]["reporter"]
    night = d["evening"]["reporter"]
    next_act = n["afternoon"]["reporter"]
    assert state["fare_cash"] and state["positions"] == {
        "reporter": "hotel",
        "producer": "Rialto",
        "camera": "Rialto",
    }
    assert reporter["decision"]["action"] == "pocket_fare_envelope"
    physical = state["effects"]["reporter"]
    assert "The envelope is empty." in physical
    said = "Phil said in the lobby: " + reporter["decision"]["words"]
    observers = {}
    for role in ("producer", "camera"):
        delivered = json.loads(d["evening"][role]["messages"][-1]["content"])[
            "what_you_observe"
        ]
        assert said in delivered and physical not in delivered
        assert said in state["seen"][role] and physical not in state["seen"][role]
        observers[role] = {
            "where": state["positions"][role],
            "heard_line": said,
            "saw_cash_action": False,
            "entire_evening_observations": delivered,
            "evening_stream": verify_orig(d["evening"][role])[1],
        }
    reporter_eyes = json.loads(night["messages"][-1]["content"])
    assert (
        physical in reporter_eyes["what_you_observe"]
        and "wire_deposit" in reporter_eyes["physical_choices"]
    )
    assert (
        night["decision"]["action"] == "go_to_bed"
        and d["ending"]["closed_clock"] == "Tuesday"
    )
    next_cue = json.loads(next_act["messages"][-1]["content"])
    fresh = next(x for x in next_cue["what_you_observe"] if "envelope holds" in x)
    assert (
        next_act["decision"]["action"] == "take_coach"
        and n["afternoon_state"]["positions"]["reporter"] == "Pittsburgh"
        and not n["afternoon_state"]["fare_cash"]
    )
    return {
        "source": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "take": source.parent.name,
        "who_spoke": reporter["speaker"],
        "spoken_full": reporter["decision"]["words"],
        "committed_choice": reporter["decision"]["action"],
        "effect": physical,
        "reporter_position": state["positions"]["reporter"],
        "afternoon_source": verify_orig(reporter)[1],
        "observers": observers,
        "allowed_wire_deposit": reporter_eyes["physical_choices"]["wire_deposit"],
        "actual_evening_choice": night["decision"]["action"],
        "actual_evening_effect": d["ending"]["effects"]["reporter"],
        "paid_deposit_issued": night["decision"]["action"] == "wire_deposit",
        "closed_next_wake": next_cue["what_you_observe"][0],
        "envelope_in_next_input": fresh,
        "next_decision": next_act["decision"],
        "next_effect": n["afternoon_state"]["effects"]["reporter"],
        "next_stream": verify_orig(next_act)[1],
        "night_stream": verify_orig(night)[1],
    }


if __name__ == "__main__":
    write(Path(sys.argv[2]), audit(Path(sys.argv[1])))
