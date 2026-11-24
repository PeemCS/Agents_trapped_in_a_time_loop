#!/usr/bin/env python3
"""Prepare grounded film edits and label-blind screening packets from town traces."""

import argparse
import csv
import hashlib
import json
import random
import re
from pathlib import Path

PLACES = {"inn", "diner", "square", "studio", "depot", "Pittsburgh"}
CULTURE = re.compile(
    r"\b(?:groundhog day|phil connors|bill murray|that movie|the movie|that film|the film)\b",
    re.I,
)
RUBRIC = Path(__file__).with_name("screening-rubric.md")
RUBRIC_SHA256 = "46afe4d8f089a4e514edc011b14d24c53c3f87dcd2d1a97d9f9e858f0d966cea"


def read_trace(path):
    raw = path.read_bytes()
    data = json.loads(raw)
    if data.get("status", "complete") != "complete":
        raise ValueError(f"unfinished trajectory in {path.name}")
    events = data.get("events")
    if not isinstance(events, list) or not events:
        raise ValueError(f"{path.name} has no recorded event stream")
    for i, e in enumerate(events):
        if not all(
            key in e
            for key in (
                "day",
                "clock",
                "origin",
                "place",
                "decision",
                "effect",
                "actor",
            )
        ):
            raise ValueError(f"incomplete event {i + 1} in {path.name}")
        if e["origin"] not in PLACES or e["place"] not in PLACES:
            raise ValueError(f"unknown location in event {i + 1} of {path.name}")
        if not isinstance(e["decision"].get("action"), str):
            raise ValueError(f"missing decision at event {i + 1} of {path.name}")
    return data, hashlib.sha256(raw).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def event_id(i, e):
    return e.get("id", e.get("event_id", f"E{i + 1:03d}"))


def cast_rows(e):
    cast = e.get("cast", [])
    if isinstance(cast, dict):
        return list(cast.values())
    return cast


def decisions(e):
    yield e["actor"], e["decision"], e["effect"]
    for other in cast_rows(e):
        yield other["actor"], other["decision"], other["effect"]
    reply = e.get("other_call")
    if reply and reply.get("name") != "world referee":
        yield reply["name"], reply["decision"], ""


def ledger_row(i, e):
    return {
        "event_index": i,
        "event_id": event_id(i, e),
        "day": e["day"],
        "clock": e["clock"],
        "origin": e["origin"],
        "place": e["place"],
        "actor": e["actor"],
        "action": e["decision"]["action"],
        "words": e["decision"].get("words", ""),
        "stated_intention": e["decision"].get("intention", ""),
        "effect": e["effect"],
        "cast": [
            {
                "actor": name,
                "action": decision["action"],
                "words": decision.get("words", ""),
                "effect": effect,
            }
            for name, decision, effect in list(decisions(e))[1:]
        ],
    }


def coach_clusters(events):
    """Find a witnessed trip, followed by a later Pittsburgh moment and an observed reset."""
    for arrival, e in enumerate(events):
        if (
            e["decision"]["action"] != "take_coach_to_Pittsburgh"
            or e["place"] != "Pittsburgh"
            or e["origin"] == "Pittsburgh"
        ):
            continue
        hold = None
        for i in range(arrival + 1, len(events)):
            later = events[i]
            if later["day"] != e["day"]:
                if (
                    hold is not None
                    and later["day"] == e["day"] + 1
                    and later["origin"] == "inn"
                ):
                    yield {"arrival": arrival, "hold": hold, "wake": i}
                break
            if later["origin"] != "Pittsburgh" or later["place"] != "Pittsburgh":
                break
            hold = i


def summary(path):
    raw, digest = read_trace(path)
    es = raw["events"]
    cast = sorted({name for e in es for name, *_ in decisions(e)})
    candidates = []
    for i, e in enumerate(es):
        for name, decision, _ in decisions(e):
            words = decision.get("words", "")
            if CULTURE.search(words):
                candidates.append(
                    {"event": event_id(i, e), "actor": name, "words": words}
                )
    return {
        "source": str(path),
        "sha256": digest,
        "events": len(es),
        "decision_makers": cast,
        "coach_arrivals": sum(
            e["decision"]["action"] == "take_coach_to_Pittsburgh"
            and e["place"] == "Pittsburgh"
            for e in es
        ),
        "ready_payoffs": list(coach_clusters(es)),
        "cultural_reference_candidates_for_review": candidates,
    }


