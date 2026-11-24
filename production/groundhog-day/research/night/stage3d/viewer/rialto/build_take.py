"""Project the observed physical facts of one finished Rialto take for offline screens."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NIGHT = HERE.parents[2]
SOURCE = NIGHT / "last-reel/runs/721-hypothesis/take.json"
# The reducer does not publish evening coordinates. These sets follow the committed
# physical action contracts in last-reel/scene.py. Their visual layout is editorial.
SETS = {"ballroom": "Ballroom", "depot": "Town depot", "rialto": "Rialto projection booth",
        "station": "Regional station patch", "terminal": "Pittsburgh terminal",
        "hotel": "Hearthside Hotel", "home": "Home"}
AFTERNOON = {"ballroom": "ballroom", "Pittsburgh": "terminal", "Rialto": "rialto"}
EVENING = {"go_dancing": "ballroom", "sit_at_depot": "depot", "go_home": "home",
           "transmit_interview": "station", "deliver_reel": "station", "sleep_at_terminal": "terminal"}
CUT = [
    (1, "afternoon", "reporter", "piano", "The last eight bars", 6),
    (1, "evening", "reporter", "bench", "The empty bench", 5),
    (1, "evening", "producer", "dance", "Meanwhile, at the ballroom", 5),
    (2, "afternoon", "reporter", "coach", "The paid coach", 4),
    (2, "afternoon", "producer", "interview", "The projectionist", 6),
    (2, "evening", "reporter", "sleep", "The terminal bench", 5),
    (2, "evening", "camera", "reel", "The second recording", 4.5),
    (2, "evening", "producer", "line", "The regional line", 5),
    (3, "afternoon", "reporter", "receipt", "The reply", 7),
]


def build():
    raw = SOURCE.read_bytes()
    run = json.loads(raw)
    assert run["condition"] == "hypothesis" and run["seed"] == 721 and run["status"] == "complete"
    assert run["days"][0]["ending"]["dance"] is False and run["days"][0]["ending"]["both_at_party"] is False
    previous = run["days"][1]["ending"]
    assert previous["delivered"] and previous["camera_delivery"] and previous["closed_clock"] == "Tuesday"
    shots = []
    for day_number, phase, role, kind, title, seconds in CUT:
        day = run["days"][day_number - 1]
        tick = day[phase]
        call = tick[role]
        state = day["afternoon_state"] if phase == "afternoon" else day["ending"]
        if phase == "afternoon":
            places = {r: AFTERNOON[k] for r,k in state["positions"].items()}
        else:
            places = {r: EVENING[e["decision"]["action"]] for r,e in tick.items()}
        crew = {r: {"actor": e["speaker"], "location": places[r], "action": e["decision"]["action"],
                    "effect": state["effects"][r], "key": e["key"], "id": f"d{day_number:02}-{phase}-{r}"}
                for r,e in tick.items()}
        shot = {"id": f"d{day_number:02}-{phase}-{role}", "key": call["key"], "kind": kind,
                "title": title, "day": day_number, "phase": phase, "role": role, "set": places[role],
                "seconds": seconds, "effect": state["effects"][role], "action": call["decision"]["action"],
                "crew": crew, "speaker": call["speaker"]}
        if kind == "receipt":
            observation = next(json.loads(m["content"])["what_you_observe"] for m in call["messages"] if m["role"] == "user")
            line = next(x for x in observation if x.startswith("An envelope has arrived from Pittsburgh."))
            assert "Six am in the Hearthside Hotel" in observation[0] and line.endswith("'I know that voice. Play it again.'")
            # This beat predates the afternoon action in the same call. It has no generated action.
            shot.update(set="hotel", phase="dawn", role="world", speaker="Hotel post",
                        effect=line, action=None, receipt=line.split("reply: '",1)[1][:-1], dayClock=previous["closed_clock"],
                        origin="what_you_observe", crew={})
        assert len(shot["key"]) == 64
        shots.append(shot)
    return {"title": "Eight bars", "run": "721-hypothesis", "source": "last-reel/runs/721-hypothesis/take.json",
            "sha256": hashlib.sha256(raw).hexdigest(), "condition": run["condition"], "sets": SETS,
            "suppliedTheory": True, "shots": shots}


if __name__ == "__main__":
    take=build()
    (HERE / "take.js").write_text("window.RialtoTake = " + json.dumps(take, ensure_ascii=False, separators=(",",":"))+";\n")
    print(f"{len(take['shots'])} shots from {take['sha256']}")
