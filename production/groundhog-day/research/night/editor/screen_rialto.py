#!/usr/bin/env python3
"""Compare complete 721 Rialto takes without carrying scenes or actor knowledge across them."""

import json, re, sys
from pathlib import Path
from rialto_film import verify_orig, sha, write


def screen(source):
    w = json.loads(source.read_text())
    if w["status"] != "complete":
        raise ValueError("wait for a closed take")
    moments = [
        (d["day"], phase, d[phase]["reporter"])
        for d in w["days"]
        for phase in ("afternoon", "evening")
    ] + [(len(w["days"]) + 1, "alarm", w["last_alarm"])]
    relevant = re.compile(
        r"groundhog day|the film|the movie|1993 (?:film|comedy)|bill murray|movie ending",
        re.I,
    )
    hits = []
    turns = []
    for day, phase, r in moments:
        thought, raw = verify_orig(r)
        channels = {
            "unspoken_external_output": thought,
            "raw_words_field": r["decision"]["words"],
            "stated_intention": r["decision"]["intention"],
        }
        candidate = []
        for ch, txt in channels.items():
            for m in list(relevant.finditer(txt))[:3]:
                result = {
                    "day": day,
                    "phase": phase,
                    "channel": ch,
                    "source_offset": m.start(),
                    "word": m.group(),
                    "excerpt": txt[max(0, m.start() - 60) : m.end() + 100],
                }
                hits.append(result)
                candidate.append(result)
        turns.append(
            {
                "day": day,
                "phase": phase,
                "physical_action": r["decision"]["action"],
                "possible_film_references": candidate,
                "stream": raw,
            }
        )
    return {
        "take": source.parent.name,
        "sha256": sha(source.read_bytes()),
        "seed": w["seed"],
        "condition": w["condition"],
        "carried_in_observations": w["source"]["events"],
        "reporter_cultural_match_candidates": hits,
        "reporter_decisions": turns,
        "closed_days": [
            {
                "day": d["day"],
                "afternoon_rehearsal": d["afternoon"]["reporter"]["decision"]["action"],
                "evening_action": d["evening"]["reporter"]["decision"]["action"],
                "producer_evening": d["evening"]["producer"]["decision"]["action"],
                "closed_clock": d["ending"]["closed_clock"],
                "mutual_dance": d["ending"]["dance"],
                "both_at_party": d["ending"]["both_at_party"],
                "interview_delivered": d["ending"]["delivered"],
            }
            for d in w["days"]
        ],
    }


if __name__ == "__main__":
    src = Path(sys.argv[1])
    out = Path(sys.argv[2])
    write(
        out,
        [
            screen(src / f"721-{arm}" / "take.json")
            for arm in ("uncued", "library", "hypothesis")
        ],
    )
