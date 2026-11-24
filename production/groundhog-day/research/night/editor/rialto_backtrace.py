#!/usr/bin/env python3
"""Trace the receiver's first actually witnessed letter backward through the Rialto reducer."""

import sys, itertools, json
from pathlib import Path
from hashlib import sha256

ROOT = Path(__file__).resolve().parent.parent / "last-reel"
sys.path.insert(0, str(ROOT))
from scene import afternoon, evening


def explain(source):
    world = json.loads(source.read_text())
    assert world["status"] == "complete"
    days = world["days"]
    delivery = next(d for d in days if d["ending"]["delivered"])
    n = delivery["day"]
    wake = days[n]["afternoon"]["reporter"] if n < len(days) else world["last_alarm"]
    seen = json.loads(wake["messages"][-1]["content"])["what_you_observe"]
    heard = next(x for x in seen if "daughter sent a receipt" in x)
    ad = {r: s["decision"] for r, s in delivery["afternoon"].items()}
    pm = {r: s["decision"] for r, s in delivery["evening"].items()}
    assert (
        afternoon(ad) == delivery["afternoon_state"]
        and evening(pm, afternoon(ad)) == delivery["ending"]
    )
    # Construct minimal sets of actual contribution actions sufficient against a recorded-absence
    # baseline. The alternate actions (hotel, time off, wait at hotel, go home) are all legal here.
    defaults = {
        ("afternoon", "reporter"): "spend_time_here",
        ("afternoon", "producer"): "take_time_off",
        ("afternoon", "camera"): "keep_battery",
        ("evening", "producer"): "take_evening_off",
        ("evening", "camera"): "go_home",
    }
    participating = [
        key
        for key in defaults
        if (ad if key[0] == "afternoon" else pm)[key[1]]["action"]
        in {
            "record_Alma",
            "interview_Alma",
            "film_Alma",
            "deliver_reel",
            "transmit_interview",
        }
    ]

    def result(active):
        a = {r: dict(v) for r, v in ad.items()}
        b = {r: dict(v) for r, v in pm.items()}
        for (phase, role), fallback in defaults.items():
            if (phase, role) not in active:
                (a if phase == "afternoon" else b)[role]["action"] = fallback
        # The reporter's evening verb cannot change the delivery; use a legal local or city wait.
        state = afternoon(a)
        b["reporter"]["action"] = (
            "wait_for_morning" if state["city"] else "sit_at_depot"
        )
        return evening(b, state)["delivered"]

    minimal = []
    for k in range(len(participating) + 1):
        for seq in itertools.combinations(participating, k):
            s = set(seq)
            if result(s) and not any(t <= s for t in minimal):
                minimal.append(s)

    def label(key):
        phase, role = key
        return {
            "event": f"d{n:02d}-{phase}-{role}",
            "verb": (ad if phase == "afternoon" else pm)[role]["action"],
        }

    return {
        "source": str(source),
        "sha256": sha256(source.read_bytes()).hexdigest(),
        "first_delivery_day": n,
        "what_reached_receiver": delivery["ending"]["effects"]["producer"],
        "witnessed_reply_in_next_reporter_input": heard,
        "chosen_actions_that_can_contribute": [label(k) for k in participating],
        "minimal_sufficient_sets_for_delivery": [
            [label(k) for k in sorted(s)] for s in minimal
        ],
        "individually_necessary_in_full_recorded_contribution_set": [
            label(k) for k in participating if not result(set(participating) - {k})
        ],
        "observed_next_closed_clock": delivery["ending"]["closed_clock"],
        "counterfactual_story_complete_clock": delivery["ending"][
            "story_complete_clock"
        ],
        "method": "Replay every subset of actually taken recording, delivery and transmission actions against a declared no-contribution baseline with legal alternative acts. Each listed set is sufficient and no proper subset suffices. Only the original all-actors row occurred. The reducer reports delivery and leaves the identity of the particular reel unresolved when two routes coexist. The separately simulated receipt-release clock stops at its first divergence.",
    }


if __name__ == "__main__":
    p, o = map(Path, sys.argv[1:])
    o.write_text(json.dumps(explain(p), indent=2, ensure_ascii=False) + "\n")
