"""Count the suggested stock phrases in committed words and look up physical refusals."""
from collections import Counter
import json
from pathlib import Path
import re
import unicodedata

HERE = Path(__file__).resolve().parent
NIGHT = HERE.parent
PHRASES = ("I hear you", "that's valid", "your feelings are valid", "thank you for sharing",
           "I understand how you feel", "I appreciate you sharing", "I'm sorry you feel that way")


def normalized(line):
    line = unicodedata.normalize("NFKC",line).casefold().replace("’","'").replace("‘","'")
    return " ".join(line.split())


def main():
    sources = json.loads((NIGHT/"ops/delivery-manifest.json").read_bytes())["cohorts"]
    lines = Counter()
    results = {p:[] for p in PHRASES}
    phrases = {p:re.compile(r"(?<!\w)"+re.escape(normalized(p))+r"(?!\w)") for p in PHRASES}
    assignments = Counter()
    role_slots = Counter()
    for cohort, runs in sources.items():
        for record in runs:
            take = json.loads((NIGHT/record["file"]).read_bytes())
            for event in take["events"]:
                for actor in [event,*event["cast"]]:
                    role = actor["role"]
                    line = actor["decision"]["words"]
                    text = normalized(line)
                    if text:
                        lines[role,text] += 1
                    role_slots[role] += 1
                    after = event["world_after"].get("assignments",{}).get(role,{})
                    before = event["world_before"].get("assignments",{}).get(role,{})
                    if before.get("status") == "invited":
                        assignments["opportunities"] += 1
                    if after.get("event_id") == actor["id"] and after.get("status") in ("accepted","declined"):
                        expected = {"accepted":"accept_assignment","declined":"decline_assignment"}
                        assert actor["decision"]["detail"].strip() == expected[after["status"]]
                        assignments[after["status"]] += 1
                    for phrase, regex in phrases.items():
                        if regex.search(text):
                            results[phrase].append({"file":record["file"],"actor":role,"event":actor["id"],
                                                    "raw_words":line,"cohort":cohort})
    out = {"scope":"43 main takes. Committed words may contain stage directions. Counts include exact reuses; a role/line count merges identical normalized words from the same role.",
           "phrases_fixed_before_counting":list(PHRASES),"total_actor_slots":sum(role_slots.values()),"role_slots":role_slots,
           "nonempty_line_slots":sum(lines.values()),"unique_role_line_pairs":len(lines),
           "matched_slots":{phrase:len(v) for phrase,v in results.items()},
           "unique_matched_wordings_by_phrase":{p:len({(r["actor"],normalized(r["raw_words"])) for r in rows}) for p,rows in results.items()},
           "hits":results,"verified_assignment_signals":dict(assignments),
           "limit":"A phrase match cannot determine tone, conflict, acquiescence or whether an actor held a grudge."}
    (HERE/"dialogue-audit.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    print(out["nonempty_line_slots"],out["unique_role_line_pairs"],out["matched_slots"],assignments)


if __name__ == "__main__":
    main()
