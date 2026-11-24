"""Keep the viewer offline while retaining committed decisions and visible world state."""
import json
from pathlib import Path

here = Path(__file__).resolve().parent
research = here.parents[1]
sources = [
    ("repeating-town/runs/seed-511.json", "Ellis · first rehearsal"),
    ("repeating-town/event-memory-runs/seed-511.json", "Ellis · event memory"),
    ("night/takes/q27/film-transcript/seed-701.json", "Phil · 27B · Pittsburgh"),
    ("night/takes/q27/film-receipts/seed-701.json", "Phil · 27B · diner"),
    ("night/takes/q27/neutral-receipts/seed-701.json", "Ellis · 27B · neutral cast"),
]


def compact(row):
    event = {k: row[k] for k in (
        "id", "day", "clock", "origin", "place", "actor", "role", "decision", "effect",
        "world_before", "world_after"
    ) if k in row}
    if row.get("other_call"):
        event["other_call"] = {k: row["other_call"][k] for k in ("name", "decision")}
    if "cast" in row:
        event["cast"] = [compact(actor) for actor in row["cast"]]
    return event


traces = []
for path, label in sources:
    raw = json.loads((research / path).read_text())
    trace = {k: raw[k] for k in ("seed", "model", "source", "protagonist", "cast_names", "municipality",
                                  "memory", "cast_condition") if k in raw}
    trace.update(label=label, archive="research/" + path, events=[compact(r) for r in raw["events"]])
    trace.setdefault("source", trace["archive"])
    traces.append(trace)
(here / "traces.js").write_text("window.TOWN_TRACES = " +
    json.dumps(traces, ensure_ascii=False, separators=(",", ":")) + ";\n")
