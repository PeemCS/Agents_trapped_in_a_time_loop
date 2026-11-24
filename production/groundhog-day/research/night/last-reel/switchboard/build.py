"""Export every legal evening at 18 recorded checkpoints from the authoritative rules."""
import hashlib
import itertools
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent
sys.path.insert(0, str(SOURCE))
from scene import ROLES, evening, options


def export_checkpoint(run_id, day):
    before = day["afternoon_state"]
    choices = {role: list(options(role, "evening", before)) for role in ROLES}
    recorded = [day["evening"][role]["decision"]["action"] for role in ROLES]
    texts = []
    references = {}

    def text_id(text):
        if text not in references:
            references[text] = len(texts)
            texts.append(text)
        return references[text]

    branches = {}
    for actions in itertools.product(*(choices[role] for role in ROLES)):
        decisions = {role: {"action": action} for role, action in zip(ROLES, actions)}
        resolved = evening(decisions, before)
        if list(actions) == recorded:
            assert resolved == day["ending"]
        branches["|".join(actions)] = [
            *(text_id(resolved["effects"][role]) for role in ROLES),
            int(resolved["delivered"]), int(resolved["dance"]), int(resolved["both_at_party"]),
            int(resolved["story_complete_clock"] == "Wednesday"),
        ]
        assert resolved["closed_clock"] == "Tuesday"
    return {
        "run": run_id, "day": day["day"], "choices": choices, "recorded": recorded,
        "afternoon": [before["effects"][r] for r in ROLES],
        "positions": [before["positions"][r] for r in ROLES],
        "texts": texts, "branches": branches,
    }


def main():
    sources = {}
    all_days = []
    for path in sorted((SOURCE / "runs").glob("*/take.json")):
        run = json.loads(path.read_bytes())
        assert run["status"] == "complete" and len(run["days"]) == 3
        name = path.parent.name
        sources[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        all_days.extend(export_checkpoint(name, day) for day in run["days"])
    assert len(all_days) == 18 and len(sources) == 6
    export = {"sources": sources, "days": all_days}
    output = json.dumps(export, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    (HERE / "replays.js").write_text("window.RIALTO_REPLAYS=" + output + ";\n")
    print(f"{len(all_days)} recorded checkpoints, {sum(len(d['branches']) for d in all_days)} legal joint evenings")


if __name__ == "__main__":
    main()
