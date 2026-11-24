#!/usr/bin/env python3
"""Locate cultural references and clock mismatches in the two committed 731 ensemble takes."""

import argparse
from pathlib import Path
import re
from edit import read_trace, write_json

PATTERNS = {
    "possible_movie_identification": r"\b(?:groundhog day|movies?|cinema|screenplay|1993|the film|film called|bill murray|murray|macdowell|harold ramis|phil connors|ned ryerson|I got you babe)\b",
    "possible_recurrence": r"(?<!\w)(?:time loop|time-loop|same day|same Tuesday|past cycles|same morning|prior runs|day repeating|repeat(?:ing|ed) Tuesday|déjà vu|deja vu|multiple [\"“]runs[”\"]|different timelines|stuck in a loop)(?!\w)",
    "possible_wrong_wednesday": r"\b(?:it.s Wednesday|today is Wednesday|Wednesday, February 3)\b",
}


def screen(paths):
    out = []
    for path in paths:
        world, digest = read_trace(path)
        events = world["events"]
        matches = []
        cache = 0
        decisions = 0
        for i, e in enumerate(events):
            for r in [e, *e["cast"]]:
                inf = r["inference"]
                decisions += 1
                cache += bool(inf.get("cache_hit"))
                accepted = next(
                    (x for x in reversed(inf["attempts"]) if x["error"] is None), None
                )
                for channel, txt in [
                    ("spoken", r["decision"]["words"]),
                    (
                        "external_unsaid",
                        accepted.get("public_thinking", "") if accepted else "",
                    ),
                ]:
                    for name, pat in PATTERNS.items():
                        for hit in re.finditer(pat, txt, re.I):
                            matches.append(
                                {
                                    "category": name,
                                    "channel": channel,
                                    "actor": r["actor"],
                                    "event_id": r["id"],
                                    "slot": i,
                                    "start": hit.start(),
                                    "end": hit.end(),
                                    "match": hit.group(),
                                    "window": txt[
                                        max(0, hit.start() - 70) : hit.end() + 90
                                    ],
                                }
                            )
        out.append(
            {
                "take": path.parent.name,
                "source_sha256": digest,
                "status": world["status"],
                "days": max(e["day"] for e in events),
                "actor_decisions": decisions,
                "cached_decisions": cache,
                "matches": matches,
            }
        )
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("paths", nargs="+", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    write_json(a.out, screen(a.paths))