def choose_shots(events, cluster):
    # Keep two early, grounded town beats, then every beat from the bus morning through the return.
    arrival, hold, wake = (cluster[x] for x in ("arrival", "hold", "wake"))
    first_on_day = next(
        i for i, e in enumerate(events) if e["day"] == events[arrival]["day"]
    )
    indices = {0, first_on_day, arrival, hold, wake}
    bystander_idx = next(
        (i for i, e in enumerate(events[:arrival]) if len(list(decisions(e))) > 1), None
    )
    if bystander_idx is not None:
        indices.add(bystander_idx)
    depot_idx = next(
        (i for i in range(arrival - 1, -1, -1) if events[i]["place"] == "depot"), None
    )
    if depot_idx is not None:
        indices.add(depot_idx)
    indices.update(range(first_on_day, wake + 1))
    if wake + 1 < len(events):
        indices.add(wake + 1)
    # Show any independent co-stars whose first visible choice falls beyond the physical gag.
    cast_seen = {name for i in indices for name, *_ in decisions(events[i])}
    for i, e in enumerate(events):
        names = {name for name, *_ in decisions(e)}
        if names - cast_seen:
            indices.add(i)
            cast_seen.update(names)
    return sorted(indices)


def make_edl(path, cut="gag"):
    trace, digest = read_trace(path)
    events = trace["events"]
    cluster = next(coach_clusters(events), None)
    if cluster is None and cut == "gag":
        raise ValueError(
            "no observed coach arrival, city hold and next-morning inn reset in one lineage"
        )
    shots = []
    indices = (
        list(range(len(events)))
        if cut == "chronicle"
        else choose_shots(events, cluster)
    )
    for i in indices:
        e = events[i]
        # At dawn the origin exists before the first action of the next day.
        if cluster is not None and i == cluster["wake"]:
            shots.append(
                {
                    "event_index": i,
                    "event_id": event_id(i, e),
                    "view": "morning",
                    "focus": e["actor"],
                    "start": 0.22,
                    "end": 0.22,
                    "seconds": 4.5,
                    "speech": [],
                }
            )
        speech = []
        # The editor may omit lines, but cannot substitute or combine their wording.
        present = {e["actor"]}
        present.update(
            other["actor"] for other in cast_rows(e) if other["origin"] == e["origin"]
        )
        if e.get("other_call") and e["other_call"].get("name") != "world referee":
            present.add(e["other_call"]["name"])
        for name, d, _ in decisions(e):
            if name not in present:
                continue
            text = d.get("words", "").strip()
            if text and len(text.split()) <= 32 and len(speech) < 2:
                speech.append({"actor": name, "text": text})
        seconds = max(
            4.0, sum(len(q["text"].split()) / 2.55 + 0.55 for q in speech) + 0.75
        )
        if cluster is not None and i in (cluster["arrival"], cluster["hold"]):
            seconds = max(seconds, 5.0)
        # The payoff uses the action even if the reported destination in speech disagrees.
        shots.append(
            {
                "event_index": i,
                "event_id": event_id(i, e),
                "view": "action",
                "focus": e["actor"],
                "start": 0.25 if cluster is not None and i == cluster["wake"] else 0.0,
                "end": 1.0,
                "seconds": round(seconds, 2),
                "speech": speech,
            }
        )
    return {
        "format": "tuesday-edl/1",
        "source_sha256": digest,
        "actor": events[0]["actor"],
        "selection": cut,
        "purpose": "Private rehearsal of a single recorded life",
        "cluster": cluster,
        "rubric_sha256": RUBRIC_SHA256,
        "shots": shots,
    }


def verify(path, edl):
    trace, digest = read_trace(path)
    if edl.get("format") != "tuesday-edl/1" or edl.get("source_sha256") != digest:
        raise ValueError("source/format mismatch")
    if hashlib.sha256(RUBRIC.read_bytes()).hexdigest() != edl.get("rubric_sha256"):
        raise ValueError("screening protocol hash mismatch")
    es = trace["events"]
    if edl["cluster"] is not None and edl["cluster"] not in list(coach_clusters(es)):
        raise ValueError("the cut does not have its stated physical payoff")
    shots = edl["shots"]
    if not shots:
        raise ValueError("empty cut")
    last = (-1, -1)
    hero_anchors = set()
    for shot in shots:
        i = shot["event_index"]
        if type(i) is not int or not 0 <= i < len(es):
            raise ValueError("unknown slot")
        e = es[i]
        if shot["event_id"] != event_id(i, e):
            raise ValueError("invalid source event")
        view = shot["view"]
        if view not in ("morning", "action"):
            raise ValueError("unknown shot type")
        position = (i, 0 if view == "morning" else 1)
        if position <= last:
            raise ValueError("out-of-order or repeated shot")
        last = position
        if view == "morning" and (
            e["origin"] != "inn" or i and es[i - 1]["day"] == e["day"]
        ):
            raise ValueError("morning shot lacks a morning origin")
        if shot["seconds"] <= 0 or not 0 <= shot["start"] <= shot["end"] <= 1:
            raise ValueError("invalid duration or progress")
        if shot["focus"] not in [a for a, *_ in decisions(e)]:
            raise ValueError("unknown actor")
        shot_row = next(
            (r for r in [e, *cast_rows(e)] if r["actor"] == shot["focus"]), e
        )
        local = {
            r["actor"] for r in [e, *cast_rows(e)] if r["origin"] == shot_row["origin"]
        }
        if (
            e.get("other_call")
            and e["other_call"].get("name") != "world referee"
            and e["origin"] == shot_row["origin"]
        ):
            local.add(e["other_call"]["name"])
        valid = {
            (name, d.get("words", "").strip())
            for name, d, _ in decisions(e)
            if name in local
        }
        if "verified_air_sources" in shot:
            b = e.get("world_after", {}).get("bulletin") or {}
            if (
                view != "action"
                or e["clock"] != "7:00 pm"
                or b.get("source_role") != shot_row.get("role")
                or not shot["verified_air_sources"]
                or shot["verified_air_sources"] != b.get("source_ids")
                or not b.get("spoken")
                or shot["speech"] != [{"actor": shot_row["actor"], "text": b["spoken"]}]
            ):
                raise ValueError(
                    "on-air line lacks a confirmed source role, source list and exact voiced carrier"
                )
        for line in shot["speech"]:
            if (
                view == "morning"
                or not line["text"]
                or (line["actor"], line["text"]) not in valid
            ):
                raise ValueError(
                    "line lacks exact committed speaker and text in this shot"
                )
        if shot["focus"] == e["actor"]:
            if view == "action" and shot["end"] >= 0.90:
                hero_anchors.add((i, view))
            if view == "morning" and 0.19 <= shot["start"] <= shot["end"] <= 0.25:
                hero_anchors.add((i, view))
    c = edl["cluster"]
    if edl.get("selection") == "five-trips":
        expected = list(coach_clusters(es))[:5]
        if len(expected) != 5 or len(shots) != 15:
            raise ValueError("five complete trips require fifteen distinct shots")
        for n, trip in enumerate(expected, 1):
            for offset, (step, part) in enumerate(
                (
                    ("arrival", "outbound"),
                    ("hold", "in Pittsburgh"),
                    ("wake", "back at the hotel"),
                )
            ):
                s = shots[(n - 1) * 3 + offset]
                if (
                    s.get("montage_index") != n
                    or s.get("montage_part") != part
                    or s["event_index"] != trip[step]
                ):
                    raise ValueError(
                        "trip number, physical location or source order mismatch"
                    )
                if (
                    trip[step],
                    "morning" if step == "wake" else "action",
                ) not in hero_anchors:
                    raise ValueError(
                        "montage lacks an actual reporter arrival, city hold or waking view"
                    )
    if c is None and edl.get("selection") == "gag":
        raise ValueError("a coach cut needs three anchors")
    if (
        c is not None
        and not {
            (c["arrival"], "action"),
            (c["hold"], "action"),
            (c["wake"], "morning"),
        }
        <= hero_anchors
    ):
        raise ValueError("coach gag missing travel, city hold or waking frame")
    return {
        "valid": True,
        "shots": len(shots),
        "seconds": round(sum(s["seconds"] for s in shots), 2),
        "source_sha256": digest,
        "cast_with_decisions": sorted(
            {a for s in shots for a, *_ in decisions(es[s["event_index"]])}
        ),
    }


def pack(paths, dest, seed):
    if dest.exists():
        raise ValueError("use a new output directory so packets and key stay in sync")
    dest.mkdir(parents=True)
    ordered = sorted(set(paths))
    random.Random(seed).shuffle(ordered)
    key = {}
    packs = []
    for n, path in enumerate(ordered, 1):
        data, digest = read_trace(path)
        world = f"Take {n:02d}"
        key[world] = {"path": str(path), "sha256": digest}
        packs.append(
            {
                "take": world,
                "events": [ledger_row(i, e) for i, e in enumerate(data["events"])],
            }
        )
    write_json(dest / "screen.json", packs)
    write_json(dest / "key.private.json", key)


def seed_csv(paths, out):
    with out.open("w", newline="") as sink:
        writer = csv.writer(sink)
        writer.writerow(
            (
                "world",
                "slot",
                "event_id",
                "day",
                "clock",
                "actor",
                "origin",
                "place",
                "action",
                "words",
                "effect",
                "is_lead",
            )
        )
        for path in sorted(paths):
            trace, digest = read_trace(path)
            for i, e in enumerate(trace["events"]):
                writer.writerow(
                    (
                        digest,
                        i,
                        event_id(i, e),
                        e["day"],
                        e["clock"],
                        e["actor"],
                        e["origin"],
                        e["place"],
                        e["decision"]["action"],
                        e["decision"].get("words", ""),
                        e["effect"],
                        True,
                    )
                )
                for other in cast_rows(e):
                    writer.writerow(
                        (
                            digest,
                            i,
                            other.get(
                                "id",
                                other.get(
                                    "event_id", event_id(i, e) + "-" + other["actor"]
                                ),
                            ),
                            e["day"],
                            e["clock"],
                            other["actor"],
                            other["origin"],
                            other["place"],
                            other["decision"]["action"],
                            other["decision"].get("words", ""),
                            other["effect"],
                            False,
                        )
                    )
                if (
                    e.get("other_call")
                    and e["other_call"].get("name") != "world referee"
                ):
                    other = e["other_call"]
                    o = other["decision"]
                    writer.writerow(
                        (
                            digest,
                            i,
                            event_id(i, e) + "-" + other["name"],
                            e["day"],
                            e["clock"],
                            other["name"],
                            e["origin"],
                            e["origin"],
                            o["action"],
                            o.get("words", ""),
                            "",
                            False,
                        )
                    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    cmds = parser.add_subparsers(dest="cmd", required=True)
    for cmd in ("scan", "pack", "seed-csv"):
        p = cmds.add_parser(cmd)
        p.add_argument("traces", nargs="+", type=Path)
        if cmd != "scan":
            p.add_argument("--out", type=Path, required=True)
        if cmd == "pack":
            p.add_argument("--shuffle", type=int, required=True)
    for cmd in ("select", "verify"):
        p = cmds.add_parser(cmd)
        p.add_argument("trace", type=Path)
        p.add_argument("edl", type=Path)
        if cmd == "select":
            p.add_argument("--cut", choices=("gag", "chronicle"), default="gag")
    a = parser.parse_args()
    if a.cmd == "scan":
        print(json.dumps([summary(p) for p in a.traces], ensure_ascii=False, indent=2))
    elif a.cmd == "pack":
        pack(a.traces, a.out, a.shuffle)
    elif a.cmd == "seed-csv":
        seed_csv(a.traces, a.out)
    elif a.cmd == "select":
        edl = make_edl(a.trace, a.cut)
        print(json.dumps(verify(a.trace, edl)))
        write_json(a.edl, edl)
    else:
        print(json.dumps(verify(a.trace, json.loads(a.edl.read_text()))))


if __name__ == "__main__":
    main()
